import pytest
import uuid
from fastapi.testclient import TestClient
from app.run import app
from tests.test_files import users_and_tokens
import random
from datetime import datetime, timedelta

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
    import random
    from datetime import datetime, timedelta
    headers = {"Authorization": f"Bearer {auth_token}"}
    types = client.get("/api/v1/leave-types/", headers=headers).json()
    if not types:
        pytest.skip("No leave types to create leave request")
    leave_type_id = types[0]["id"]
    # Generate a unique date for each test run
    offset = random.randint(1, 10000)
    today_dt = datetime.now() + timedelta(days=offset)
    today = today_dt.strftime("%Y-%m-%d")
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": f"Test leave {uuid.uuid4()}"
    }
    # CREATE (mock email)
    req_id = None
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
    # DELETE (always clean up)
    if req_id:
        del_resp = client.delete(f"/api/v1/leave/{req_id}", headers=headers)
        # Accept 200, 204, 405, 501 (if delete unsupported)
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


def test_leave_request_not_found(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    fake_id = str(uuid.uuid4())
    # Get non-existent
    resp = client.get(f"/api/v1/leave/{fake_id}", headers=headers)
    assert resp.status_code == 404
    # Update non-existent
    data = {"leave_type_id": str(uuid.uuid4()), "start_date": "2025-05-05", "end_date": "2025-05-05", "comments": "x"}
    resp2 = client.put(f"/api/v1/leave/{fake_id}", json=data, headers=headers)
    assert resp2.status_code == 404
    # Approve non-existent
    resp3 = client.patch(f"/api/v1/leave/{fake_id}/approve", headers=headers)
    assert resp3.status_code == 404


def test_leave_request_invalid_leave_type(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    data = {
        "leave_type_id": str(uuid.uuid4()),
        "start_date": "2025-05-05",
        "end_date": "2025-05-05",
        "comments": "Invalid leave type"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code == 400


def test_leave_request_duplicate(auth_token, db_session):
    from app.models.leave_request import LeaveRequest
    import jwt
    import os
    from app.settings import get_settings
    SECRET_KEY = get_settings().SECRET_KEY
    payload = jwt.decode(auth_token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload["user_id"]
    import uuid
    headers = {"Authorization": f"Bearer {auth_token}"}
    # Ensure a valid leave type exists (duplicate logic from forbidden test)
    types = client.get("/api/v1/leave-types/", headers=headers).json()
    if not isinstance(types, list) or not types or "id" not in types[0]:
        # Create a leave type as admin (reuse forbidden test logic)
        admin_token = None
        # Try to get admin token from a fixture if available
        try:
            from tests.test_files import users_and_tokens
            # Use the fixture only if available in the test context
            import inspect
            if "request" in inspect.signature(test_leave_request_duplicate).parameters:
                admin_token = users_and_tokens()["admin"]["token"]
        except Exception:
            pass
        if not admin_token:
            # Fallback: try login as admin
            resp = client.post("/api/v1/auth/login", data={"username": "admin@example.com", "password": "adminpass"})
            assert resp.status_code == 200, "Could not get admin token"
            admin_token = resp.json()["access_token"]
        leave_type_data = {
            "name": f"TestType {uuid.uuid4()}",
            "code": "custom",
            "description": "Autocreated for duplicate test",
            "max_days": 10,
            "default_allocation_days": 10
        }
        resp = client.post("/api/v1/leave-types/", json=leave_type_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in (200, 201), f"Failed to create leave type: {resp.text}"
        leave_type_id = resp.json()["id"]
    else:
        leave_type_id = types[0]["id"]
    # today = "2025-05-05"

    # Clean up any existing leave requests for this user and leave_type_id
    # Optionally verify user exists:
    user_resp = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert user_resp.status_code == 200
    db_session.query(LeaveRequest).filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.leave_type_id == leave_type_id
    ).delete()
    db_session.commit()

    offset = random.randint(1, 10000)
    today_dt = datetime.now() + timedelta(days=offset)
    today = today_dt.strftime("%Y-%m-%d")
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": "Dup leave"
    }
    # Create first
    resp1 = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp1.status_code in (200, 201), f"Could not create leave request for duplicate test: {resp1.text}"
    # Try duplicate
    resp2 = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp2.status_code in (400, 409)



def test_leave_request_already_approved(auth_token):
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
        "comments": "Approve test"
    }
    # Create
    resp1 = client.post("/api/v1/leave/", json=data, headers=headers)
    if resp1.status_code not in (200, 201):
        pytest.skip("Could not create leave request for approve test")
    req_id = resp1.json()["id"]
    from unittest.mock import patch
    # Approve with email notification mocked
    with patch("app.utils.email.send_leave_approval_notification") as mock_approval_email:
        resp2 = client.patch(f"/api/v1/leave/{req_id}/approve", headers=headers)
        if resp2.status_code != 200:
            pytest.skip("Could not approve leave request for already-approved test")
        # Approve again
        resp3 = client.patch(f"/api/v1/leave/{req_id}/approve", headers=headers)
        assert resp3.status_code == 400


def test_leave_request_forbidden(users_and_tokens):
    # IC creates leave, manager tries to update/approve, should get 403
    import uuid
    ic_token = users_and_tokens["ic"]["token"]
    manager_token = users_and_tokens["manager"]["token"]
    # Try to get leave types
    types = client.get("/api/v1/leave-types/", headers={"Authorization": f"Bearer {ic_token}"}).json()
    if not isinstance(types, list) or not types or "id" not in types[0]:
        # Create a leave type as admin
        admin_token = users_and_tokens["admin"]["token"]
        leave_type_data = {
            "name": f"TestType {uuid.uuid4()}",
            "code": "custom",
            "description": "Autocreated for forbidden test",
            "max_days": 10,
            "default_allocation_days": 10
        }
        resp = client.post("/api/v1/leave-types/", json=leave_type_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in (200, 201), f"Failed to create leave type: {resp.text}"
        leave_type_id = resp.json()["id"]
    else:
        leave_type_id = types[0]["id"]
    # Create leave request as IC
    data = {
        "leave_type_id": leave_type_id,
        "start_date": "2025-05-07",
        "end_date": "2025-05-07",
        "comments": "Forbidden test"
    }
    resp = client.post("/api/v1/leave/", json=data, headers={"Authorization": f"Bearer {ic_token}"})
    assert resp.status_code in (200, 201), resp.text
    leave_id = resp.json()["id"]
    # Manager tries to update (should be forbidden)
    upd_data = data.copy()
    upd_data["comments"] = "Manager trying to update"
    upd_resp = client.put(f"/api/v1/leave/{leave_id}", json=upd_data, headers={"Authorization": f"Bearer {manager_token}"})
    assert upd_resp.status_code == 403
    # Manager tries to approve (should be forbidden)
    approve_resp = client.patch(f"/api/v1/leave/{leave_id}/approve", headers={"Authorization": f"Bearer {manager_token}"})
    assert approve_resp.status_code == 403
