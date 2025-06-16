import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from app.run import app
from app.utils.password import hash_password

client = TestClient(app)


def create_test_user(role_band, role_title, org_unit_id):
    email = f"{role_title.lower()}_{uuid4()}@test.com"
    user_data = {
        "name": f"{role_title} User",
        "email": email,
        "password": "adminpass",
        "role_band": role_band,
        "role_title": role_title,
        "is_active": True,
        "passport_or_id_number": str(uuid4()),
        "org_unit_id": org_unit_id,
        "gender": "male"
    }
    resp = client.post(
        "/api/v1/users/",
        json=user_data,
        headers={
            "Authorization": f"Bearer {
                get_admin_token()}"})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"], email, user_data["password"]


def login(email, password):
    data = {"username": email, "password": password}
    resp = client.post("/api/v1/auth/login", data=data)
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def get_admin_token():
    # You may want to replace this logic to fetch/create a real admin user
    admin_email = "user@example.com"
    admin_password = "secret123"
    data = {"username": admin_email, "password": admin_password}
    resp = client.post("/api/v1/auth/login", data=data)
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def analytics_users(org_unit_id):
    admin_id, admin_email, admin_pw = create_test_user(
        "Admin", "Admin", org_unit_id)
    admin_token = login(admin_email, admin_pw)
    hr_id, hr_email, hr_pw = create_test_user("HR", "HR", org_unit_id)
    hr_token = login(hr_email, hr_pw)
    manager_id, manager_email, manager_pw = create_test_user(
        "", "Manager", org_unit_id)
    manager_token = login(manager_email, manager_pw)
    ic_id, ic_email, ic_pw = create_test_user("", "IC", org_unit_id)
    ic_token = login(ic_email, ic_pw)
    requester_id, requester_email, requester_pw = create_test_user(
        "", "IC", org_unit_id)
    requester_token = login(requester_email, requester_pw)
    users_dict = {
        "admin": {"id": admin_id, "token": admin_token},
        "hr": {"id": hr_id, "token": hr_token},
        "manager": {"id": manager_id, "token": manager_token},
        "ic": {"id": ic_id, "token": ic_token},
        "requester": {"id": requester_id, "token": requester_token}
    }
    yield users_dict
    # Cleanup after tests
    from app.db.session import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    for user_key in ["admin", "hr", "manager", "ic", "requester"]:
        user_id = users_dict[user_key]["id"]
        try:
            # Delete audit logs
            db.execute(
                text("DELETE FROM audit_logs WHERE user_id = :user_id"), {
                    "user_id": str(user_id)})
            db.commit()
        except Exception:
            db.rollback()
        try:
            # Delete leave_balances
            db.execute(
                text("DELETE FROM leave_balances WHERE user_id = :user_id"), {
                    "user_id": str(user_id)})
            db.commit()
        except Exception:
            db.rollback()
        try:
            # Delete leave_requests (direct)
            db.execute(
                text("DELETE FROM leave_requests WHERE user_id = :user_id OR decided_by = :user_id"), {
                    "user_id": str(user_id)})
            db.commit()
        except Exception:
            db.rollback()
            # Fallback: delete from leave_documents and then leave_requests if
            # any remain
            remaining_requests = db.execute(
                text("SELECT id FROM leave_requests WHERE user_id = :user_id OR decided_by = :user_id"), {
                    "user_id": str(user_id)}).fetchall()
            if remaining_requests:
                print(
                    f"User {user_id} still referenced in leave_requests: {remaining_requests}")
                for req_id, in remaining_requests:
                    db.execute(
                        text("DELETE FROM leave_documents WHERE request_id = :req_id"), {
                            "req_id": str(req_id)})
                    db.commit()
                    db.execute(
                        text("DELETE FROM leave_requests WHERE id = :id"), {
                            "id": str(req_id)})
                    db.commit()
        try:
            # Nullify manager_id for users managed by this user
            db.execute(
                text("UPDATE users SET manager_id = NULL WHERE manager_id = :user_id"), {
                    "user_id": str(user_id)})
            db.commit()
        except Exception:
            db.rollback()
        # Final check for remaining leave_requests
        remaining_requests = db.execute(
            text("SELECT id FROM leave_requests WHERE user_id = :user_id OR decided_by = :user_id"), {
                "user_id": str(user_id)}).fetchall()
        if remaining_requests:
            print(
                f"User {user_id} still referenced in leave_requests: {remaining_requests}")
        # Delete user via API
        from fastapi.testclient import TestClient
        client = TestClient(app)
        admin_token = users_dict["admin"]["token"]
        resp = client.delete(
            f"/api/v1/users/{user_id}",
            headers={
                "Authorization": f"Bearer {admin_token}"})
        if resp.status_code not in (200, 204, 404):
            print(
                f"Failed to delete user {user_id}, status: {
                    resp.status_code}")
        try:
            db.execute(
                text("DELETE FROM leave_requests WHERE user_id = :user_id"), {
                    "user_id": str(user_id)})
            db.commit()
        except Exception:
            db.rollback()
        # Delete user via API (soft/hard)
        resp = client.delete(
            f"/api/v1/users/{user_id}",
            headers={
                "Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in (200, 204, 404)
    db.close()
