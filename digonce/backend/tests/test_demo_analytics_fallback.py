import numpy as np
from fastapi.testclient import TestClient

from backend.app import db, main, services, users
from backend.app.demo_analytics import DemoPriorityScorer


def test_demo_priority_scorer_is_bounded_and_repeatable():
    scorer = DemoPriorityScorer()
    features = np.array([[30, 0.4, 18, 0.7, 2, 100, 0.2, 3]], dtype=float)

    first = scorer.predict_proba(features)
    second = scorer.predict_proba(features)

    assert first.shape == (1,)
    assert 0.0 <= first[0] <= 1.0
    assert np.array_equal(first, second)


def test_blocked_ml_loads_simulated_statewide_demo(monkeypatch, tmp_path):
    monkeypatch.setattr(users, "_STORE", tmp_path / "users.json")
    monkeypatch.setattr(users, "_col", lambda: None)
    monkeypatch.setattr(db, "ping", lambda: False)
    monkeypatch.setattr(db, "last_error", lambda: "Database unavailable in test")
    monkeypatch.setattr(services, "_runtime_ready", False)
    monkeypatch.setattr(services, "_runtime_error", None)
    monkeypatch.setattr(services, "_runtime_demo_mode", False)
    monkeypatch.setattr(services, "_runtime_ready", False)
    monkeypatch.setattr(services, "_runtime_error", None)
    users.create_managed_user(
        "demo-admin@example.test",
        "LocalDemoPassword2026!",
        "admin",
        "Demo Administrator",
    )

    def blocked_model_load():
        raise ImportError("DLL load failed: An Application Control policy has blocked this file.")

    monkeypatch.setattr(services._state, "load", blocked_model_load)

    with TestClient(main.app) as client:
        login = client.post(
            "/api/auth/login",
            json={
                "email": "demo-admin@example.test",
                "password": "LocalDemoPassword2026!",
            },
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        health = client.get("/api/health", headers=headers)
        summary = client.get("/api/summary", headers=headers)
        wards = client.get("/api/wards", headers=headers)
        leaks = client.get("/api/leaks", headers=headers)
        assets = client.get("/api/assets?limit=1", headers=headers)
        asset = client.get(f"/api/assets/{assets.json()[0]['asset_id']}", headers=headers)
        corridor_assets = client.get(
            f"/api/assets?corridor_id={assets.json()[0]['corridor_id']}",
            headers=headers,
        )
        experiments = client.get("/api/experiments", headers=headers)
        live = client.get("/api/live", headers=headers)
        recommendation = client.post(
            "/api/recommend",
            headers=headers,
            json={
                "budget_lakh": 5000,
                "strategy": "greedy_coordinated",
                "prefer_coordination": True,
                "limit": 5,
            },
        )
        with client.websocket_connect(
            "/ws/live",
            subprotocols=["nagar-sync", f"bearer.{login.json()['token']}"],
        ) as websocket:
            live_message = websocket.receive_json()

    assert health.status_code == 200
    assert health.json()["analytics"] == {
        "available": True,
        "mode": "simulated_demo",
        "demo_only": True,
    }
    assert summary.status_code == 200
    assert summary.json()["total_assets"] > 0
    assert summary.json()["n_wards"] == 37
    assert summary.json()["score_mode"] == "simulated_condition_priority"
    assert wards.status_code == 200
    assert len(wards.json()) == 37
    assert leaks.status_code == 200
    assert len(leaks.json()) == 37
    assert assets.status_code == 200
    assert len(assets.json()) == 1
    assert asset.status_code == 200
    assert asset.json()["score_mode"] == "simulated_condition_priority"
    assert corridor_assets.status_code == 200
    assert all(item["corridor_id"] == assets.json()[0]["corridor_id"] for item in corridor_assets.json())
    assert experiments.status_code == 200
    assert experiments.json()["summary"]
    assert live.status_code == 200
    assert live.json()["data_mode"] == "simulated_demo"
    assert recommendation.status_code == 200
    assert recommendation.json()["selected_count"] > 0
    assert recommendation.json()["assets"][0]["score_mode"] == "simulated_condition_priority"
    assert live_message["type"] == "hello"
    assert live_message["data_mode"] == "simulated_demo"
