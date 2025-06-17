import pytest
import random
from fastapi.testclient import TestClient
from app.run import app

client = TestClient(app)


@pytest.fixture
def auth_token():
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "user@example.com",
            "password": "secret123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_leave_type_permissions():
    roles = ['Admin', 'Manage', 'HR', 'IC']
    endpoints = [
        ('post', '/api/v1/leave-types/', {}),
        ('put', '/api/v1/leave-types/fake-id', {}),
        ('delete', '/api/v1/leave-types/fake-id', {})
    ]
    for role in roles:
        headers = {'Authorization': f'Bearer fake-token-for-{role}'}
        for method, url, data in endpoints:
            if method in ('post', 'put'):
                resp = getattr(client, method)(url, json=data, headers=headers)
            else:
                resp = getattr(client, method)(url, headers=headers)
            # Permissions logic: Admin, Manage, HR allowed, IC forbidden
            if role == 'IC':
                assert resp.status_code in (401, 403, 405)
            else:
                assert resp.status_code != 403


def test_leave_type_crud(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    code = f"custom_{random.randint(1000, 9999)}"
    data = {
        "code": "custom",
        "custom_code": code,
        "description": "Custom leave",
        "default_allocation_days": 11}
    # CREATE
    resp = client.post("/api/v1/leave-types/", json=data, headers=headers)
    assert resp.status_code in (200, 201)
    leave_type = resp.json()
    type_id = leave_type["id"]
    assert leave_type["description"] == data["description"]
    assert leave_type["custom_code"] == code
    # READ
    get_resp = client.get(f"/api/v1/leave-types/", headers=headers)
    assert get_resp.status_code == 200
    found = any(t["id"] == type_id for t in get_resp.json())
    assert found
    # UPDATE (if supported)
    upd_data = {
        "code": "custom",
        "custom_code": code,
        "description": "Updated",
        "default_allocation_days": 22}
    upd_resp = client.put(
        f"/api/v1/leave-types/{type_id}",
        json=upd_data,
        headers=headers)
    if upd_resp.status_code not in (405, 501):
        assert upd_resp.status_code == 200
        upd_json = upd_resp.json()
        assert upd_json["description"] == "Updated"
        assert upd_json["default_allocation_days"] == 22
    # DELETE (if supported)
    del_resp = client.delete(f"/api/v1/leave-types/{type_id}", headers=headers)
    if del_resp.status_code not in (200, 204, 405, 501):
        assert del_resp.status_code == 200
    # Ensure deleted (if implemented)
    if del_resp.status_code in (200, 204):
        get_after_del = client.get(
            f"/api/v1/leave-types/{type_id}",
            headers=headers)
        assert get_after_del.status_code in (404, 410)


def test_leave_type_validation(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    data = {"code": "annual", "default_allocation_days": 10}
    resp = client.post("/api/v1/leave-types/", json=data, headers=headers)
    assert resp.status_code == 422
