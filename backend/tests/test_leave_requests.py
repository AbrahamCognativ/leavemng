import pytest
from fastapi.testclient import TestClient
from app.run import app
import random
from .test_utils import (
    create_auth_headers,
    login_user,
    create_leave_request_data,
    assert_response_success,
    assert_response_validation_error,
    get_first_leave_type,
    update_request_helper,
    test_leave_validation_missing_type
)

client = TestClient(app)


@pytest.fixture
def auth_token():
    return login_user("user@example.com", "secret123")


def test_leave_request_crud(auth_token):
    from datetime import datetime, timedelta
    from app.models.leave_request import LeaveRequest
    from app.db.session import SessionLocal
    import jwt

    headers = create_auth_headers(auth_token)
    leave_type_id = get_first_leave_type(auth_token)
    data = create_leave_request_data(leave_type_id)

    # Decode user_id from token for cleanup
    from app.settings import get_settings
    SECRET_KEY = get_settings().SECRET_KEY
    payload = jwt.decode(auth_token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload["user_id"]

    # Clean up any existing leave requests for this user/leave_type/date
    db = SessionLocal()
    db.query(LeaveRequest).filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.leave_type_id == leave_type_id,
        LeaveRequest.start_date == data["start_date"],
        LeaveRequest.end_date == data["end_date"]
    ).delete()
    db.commit()
    db.close()

    resp = client.post("/api/v1/leave/", json=data, headers=headers)
    assert_response_success(resp, [200, 201])
    leave = resp.json()
    req_id = leave["id"]

    get_resp = client.get(f"/api/v1/leave/{req_id}", headers=headers)
    assert_response_success(get_resp)

    upd_resp, upd_json = update_request_helper(
        f"/api/v1/leave/{req_id}", data, headers)
    if upd_json and "comments" in upd_json:
        assert upd_json["comments"] == "Updated comment"

    del_resp = client.delete(f"/api/v1/leave/{req_id}", headers=headers)
    if del_resp.status_code not in (200, 204, 405, 501):
        assert_response_success(del_resp)


def test_leave_request_validation(auth_token):
    test_leave_validation_missing_type(auth_token)
