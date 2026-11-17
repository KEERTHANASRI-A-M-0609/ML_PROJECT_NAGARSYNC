from fastapi.testclient import TestClient

from backend.app import audit, main, projects, users
from backend.app.seed_demo_projects import seed_demo_projects


def _client_with_local_stores(monkeypatch, tmp_path):
    for module, name in (
        (users, "users.json"),
        (projects, "projects.json"),
        (audit, "audit.json"),
    ):
        monkeypatch.setattr(module, "_STORE", tmp_path / name)
        if hasattr(module, "_col"):
            monkeypatch.setattr(module, "_col", lambda: None)
    users.create_managed_user("projects-admin@example.test", "AdminPassword2026!", "admin", "Project Admin")
    users.create_managed_user("projects-citizen@example.test", "CitizenPassword2026!", "citizen", "Project Resident")
    client = TestClient(main.app)

    def login(email, password):
        response = client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}

    return client, login(
        "projects-admin@example.test",
        "AdminPassword2026!",
    ), login("projects-citizen@example.test", "CitizenPassword2026!")


def test_project_lifecycle_public_visibility_and_expenditure_limits(monkeypatch, tmp_path):
    client, admin, citizen = _client_with_local_stores(monkeypatch, tmp_path)
    payload = {
        "title": "Local drainage improvement",
        "description": "A demo test project record.",
        "category": "drainage",
        "district": "Chennai",
        "taluk": "Test Taluk",
        "local_body": "Test Municipality",
        "ward": "Ward 01",
        "estimated_cost_lakh": 100,
        "expected_completion_date": "2027-12-31",
    }

    denied = client.post("/api/projects", headers=citizen, json=payload)
    assert denied.status_code == 403

    created = client.post("/api/projects", headers=admin, json=payload)
    assert created.status_code == 200
    project_id = created.json()["id"]
    assert client.get("/api/projects", headers=citizen).json() == []
    assert client.get(f"/api/projects/{project_id}", headers=citizen).status_code == 404

    for status in ("SUBMITTED_FOR_APPROVAL", "APPROVED", "PLANNED", "ONGOING"):
        response = client.patch(
            f"/api/projects/{project_id}",
            headers=admin,
            json={"status": status, "status_note": f"Moved to {status}"},
        )
        assert response.status_code == 200

    invalid_transition = client.patch(
        f"/api/projects/{project_id}",
        headers=admin,
        json={"status": "VERIFIED"},
    )
    assert invalid_transition.status_code == 409

    milestone = client.post(
        f"/api/projects/{project_id}/milestones",
        headers=admin,
        json={"title": "Drain survey", "due_date": "2026-12-01"},
    )
    assert milestone.status_code == 200
    milestone_id = milestone.json()["milestones"][0]["id"]
    completed = client.patch(
        f"/api/projects/{project_id}/milestones/{milestone_id}",
        headers=admin,
        json={"completed": True},
    )
    assert completed.status_code == 200
    assert completed.json()["milestones"][0]["completed"] is True

    recorded = client.post(
        f"/api/projects/{project_id}/expenditures",
        headers=admin,
        json={
            "amount_lakh": 35,
            "description": "Initial survey and design",
            "expenditure_date": "2026-11-16",
            "reference": "TEST-INV-01",
        },
    )
    assert recorded.status_code == 200
    assert recorded.json()["actual_expenditure_lakh"] == 35

    over_budget = client.post(
        f"/api/projects/{project_id}/expenditures",
        headers=admin,
        json={
            "amount_lakh": 70,
            "description": "Over-budget test",
            "expenditure_date": "2026-11-16",
        },
    )
    assert over_budget.status_code == 409

    public = client.get("/api/projects", headers=citizen).json()
    assert len(public) == 1
    assert public[0]["id"] == project_id
    assert public[0]["actual_expenditure_lakh"] == 35
    assert "created_by" not in public[0]
    assert "recorded_by" not in public[0]["expenditures"][0]
    assert "actor_id" not in public[0]["status_history"][0]


def test_demo_project_seed_is_local_and_repeatable(monkeypatch, tmp_path):
    monkeypatch.setattr(projects, "_STORE", tmp_path / "projects.json")
    monkeypatch.setattr(projects, "_col", lambda: None)
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert seed_demo_projects() == 3
    assert seed_demo_projects() == 0
    seeded = projects.list_projects(include_private=True, limit=20)
    assert len(seeded) == 3
    assert all(item["is_demo_sample"] for item in seeded)
    assert {item["status"] for item in seeded} == {"ONGOING", "DELAYED", "VERIFIED"}
    assert all(item["milestones"] and item["expenditures"] for item in seeded)

    monkeypatch.setenv("MONGODB_URI", "mongodb://configured.example.invalid")
    try:
        seed_demo_projects()
    except RuntimeError as exc:
        assert "Refusing to seed" in str(exc)
    else:
        raise AssertionError("The demo seeder must refuse configured database environments")
