import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from app.run import app
from .test_utils import (
    create_auth_headers,
    login_user,
    create_user_data,
    cleanup_user_data,
    create_users_dict_with_requester,
    cleanup_users_dict
)

client = TestClient(app)


def create_test_user(role_band, role_title, org_unit_id):
    email = f"{role_title.lower()}_{uuid4()}@test.com"
    user_data = create_user_data(
        name=f"{role_title} User",
        email=email,
        password="adminpass",
        role_band=role_band,
        role_title=role_title,
        org_unit_id=org_unit_id
    )
    headers = create_auth_headers(get_admin_token())
    resp = client.post("/api/v1/users/", json=user_data, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"], email, user_data["password"]


def login(email, password):
    return login_user(email, password)


def get_admin_token():
    return login_user("user@example.com", "secret123")


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

    users_dict = create_users_dict_with_requester(
        admin_token, hr_token, manager_token, ic_token, requester_token,
        admin_id, hr_id, manager_id, ic_id, requester_id
    )

    yield users_dict

    # Cleanup after tests
    cleanup_users_dict(
        users_dict, [
            "admin", "hr", "manager", "ic", "requester"])
