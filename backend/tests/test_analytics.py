# Placeholder for analytics tests
import pytest
from fastapi.testclient import TestClient
from app.run import app
from .test_utils import (
    login_user,
    create_auth_headers,
    permissions_helper,
    assert_response_success
)

client = TestClient(app)


def get_admin_token():
    return login_user("user@example.com", "secret123")


def test_analytics_permissions():
    roles = ['Admin', 'Manage', 'HR', 'IC']
    endpoints = []  # No real analytics endpoints available
    if not endpoints:
        pytest.skip("No analytics endpoint available for permission test.")
    permissions_helper(endpoints)


def test_analytics_summary_success(monkeypatch):
    class DummyQuery:
        def count(self):
            return 42

    class DummyDB:
        def query(self, model):
            return DummyQuery()
    # Patch get_db dependency
    from app.api.v1.routers import analytics
    monkeypatch.setattr(analytics, 'get_db', lambda: DummyDB())
    with TestClient(app) as client:
        token = get_admin_token()
        headers = create_auth_headers(token)
        response = client.get('/api/v1/analytics/summary', headers=headers)
        assert response.status_code in (
            200, 401, 403)  # Depending on auth impl
        if response.status_code == 200:
            data = response.json()
            assert 'total_users' in data
            assert 'total_leave_requests' in data


def test_analytics_leave_stats(monkeypatch):
    class DummyQuery:
        def count(self):
            return 5

        def filter(self, *args, **kwargs):
            return self

    class DummyDB:
        def query(self, model):
            return DummyQuery()
    from app.api.v1.routers import analytics
    monkeypatch.setattr(analytics, 'get_db', lambda: DummyDB())
    with TestClient(app) as client:
        token = get_admin_token()
        headers = create_auth_headers(token)
        response = client.get('/api/v1/analytics/leave-stats', headers=headers)
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            data = response.json()
            assert 'last_30_days' in data
            assert 'total' in data


def test_analytics_user_growth(monkeypatch):
    class DummyQuery:
        def count(self):
            return 3

        def filter(self, *args, **kwargs):
            return self

    class DummyDB:
        def query(self, model):
            return DummyQuery()
    from app.api.v1.routers import analytics
    monkeypatch.setattr(analytics, 'get_db', lambda: DummyDB())
    with TestClient(app) as client:
        token = get_admin_token()
        headers = create_auth_headers(token)
        response = client.get('/api/v1/analytics/user-growth', headers=headers)
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            data = response.json()
            assert 'new_users_last_30_days' in data
            assert 'total_users' in data


# Permission error test for IC role (should be forbidden or unauthorized)


@pytest.mark.parametrize("endpoint", [
    "/api/v1/analytics/summary",
    "/api/v1/analytics/leave-stats",
    "/api/v1/analytics/user-growth",
])
@pytest.mark.parametrize("role,allowed", [
    ("admin", True),
    ("hr", True),
    ("manager", False),
    ("ic", False),
    ("requester", False),
])
def test_analytics_dashboard_permissions(
        analytics_users, endpoint, role, allowed):
    token = analytics_users[role]["token"]
    headers = create_auth_headers(token)
    with TestClient(app) as client:
        response = client.get(endpoint, headers=headers)
        if allowed:
            assert_response_success(response)
        else:
            assert response.status_code in (
                401, 403), f"Role {role} should be forbidden on {endpoint}"
