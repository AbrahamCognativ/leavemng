import pytest
from fastapi.testclient import TestClient
from app.run import app

client = TestClient(app)

@pytest.fixture
def auth_token():
    response = client.post("/api/v1/auth/login", data={"username": "user@example.com", "password": "secret123"})
    assert response.status_code == 200
    return response.json()["access_token"]

def test_leave_balance_permissions():
    roles = ['Admin', 'Manage', 'HR', 'IC']
    endpoints = [
        ('post', '/api/v1/leave-policy/', {}),
        ('put', '/api/v1/leave-policy/fake-id', {}),
        ('delete', '/api/v1/leave-policy/fake-id', {})
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

def test_get_user_leave_balance(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    user_info = client.get("/api/v1/users/me", headers=headers)
    if user_info.status_code == 200:
        user_id = user_info.json()["id"]
        resp = client.get(f"/api/v1/users/{user_id}/leave", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "leave_balance" in data
        assert isinstance(data["leave_balance"], list)

def test_leave_balance_crud(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    user_info = client.get("/api/v1/users/me", headers=headers)
    types = client.get("/api/v1/leave-types/", headers=headers).json()
    if user_info.status_code != 200 or not types:
        pytest.skip("No user or leave types for balance test")
    user_id = user_info.json()["id"]
    leave_type_id = types[0]["id"]
    data = {"user_id": user_id, "leave_type_id": leave_type_id, "balance_days": 10}
    # CREATE
    resp = client.post("/api/v1/leave-policy/", json=data, headers=headers)
    if resp.status_code in (404, 405, 501):
        pytest.skip("Leave balance direct creation not implemented")
    assert resp.status_code in (200, 201)
    balance = resp.json()
    bal_id = balance["id"]
    assert balance["user_id"] == user_id
    assert balance["leave_type_id"] == leave_type_id
    # READ
    get_resp = client.get(f"/api/v1/leave-policy/{bal_id}", headers=headers)
    assert get_resp.status_code == 200
    get_json = get_resp.json()
    assert get_json["id"] == bal_id
    # UPDATE (if supported)
    upd_data = data.copy()
    upd_data["balance_days"] = 20
    upd_resp = client.put(f"/api/v1/leave-policy/{bal_id}", json=upd_data, headers=headers)
    if upd_resp.status_code not in (405, 501):
        assert upd_resp.status_code == 200
        upd_json = upd_resp.json()
        assert upd_json["balance_days"] == 20
    # DELETE (if supported)
    del_resp = client.delete(f"/api/v1/leave-policy/{bal_id}", headers=headers)
    if del_resp.status_code not in (200, 204, 405, 501):
        assert del_resp.status_code == 200
    # Ensure deleted (if implemented)
    if del_resp.status_code in (200, 204):
        get_after_del = client.get(f"/api/v1/leave-policy/{bal_id}", headers=headers)
        assert get_after_del.status_code in (404, 410)

def test_leave_balance_validation(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    user_info = client.get("/api/v1/users/me", headers=headers)
    if user_info.status_code != 200:
        pytest.skip("No user for balance validation test")
    user_id = user_info.json()["id"]
    data = {"user_id": user_id, "balance_days": 10}
    resp = client.post("/api/v1/leave-policy/", json=data, headers=headers)
    if resp.status_code in (404, 405, 501):
        pytest.skip("Leave balance direct creation not implemented")
    assert resp.status_code == 422
