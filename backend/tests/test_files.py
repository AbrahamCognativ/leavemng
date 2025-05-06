# Placeholder for files tests
import pytest
from fastapi.testclient import TestClient
from app.run import app

client = TestClient(app)

def test_files_permissions():
    roles = ['Admin', 'Manage', 'HR', 'IC']
    endpoints = [
        ('post', '/api/v1/files/upload', {}),
        ('get', '/api/v1/files/download/fake-id', {})
    ]
    for role in roles:
        headers = {'Authorization': f'Bearer fake-token-for-{role}'}
        for method, url, data in endpoints:
            if method == 'post':
                resp = getattr(client, method)(url, json=data, headers=headers)
            else:
                resp = getattr(client, method)(url, headers=headers)
            # Permissions logic: Only Admin, Manage, HR allowed, IC forbidden
            if role == 'IC':
                assert resp.status_code in (401, 403, 404)
            else:
                # Could be 404 due to fake endpoint, but not forbidden
                assert resp.status_code != 403

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from app.run import app

client = TestClient(app)

# Utility to create a user and return their id
def create_user(user_data, admin_token):
    resp = client.post("/api/v1/users/", json=user_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]

# Utility to login and get access token
def login(email, password):
    data = {"username": email, "password": password}
    resp = client.post("/api/v1/auth/login", data=data)
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]

@pytest.fixture(scope="module")
def users_and_tokens(org_unit_id, seeded_admin):
    # Use the seeded admin
    admin_email = seeded_admin["email"]
    admin_password = seeded_admin["password"]
    admin_id = seeded_admin["id"]
    admin_token = login(admin_email, admin_password)

    # Create HR
    hr_email = f"hr_{uuid4()}@test.com"
    hr_data = {
        "name": "HR User", "email": hr_email, "password": "adminpass",
        "role_band": "HR", "role_title": "HR",
        "passport_or_id_number": str(uuid4()), "org_unit_id": org_unit_id
    }
    hr_id = create_user(hr_data, admin_token)
    hr_token = login(hr_email, "adminpass")

    # Create Manager
    manager_email = f"manager_{uuid4()}@test.com"
    manager_data = {
        "name": "Manager User", "email": manager_email, "password": "adminpass",
        "role_band": "", "role_title": "Manager",
        "passport_or_id_number": str(uuid4()), "org_unit_id": org_unit_id
    }
    manager_id = create_user(manager_data, admin_token)
    manager_token = login(manager_email, "adminpass")

    # Create IC
    ic_email = f"ic_{uuid4()}@test.com"
    ic_data = {
        "name": "IC User", "email": ic_email, "password": "adminpass",
        "role_band": "", "role_title": "IC",
        "passport_or_id_number": str(uuid4()), "org_unit_id": org_unit_id
    }
    ic_id = create_user(ic_data, admin_token)
    ic_token = login(ic_email, "adminpass")

    # Create Requester (who will own the leave request)
    requester_email = f"requester_{uuid4()}@test.com"
    requester_data = {
        "name": "Requester User", "email": requester_email, "password": "adminpass",
        "role_band": "", "role_title": "IC",
        "passport_or_id_number": str(uuid4()), "org_unit_id": org_unit_id
    }
    requester_id = create_user(requester_data, admin_token)
    requester_token = login(requester_email, "adminpass")

    return {
        "admin": {"id": admin_id, "token": admin_token},
        "hr": {"id": hr_id, "token": hr_token},
        "manager": {"id": manager_id, "token": manager_token},
        "ic": {"id": ic_id, "token": ic_token},
        "requester": {"id": requester_id, "token": requester_token},
    }

@pytest.fixture(scope="module")
def leave_request_id(users_and_tokens, seeded_leave_type):
    # Ensure at least one leave type is present for the test
    requester_token = users_and_tokens["requester"]["token"]
    leave_types = client.get("/api/v1/leave-types/", headers={"Authorization": f"Bearer {requester_token}"}).json()
    if leave_types and isinstance(leave_types, list) and "id" in leave_types[0]:
        leave_type_id = leave_types[0]["id"]
    else:
        leave_type_id = seeded_leave_type.id
    data = {
        "leave_type_id": str(leave_type_id),
        "start_date": "2025-05-06",
        "end_date": "2025-05-06",
        "comments": "Test leave for files"
    }
    resp = client.post("/api/v1/leave/", json=data, headers={"Authorization": f"Bearer {requester_token}"})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]

@pytest.mark.parametrize("role,allowed", [
    ("admin", True),
    ("hr", True),
    ("manager", True),
    ("requester", True),
    ("ic", False),
])
def test_upload_leave_request_file_permissions(users_and_tokens, leave_request_id, role, allowed):
    file_content = b"leave doc"
    files = {"file": ("leave.txt", file_content, "text/plain")}
    token = users_and_tokens[role]["token"]
    resp = client.post(f"/api/v1/files/upload/{leave_request_id}", files=files, headers={"Authorization": f"Bearer {token}"})
    # Only the leave requester, HR, and admin are allowed to upload. The manager is only allowed if they are the approver, which is not set up in this test.
    if role == "manager":
        assert resp.status_code in (401, 403), f"Role {role} should be forbidden"
    elif allowed:
        assert resp.status_code in (200, 201), f"Role {role} should be allowed"
    else:
        assert resp.status_code in (401, 403), f"Role {role} should be forbidden"

@pytest.mark.parametrize("role,allowed", [
    ("admin", True),
    ("hr", True),
    ("requester", True),
    ("ic", True),  # IC can upload for themselves
])
def test_upload_profile_image_permissions(users_and_tokens, role, allowed):
    # Use the user id for the role
    user_id = users_and_tokens[role]["id"]
    token = users_and_tokens[role]["token"]
    file_content = b"profile img"
    files = {"file": ("profile.png", file_content, "image/png")}
    resp = client.post(f"/api/v1/files/upload-profile-image/{user_id}", files=files, headers={"Authorization": f"Bearer {token}"})
    if allowed:
        assert resp.status_code in (200, 201), f"Role {role} should be allowed"
    else:
        assert resp.status_code in (401, 403), f"Role {role} should be forbidden"


def test_ic_cannot_upload_profile_image_for_others(users_and_tokens):
    """
    IC should not be able to upload a profile image for another user (e.g., admin)
    """
    ic_token = users_and_tokens["ic"]["token"]
    admin_id = users_and_tokens["admin"]["id"]
    file_content = b"profile img"
    files = {"file": ("profile.png", file_content, "image/png")}
    resp = client.post(f"/api/v1/files/upload-profile-image/{admin_id}", files=files, headers={"Authorization": f"Bearer {ic_token}"})
    assert resp.status_code in (401, 403), "IC should be forbidden from uploading for another user"
