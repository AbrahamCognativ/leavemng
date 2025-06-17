import pytest
import uuid
from fastapi.testclient import TestClient
from app.run import app
from .test_utils import (
    create_auth_headers,
    login_user,
    permissions_helper,
    assert_response_success,
    assert_response_validation_error
)

client = TestClient(app)


@pytest.fixture
def auth_token():
    return login_user("user@example.com", "secret123")


def test_org_permissions():
    endpoints = [
        ('post', '/api/v1/org/', {}),
        ('put', '/api/v1/org/fake-id', {}),
        ('delete', '/api/v1/org/fake-id', {})
    ]
    permissions_helper(endpoints)


def test_create_org_unit_crud(auth_token):
    unique_name = f"TestDept-{uuid.uuid4()}"
    data = {"name": unique_name, "parent_unit_id": None}
    headers = create_auth_headers(auth_token)
    # CREATE
    resp = client.post("/api/v1/org/", json=data, headers=headers)
    assert_response_success(resp, [200, 201])
    org_unit = resp.json()
    org_id = org_unit["id"]
    assert org_unit["name"] == data["name"]
    # READ
    get_resp = client.get(f"/api/v1/org/{org_id}", headers=headers)
    assert_response_success(get_resp)
    get_data = get_resp.json()
    assert get_data["id"] == org_id
    # UPDATE
    update_data = {"name": unique_name + "-Updated", "parent_unit_id": None}
    upd_resp = client.put(
        f"/api/v1/org/{org_id}",
        json=update_data,
        headers=headers)
    assert_response_success(upd_resp)
    upd_data = upd_resp.json()
    assert upd_data["name"] == update_data["name"]
    # DELETE (if supported)
    del_resp = client.delete(f"/api/v1/org/{org_id}", headers=headers)
    if del_resp.status_code not in (200, 204, 405, 501):
        assert_response_success(del_resp)
    # Ensure deleted (if implemented)
    if del_resp.status_code in (200, 204):
        get_after_del = client.get(f"/api/v1/org/{org_id}", headers=headers)
        assert get_after_del.status_code in (404, 410)


def test_create_org_unit_validation(auth_token):
    headers = create_auth_headers(auth_token)
    data = {}  # No name provided
    resp = client.post("/api/v1/org/", json=data, headers=headers)
    assert_response_validation_error(resp)
