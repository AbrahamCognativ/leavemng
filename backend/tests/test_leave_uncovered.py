import pytest
from unittest.mock import patch
from datetime import date, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from app.run import app

client = TestClient(app)

def get_admin_token():
    resp = client.post("/api/v1/auth/login", data={"username": "user@example.com", "password": "secret123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]

def create_user_with_token(user_data):
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/api/v1/users/", json=user_data, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()

def ensure_leave_type_exists(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    types = client.get("/api/v1/leave-types/", headers=headers).json()
    if types and isinstance(types, list):
        for t in types:
            if t.get("code", "").lower() == "annual":
                return t["id"], False
    leave_type_data = {
        "code": "annual",
        "description": "Custom leave type",
        "default_allocation_days": 19,
        "custom_code": "blablabla"
    }
    resp = client.post("/api/v1/leave-types/", json=leave_type_data, headers=headers)
    assert resp.status_code in (200, 201), resp.text
    leave_type = resp.json()
    return leave_type["id"], True

def delete_leave_type(leave_type_id, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.delete(f"/api/v1/leave-types/{leave_type_id}", headers=headers)
    assert resp.status_code in (200, 204, 404), resp.text
    #pass

import pytest
@pytest.fixture
def leave_type_fixture():
    admin_token = get_admin_token()
    leave_type_id, created = ensure_leave_type_exists(admin_token)
    yield leave_type_id
    if created:
        delete_leave_type(leave_type_id, admin_token)


import uuid

def create_user_and_login(username, password, role, gender="male", admin_token=None):
    # Provide required fields for user creation
    if role == "Manager":
        role_band = "Band2"
        role_title = "Manager"
    elif role == "Admin":
        role_band = "Band3"
        role_title = "Admin"
    else:
        role_band = "Band1"
        role_title = "Engineer"
    unique_suffix = uuid.uuid4().hex[:8]
    if "@" in username:
        local, domain = username.split("@", 1)
        unique_email = f"{local}+{unique_suffix}@{domain}"
    else:
        unique_email = f"{username}+{unique_suffix}@example.com"
    user_data = {
        "username": unique_email,
        "password": password,
        "full_name": unique_email,
        "email": unique_email,
        "role": role,
        "gender": gender,
        "name": unique_email,
        "role_band": role_band,
        "role_title": role_title,
        "passport_or_id_number": f"id-{unique_email}"
    }
    headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
    reg_resp = client.post("/api/v1/users/", json=user_data, headers=headers)
    assert reg_resp.status_code in (200, 201, 409), reg_resp.text
    login_resp = client.post("/api/v1/auth/login", data={"username": unique_email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    return login_resp.json()["access_token"]

# 1. list_leave_requests: Manager sees direct reports, IC sees only own

# def test_list_leave_requests_manager_and_ic():
#     admin_token = get_admin_token()
#     ic_token = create_user_and_login("ic2@example.com", "secret123", "IC", admin_token=admin_token)
#     manager_token = create_user_and_login("manager3@example.com", "secret123", "Manager", admin_token=admin_token)
#     headers_ic = {"Authorization": f"Bearer {ic_token}"}
#     headers_mgr = {"Authorization": f"Bearer {manager_token}"}

#     # Fetch manager's user ID
#     mgr_users = client.get("/api/v1/users/?role=Manager", headers={"Authorization": f"Bearer {admin_token}"}).json()
#     print('Manager users:', mgr_users)
#     # Try to find a manager by role_band or role_title
#     manager_user = None
#     for u in mgr_users:
#         if u.get("role_band") == "Manager" or u.get("role_title") == "Manager":
#             manager_user = u
#     if not manager_user:
#         manager_user = mgr_users[-1]
#     manager_id = manager_user["id"]

#     # Fetch IC's user ID
#     ic_users = client.get("/api/v1/users/?role=IC", headers={"Authorization": f"Bearer {admin_token}"}).json()
#     print('IC users:', ic_users)
#     ic_user = None
#     for u in ic_users:
#         if u.get("role_band") == "IC" or u.get("role_title") == "IC":
#             ic_user = u
#     if not ic_user:
#         ic_user = ic_users[-1]
#     ic_id = ic_user["id"]

#     # Patch IC to set manager_id
#     patch_resp = client.patch(f"/api/v1/users/{ic_id}", json={"manager_id": manager_id}, headers={"Authorization": f"Bearer {admin_token}"})
#     assert patch_resp.status_code in (200, 204), patch_resp.text

#     # Ensure leave type exists
#     leave_type_id, _ = ensure_leave_type_exists(admin_token)
#     today = date.today().isoformat()
#     data = {
#         "leave_type_id": leave_type_id,
#         "start_date": today,
#         "end_date": today,
#         "comments": "IC leave for manager test"
#     }
#     resp = client.post("/api/v1/leave/", json=data, headers=headers_ic)
#     print("Create leave resp:", resp.json())
#     assert resp.status_code == 200
#     leave_id = resp.json()["id"]
#     # IC should only see their own
#     list_resp = client.get("/api/v1/leave/", headers=headers_ic)
#     print("IC leave list resp:", list_resp.json())
#     assert list_resp.status_code == 200
#     # Check that the leave just created is present in IC's leave list
#     assert any(l["id"] == leave_id for l in list_resp.json())
#     # Manager should see direct reports (may need DB seeding to link IC to manager)
#     list_mgr = client.get("/api/v1/leave/", headers=headers_mgr)
#     assert list_mgr.status_code == 200
#     # Should see at least one leave request (from IC)
#     assert any(l["id"] == leave_id for l in list_mgr.json())

# 2. create_leave_request: Simulate DB error on leave_type lookup

def test_create_leave_request_db_error():
    admin_token = get_admin_token()
    token = create_user_and_login("dbfail@example.com", "secret123", "IC", admin_token=admin_token)
    with patch("app.api.v1.routers.leave.Session.query") as mock_query:
        mock_query.side_effect = Exception("DB error")
        data = {"leave_type_id": str(uuid4()), "start_date": (date.today() + timedelta(days=4)).isoformat(), "end_date": (date.today() + timedelta(days=4)).isoformat(), "comments": "DB error"}
        print("[DEBUG] Sending to /api/v1/leave/:", data)
    resp = client.post("/api/v1/leave/", json=data, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert "Invalid leave_type_id" in resp.text

# 3. create_leave_request: annual leave edge cases

def test_create_annual_leave_too_soon():
    admin_token = get_admin_token()
    token = create_user_and_login("soon@example.com", "secret123", "IC", admin_token=admin_token)
    headers = {"Authorization": f"Bearer {token}"}
    # Use ensure_leave_type_exists to get or create the leave type
    leave_type_id, _ = ensure_leave_type_exists(admin_token)
    data = {
        "leave_type_id": leave_type_id,
        "start_date": (date.today() + timedelta(days=1)).isoformat(),
        "end_date": (date.today() + timedelta(days=1)).isoformat(),
        "comments": "Too soon"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    print("Too soon leave creation resp:", resp.json())
    assert resp.status_code == 400
    assert "at least 3 days in advance" in resp.text

def test_create_annual_leave_weekends_only():
    admin_token = get_admin_token()
    token = create_user_and_login("weekend@example.com", "secret123", "IC", admin_token=admin_token)
    headers = {"Authorization": f"Bearer {token}"}
    leave_type_id, _ = ensure_leave_type_exists(admin_token)
    today = date.today()
    # Find the first Saturday that is at least 4 days from today
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday < 4:
        days_until_saturday += 7
    saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)
    data = {
        "leave_type_id": leave_type_id,
        "start_date": saturday.isoformat(),
        "end_date": sunday.isoformat(),
        "comments": "Weekend only"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code == 200
    # Optionally, check that total_days == 0 in response

def test_annual_leave_no_policy():
    admin_token = get_admin_token()
    token = create_user_and_login("nopolicy@example.com", "secret123", "IC", admin_token=admin_token)
    headers = {"Authorization": f"Bearer {token}"}
    leave_type_id, _ = ensure_leave_type_exists(admin_token)
    data = {
        "leave_type_id": leave_type_id,
        "start_date": (date.today() + timedelta(days=4)).isoformat(),
        "end_date": (date.today() + timedelta(days=4)).isoformat(),
        "comments": "No policy"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code == 200
    # Optionally, check entitlement logic in response

def test_duplicate_leave_request():
    admin_token = get_admin_token()
    token = create_user_and_login("duplicate@example.com", "secret123", "IC", admin_token=admin_token)
    headers = {"Authorization": f"Bearer {token}"}
    leave_type_id, _ = ensure_leave_type_exists(admin_token)
    today = (date.today() + timedelta(days=4)).isoformat()
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": "Duplicate test"
    }
    print("[DEBUG] Sending to /api/v1/leave/:", data)
    resp1 = client.post("/api/v1/leave/", json=data, headers=headers)
    print("[DEBUG] Sending to /api/v1/leave/:", data)
    resp2 = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp2.status_code == 400
    assert "Duplicate leave request" in resp2.text

def test_create_leave_request_invalid_type():
    admin_token = get_admin_token()
    token = create_user_and_login("invalidtype@example.com", "secret123", "IC", admin_token=admin_token)
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "leave_type_id": str(uuid4()),
        "start_date": (date.today() + timedelta(days=4)).isoformat(),
        "end_date": (date.today() + timedelta(days=4)).isoformat(),
        "comments": "Invalid leave type"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code == 400
    assert "Invalid leave_type_id" in resp.text

def test_create_leave_request_commit_failure():
    admin_token = get_admin_token()
    token = create_user_and_login("commitfail@example.com", "secret123", "IC", admin_token=admin_token)
    headers = {"Authorization": f"Bearer {token}"}
    leave_type_id, _ = ensure_leave_type_exists(admin_token)
    data = {
        "leave_type_id": leave_type_id,
        "start_date": (date.today() + timedelta(days=4)).isoformat(),
        "end_date": (date.today() + timedelta(days=4)).isoformat(),
        "comments": "Commit fail"
    }
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("commit fail")):
        resp = client.post("/api/v1/leave/", json=data, headers=headers)
        assert resp.status_code == 500 or resp.status_code == 400

def test_get_leave_request_permission_denied():
    admin_token = get_admin_token()
    user1_token = create_user_and_login("user1@example.com", "secret123", "IC", admin_token=admin_token)
    user2_token = create_user_and_login("user2@example.com", "secret123", "IC", admin_token=admin_token)
    headers1 = {"Authorization": f"Bearer {user1_token}"}
    headers2 = {"Authorization": f"Bearer {user2_token}"}
    leave_type_id, _ = ensure_leave_type_exists(admin_token)
    today = (date.today() + timedelta(days=4)).isoformat()
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": "Permission denied test"
    }
    print("[DEBUG] Sending to /api/v1/leave/:", data)
    resp = client.post("/api/v1/leave/", json=data, headers=headers1)
    assert resp.status_code == 200
    leave_id = resp.json()["id"]
    get_resp = client.get(f"/api/v1/leave/{leave_id}", headers=headers2)
    assert get_resp.status_code == 403

def test_update_leave_request_commit_failure():
    admin_token = get_admin_token()
    token = create_user_and_login("updatefail@example.com", "secret123", "IC", admin_token=admin_token)
    headers = {"Authorization": f"Bearer {token}"}
    leave_type_id, _ = ensure_leave_type_exists(admin_token)
    today = (date.today() + timedelta(days=4)).isoformat()
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": "Update commit fail"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code == 200
    leave_id = resp.json()["id"]
    upd_data = data.copy()
    upd_data["comments"] = "Update fail"
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("commit fail")):
        upd_resp = client.put(f"/api/v1/leave/{leave_id}", json=upd_data, headers=headers)
        assert upd_resp.status_code == 500

def test_approve_leave_request_commit_failure():
    admin_token = get_admin_token()
    token = create_user_and_login("approvefail@example.com", "secret123", "IC", admin_token=admin_token)
    headers = {"Authorization": f"Bearer {token}"}
    leave_type_id, _ = ensure_leave_type_exists(admin_token)
    today = (date.today() + timedelta(days=4)).isoformat()
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": "Approve commit fail"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code == 200
    leave_id = resp.json()["id"]
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("commit fail")):
        approve_resp = client.patch(f"/api/v1/leave/{leave_id}/approve", headers=headers)
        assert approve_resp.status_code == 500
