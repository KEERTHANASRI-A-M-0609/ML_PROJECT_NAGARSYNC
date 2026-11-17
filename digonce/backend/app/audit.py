"""Persist a minimal history of user and municipal record changes."""
from __future__ import annotations

import json
import time
import uuid
from threading import Lock

from ml.config import REPORTS_DIR
from backend.app.db import get_db

_STORE = REPORTS_DIR / "audit_events.json"
_LOCK = Lock()


def _col():
    db = get_db()
    return db["audit_events"] if db is not None else None


def _load() -> list[dict]:
    if not _STORE.exists():
        return []
    try:
        events = json.loads(_STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read audit events: {exc}") from exc
    if not isinstance(events, list):
        raise RuntimeError("Audit event store must contain a JSON list")
    return events


def record_event(
    actor: dict,
    action: str,
    entity_type: str,
    entity_id: str,
    summary: str,
) -> dict:
    event = {
        "id": "AUD-" + str(uuid.uuid4())[:8].upper(),
        "actor_id": actor["sub"],
        "actor_name": actor.get("name", ""),
        "actor_email": actor.get("email", ""),
        "actor_role": actor.get("role", ""),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "summary": summary[:500],
        "created_at": time.time(),
    }
    col = _col()
    if col is not None:
        col.insert_one(dict(event))
    else:
        with _LOCK:
            events = _load()
            events.append(event)
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            _STORE.write_text(json.dumps(events[-10000:], indent=2), encoding="utf-8")
    return event


def list_events(
    limit: int = 100,
    entity_type: str | None = None,
    actor_id: str | None = None,
) -> list[dict]:
    col = _col()
    if col is not None:
        query = {}
        if entity_type:
            query["entity_type"] = entity_type
        if actor_id:
            query["actor_id"] = actor_id
        return list(col.find(query, {"_id": 0}).sort("created_at", -1).limit(limit))
    with _LOCK:
        events = _load()
    if entity_type:
        events = [event for event in events if event.get("entity_type") == entity_type]
    if actor_id:
        events = [event for event in events if event.get("actor_id") == actor_id]
    events.sort(key=lambda event: event.get("created_at", 0), reverse=True)
    return events[:limit]
