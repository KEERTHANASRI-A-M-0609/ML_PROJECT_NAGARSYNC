import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.app import db, main, services, users


@pytest.fixture
def protected_client(monkeypatch, tmp_path):
    monkeypatch.setattr(users, "_STORE", tmp_path / "users.json")
    monkeypatch.setattr(users, "_col", lambda: None)
    monkeypatch.setattr(db, "ping", lambda: False)
    monkeypatch.setattr(db, "last_error", lambda: "Database unavailable in test")
    monkeypatch.setattr(services, "_runtime_ready", False)
    monkeypatch.setattr(services, "_runtime_error", RuntimeError("Analytics disabled in test"))

    def unavailable_runtime():
        raise RuntimeError("Analytics disabled in test")

    monkeypatch.setattr(main, "initialize_runtime", unavailable_runtime)
    users.create_managed_user(
        "portal-admin@example.test",
        "PortalAdminPassword2026!",
        "admin",
        "Portal Administrator",
    )
    with TestClient(main.app) as client:
        yield client


def test_data_api_requires_a_valid_session(protected_client):
    unauthenticated = protected_client.get("/api/health")
    assert unauthenticated.status_code == 401

    login = protected_client.post(
        "/api/auth/login",
        json={
            "email": "portal-admin@example.test",
            "password": "PortalAdminPassword2026!",
        },
    )
    assert login.status_code == 200
    token = login.json()["token"]

    authenticated = protected_client.get(
        "/api/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert authenticated.status_code == 503
    assert authenticated.json()["service"] == "analytics"

    invalid = protected_client.get(
        "/api/health",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert invalid.status_code == 401


def test_live_websocket_requires_a_session(protected_client):
    with pytest.raises(WebSocketDisconnect):
        with protected_client.websocket_connect("/ws/live"):
            pass
