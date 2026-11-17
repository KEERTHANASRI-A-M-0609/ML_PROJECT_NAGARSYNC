"""
backend/tests/test_api.py — API smoke tests.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app import db, users
from backend.app.main import app
from backend.app.auth import require_admin, require_field

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    original_store = users._STORE
    original_users_col = users._col
    original_get_db = db.get_db
    original_ping = db.ping
    original_last_error = db.last_error
    users._STORE = tmp_path_factory.mktemp("api-users") / "users.json"
    users._col = lambda: None
    db.get_db = lambda: None
    db.ping = lambda: False
    db.last_error = lambda: "Database unavailable in test"
    try:
        users.create_managed_user(
            "test-admin@nagarsync.test",
            "LocalApiPassword2026!",
            "admin",
            "Test Admin",
        )
        with TestClient(app) as c:
            login = c.post("/api/auth/login", json={
                "email": "test-admin@nagarsync.test",
                "password": "LocalApiPassword2026!",
            })
            assert login.status_code == 200
            c.headers["Authorization"] = f"Bearer {login.json()['token']}"
            yield c
    finally:
        users._STORE = original_store
        users._col = original_users_col
        db.get_db = original_get_db
        db.ping = original_ping
        db.last_error = original_last_error


@pytest.fixture
def admin_client(client):
    admin = {"sub": "test-admin", "email": "test-admin@nagarsync.test", "role": "admin", "name": "Test Admin"}
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[require_field] = lambda: admin
    yield client
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(require_field, None)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_summary(client):
    r = client.get("/api/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total_assets" in data
    assert data["total_assets"] > 0
    metrics = data["research_metrics"]
    assert metrics["digonce_failure_reduction_vs_reactive_pct"] is not None
    assert metrics["spend_difference_vs_ml_per_rupee_lakh"] is not None
    assert metrics["calibrated_ece"] is not None


def test_corridors(client):
    r = client.get("/api/corridors")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "corridor_id" in data[0]


def test_assets(client):
    r = client.get("/api/assets?limit=10")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) <= 10


def test_asset_detail(client):
    assets = client.get("/api/assets?limit=1").json()
    if not assets:
        pytest.skip("No assets")
    aid = assets[0]["asset_id"]
    r = client.get(f"/api/assets/{aid}")
    assert r.status_code == 200
    data = r.json()
    assert data["asset_id"] == aid
    assert "attribution" in data


def test_asset_not_found(client):
    r = client.get("/api/assets/NONEXISTENT")
    assert r.status_code == 404


def test_wards(client):
    r = client.get("/api/wards")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_leaks(client):
    r = client.get("/api/leaks")
    assert r.status_code == 200


def test_experiments(admin_client):
    r = admin_client.get("/api/experiments")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data


def test_plan(admin_client):
    r = admin_client.post("/api/plan", json={
        "budget_lakh": 1000,
        "strategy": "ml_per_rupee",
        "mobilisation_scale": 1.0,
        "min_ward_share": 0.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert "selected_count" in data
    assert data["planned_spend"] <= 1000 + 1.0  # allow tiny float tolerance


def test_plan_digonce(admin_client):
    r = admin_client.post("/api/plan", json={
        "budget_lakh": 2000,
        "strategy": "digonce_ilp",
        "mobilisation_scale": 1.0,
        "min_ward_share": 0.0,
    })
    assert r.status_code == 200


def test_score(admin_client):
    assets = admin_client.get("/api/assets?limit=1").json()
    if not assets:
        pytest.skip("No assets")
    r = admin_client.post("/api/score", json={"asset_id": assets[0]["asset_id"]})
    assert r.status_code == 200


def test_admin_routes_require_auth(client):
    no_auth = {"Authorization": ""}
    assert client.get("/api/experiments", headers=no_auth).status_code == 401
    assert client.post("/api/plan", json={"budget_lakh": 1000}, headers=no_auth).status_code == 401
    assert client.get("/api/admin/audit", headers=no_auth).status_code == 401


def test_admin_audit_route(admin_client, monkeypatch, tmp_path):
    from backend.app import audit

    monkeypatch.setattr(audit, "_STORE", tmp_path / "audit.json")
    monkeypatch.setattr(audit, "_col", lambda: None)
    response = admin_client.get("/api/admin/audit?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_public_registration_cannot_create_admin(client, monkeypatch, tmp_path):
    from backend.app import users

    monkeypatch.setattr(users, "_STORE", tmp_path / "users.json")
    monkeypatch.setattr(users, "_col", lambda: None)
    response = client.post("/api/auth/register", json={
        "email": "citizen@example.test",
        "password": "a-strong-password",
        "name": "Test Citizen",
        "role": "admin",
    })
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "citizen"
    assert "password_hash" not in response.json()["user"]
    assert "token" not in response.json()
    assert client.get("/api/auth/me", headers={"Authorization": ""}).status_code == 401
    duplicate = client.post("/api/auth/register", json={
        "email": "citizen@example.test",
        "password": "a-different-password",
        "name": "Duplicate Citizen",
    })
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Email already registered"

    login = client.post("/api/auth/login", json={
        "email": "citizen@example.test",
        "password": "a-strong-password",
    })
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "citizen"

    monkeypatch.setenv("NAGARSYNC_BOOTSTRAP_KEY", "unit-test-one-time-key")
    bootstrap = client.post("/api/auth/bootstrap", json={
        "email": "admin@example.test",
        "password": "another-strong-password",
        "name": "Test Administrator",
        "bootstrap_key": "unit-test-one-time-key",
    })
    assert bootstrap.status_code == 200
    assert bootstrap.json()["user"]["role"] == "admin"
    assert "token" not in bootstrap.json()
    assert client.get("/api/auth/me", headers={"Authorization": ""}).status_code == 401
    admin_login = client.post("/api/auth/login", json={
        "email": "admin@example.test",
        "password": "another-strong-password",
    })
    assert admin_login.status_code == 200
    assert admin_login.json()["user"]["role"] == "admin"


def test_admin_managed_assets_create_update_archive_restore(admin_client, monkeypatch, tmp_path):
    from backend.app import admin_assets

    monkeypatch.setattr(admin_assets, "_STORE", tmp_path / "managed_assets.json")
    payload = {
        "name": "North Ward pump station",
        "asset_type": "water_pump",
        "district": "Chennai",
        "ward": 4,
        "lat": 13.08,
        "lon": 80.27,
        "age_years": 12,
        "condition_score": 0.7,
        "criticality": 4,
        "work_cost_lakh": 3.5,
    }

    created = admin_client.post("/api/admin/assets", json=payload)
    assert created.status_code == 200
    asset_id = created.json()["id"]
    assert created.json()["model_status"] == "unscored_manual_record"

    updated_payload = {**payload, "name": "North Ward water pump"}
    updated = admin_client.put(f"/api/admin/assets/{asset_id}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["name"] == "North Ward water pump"

    archived = admin_client.post(f"/api/admin/assets/{asset_id}/archive")
    assert archived.status_code == 200
    assert admin_client.get("/api/admin/assets").json() == []
    assert len(admin_client.get("/api/admin/assets?include_archived=true").json()) == 1

    restored = admin_client.post(f"/api/admin/assets/{asset_id}/restore")
    assert restored.status_code == 200
    assert len(admin_client.get("/api/admin/assets").json()) == 1


def test_admin_report_edit_archive_restore(admin_client, monkeypatch, tmp_path):
    from backend.app import reports

    monkeypatch.setattr(reports, "_STORE", tmp_path / "reports.json")
    monkeypatch.setattr(reports, "_col", lambda: None)
    report = reports.create_report(
        citizen_id="test-citizen",
        citizen_name="Test Citizen",
        category="pothole",
        description="A road surface issue",
        lat=13.0,
        lon=80.0,
        location_text="North road",
        image_filename=None,
        image_data_url=None,
    )
    updated = admin_client.put(f"/api/reports/{report['id']}", json={
        "category": "streetlight",
        "description": "A damaged streetlight",
        "location_text": "Market road",
        "lat": 13.1,
        "lon": 80.1,
    })
    assert updated.status_code == 200
    assert updated.json()["category"] == "streetlight"

    assert admin_client.post(f"/api/reports/{report['id']}/archive").status_code == 200
    assert reports.list_reports() == []
    assert len(reports.list_reports(include_archived=True)) == 1
    assert admin_client.post(f"/api/reports/{report['id']}/restore").status_code == 200
    assert len(reports.list_reports()) == 1


def test_admin_incident_edit_archive_restore(admin_client, monkeypatch, tmp_path):
    from backend.app import incidents

    monkeypatch.setattr(incidents, "_STORE", tmp_path / "incidents.json")
    monkeypatch.setattr(incidents, "_col", lambda: None)
    incident = incidents.create_incident(
        asset_id=None,
        report_id=None,
        title="Inspect road damage",
        description="Inspect the reported road section",
        severity="medium",
        created_by="test-admin",
    )
    updated = admin_client.put(f"/api/incidents/{incident['id']}", json={
        "title": "Repair road surface",
        "description": "Schedule a surface repair",
        "severity": "high",
        "district": "Chennai",
        "asset_type": "road",
    })
    assert updated.status_code == 200
    assert updated.json()["title"] == "Repair road surface"

    assert admin_client.post(f"/api/incidents/{incident['id']}/archive").status_code == 200
    assert incidents.list_incidents() == []
    assert len(incidents.list_incidents(include_archived=True)) == 1
    assert admin_client.post(f"/api/incidents/{incident['id']}/restore").status_code == 200
    assert len(incidents.list_incidents()) == 1


def test_mongodb_connection_failure_uses_retry_backoff(monkeypatch):
    import pymongo
    import backend.app.db as db

    calls = []

    class UnavailableMongoClient:
        def __init__(self, uri, serverSelectionTimeoutMS):
            calls.append(uri)

        @property
        def admin(self):
            return self

        def command(self, name):
            raise OSError("database unavailable")

    now = [100.0]
    monkeypatch.setenv("MONGODB_URI", "mongodb://unavailable.example.test")
    monkeypatch.setattr(pymongo, "MongoClient", UnavailableMongoClient)
    monkeypatch.setattr(db.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(db, "_client", None)
    monkeypatch.setattr(db, "_last_error", None)
    monkeypatch.setattr(db, "_failed_uri", None)
    monkeypatch.setattr(db, "_failed_at", None)

    assert db.get_client() is None
    assert db.get_client() is None
    assert len(calls) == 1

    now[0] += 31
    assert db.get_client() is None
    assert len(calls) == 2
