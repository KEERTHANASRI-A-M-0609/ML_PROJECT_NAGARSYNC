from fastapi.testclient import TestClient

from backend.app import audit, community, incidents, main, notifications, reports, users


def test_area_reports_are_public_scoped_and_engagement_is_private_safe(monkeypatch, tmp_path):
    stores = {
        "users": (users, "_STORE", "users.json"),
        "reports": (reports, "_STORE", "reports.json"),
        "incidents": (incidents, "_STORE", "incidents.json"),
        "notifications": (notifications, "_STORE", "notifications.json"),
        "audit": (audit, "_STORE", "audit.json"),
        "community": (community, "_STORE", "community.json"),
    }
    for _, (module, store_name, filename) in stores.items():
        monkeypatch.setattr(module, store_name, tmp_path / filename)
        if hasattr(module, "_col"):
            monkeypatch.setattr(module, "_col", lambda *args: None)

    users.create_managed_user("resident-a@example.test", "ResidentPassword2026!", "citizen", "Resident A")
    users.create_managed_user("resident-b@example.test", "ResidentPassword2026!", "citizen", "Resident B")
    users.create_managed_user("resident-c@example.test", "ResidentPassword2026!", "citizen", "Resident C")
    users.create_managed_user("administrator@example.test", "AdminPassword2026!", "admin", "Area Administrator")

    client = TestClient(main.app)

    def login(email, password):
        response = client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}

    resident_a = login("resident-a@example.test", "ResidentPassword2026!")
    resident_b = login("resident-b@example.test", "ResidentPassword2026!")
    resident_c = login("resident-c@example.test", "ResidentPassword2026!")
    admin = login("administrator@example.test", "AdminPassword2026!")

    area = {"district": "Chennai", "taluk": "Mylapore", "local_body": "Chennai Corporation", "ward": "Ward 123"}
    assert client.put("/api/community/subscription", headers=resident_b, json=area).status_code == 200
    response = client.post(
        "/api/reports",
        headers=resident_a,
        json={
            "category": "streetlight",
            "description": "Streetlight has been out for three nights.",
            "location_text": "Near the public library",
            "lat": 13.04,
            "lon": 80.27,
            **area,
        },
    )
    assert response.status_code == 200
    report_id = response.json()["report"]["id"]
    assert any("New infrastructure report" in item["title"] for item in client.get("/api/notifications", headers=resident_b).json())

    scoped = client.get(
        "/api/community/reports",
        headers=resident_b,
        params=area,
    )
    assert scoped.status_code == 200
    assert len(scoped.json()) == 1
    public_report = scoped.json()[0]
    assert public_report["id"] == report_id
    assert "citizen_id" not in public_report
    assert "citizen_name" not in public_report
    assert "lat" not in public_report
    assert "lon" not in public_report
    assert client.get(
        "/api/community/reports",
        headers=resident_c,
        params={"district": "Chennai", "taluk": "Mylapore", "local_body": "Chennai Corporation", "ward": "Ward 123"},
    ).status_code == 403
    assert client.post(f"/api/community/reports/{report_id}/acknowledge", headers=resident_c).status_code == 403

    assert client.get(
        "/api/community/reports",
        headers=resident_b,
        params={"district": "Chennai", "taluk": "Adyar"},
    ).status_code == 403
    assert client.post(f"/api/community/reports/{report_id}/acknowledge", headers=resident_b).status_code == 200
    repeated = client.post(f"/api/community/reports/{report_id}/acknowledge", headers=resident_b)
    assert repeated.json()["acknowledgement_count"] == 1
    comment = client.post(
        f"/api/community/reports/{report_id}/comments",
        headers=resident_b,
        json={"message": "The light is still out this evening."},
    )
    assert comment.status_code == 200
    assert comment.json()["comments"] == [{
        "message": "The light is still out this evening.",
        "created_at": comment.json()["comments"][0]["created_at"],
        "author": "Community member",
    }]

    triaged = client.patch(
        f"/api/reports/{report_id}",
        headers=admin,
        json={"status": "triaged", "note": "Inspection queued."},
    )
    assert triaged.status_code == 200
    assert any("Area report update" in item["title"] for item in client.get("/api/notifications", headers=resident_b).json())

    district_results = client.get(
        "/api/community/reports",
        headers=admin,
        params={"district": "Chennai"},
    )
    assert district_results.status_code == 200
    assert district_results.json()[0]["status"] == "triaged"
    accepted = client.patch(
        f"/api/reports/{report_id}",
        headers=admin,
        json={"status": "accepted", "note": "Accepted for municipal action."},
    )
    assert accepted.status_code == 200
    incident_id = client.get(f"/api/reports/{report_id}", headers=admin).json()["incident_id"]
    moved_to_triage = client.patch(
        f"/api/incidents/{incident_id}",
        headers=admin,
        json={"status": "TRIAGED", "note": "Field inspection scheduled."},
    )
    assert moved_to_triage.status_code == 200
    refreshed = client.get(
        "/api/community/reports",
        headers=resident_b,
        params={"district": "Chennai", **area},
    ).json()[0]
    assert refreshed["work_status"] == "TRIAGED"
    assert refreshed["work_history"][-1]["note"] == "Field inspection scheduled."
    assert any("Municipal work update" in item["title"] for item in client.get("/api/notifications", headers=resident_b).json())

    direct_work = client.post(
        "/api/incidents",
        headers=admin,
        json={
            "title": "Replace damaged streetlight controller",
            "description": "Work order for the local streetlighting circuit.",
            "severity": "medium",
            **area,
        },
    )
    assert direct_work.status_code == 200
    work_list = client.get(
        "/api/community/work",
        headers=resident_b,
        params={"district": "Chennai", **area},
    )
    assert work_list.status_code == 200
    assert any(item["id"] == direct_work.json()["id"] for item in work_list.json())
    assert all("assigned_to" not in item and "evidence" not in item for item in work_list.json())
