"""
backend/tests/test_workflows.py — End-to-end multi-role lifecycle tests:
1. Citizen: Register → Login → Submit Report with photo & GPS → Track status.
2. Admin: Review priority attention → Triage & Accept Report → Auto-create Incident → Assign to Field Worker.
3. Field Worker: View Assigned job → Start work (IN_PROGRESS) → Add completion photo evidence → Submit completion.
4. Admin: Verify completion evidence → Close incident.
5. Notification & RBAC verification.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import users, reports, incidents, notifications, audit


@pytest.fixture(autouse=True)
def reset_stores(tmp_path, monkeypatch):
    """Use isolated temporary file stores for testing."""
    users_file = tmp_path / "users.json"
    reports_file = tmp_path / "reports.json"
    incidents_file = tmp_path / "incidents.json"
    notifs_file = tmp_path / "notifications.json"
    audit_file = tmp_path / "audit.json"

    monkeypatch.setattr(users, "_STORE", users_file)
    monkeypatch.setattr(users, "_col", lambda: None)
    monkeypatch.setattr(reports, "_STORE", reports_file)
    monkeypatch.setattr(reports, "_col", lambda: None)
    monkeypatch.setattr(incidents, "_STORE", incidents_file)
    monkeypatch.setattr(incidents, "_col", lambda: None)
    monkeypatch.setattr(notifications, "_STORE", notifs_file)
    monkeypatch.setattr(notifications, "_col", lambda: None)
    monkeypatch.setattr(audit, "_STORE", audit_file)
    monkeypatch.setattr(audit, "_col", lambda: None)

    users.create_managed_user(
        "admin@nagarsync.test", "TestAdminPassword2026!", "admin", "Test Administrator"
    )
    users.create_managed_user(
        "worker@nagarsync.test", "TestWorkerPassword2026!", "field_worker", "Test Field Worker"
    )


def test_complete_end_to_end_repair_lifecycle():
    client = TestClient(app)

    # ── 1. Citizen registers and logs in ─────────────────────────────────────
    reg_res = client.post("/api/auth/register", json={
        "email": "priya.citizen@nagarsync.test",
        "password": "StrongPassword2026!",
        "name": "Priya Sundaram",
    })
    assert reg_res.status_code == 200
    assert reg_res.json()["user"]["role"] == "citizen"

    cit_login = client.post("/api/auth/login", json={
        "email": "priya.citizen@nagarsync.test",
        "password": "StrongPassword2026!",
    })
    assert cit_login.status_code == 200
    cit_token = cit_login.json()["token"]
    cit_headers = {"Authorization": f"Bearer {cit_token}"}

    # ── 2. Citizen captures/submits report with location ────────────────────
    report_res = client.post("/api/reports", headers=cit_headers, json={
        "category": "pothole",
        "description": "Deep asphalt fissure near junction, hazardous to two-wheelers.",
        "lat": 13.0827,
        "lon": 80.2707,
        "location_text": "Anna Salai near Mount Road Junction",
    })
    assert report_res.status_code == 200
    rep_data = report_res.json()["report"]
    report_id = rep_data["id"]
    assert report_id.startswith("RPT-")
    assert rep_data["status"] == "new"

    # Verify duplicate detection flag exists
    assert "possible_duplicates" in report_res.json()

    # ── 3. Admin logs in and reviews attention areas ─────────────────────────
    admin_login = client.post("/api/auth/login", json={
        "email": "admin@nagarsync.test",
        "password": "TestAdminPassword2026!",
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Check attention areas
    att_res = client.get("/api/attention?limit=10", headers=admin_headers)
    assert att_res.status_code == 200
    assert "items" in att_res.json()
    assert "corridor_clusters" in att_res.json()

    # ── 4. Admin triages & accepts report → auto-creates incident ────────────
    triage_res = client.patch(f"/api/reports/{report_id}", headers=admin_headers, json={
        "status": "triaged",
        "note": "Verified by municipal operations triage desk.",
    })
    assert triage_res.status_code == 200
    assert triage_res.json()["status"] == "triaged"

    accept_res = client.patch(f"/api/reports/{report_id}", headers=admin_headers, json={
        "status": "accepted",
        "note": "Report accepted; incident created for immediate road crew dispatch.",
    })
    assert accept_res.status_code == 200
    updated_rep = client.get(f"/api/reports/{report_id}", headers=admin_headers).json()
    assert updated_rep["status"] == "accepted"
    incident_id = updated_rep.get("incident_id")
    assert incident_id is not None
    assert incident_id.startswith("INC-")

    # ── 5. Admin assigns incident to registered Field Engineer ───────────────
    # Fetch field worker user id
    worker_user = users.get_user_by_id(
        users.login("worker@nagarsync.test", "TestWorkerPassword2026!")["user"]["id"]
    )
    worker_id = worker_user["id"]

    assign_res = client.patch(f"/api/incidents/{incident_id}", headers=admin_headers, json={
        "status": "ASSIGNED",
        "assigned_to": worker_id,
        "note": "Assigned to road maintenance unit 4.",
    })
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == "ASSIGNED"
    assert assign_res.json()["assigned_to"] == worker_id

    # ── 6. Field Worker logs in and views assigned work ──────────────────────
    work_login = client.post("/api/auth/login", json={
        "email": "worker@nagarsync.test",
        "password": "TestWorkerPassword2026!",
    })
    assert work_login.status_code == 200
    work_token = work_login.json()["token"]
    work_headers = {"Authorization": f"Bearer {work_token}"}

    # Worker lists assigned jobs
    my_jobs = client.get("/api/incidents", headers=work_headers).json()
    assert any(j["id"] == incident_id for j in my_jobs)

    # Worker checks notifications
    worker_notifs = client.get("/api/notifications", headers=work_headers).json()
    assert any("Assigned" in n["title"] for n in worker_notifs)

    # Worker starts work (IN_PROGRESS)
    start_res = client.patch(f"/api/incidents/{incident_id}", headers=work_headers, json={
        "status": "IN_PROGRESS",
        "note": "Field crew arrived on site with asphalt patch equipment.",
    })
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "IN_PROGRESS"

    # Worker adds completion evidence
    ev_res = client.post(f"/api/incidents/{incident_id}/evidence", headers=work_headers, json={
        "evidence_url": "patch_completed_photo_01.jpg",
        "note": "Filled 50mm depression, compacted with vibro-roller, road open.",
    })
    assert ev_res.status_code == 200
    assert len(ev_res.json()["evidence"]) > 0

    # Worker submits for verification
    sub_res = client.patch(f"/api/incidents/{incident_id}", headers=work_headers, json={
        "status": "COMPLETION_SUBMITTED",
        "note": "Pothole filled and sealed; ready for inspection verification.",
    })
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "COMPLETION_SUBMITTED"

    # ── 7. Admin verifies evidence and closes incident ───────────────────────
    # Admin cannot verify without evidence (already tested, here evidence exists)
    ver_res = client.patch(f"/api/incidents/{incident_id}", headers=admin_headers, json={
        "status": "VERIFIED",
        "note": "Evidence photo reviewed and verified by municipal engineer.",
    })
    assert ver_res.status_code == 200
    assert ver_res.json()["status"] == "VERIFIED"

    close_res = client.patch(f"/api/incidents/{incident_id}", headers=admin_headers, json={
        "status": "CLOSED",
        "note": "Work order closed.",
    })
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "CLOSED"

    # ── 8. Citizen receives status notifications ─────────────────────────────
    cit_notifs = client.get("/api/notifications", headers=cit_headers).json()
    assert len(cit_notifs) > 0
    assert any("in progress" in item["message"] for item in cit_notifs)

    audit_events = client.get("/api/admin/audit?limit=100", headers=admin_headers)
    assert audit_events.status_code == 200
    assert any(event["entity_id"] == report_id and event["action"] == "status_changed" for event in audit_events.json())
    assert any(event["entity_id"] == incident_id and event["action"] == "status_changed" for event in audit_events.json())


def test_evidence_required_before_verification():
    """Ensure state machine strictly prevents VERIFIED state without prior completion evidence."""
    client = TestClient(app)

    admin_login = client.post("/api/auth/login", json={
        "email": "admin@nagarsync.test",
        "password": "TestAdminPassword2026!",
    })
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create unverified incident directly
    inc = client.post("/api/incidents", headers=admin_headers, json={
        "title": "Bridge joint check",
        "description": "Routine joint inspection",
        "severity": "medium",
    }).json()

    # Attempt to transition to VERIFIED without any evidence attached
    bad_res = client.patch(f"/api/incidents/{inc['id']}", headers=admin_headers, json={
        "status": "VERIFIED",
        "note": "Premature verification attempt",
    })
    assert bad_res.status_code == 409
    assert "evidence is required" in bad_res.json()["detail"].lower()
