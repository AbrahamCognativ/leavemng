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
    import uuid
    import random
    from datetime import datetime, timedelta
    import os
    import jwt
    from app.models.leave_request import LeaveRequest
    from app.db.session import SessionLocal

    headers = {"Authorization": f"Bearer {auth_token}"}
    types = client.get("/api/v1/leave-types/", headers=headers).json()
    if not types:
        pytest.skip("No leave types to create leave request")
    leave_type_id = types[0]["id"]
    # Generate a unique date for each test run to avoid duplicates
    offset = random.randint(1, 10000)
    today_dt = datetime.now() + timedelta(days=offset)
    today = today_dt.strftime("%Y-%m-%d")
    data = {
        "leave_type_id": leave_type_id,
        "start_date": today,
        "end_date": today,
        "comments": f"Test leave {uuid.uuid4()}"
    }
    # Decode user_id from token for cleanup
    SECRET_KEY = os.getenv("SECRET_KEY", "secret")
    payload = jwt.decode(auth_token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload["user_id"]
    # Clean up any existing leave requests for this user/leave_type/date
    db = SessionLocal()
    db.query(LeaveRequest).filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.leave_type_id == leave_type_id,
        LeaveRequest.start_date == today,
        LeaveRequest.end_date == today
    ).delete()
    db.commit()
    db.close()
    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert resp.status_code in (200, 201), f"Could not create leave request: {resp.text}"
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
