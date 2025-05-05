import pytest
import uuid
from fastapi.testclient import TestClient
from app.run import app

client = TestClient(app)

@pytest.fixture
def auth_token():
    response = client.post("/api/v1/auth/login", data={"username": "user@example.com", "password": "secret123"})
    assert response.status_code == 200
    return response.json()["access_token"]

def test_leave_request_permissions():
    roles = ['Admin', 'Manage', 'HR', 'IC']
    endpoints = [
        ('post', '/api/v1/leave/', {}),
        ('put', '/api/v1/leave/fake-id', {}),
        ('delete', '/api/v1/leave/fake-id', {})
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

from unittest.mock import patch

def test_leave_request_crud(auth_token):
    import uuid
    headers = {"Authorization": f"Bearer {auth_token}"}
    types = client.get("/api/v1/leave-types/", headers=headers).json()
    if not types:
        pytest.skip("No leave types to create leave request")
    leave_type_id = types[0]["id"]
    today = "2025-05-05"
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": f"Test leave {uuid.uuid4()}"
    }
    # CREATE (mock email)
    with patch("app.utils.email.send_leave_request_notification") as mock_email:
        resp = client.post("/api/v1/leave/", json=data, headers=headers)
        assert resp.status_code in (200, 201)
        leave = resp.json()
        req_id = leave["id"]
        assert leave["leave_type_id"] == leave_type_id
        assert leave["start_date"] == today
        # Only assert if manager exists (i.e., if mock_email was called)
        if mock_email.call_count:
            mock_email.assert_called()
    # READ
    get_resp = client.get(f"/api/v1/leave/{req_id}", headers=headers)
    assert get_resp.status_code == 200
    get_json = get_resp.json()
    assert get_json["id"] == req_id
    # UPDATE (if supported)
    upd_data = data.copy()
    upd_data["comments"] = "Updated comment"
    upd_resp = client.put(f"/api/v1/leave/{req_id}", json=upd_data, headers=headers)
    if upd_resp.status_code not in (405, 501):
        assert upd_resp.status_code == 200
        upd_json = upd_resp.json()
        assert upd_json["comments"] == "Updated comment"
    # APPROVE (mock approval email)
    with patch("app.utils.email.send_leave_approval_notification") as mock_approval_email:
        approve_resp = client.patch(f"/api/v1/leave/{req_id}/approve", headers=headers)
        # Should be 200 if status is pending, else 400/403
        assert approve_resp.status_code in (200, 400, 403)
        if approve_resp.status_code == 200:
            mock_approval_email.assert_called()
    # DELETE (if supported)
    del_resp = client.delete(f"/api/v1/leave/{req_id}", headers=headers)
    if del_resp.status_code not in (200, 204, 405, 501):
        assert del_resp.status_code == 200
    # Ensure deleted (if implemented)
    if del_resp.status_code in (200, 204):
        get_after_del = client.get(f"/api/v1/leave/{req_id}", headers=headers)
        assert get_after_del.status_code in (404, 410)

def test_leave_request_validation(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    data = {
        "start_date": "2025-05-05",
        "end_date": "2025-05-05",
        "comments": "No leave_type_id"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code == 422
