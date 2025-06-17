import pytest
import random
from fastapi.testclient import TestClient
from app.run import app
from .test_utils import (
    create_auth_headers,
    login_user,
    permissions_helper,
    assert_response_success,
    assert_response_validation_error,
    assert_response_bad_request
)

client = TestClient(app)


@pytest.fixture
def auth_token():
    return login_user("user@example.com", "secret123")


def test_leave_type_permissions():
    endpoints = [
        ('post', '/api/v1/leave-types/', {}),
        ('put', '/api/v1/leave-types/fake-id', {}),
        ('delete', '/api/v1/leave-types/fake-id', {})
    ]
    permissions_helper(endpoints)


def test_leave_type_crud(auth_token):
    headers = create_auth_headers(auth_token)
    code = f"custom_{random.randint(1000, 9999)}"
    data = {
        "code": "custom",
        "description": f"Custom Leave {code}",
        "default_allocation_days": 5
    }
    # CREATE
    resp = client.post("/api/v1/leave-types/", json=data, headers=headers)
    assert_response_success(resp, [200, 201])
    leave_type = resp.json()
    lt_id = leave_type["id"]
    assert leave_type["code"] == data["code"]
    assert leave_type["description"] == data["description"]
    # READ
    get_resp = client.get(f"/api/v1/leave-types/{lt_id}", headers=headers)
    assert_response_success(get_resp)
    get_json = get_resp.json()
    assert get_json["id"] == lt_id
    # UPDATE
    upd_data = data.copy()
    upd_data["description"] = f"Updated Custom Leave {code}"
    upd_resp = client.put(
        f"/api/v1/leave-types/{lt_id}",
        json=upd_data,
        headers=headers)
    assert_response_success(upd_resp)
    upd_json = upd_resp.json()
    assert upd_json["description"] == upd_data["description"]
    # DELETE
    del_resp = client.delete(f"/api/v1/leave-types/{lt_id}", headers=headers)
    assert_response_success(del_resp, [200, 204])
    # Ensure deleted
    get_after_del = client.get(f"/api/v1/leave-types/{lt_id}", headers=headers)
    assert get_after_del.status_code in (404, 410)


def test_leave_type_validation(auth_token):
    headers = create_auth_headers(auth_token)
    # Missing required fields
    data = {"description": "Invalid Leave Type"}
    resp = client.post("/api/v1/leave-types/", json=data, headers=headers)
    assert_response_validation_error(resp)


def test_leave_type_duplicate(auth_token):
    headers = create_auth_headers(auth_token)
    code = f"dup_{random.randint(1000, 9999)}"
    data = {
        "code": code,
        "description": f"Duplicate Test {code}",
        "default_allocation_days": 5
    }
    # First creation should succeed
    resp1 = client.post("/api/v1/leave-types/", json=data, headers=headers)
    assert_response_success(resp1, [200, 201])
    lt_id = resp1.json()["id"]
    # Second creation with same code should fail
    resp2 = client.post("/api/v1/leave-types/", json=data, headers=headers)
    assert_response_bad_request(resp2)
    # Cleanup
    client.delete(f"/api/v1/leave-types/{lt_id}", headers=headers)
