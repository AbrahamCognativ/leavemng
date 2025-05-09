import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from app.run import app

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
    resp = client.post("/api/v1/users/", json=user_data, headers={"Authorization": f"Bearer {get_admin_token()}"})
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
    admin_id, admin_email, admin_pw = create_test_user("Admin", "Admin", org_unit_id)
    admin_token = login(admin_email, admin_pw)
    hr_id, hr_email, hr_pw = create_test_user("HR", "HR", org_unit_id)
    hr_token = login(hr_email, hr_pw)
    manager_id, manager_email, manager_pw = create_test_user("", "Manager", org_unit_id)
    manager_token = login(manager_email, manager_pw)
    ic_id, ic_email, ic_pw = create_test_user("", "IC", org_unit_id)
    ic_token = login(ic_email, ic_pw)
    requester_id, requester_email, requester_pw = create_test_user("", "IC", org_unit_id)
    requester_token = login(requester_email, requester_pw)
    return {
        "admin": {"id": admin_id, "token": admin_token},
        "hr": {"id": hr_id, "token": hr_token},
        "manager": {"id": manager_id, "token": manager_token},
        "ic": {"id": ic_id, "token": ic_token},
        "requester": {"id": requester_id, "token": requester_token}
    }
