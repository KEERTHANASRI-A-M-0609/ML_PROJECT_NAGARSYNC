from fastapi.testclient import TestClient

from backend.app import admin_assets, governance, incidents, main, reports, users
from backend.app.seed_demo_governance import seed_demo_governance


def _use_local_stores(monkeypatch, tmp_path):
    for module, name in (
        (users, "users.json"),
        (reports, "reports.json"),
        (incidents, "incidents.json"),
    ):
        monkeypatch.setattr(module, "_STORE", tmp_path / name)
        monkeypatch.setattr(module, "_col", lambda: None)
    monkeypatch.setattr(admin_assets, "_STORE", tmp_path / "managed_assets.json")
    monkeypatch.delenv("MONGODB_URI", raising=False)


def test_governance_seed_is_local_idempotent_and_visible(monkeypatch, tmp_path):
    _use_local_stores(monkeypatch, tmp_path)

    assert seed_demo_governance() == 35
    assert seed_demo_governance() == 0

    state = governance.state_overview()
    assert state["total_districts"] == 37
    assert state["total_reports"] == 15
    assert state["total_work_orders"] == 10
    assert state["resolved_work_orders"] == 2
    assert state["sample_records"] == 25
    assert len(state["districts"]) == 37
    assert next(item for item in state["districts"] if item["district"] == "Salem")["total_reports"] == 1
    assets = admin_assets.list_assets()
    assert len(assets) == 10
    assert all(item["is_demo_sample"] for item in assets)
    assert len(reports.list_reports(limit=1000)) == 15
    assert len(incidents.list_incidents(limit=1000)) == 10

    area = governance.area_overview(
        "Chennai",
        "Demo Taluk - Chennai",
        "Demo Municipal Council - Chennai",
        "Demo Ward 01",
    )
    assert area["total_reports"] == 1
    assert area["total_work_orders"] == 1
    assert area["resolved"] == 1
    assert area["sample_records"] == 2
    assert area["resolved_work"][0]["is_demo_sample"] is True
    assert area["resource_monitoring"] == {"streetlight": 1}
    assert "no live sensor" in area["resource_note"]


def test_login_uses_authenticated_account_role_without_portal_selection(monkeypatch, tmp_path):
    _use_local_stores(monkeypatch, tmp_path)
    users.create_managed_user("resident@example.test", "ResidentPassword2026!", "citizen", "Resident")
    users.create_managed_user("admin@example.test", "AdminPassword2026!", "admin", "Administrator")
    client = TestClient(main.app)

    assert client.post(
        "/api/auth/login",
        json={"email": "resident@example.test", "password": "ResidentPassword2026!", "expected_role": "admin"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": "admin@example.test", "password": "AdminPassword2026!", "expected_role": "citizen"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": "resident@example.test", "password": "ResidentPassword2026!", "expected_role": "citizen"},
    ).status_code == 200
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.test", "password": "AdminPassword2026!"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"
