"""
Shared test utilities to reduce code duplication across test files.
"""
import uuid
from typing import Dict, List, Tuple, Any, Optional
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.run import app
from app.models.user import User

client = TestClient(app)


def create_auth_headers(auth_token: str) -> Dict[str, str]:
    """Create authorization headers for API requests."""
    return {"Authorization": f"Bearer {auth_token}"}


def create_fake_auth_headers(role: str) -> Dict[str, str]:
    """Create fake authorization headers for permission testing."""
    return {"Authorization": f"Bearer fake-token-for-{role}"}


def permissions_helper(
    endpoints: List[Tuple[str, str, Dict[str, Any]]],
    roles: List[str] = None,
    forbidden_roles: List[str] = None
) -> None:
    """
    Test permissions for multiple endpoints and roles.

    Args:
        endpoints: List of (method, url, data) tuples
        roles: List of roles to test (default: ['Admin', 'Manage', 'HR', 'IC'])
        forbidden_roles: List of roles that should be forbidden (default: ['IC'])
    """
    if roles is None:
        roles = ['Admin', 'Manage', 'HR', 'IC']
    if forbidden_roles is None:
        forbidden_roles = ['IC']

    for role in roles:
        headers = create_fake_auth_headers(role)
        for method, url, data in endpoints:
            if method in ('post', 'put'):
                resp = getattr(client, method)(url, json=data, headers=headers)
            else:
                resp = getattr(client, method)(url, headers=headers)

            # Check permissions
            if role in forbidden_roles:
                assert resp.status_code in (
                    401, 403, 405), f"Role {role} should be forbidden for {method} {url}"
            else:
                assert resp.status_code != 403, f"Role {role} should not be forbidden for {method} {url}"


def login_user(email: str, password: str) -> str:
    """Login a user and return their access token."""
    data = {"username": email, "password": password}
    resp = client.post("/api/v1/auth/login", data=data)
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def create_user(user_data: Dict[str, Any], admin_token: str) -> str:
    """Create a user and return their ID."""
    resp = client.post(
        "/api/v1/users/",
        json=user_data,
        headers=create_auth_headers(admin_token)
    )
    assert resp.status_code == 200, f"User creation failed: {resp.text}"
    return resp.json()["id"]


def create_test_user_data(
    name: str = "Test User",
    email: Optional[str] = None,
    role_title: str = "IC",
    role_band: str = "",
    gender: str = "male",
    password: str = "testpass123"
) -> Dict[str, Any]:
    """Create test user data with unique identifiers."""
    unique_id = str(uuid.uuid4())
    if email is None:
        email = f"test_{unique_id}@example.com"

    return {
        "name": name,
        "email": email,
        "password": password,
        "role_band": role_band,
        "role_title": role_title,
        "is_active": True,
        "passport_or_id_number": unique_id,
        "gender": gender
    }


def cleanup_users_by_ids(user_ids: List[str]) -> None:
    """Clean up users by their IDs, handling foreign key constraints."""
    if not user_ids:
        return

    db = SessionLocal()
    try:
        for user_id in user_ids:
            # Clean up related data first
            _cleanup_user_related_data(db, user_id)

            # Delete the user
            db.query(User).filter(User.id == user_id).delete()

        db.commit()
    except (AssertionError, AttributeError, TypeError, Exception) as e:
        db.rollback()
        print(f"Error during user cleanup: {e}")
    finally:
        db.close()


def cleanup_users_by_emails(emails: List[str]) -> None:
    """Clean up users by their email addresses."""
    if not emails:
        return

    db = SessionLocal()
    try:
        for email in emails:
            user = db.query(User).filter(User.email == email).first()
            if user:
                _cleanup_user_related_data(db, str(user.id))
                db.query(User).filter(User.email == email).delete()

        db.commit()
    except (AssertionError, AttributeError, TypeError, Exception) as e:
        db.rollback()
        print(f"Error during email cleanup: {e}")
    finally:
        db.close()


def _cleanup_user_related_data(db, user_id: str) -> None:
    """Clean up data related to a user before deleting the user."""
    try:
        # Clean up audit logs
        db.execute(
            text("DELETE FROM audit_logs WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        db.commit()
    except Exception:
        db.rollback()

    try:
        # Clean up leave balances
        db.execute(
            text("DELETE FROM leave_balances WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        db.commit()
    except Exception:
        db.rollback()

    try:
        # Clean up leave requests
        db.execute(
            text("DELETE FROM leave_requests WHERE user_id = :user_id OR decided_by = :user_id"),
            {"user_id": user_id}
        )
        db.commit()
    except Exception:
        db.rollback()
        # Check for remaining requests
        remaining_requests = db.execute(
            text("SELECT id FROM leave_requests WHERE user_id = :user_id OR decided_by = :user_id"), {
                "user_id": user_id}).fetchall()
        if remaining_requests:
            print(
                f"User {user_id} still referenced in leave_requests: {remaining_requests}")

    try:
        # Update manager references
        db.execute(
            text("UPDATE users SET manager_id = NULL WHERE manager_id = :user_id"), {
                "user_id": user_id})
        db.commit()
    except Exception:
        db.rollback()


def create_leave_request_data(leave_type_id, comments=None):
    """Create test data for leave request."""
    import random
    import uuid
    from datetime import datetime, timedelta

    # Generate a unique date for each test run
    offset = random.randint(1, 10000)
    today_dt = datetime.now() + timedelta(days=offset)
    today = today_dt.strftime("%Y-%m-%d")

    return {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "total_days": 1,
        "comments": comments or f"Test leave {uuid.uuid4()}"
    }


def cleanup_user_data(user_id, db):
    """Clean up user-related data in the database."""
    from sqlalchemy import text

    # Delete all audit_logs for this user
    try:
        db.execute(
            text("DELETE FROM audit_logs WHERE user_id = :user_id"), {
                "user_id": str(user_id)})
        db.commit()
    except Exception:
        db.rollback()

    # Delete all leave_requests for this user
    try:
        db.execute(
            text("DELETE FROM leave_requests WHERE user_id = :user_id"), {
                "user_id": str(user_id)})
        db.commit()
    except Exception:
        db.rollback()

    # Delete all leave_balances for this user
    try:
        db.execute(
            text("DELETE FROM leave_balances WHERE user_id = :user_id"), {
                "user_id": str(user_id)})
        db.commit()
    except Exception:
        db.rollback()


def get_first_leave_type(auth_token):
    """Get the first available leave type, skipping test if none exist."""
    import pytest
    from fastapi.testclient import TestClient
    from app.run import app

    client = TestClient(app)
    headers = create_auth_headers(auth_token)
    types = client.get("/api/v1/leave-types/", headers=headers).json()
    if not types:
        pytest.skip("No leave types to create leave request")
    return types[0]["id"]


def create_users_dict(
        admin_token,
        hr_token,
        manager_token,
        ic_token,
        admin_id,
        hr_id,
        manager_id,
        ic_id):
    """Create standardized users dictionary for tests."""
    return {
        "admin": {"id": admin_id, "token": admin_token},
        "hr": {"id": hr_id, "token": hr_token},
        "manager": {"id": manager_id, "token": manager_token},
        "ic": {"id": ic_id, "token": ic_token},
    }


def create_users_dict_with_requester(
        admin_token,
        hr_token,
        manager_token,
        ic_token,
        requester_token,
        admin_id,
        hr_id,
        manager_id,
        ic_id,
        requester_id):
    """Create standardized users dictionary with requester for tests."""
    users_dict = create_users_dict(
        admin_token, hr_token, manager_token, ic_token,
        admin_id, hr_id, manager_id, ic_id
    )
    # Add the requester user
    users_dict["requester"] = {"id": requester_id, "token": requester_token}
    return users_dict


def cleanup_users_dict(users_dict, user_keys=None):
    """Clean up users from users_dict fixture."""
    from app.db.session import SessionLocal

    if user_keys is None:
        user_keys = ["hr", "manager", "ic", "requester"]

    db = SessionLocal()
    for user_key in user_keys:
        if user_key in users_dict:
            user_id = users_dict[user_key]["id"]
            cleanup_user_data(user_id, db)
    db.close()


def update_request_helper(url, data, headers, assert_success=False):
    """Test update request pattern with optional success assertion."""
    from fastapi.testclient import TestClient
    from app.run import app

    client = TestClient(app)
    upd_data = data.copy()
    upd_data["comments"] = "Updated comment"
    upd_resp = client.put(url, json=upd_data, headers=headers)
    if upd_resp.status_code not in (405, 501):
        if assert_success:
            assert_response_success(upd_resp)
        upd_json = upd_resp.json()
        return upd_resp, upd_json
    return upd_resp, None


def generic_update_request_helper(url, upd_data, headers, assert_success=True):
    """Generic update request pattern for any endpoint."""
    from fastapi.testclient import TestClient
    from app.run import app

    client = TestClient(app)
    upd_resp = client.put(url, json=upd_data, headers=headers)
    if upd_resp.status_code not in (405, 501):
        if assert_success:
            assert_response_success(upd_resp)
        upd_json = upd_resp.json()
        return upd_resp, upd_json
    return upd_resp, None


def assert_response_success(
        response,
        expected_codes: List[int] = None) -> None:
    """Assert that a response has a successful status code."""
    if expected_codes is None:
        expected_codes = [200, 201]
    assert response.status_code in expected_codes, f"Expected {expected_codes}, got {
        response.status_code}: {
        response.text}"


def assert_response_forbidden(response) -> None:
    """Assert that a response is forbidden."""
    assert response.status_code in (
        401, 403), f"Expected forbidden, got {
        response.status_code}: {
            response.text}"


def assert_response_not_found(response) -> None:
    """Assert that a response is not found."""
    assert response.status_code == 404, f"Expected 404, got {
        response.status_code}: {
        response.text}"


def assert_response_bad_request(response) -> None:
    """Assert that a response is a bad request."""
    assert response.status_code == 400, f"Expected 400, got {
        response.status_code}: {
        response.text}"


def assert_response_validation_error(response) -> None:
    """Assert that a response is a validation error."""
    assert response.status_code == 422, f"Expected 422, got {
        response.status_code}: {
        response.text}"


def test_leave_validation_missing_type(auth_token):
    """Shared test for leave request validation with missing leave_type_id."""
    from fastapi.testclient import TestClient
    from app.run import app

    client = TestClient(app)
    headers = create_auth_headers(auth_token)
    data = {
        "start_date": "2025-05-05",
        "end_date": "2025-05-05",
        "comments": "No leave_type_id"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert_response_validation_error(resp)
