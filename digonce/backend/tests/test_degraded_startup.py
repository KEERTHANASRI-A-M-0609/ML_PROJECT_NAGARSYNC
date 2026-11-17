from fastapi.testclient import TestClient

from backend.app import db, main, services, users


def test_authentication_survives_analytics_startup_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(users, "_STORE", tmp_path / "users.json")
    monkeypatch.setattr(users, "_col", lambda: None)
    monkeypatch.setattr(services, "_runtime_ready", False)
    monkeypatch.setattr(services, "_runtime_error", None)
    monkeypatch.setattr(db, "ping", lambda: False)
    monkeypatch.setattr(db, "last_error", lambda: "Database unavailable in test")
    users.create_managed_user(
        "municipal-admin@example.test",
        "LocalAdminPassword2026!",
        "admin",
        "Municipal Administrator",
    )

    def fail_analytics_startup():
        raise ImportError("A native analytics dependency was blocked")

    monkeypatch.setattr(main, "initialize_runtime", fail_analytics_startup)

    with TestClient(main.app) as client:
        login = client.post(
            "/api/auth/login",
            json={
                "email": "municipal-admin@example.test",
                "password": "LocalAdminPassword2026!",
            },
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        health = client.get("/api/health", headers=headers)
        summary = client.get("/api/summary", headers=headers)

    assert health.status_code == 200
    assert health.json()["analytics"]["available"] is False
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "admin"
    assert summary.status_code == 503
    assert summary.json()["service"] == "analytics"
