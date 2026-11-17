from backend.app import audit


def test_audit_events_are_persisted_and_filterable(monkeypatch, tmp_path):
    monkeypatch.setattr(audit, "_STORE", tmp_path / "audit.json")
    monkeypatch.setattr(audit, "_col", lambda: None)
    actor = {
        "sub": "admin-1",
        "name": "Municipal Admin",
        "email": "admin@example.test",
        "role": "admin",
    }

    audit.record_event(actor, "status_changed", "incident", "INC-1", "Assigned to field crew")
    audit.record_event(actor, "updated", "user", "USER-1", "Updated role")

    incidents = audit.list_events(entity_type="incident")
    assert len(incidents) == 1
    assert incidents[0]["entity_id"] == "INC-1"
    assert incidents[0]["actor_email"] == "admin@example.test"
    assert audit.list_events(actor_id="another-admin") == []
