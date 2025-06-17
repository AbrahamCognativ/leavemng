import pytest
import random
import uuid
from fastapi.testclient import TestClient
from app.run import app
from .test_utils import (
    create_auth_headers,
    login_user,
    permissions_helper,
    assert_response_success,
    assert_response_validation_error,
    generic_update_request_helper
)

client = TestClient(app)


@pytest.fixture
def auth_token():
    return login_user("user@example.com", "secret123")


def test_leave_policy_permissions():
    endpoints = [
        ('post', '/api/v1/leave-policy', {}),
        ('put', '/api/v1/leave-policy/fake-id', {}),
        ('delete', '/api/v1/leave-policy/fake-id', {})
    ]
    permissions_helper(endpoints)


def test_leave_policy_crud(auth_token):
    headers = create_auth_headers(auth_token)
    orgs = client.get("/api/v1/org/", headers=headers).json()
    types = client.get("/api/v1/leave-types/", headers=headers).json()
    if not orgs or not types:
        pytest.skip("No orgs or leave types available")
    org_unit_id = orgs[0]["id"]
    leave_type_id = types[0]["id"]
    data = {
        "org_unit_id": org_unit_id,
        "leave_type_id": leave_type_id,
        "allocation_days_per_year": random.randint(5, 30),
        "accrual_frequency": "monthly",
        "accrual_amount_per_period": 1.0
    }
    # CREATE
    resp = client.post("/api/v1/leave-policy", json=data, headers=headers)
    assert_response_success(resp, [200, 201])
    policy = resp.json()
    policy_id = policy["id"]
    assert policy["org_unit_id"] == org_unit_id
    assert policy["leave_type_id"] == leave_type_id
    # READ
    get_resp = client.get(f"/api/v1/leave-policy", headers=headers)
    assert_response_success(get_resp)
    found = any(p["id"] == policy_id for p in get_resp.json())
    assert found
    # UPDATE (if supported)
    upd_data = data.copy()
    upd_data["allocation_days_per_year"] = 99
    upd_data["accrual_amount_per_period"] = 2.0
    upd_resp, upd_json = generic_update_request_helper(
        f"/api/v1/leave-policy/{policy_id}",
        upd_data,
        headers)
    if upd_json:
        assert upd_json["allocation_days_per_year"] == 99
        assert upd_json["accrual_amount_per_period"] == 2.0
    # DELETE (if supported)
    del_resp = client.delete(
        f"/api/v1/leave-policy/{policy_id}",
        headers=headers)
    if del_resp.status_code not in (200, 204, 405, 501):
        assert_response_success(del_resp)
    # Ensure deleted (if implemented)
    if del_resp.status_code in (200, 204):
        get_after_del = client.get(
            f"/api/v1/leave-policy/{policy_id}",
            headers=headers)
        assert get_after_del.status_code in (404, 410)


def test_leave_policy_validation(auth_token):
    headers = create_auth_headers(auth_token)
    data = {
        "leave_type_id": str(uuid.uuid4()),
        "allocation_days_per_year": 10,
        "accrual_frequency": "monthly",
        "accrual_amount_per_period": 1.0
    }
    resp = client.post("/api/v1/leave-policy", json=data, headers=headers)
    assert_response_validation_error(resp)
