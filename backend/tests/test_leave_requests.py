import pytest
import uuid
from fastapi.testclient import TestClient
from app.run import app

client = TestClient(app)

@pytest.fixture
def auth_token():
    response = client.post("/api/v1/auth/login", data={"username": "user@example.com", "password": "secret123"})
    assert response.status_code == 200
    return response.json()["access_token"]

def test_leave_request_crud(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    types = client.get("/api/v1/leave-types/", headers=headers).json()
    if not types:
        pytest.skip("No leave types to create leave request")
    leave_type_id = types[0]["id"]
    today = "2025-05-05"
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": f"Test leave {uuid.uuid4()}"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code in (200, 201)
    leave = resp.json()
    req_id = leave["id"]
    get_resp = client.get(f"/api/v1/leave/{req_id}", headers=headers)
    assert get_resp.status_code == 200
    upd_data = data.copy()
    upd_data["comments"] = "Updated comment"
    upd_resp = client.put(f"/api/v1/leave/{req_id}", json=upd_data, headers=headers)
    if upd_resp.status_code not in (405, 501):
        assert upd_resp.status_code == 200
        assert upd_resp.json()["comments"] == "Updated comment"
    del_resp = client.delete(f"/api/v1/leave/{req_id}", headers=headers)
    if del_resp.status_code not in (200, 204, 405, 501):
        assert del_resp.status_code == 200

def test_leave_request_validation(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    data = {
        "start_date": "2025-05-05",
        "end_date": "2025-05-05",
        "comments": "No leave_type_id"
    }
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code == 422
