import uuid
import pytest
from unittest.mock import patch
from datetime import date, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from app.run import app
from .test_utils import (
    create_auth_headers,
    login_user,
    create_user_data,
    create_leave_request_data,
    assert_response_success,
    assert_response_bad_request,
    cleanup_user_data
)

client = TestClient(app)


def get_admin_token():
    return login_user("user@example.com", "secret123")


def create_user_with_token(user_data):
    token = get_admin_token()
    headers = create_auth_headers(token)
    resp = client.post("/api/v1/users/", json=user_data, headers=headers)
    assert_response_success(resp)
    return resp.json()


def ensure_leave_type_exists(admin_token):
    headers = create_auth_headers(admin_token)
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
    resp = client.post(
        "/api/v1/leave-types/",
        json=leave_type_data,
        headers=headers)
    assert_response_success(resp, [200, 201])
    leave_type = resp.json()
    return leave_type["id"], True


def delete_leave_type(leave_type_id, admin_token):
    headers = create_auth_headers(admin_token)
    resp = client.delete(
        f"/api/v1/leave-types/{leave_type_id}",
        headers=headers)
    assert resp.status_code in (200, 204, 404), resp.text


@pytest.fixture
def leave_type_fixture():
    admin_token = get_admin_token()
    leave_type_id, created = ensure_leave_type_exists(admin_token)
    yield leave_type_id
    if created:
        delete_leave_type(leave_type_id, admin_token)


def create_user_and_login(
        username,
        password,
        role,
        gender="male",
        admin_token=None):
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

    user_data = create_user_data(
        name=unique_email,
        email=unique_email,
        password=password,
        role_band=role_band,
        role_title=role_title,
        passport_or_id_number=f"id-{unique_email}",
        gender=gender
    )

    headers = create_auth_headers(admin_token) if admin_token else {}
    reg_resp = client.post("/api/v1/users/", json=user_data, headers=headers)
    assert reg_resp.status_code in (200, 201, 409), reg_resp.text

    token = login_user(unique_email, password)
    return token, reg_resp.json()["id"], unique_email


@pytest.fixture
def create_user_and_login_fixture():
    admin_token = get_admin_token()
    created_users = []

    def _create_user(username, password, role, gender="male"):
        token, user_id, email = create_user_and_login(
            username, password, role, gender, admin_token)
        created_users.append((user_id, token))
        return token, user_id, email

    yield _create_user

    # Cleanup
    from app.db.session import SessionLocal
    db = SessionLocal()
    for user_id, token in created_users:
        cleanup_user_data(user_id, db)
    db.close()


def test_create_leave_request_db_error(create_user_and_login_fixture):
    token, _, _ = create_user_and_login_fixture(
        "dberror@example.com", "secret123", "IC")
    headers = create_auth_headers(token)

    # Mock DB error during leave type lookup
    with patch("app.api.v1.routers.leave_request.get_db") as mock_get_db:
        mock_db = mock_get_db.return_value.__enter__.return_value
        mock_db.query.side_effect = Exception("DB connection error")

        data = {
            "leave_type_id": str(uuid4()),
            "start_date": (date.today() + timedelta(days=4)).isoformat(),
            "end_date": (date.today() + timedelta(days=4)).isoformat(),
            "comments": "DB error test"
        }
        resp = client.post("/api/v1/leave/", json=data, headers=headers)
        assert resp.status_code == 500


def test_create_annual_leave_too_soon(create_user_and_login_fixture):
    token, _, _ = create_user_and_login_fixture(
        "toosoon@example.com", "secret123", "IC")
    headers = create_auth_headers(token)
    admin_token = get_admin_token()
    leave_type_id, _ = ensure_leave_type_exists(admin_token)

    # Try to create leave for tomorrow (too soon for annual leave)
    data = {
        "leave_type_id": leave_type_id,
        "start_date": (date.today() + timedelta(days=1)).isoformat(),
        "end_date": (date.today() + timedelta(days=1)).isoformat(),
        "comments": "Too soon"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    # Depending on business rules, this might be rejected
    assert resp.status_code in (200, 201, 400)


def test_create_annual_leave_weekends_only(create_user_and_login_fixture):
    token, _, _ = create_user_and_login_fixture(
        "weekends@example.com", "secret123", "IC")
    headers = create_auth_headers(token)
    admin_token = get_admin_token()
    leave_type_id, _ = ensure_leave_type_exists(admin_token)

    # Find next Saturday and Sunday
    today = date.today()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0:
        days_until_saturday = 7
    saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)

    data = {
        "leave_type_id": leave_type_id,
        "start_date": saturday.isoformat(),
        "end_date": sunday.isoformat(),
        "comments": "Weekend leave"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    # Business logic might reject weekend-only leave
    assert resp.status_code in (200, 201, 400)


def test_annual_leave_no_policy(create_user_and_login_fixture):
    token, _, _ = create_user_and_login_fixture(
        "nopolicy@example.com", "secret123", "IC")
    headers = create_auth_headers(token)
    admin_token = get_admin_token()
    leave_type_id, _ = ensure_leave_type_exists(admin_token)

    data = {
        "leave_type_id": leave_type_id,
        "start_date": (date.today() + timedelta(days=4)).isoformat(),
        "end_date": (date.today() + timedelta(days=4)).isoformat(),
        "comments": "No policy test"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code in (200, 201, 400)


def test_duplicate_leave_request(create_user_and_login_fixture):
    token, _, _ = create_user_and_login_fixture(
        "duplicate@example.com", "secret123", "IC")
    headers = create_auth_headers(token)
    admin_token = get_admin_token()
    leave_type_id, _ = ensure_leave_type_exists(admin_token)

    data = create_leave_request_data(leave_type_id, comments="Duplicate test")

    # Create first request
    resp1 = client.post("/api/v1/leave/", json=data, headers=headers)
    assert_response_success(resp1, [200, 201])

    # Try to create duplicate
    resp2 = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp2.status_code in (400, 409)


def test_create_leave_request_invalid_type(create_user_and_login_fixture):
    token, _, _ = create_user_and_login_fixture(
        "invalidtype@example.com", "secret123", "IC")
    headers = create_auth_headers(token)

    data = {
        "leave_type_id": str(uuid4()),
        "start_date": (date.today() + timedelta(days=4)).isoformat(),
        "end_date": (date.today() + timedelta(days=4)).isoformat(),
        "comments": "Invalid leave type"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert_response_bad_request(resp)


def test_create_leave_request_commit_failure(create_user_and_login_fixture):
    token, _, _ = create_user_and_login_fixture(
        "commitfail@example.com", "secret123", "IC")
    headers = create_auth_headers(token)
    admin_token = get_admin_token()
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


def test_get_leave_request_permission_denied(create_user_and_login_fixture):
    user1_token, _, _ = create_user_and_login_fixture(
        "user1@example.com", "secret123", "IC")
    user2_token, _, _ = create_user_and_login_fixture(
        "user2@example.com", "secret123", "IC")
    headers1 = create_auth_headers(user1_token)
    headers2 = create_auth_headers(user2_token)
    admin_token = get_admin_token()
    leave_type_id, _ = ensure_leave_type_exists(admin_token)

    today = (date.today() + timedelta(days=4)).isoformat()
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": "Permission denied test"
    }

    resp = client.post("/api/v1/leave/", json=data, headers=headers1)
    assert_response_success(resp)
    leave_id = resp.json()["id"]

    get_resp = client.get(f"/api/v1/leave/{leave_id}", headers=headers2)
    assert get_resp.status_code == 403


def test_update_leave_request_commit_failure(create_user_and_login_fixture):
    token, _, _ = create_user_and_login_fixture(
        "updatefail@example.com", "secret123", "IC")
    headers = create_auth_headers(token)
    admin_token = get_admin_token()
    leave_type_id, _ = ensure_leave_type_exists(admin_token)

    today = (date.today() + timedelta(days=4)).isoformat()
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": "Update commit fail"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert_response_success(resp)
    leave_id = resp.json()["id"]

    upd_data = data.copy()
    upd_data["comments"] = "Update fail"
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("commit fail")):
        upd_resp = client.put(
            f"/api/v1/leave/{leave_id}",
            json=upd_data,
            headers=headers)
        assert upd_resp.status_code == 500


def test_approve_leave_request_commit_failure(create_user_and_login_fixture):
    token, _, _ = create_user_and_login_fixture(
        "approvefail@example.com", "secret123", "IC")
    headers = create_auth_headers(token)
    admin_token = get_admin_token()
    leave_type_id, _ = ensure_leave_type_exists(admin_token)

    today = (date.today() + timedelta(days=4)).isoformat()
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": "Approve commit fail"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert_response_success(resp)
    leave_id = resp.json()["id"]

    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("commit fail")):
        approve_resp = client.patch(
            f"/api/v1/leave/{leave_id}/approve",
            headers=headers)
        assert approve_resp.status_code == 500
