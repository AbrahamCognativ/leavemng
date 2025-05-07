import pytest
from fastapi.testclient import TestClient
from app.run import app
from app.db.session import SessionLocal
from app.models.user import User
from app.models.audit_log import AuditLog

client = TestClient(app)

@pytest.fixture(scope="module")
def auth_token():
    login_data = {
        "username": "user@example.com",
        "password": "secret123"
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return token

# Sample valid user data

def test_soft_delete_user(auth_token, created_user_cleanup):
    data = valid_user_data()
    data["gender"] = "male"
    import uuid
    data["passport_or_id_number"] = str(uuid.uuid4())
    data["email"] = f"softdelete.{data['passport_or_id_number']}@example.com"
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert resp.status_code == 200
    user_id = resp.json()["id"]
    created_user_cleanup[0].append(user_id)
    # Soft delete
    del_resp = client.patch(f"/api/v1/users/{user_id}/softdelete", headers=headers)
    assert del_resp.status_code == 200
    assert "soft-deleted" in del_resp.json()["detail"]
    # Try soft deleting again
    del_resp2 = client.patch(f"/api/v1/users/{user_id}/softdelete", headers=headers)
    assert del_resp2.status_code == 400
    assert "already inactive" in del_resp2.json()["detail"]

def test_list_users(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.get("/api/v1/users/", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    # Should contain dicts with at least 'id' and 'email'
    if resp.json():
        assert "id" in resp.json()[0]
        assert "email" in resp.json()[0]

def test_get_user_permission_denied(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    # Try to get a user that isn't self or allowed by role
    # Use a random UUID that isn't the test user
    import uuid
    random_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/users/{random_id}", headers=headers)
    # Should be 403 or 404
    assert resp.status_code in (403, 404)

def test_update_user(auth_token, created_user_cleanup):
    data = valid_user_data()
    data["gender"] = "male"
    import uuid
    data["passport_or_id_number"] = str(uuid.uuid4())
    data["email"] = f"update.{data['passport_or_id_number']}@example.com"
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert resp.status_code == 200
    user_id = resp.json()["id"]
    created_user_cleanup[0].append(user_id)
    update_data = data.copy()
    update_data["name"] = "Updated Name"
    update_data["password"] = "newpassword123"
    upd_resp = client.put(f"/api/v1/users/{user_id}", json=update_data, headers=headers)
    assert upd_resp.status_code == 200
    assert upd_resp.json()["name"] == "Updated Name"

def test_get_user_leave(auth_token, created_user_cleanup):
    data = valid_user_data()
    data["gender"] = "male"
    import uuid
    data["passport_or_id_number"] = str(uuid.uuid4())
    data["email"] = f"leave.{data['passport_or_id_number']}@example.com"
    data["gender"] = "male"
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.post("/api/v1/users/", json=data, headers=headers)
    assert resp.status_code == 200
    user_id = resp.json()["id"]
    created_user_cleanup[0].append(user_id)
    leave_resp = client.get(f"/api/v1/users/{user_id}/leave", headers=headers)
    # Should be 200 or 404 if no leave balance
    assert leave_resp.status_code in (200, 404)
    if leave_resp.status_code == 200:
        assert "leave_balance" in leave_resp.json()
        assert "leave_request" in leave_resp.json()

def valid_user_data():
    return {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "role_band": "HR",
        "role_title": "HR",
        "passport_or_id_number": "P1234567",
        "profile_image_url": None,
        "manager_id": None,
        "org_unit_id": None,
        "extra_metadata": None,
        "password": "securepassword123",
        "gender": "male"
    }

@pytest.fixture
def created_user_cleanup():
    created_user_ids = []
    created_emails = []
    yield created_user_ids, created_emails
    # Cleanup after test
    db = SessionLocal()
    for user_id in created_user_ids:
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
    for email in created_emails:
        # Also remove any audit logs for this email if needed (if you log by email elsewhere)
        db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()

@pytest.mark.parametrize("missing_field", [
    "name", "email", "role_band", "role_title", "passport_or_id_number", "password", "gender"
])
def test_create_user_validation_error(missing_field, auth_token):
    data = valid_user_data()
    data["gender"] = "male"
    data.pop(missing_field)
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/api/v1/users/", json=data, headers=headers)
    assert response.status_code == 422

@pytest.mark.parametrize("invalid_email", ["not-an-email", "@no-user.com", "user@.com"])
def test_create_user_invalid_email(invalid_email, auth_token):
    data = valid_user_data()
    data["gender"] = "male"
    data["email"] = invalid_email
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/api/v1/users/", json=data, headers=headers)
    assert response.status_code == 422

def test_create_user_success(auth_token, created_user_cleanup):
    data = valid_user_data()
    data["gender"] = "male"
    import uuid
    data["passport_or_id_number"] = str(uuid.uuid4())
    data["email"] = f"john.doe.{data['passport_or_id_number']}@example.com"
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/api/v1/users/", json=data, headers=headers)
    assert response.status_code == 200
    resp_json = response.json()
    # Track for cleanup
    created_user_cleanup[0].append(resp_json["id"])
    created_user_cleanup[1].append(resp_json["email"])
    assert resp_json["name"] == data["name"]
    assert resp_json["email"] == data["email"]
    assert resp_json["role_band"] == data["role_band"]
    assert resp_json["role_title"] == data["role_title"]
    assert resp_json["passport_or_id_number"] == data["passport_or_id_number"]
    assert "id" in resp_json
    assert "created_at" in resp_json

def test_create_user_duplicate(auth_token):
    data = valid_user_data()
    data["gender"] = "male"
    import uuid
    unique_id = str(uuid.uuid4())
    data["passport_or_id_number"] = unique_id
    data["email"] = f"johndoe_{unique_id}@example.com"  # ensure unique email for each run
    headers = {"Authorization": f"Bearer {auth_token}"}
    # First creation should succeed
    resp1 = client.post("/api/v1/users/", json=data, headers=headers)
    assert resp1.status_code == 200
    # Second creation with same passport_or_id_number and email should fail
    resp2 = client.post("/api/v1/users/", json=data, headers=headers)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]
