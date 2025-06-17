# Placeholder for files tests
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.run import app
from .test_utils import (
    create_auth_headers,
    login_user,
    create_user,
    create_test_user_data,
    permissions_helper,
    assert_response_success,
    assert_response_validation_error,
    cleanup_user_data,
    create_users_dict_with_requester,
    cleanup_users_dict,
    permissions_helper,
)

client = TestClient(app)


@pytest.fixture
def auth_token():
    return login_user("user@example.com", "secret123")


def test_file_upload_permissions():
    endpoints = [
        ('post', '/api/v1/files/upload', {}),
        ('get', '/api/v1/files/fake-id', {}),
        ('delete', '/api/v1/files/fake-id', {})
    ]
    permissions_helper(endpoints)


def test_file_upload_success(auth_token):
    headers = create_auth_headers(auth_token)
    # Create a test file
    test_content = b"This is a test file content"
    test_file = io.BytesIO(test_content)
    files = {"file": ("test.txt", test_file, "text/plain")}

    resp = client.post("/api/v1/files/upload", files=files, headers=headers)
    assert_response_success(resp, [200, 201])
    file_data = resp.json()
    assert "id" in file_data
    assert "filename" in file_data
    assert file_data["filename"] == "test.txt"


def test_file_upload_validation(auth_token):
    headers = create_auth_headers(auth_token)
    # Try to upload without file
    resp = client.post("/api/v1/files/upload", headers=headers)
    assert_response_validation_error(resp)


def test_file_download(auth_token):
    headers = create_auth_headers(auth_token)
    # First upload a file
    test_content = b"Download test content"
    test_file = io.BytesIO(test_content)
    files = {"file": ("download_test.txt", test_file, "text/plain")}

    upload_resp = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers)
    assert_response_success(upload_resp, [200, 201])
    file_id = upload_resp.json()["id"]

    # Now download the file
    download_resp = client.get(f"/api/v1/files/{file_id}", headers=headers)
    assert_response_success(download_resp)


def test_file_delete(auth_token):
    headers = create_auth_headers(auth_token)
    # First upload a file
    test_content = b"Delete test content"
    test_file = io.BytesIO(test_content)
    files = {"file": ("delete_test.txt", test_file, "text/plain")}

    upload_resp = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers)
    assert_response_success(upload_resp, [200, 201])
    file_id = upload_resp.json()["id"]

    # Now delete the file
    delete_resp = client.delete(f"/api/v1/files/{file_id}", headers=headers)
    assert_response_success(delete_resp, [200, 204])

    # Verify file is deleted
    get_resp = client.get(f"/api/v1/files/{file_id}", headers=headers)
    assert get_resp.status_code in (404, 410)


def test_file_list(auth_token):
    headers = create_auth_headers(auth_token)
    resp = client.get("/api/v1/files/", headers=headers)
    assert_response_success(resp)
    files = resp.json()
    assert isinstance(files, list)


def test_file_upload_large_file(auth_token):
    headers = create_auth_headers(auth_token)
    # Create a larger test file (1MB)
    large_content = b"x" * (1024 * 1024)
    test_file = io.BytesIO(large_content)
    files = {"file": ("large_test.txt", test_file, "text/plain")}

    resp = client.post("/api/v1/files/upload", files=files, headers=headers)
    # Should succeed or fail with appropriate error
    assert resp.status_code in (200, 201, 413, 422)


def test_file_upload_empty_file(auth_token):
    headers = create_auth_headers(auth_token)
    # Create an empty file
    empty_file = io.BytesIO(b"")
    files = {"file": ("empty.txt", empty_file, "text/plain")}

    resp = client.post("/api/v1/files/upload", files=files, headers=headers)
    # Should fail validation or succeed depending on implementation
    assert resp.status_code in (200, 201, 400, 422)


def test_file_upload_different_types(auth_token):
    headers = create_auth_headers(auth_token)
    file_types = [
        ("test.pdf", b"PDF content", "application/pdf"),
        ("test.jpg", b"JPEG content", "image/jpeg"),
        ("test.png", b"PNG content", "image/png"),
        ("test.doc", b"DOC content", "application/msword")
    ]

    for filename, content, content_type in file_types:
        test_file = io.BytesIO(content)
        files = {"file": (filename, test_file, content_type)}

        resp = client.post(
            "/api/v1/files/upload",
            files=files,
            headers=headers)
        # Should succeed or fail based on allowed file types
        assert resp.status_code in (200, 201, 400, 415, 422)


def test_file_metadata(auth_token):
    headers = create_auth_headers(auth_token)
    # Upload a file with metadata
    test_content = b"Metadata test content"
    test_file = io.BytesIO(test_content)
    files = {"file": ("metadata_test.txt", test_file, "text/plain")}

    resp = client.post("/api/v1/files/upload", files=files, headers=headers)
    if resp.status_code in (200, 201):
        file_data = resp.json()
        assert "id" in file_data
        assert "filename" in file_data
        assert "size" in file_data or "content_length" in file_data
        assert "created_at" in file_data or "upload_date" in file_data


@pytest.fixture(scope="module")
def users_and_tokens(org_unit_id, seeded_admin):
    # Use the seeded admin
    admin_email = "user@example.com"
    admin_password = "secret123"
    admin_id = seeded_admin["id"]
    admin_token = login_user(admin_email, admin_password)

    # Create HR
    hr_email = f"hr_{uuid4()}@test.com"
    hr_data = {
        "name": "HR User", "email": hr_email, "password": "adminpass",
        "role_band": "HR", "role_title": "HR", "is_active": True,
        "passport_or_id_number": str(uuid4()), "org_unit_id": org_unit_id,
        "gender": "male"
    }
    hr_id = create_user(hr_data, admin_token)
    hr_token = login_user(hr_email, "adminpass")

    # Create Manager
    manager_email = f"manager_{uuid4()}@test.com"
    manager_data = {
        "name": "Manager User",
        "email": manager_email,
        "password": "adminpass",
        "role_band": "",
        "role_title": "Manager",
        "is_active": True,
        "passport_or_id_number": str(
            uuid4()),
        "org_unit_id": org_unit_id,
        "gender": "male"}
    manager_id = create_user(manager_data, admin_token)
    manager_token = login_user(manager_email, "adminpass")

    # Create IC
    ic_email = f"ic_{uuid4()}@test.com"
    ic_data = {
        "name": "IC User", "email": ic_email, "password": "adminpass",
        "role_band": "", "role_title": "IC", "is_active": True,
        "passport_or_id_number": str(uuid4()), "org_unit_id": org_unit_id,
        "gender": "male"
    }
    ic_id = create_user(ic_data, admin_token)
    ic_token = login_user(ic_email, "adminpass")

    # Create Requester (who will own the leave request)
    requester_email = f"requester_{uuid4()}@test.com"
    requester_data = {
        "name": "Requester User",
        "email": requester_email,
        "password": "adminpass",
        "role_band": "",
        "role_title": "IC",
        "is_active": True,
        "passport_or_id_number": str(
            uuid4()),
        "org_unit_id": org_unit_id,
        "gender": "male"}
    requester_id = create_user(requester_data, admin_token)
    requester_token = login_user(requester_email, "adminpass")

    users_dict = create_users_dict_with_requester(
        admin_token, hr_token, manager_token, ic_token, requester_token,
        admin_id, hr_id, manager_id, ic_id, requester_id
    )

    yield users_dict
    # Cleanup after tests
    cleanup_users_dict(users_dict, ["hr", "manager", "ic", "requester"])


@pytest.fixture(scope="module")
def leave_request_id(users_and_tokens, seeded_leave_type):
    # Ensure at least one leave type is present for the test
    requester_token = users_and_tokens["requester"]["token"]
    leave_types = client.get(
        "/api/v1/leave-types/",
        headers={
            "Authorization": f"Bearer {requester_token}"}).json()
    if leave_types and isinstance(
            leave_types,
            list) and "id" in leave_types[0]:
        leave_type_id = leave_types[0]["id"]
    else:
        leave_type_id = seeded_leave_type.id
    data = {
        "leave_type_id": str(leave_type_id),
        "start_date": "2025-05-06",
        "end_date": "2025-05-06",
        "comments": "Test leave for files"
    }
    resp = client.post(
        "/api/v1/leave/",
        json=data,
        headers={
            "Authorization": f"Bearer {requester_token}"})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


@pytest.mark.parametrize("role,allowed", [
    ("admin", True),
    ("hr", True),
    ("manager", True),
    ("requester", True),
    ("ic", False),
])
def test_upload_leave_request_file_permissions(
        users_and_tokens, leave_request_id, role, allowed):
    file_content = b"leave doc"
    files = {"file": ("leave.txt", file_content, "text/plain")}
    token = users_and_tokens[role]["token"]
    resp = client.post(
        f"/api/v1/files/upload/{leave_request_id}",
        files=files,
        headers={
            "Authorization": f"Bearer {token}"})
    # Only the leave requester, HR, and admin are allowed to upload. The
    # manager is only allowed if they are the approver, which is not set up in
    # this test.
    if role == "manager":
        assert resp.status_code in (
            401, 403), f"Role {role} should be forbidden"
    elif allowed:
        assert resp.status_code in (200, 201), f"Role {role} should be allowed"
    else:
        assert resp.status_code in (
            401, 403), f"Role {role} should be forbidden"


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
    resp = client.post(
        f"/api/v1/files/upload-profile-image/{user_id}",
        files=files,
        headers={
            "Authorization": f"Bearer {token}"})
    if allowed:
        assert resp.status_code in (200, 201), f"Role {role} should be allowed"
    else:
        assert resp.status_code in (
            401, 403), f"Role {role} should be forbidden"


def test_ic_cannot_upload_profile_image_for_others(users_and_tokens):
    """
    IC should not be able to upload a profile image for another user (e.g., admin)
    """
    ic_token = users_and_tokens["ic"]["token"]
    admin_id = users_and_tokens["admin"]["id"]
    file_content = b"profile img"
    files = {"file": ("profile.png", file_content, "image/png")}
    resp = client.post(
        f"/api/v1/files/upload-profile-image/{admin_id}",
        files=files,
        headers={
            "Authorization": f"Bearer {ic_token}"})
    assert resp.status_code in (
        401, 403), "IC should be forbidden from uploading for another user"
