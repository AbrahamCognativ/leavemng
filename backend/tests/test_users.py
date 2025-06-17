import pytest
import uuid
from fastapi.testclient import TestClient
from app.run import app
from .test_utils import (
    create_auth_headers,
    login_user,
    permissions_helper,
    assert_response_success,
    assert_response_validation_error,
    assert_response_bad_request,
    cleanup_user_and_related_data
)

client = TestClient(app)


@pytest.fixture
def auth_token():
    return login_user("user@example.com", "secret123")


def test_user_permissions():
    endpoints = [
        ('post', '/api/v1/users/', {}),
        ('put', '/api/v1/users/fake-id', {}),
        ('delete', '/api/v1/users/fake-id', {})
    ]
    permissions_helper(endpoints)


def test_user_crud(auth_token):
    headers = create_auth_headers(auth_token)
    unique_email = f"testuser{uuid.uuid4()}@example.com"
    data = {
        "email": unique_email,
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "User",
        "role": "IC"
    }
    # CREATE
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_success(resp, [200, 201])
    user = resp.json()
    user_id = user["id"]
    assert user["email"] == data["email"]
    assert user["first_name"] == data["first_name"]
    assert user["last_name"] == data["last_name"]
    assert user["role"] == data["role"]
    # READ
    get_resp = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert_response_success(get_resp)
    get_user = get_resp.json()
    assert get_user["id"] == user_id
    # UPDATE
    upd_data = {
        "email": unique_email,
        "first_name": "Updated",
        "last_name": "User",
        "role": "HR"
    }
    upd_resp = client.put(
        f"/api/v1/users/{user_id}",
        json=upd_data,
        headers=headers)
    assert_response_success(upd_resp)
    upd_user = upd_resp.json()
    assert upd_user["first_name"] == "Updated"
    assert upd_user["role"] == "HR"
    # DELETE
    del_resp = client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert_response_success(del_resp, [200, 204])
    # Ensure deleted
    get_after_del = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert get_after_del.status_code in (404, 410)


def test_user_validation(auth_token):
    headers = create_auth_headers(auth_token)
    # Missing required fields
    data = {"first_name": "Test"}
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_validation_error(resp)


def test_user_duplicate_email(auth_token):
    headers = create_auth_headers(auth_token)
    unique_email = f"duplicate{uuid.uuid4()}@example.com"
    data = {
        "email": unique_email,
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "User",
        "role": "IC"
    }
    # First creation should succeed
    resp1 = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_success(resp1, [200, 201])
    user_id = resp1.json()["id"]
    # Second creation with same email should fail
    resp2 = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_bad_request(resp2)
    # Cleanup
    cleanup_user_and_related_data(user_id)


def test_user_login():
    # Test login with valid credentials
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "user@example.com", "password": "secret123"}
    )
    assert_response_success(resp)
    token_data = resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


def test_user_login_invalid():
    # Test login with invalid credentials
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "invalid@example.com", "password": "wrongpass"}
    )
    assert resp.status_code in (401, 422)


def test_user_profile(auth_token):
    headers = create_auth_headers(auth_token)
    resp = client.get("/api/v1/users/me", headers=headers)
    assert_response_success(resp)
    profile = resp.json()
    assert "email" in profile
    assert "first_name" in profile
    assert "last_name" in profile


def test_user_list(auth_token):
    headers = create_auth_headers(auth_token)
    resp = client.get("/api/v1/users/", headers=headers)
    assert_response_success(resp)
    users = resp.json()
    assert isinstance(users, list)


def test_user_role_update(auth_token):
    headers = create_auth_headers(auth_token)
    unique_email = f"roletest{uuid.uuid4()}@example.com"
    data = {
        "email": unique_email,
        "password": "testpass123",
        "first_name": "Role",
        "last_name": "Test",
        "role": "IC"
    }
    # Create user
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_success(resp, [200, 201])
    user_id = resp.json()["id"]
    # Update role
    upd_data = {
        "email": unique_email,
        "first_name": "Role",
        "last_name": "Test",
        "role": "HR"
    }
    upd_resp = client.put(
        f"/api/v1/users/{user_id}",
        json=upd_data,
        headers=headers)
    assert_response_success(upd_resp)
    assert upd_resp.json()["role"] == "HR"
    # Cleanup
    cleanup_user_and_related_data(user_id)


def test_soft_delete_user(auth_token):
    headers = create_auth_headers(auth_token)
    unique_email = f"softdelete{uuid.uuid4()}@example.com"
    data = {
        "email": unique_email,
        "password": "testpass123",
        "first_name": "Soft",
        "last_name": "Delete",
        "role": "IC"
    }
    # Create user
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_success(resp, [200, 201])
    user_id = resp.json()["id"]
    # Soft delete
    del_resp = client.patch(
        f"/api/v1/users/{user_id}/softdelete",
        headers=headers)
    assert_response_success(del_resp)
    assert "soft-deleted" in del_resp.json()["detail"]
    # Try soft deleting again
    del_resp2 = client.patch(
        f"/api/v1/users/{user_id}/softdelete",
        headers=headers)
    assert del_resp2.status_code == 400
    assert "already inactive" in del_resp2.json()["detail"]


def test_list_users(auth_token):
    headers = create_auth_headers(auth_token)
    resp = client.get("/api/v1/users/", headers=headers)
    assert_response_success(resp)
    assert isinstance(resp.json(), list)


def test_get_user_permission_denied(auth_token):
    headers = create_auth_headers(auth_token)
    # Try to get a user that isn't self or allowed by role
    # Use a random UUID that isn't the test user
    import uuid
    random_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/users/{random_id}", headers=headers)
    # Should be 403 or 404
    assert resp.status_code in (403, 404)


def test_update_user(auth_token):
    headers = create_auth_headers(auth_token)
    unique_email = f"update{uuid.uuid4()}@example.com"
    data = {
        "email": unique_email,
        "password": "testpass123",
        "first_name": "Update",
        "last_name": "User",
        "role": "IC"
    }
    # Create user
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_success(resp, [200, 201])
    user_id = resp.json()["id"]
    # Update user
    upd_data = {
        "email": unique_email,
        "first_name": "Updated",
        "last_name": "User",
        "role": "HR"
    }
    upd_resp = client.put(
        f"/api/v1/users/{user_id}",
        json=upd_data,
        headers=headers)
    assert_response_success(upd_resp)
    assert upd_resp.json()["first_name"] == "Updated"
    assert upd_resp.json()["role"] == "HR"
    # Cleanup
    cleanup_user_and_related_data(user_id)


def test_get_user_leave(auth_token):
    headers = create_auth_headers(auth_token)
    unique_email = f"leave{uuid.uuid4()}@example.com"
    data = {
        "email": unique_email,
        "password": "testpass123",
        "first_name": "Leave",
        "last_name": "User",
        "role": "IC"
    }
    # Create user
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_success(resp, [200, 201])
    user_id = resp.json()["id"]
    # Get leave
    leave_resp = client.get(f"/api/v1/users/{user_id}/leave", headers=headers)
    # Should be 200 or 404 if no leave balance
    assert leave_resp.status_code in (200, 404)
    if leave_resp.status_code == 200:
        assert "leave_balance" in leave_resp.json()
        assert "leave_request" in leave_resp.json()
    # Cleanup
    cleanup_user_and_related_data(user_id)


def test_create_user_success(auth_token):
    headers = create_auth_headers(auth_token)
    unique_email = f"create{uuid.uuid4()}@example.com"
    data = {
        "email": unique_email,
        "password": "testpass123",
        "first_name": "Create",
        "last_name": "User",
        "role": "IC"
    }
    # Create user
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_success(resp, [200, 201])
    user = resp.json()
    assert user["email"] == data["email"]
    assert user["first_name"] == data["first_name"]
    assert user["last_name"] == data["last_name"]
    assert user["role"] == data["role"]
    # Cleanup
    cleanup_user_and_related_data(user["id"])


def test_create_user_duplicate(auth_token):
    headers = create_auth_headers(auth_token)
    unique_email = f"duplicate{uuid.uuid4()}@example.com"
    data = {
        "email": unique_email,
        "password": "testpass123",
        "first_name": "Duplicate",
        "last_name": "User",
        "role": "IC"
    }
    # First creation should succeed
    resp1 = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_success(resp1, [200, 201])
    user_id = resp1.json()["id"]
    # Second creation with same email should fail
    resp2 = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_bad_request(resp2)
    # Cleanup
    cleanup_user_and_related_data(user_id)


def test_create_user_validation_error(auth_token):
    headers = create_auth_headers(auth_token)
    # Missing required fields
    data = {"first_name": "Test"}
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_validation_error(resp)


@pytest.mark.parametrize("missing_field",
                         ["email",
                          "password",
                          "first_name",
                          "last_name",
                          "role"])
def test_create_user_missing_field(auth_token, missing_field):
    headers = create_auth_headers(auth_token)
    data = {
        "email": f"test{uuid.uuid4()}@example.com",
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "User",
        "role": "IC"
    }
    data.pop(missing_field)
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_validation_error(resp)


@pytest.mark.parametrize("invalid_email",
                         ["not-an-email", "@no-user.com", "user@.com"])
def test_create_user_invalid_email(auth_token, invalid_email):
    headers = create_auth_headers(auth_token)
    data = {
        "email": invalid_email,
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "User",
        "role": "IC"
    }
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert_response_validation_error(resp)
