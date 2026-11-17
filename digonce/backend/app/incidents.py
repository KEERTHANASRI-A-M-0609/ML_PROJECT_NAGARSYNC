"""
backend/app/incidents.py — Incident and repair workflow.

States: NEW → TRIAGED → INSPECTION_REQUIRED → INSPECTED →
        PLAN_PROPOSED → APPROVED → ASSIGNED → IN_PROGRESS →
        COMPLETION_SUBMITTED → VERIFIED → CLOSED

Also supports: REJECTED, CANCELLED, REOPENED, ESCALATED
"""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Optional

from ml.config import REPORTS_DIR
from backend.app.db import get_db

_STORE = REPORTS_DIR / "incidents.json"
_LOCK = Lock()

VALID_TRANSITIONS: dict[str, set[str]] = {
    "NEW":                  {"TRIAGED", "CANCELLED", "ASSIGNED"},
    "TRIAGED":              {"INSPECTION_REQUIRED", "PLAN_PROPOSED", "CANCELLED"},
    "INSPECTION_REQUIRED":  {"INSPECTED", "CANCELLED", "ESCALATED"},
    "INSPECTED":            {"PLAN_PROPOSED", "ESCALATED"},
    "PLAN_PROPOSED":        {"APPROVED", "TRIAGED", "CANCELLED"},
    "APPROVED":             {"ASSIGNED", "CANCELLED"},
    "ASSIGNED":             {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS":          {"COMPLETION_SUBMITTED", "ESCALATED"},
    "COMPLETION_SUBMITTED": {"VERIFIED", "IN_PROGRESS"},
    "VERIFIED":             {"CLOSED"},
    "CLOSED":               {"REOPENED"},
    "REOPENED":             {"TRIAGED"},
    "ESCALATED":            {"TRIAGED", "CANCELLED"},
    "CANCELLED":            {"REOPENED"},
    "REJECTED":             set(),
}


def _col():
    db = get_db()
    return db["incidents"] if db is not None else None


def _file_load() -> list[dict]:
    if not _STORE.exists():
        return []
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _file_save(items: list[dict]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(items[-2000:], indent=2), encoding="utf-8")


def create_incident(
    *,
    asset_id: Optional[str],
    report_id: Optional[str],
    title: str,
    description: str,
    severity: str,
    created_by: str,
    district: Optional[str] = None,
    taluk: Optional[str] = None,
    block: Optional[str] = None,
    local_body: Optional[str] = None,
    ward: Optional[str] = None,
    locality: Optional[str] = None,
    asset_type: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    is_demo_sample: bool = False,
    demo_seed_key: Optional[str] = None,
) -> dict:
    inc_id = "INC-" + str(uuid.uuid4())[:8].upper()
    incident = {
        "id": inc_id,
        "asset_id": asset_id,
        "report_id": report_id,
        "title": title.strip()[:300],
        "description": description.strip()[:2000],
        "severity": severity,
        "status": "NEW",
        "district": district,
        "taluk": (taluk or "").strip()[:100],
        "block": (block or "").strip()[:100],
        "local_body": (local_body or "").strip()[:120],
        "ward": (ward or "").strip()[:120],
        "locality": (locality or "").strip()[:200],
        "asset_type": asset_type,
        "lat": lat,
        "lon": lon,
        "assigned_to": None,
        "plan_id": None,
        "evidence": [],
        "status_history": [{"status": "NEW", "ts": time.time(), "actor": created_by, "note": "Created"}],
        "created_by": created_by,
        "created_at": time.time(),
        "updated_at": time.time(),
        "overdue": False,
        "is_demo_sample": is_demo_sample,
        "demo_seed_key": demo_seed_key,
    }
    col = _col()
    if col is not None:
        col.insert_one(dict(incident))
    else:
        with _LOCK:
            items = _file_load()
            items.append(incident)
            _file_save(items)
    return incident


def list_incidents(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    asset_id: Optional[str] = None,
    limit: int = 50,
    include_archived: bool = False,
    area: Optional[dict[str, str]] = None,
) -> list[dict]:
    col = _col()
    if col is not None:
        q: dict = {}
        if status:
            q["status"] = status
        if assigned_to:
            q["assigned_to"] = assigned_to
        if asset_id:
            q["asset_id"] = asset_id
        if area:
            q.update({
                key: {"$regex": f"^{re.escape(value)}$", "$options": "i"}
                for key, value in area.items()
            })
        items = list(col.find(q, {"_id": 0}).sort("created_at", -1).limit(limit * 2))
        if not include_archived:
            items = [item for item in items if item.get("archived_at") is None]
        return items[:limit]
    with _LOCK:
        items = _file_load()
    if status:
        items = [i for i in items if i["status"] == status]
    if assigned_to:
        items = [i for i in items if i.get("assigned_to") == assigned_to]
    if asset_id:
        items = [i for i in items if i.get("asset_id") == asset_id]
    if area:
        items = [
            i for i in items
            if all(str(i.get(key) or "").strip().casefold() == value.casefold() for key, value in area.items())
        ]
    if not include_archived:
        items = [item for item in items if item.get("archived_at") is None]
    return list(reversed(items))[:limit]


def get_incident(inc_id: str) -> dict | None:
    col = _col()
    if col is not None:
        return col.find_one({"id": inc_id}, {"_id": 0})
    with _LOCK:
        items = _file_load()
    return next((i for i in items if i["id"] == inc_id), None)


def update_incident_fields(inc_id: str, values: dict) -> dict | None:
    ts = time.time()
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        return col.find_one_and_update(
            {"id": inc_id},
            {"$set": {**values, "updated_at": ts}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _file_load()
        for incident in items:
            if incident["id"] == inc_id:
                incident.update(values)
                incident["updated_at"] = ts
                _file_save(items)
                return incident
    return None


def set_archived(inc_id: str, archived: bool) -> dict | None:
    ts = time.time()
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        return col.find_one_and_update(
            {"id": inc_id},
            {"$set": {"archived_at": ts if archived else None, "updated_at": ts}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _file_load()
        for incident in items:
            if incident["id"] == inc_id:
                incident["archived_at"] = ts if archived else None
                incident["updated_at"] = ts
                _file_save(items)
                return incident
    return None


def transition_incident(
    inc_id: str,
    new_status: str,
    actor_id: str,
    note: str = "",
    assigned_to: Optional[str] = None,
    plan_id: Optional[str] = None,
    evidence_url: Optional[str] = None,
) -> dict | str:
    """Returns updated incident or error string."""
    incident = get_incident(inc_id)
    if not incident:
        return "Incident not found"
    current = incident["status"]
    allowed = VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        return f"Cannot transition from {current} to {new_status}"

    ts = time.time()
    history_entry = {"status": new_status, "ts": ts, "actor": actor_id, "note": note}
    updates: dict = {
        "status": new_status,
        "updated_at": ts,
    }
    if assigned_to:
        updates["assigned_to"] = assigned_to
    if plan_id:
        updates["plan_id"] = plan_id
    if evidence_url:
        updates.setdefault("evidence", [])

    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        mongo_update: dict = {"$set": updates, "$push": {"status_history": history_entry}}
        if evidence_url:
            mongo_update["$push"]["evidence"] = evidence_url  # type: ignore[index]
        return col.find_one_and_update(
            {"id": inc_id},
            mongo_update,
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _file_load()
        for inc in items:
            if inc["id"] == inc_id:
                inc.update(updates)
                inc.setdefault("status_history", []).append(history_entry)
                if evidence_url:
                    inc.setdefault("evidence", []).append(evidence_url)
                _file_save(items)
                return inc
    return "Incident not found"


_EVIDENCE_DIR = REPORTS_DIR / "incident_evidence"


def add_evidence(inc_id: str, evidence_url: str, actor_id: str, note: str = "", image_data_url: Optional[str] = None) -> dict | None:
    final_url = evidence_url
    if image_data_url and image_data_url.startswith("data:image"):
        try:
            import base64
            header, encoded = image_data_url.split(",", 1)
            ext = ".jpg"
            if "png" in header:
                ext = ".png"
            elif "webp" in header:
                ext = ".webp"
            img_bytes = base64.b64decode(encoded)
            _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            fname = f"{inc_id}_{int(time.time())}{ext}"
            img_path = _EVIDENCE_DIR / fname
            img_path.write_bytes(img_bytes)
            final_url = f"/api/incidents/{inc_id}/evidence-image/{fname}"
        except Exception:
            final_url = evidence_url or "photo_evidence.jpg"

    col = _col()
    entry = {"url": final_url, "actor": actor_id, "note": note, "ts": time.time()}
    if col is not None:
        from pymongo import ReturnDocument
        return col.find_one_and_update(
            {"id": inc_id},
            {"$push": {"evidence": entry}, "$set": {"updated_at": time.time()}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _file_load()
        for inc in items:
            if inc["id"] == inc_id:
                inc.setdefault("evidence", []).append(entry)
                inc["updated_at"] = time.time()
                _file_save(items)
                return inc
    return None
