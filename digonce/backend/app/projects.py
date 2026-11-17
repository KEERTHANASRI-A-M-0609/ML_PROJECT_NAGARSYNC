"""Persistent development project records and auditable project workflows."""
from __future__ import annotations

import json
import time
import uuid
from threading import Lock

from ml.config import REPORTS_DIR
from backend.app.db import get_db

_STORE = REPORTS_DIR / "development_projects.json"
_LOCK = Lock()

PUBLIC_STATUSES = {"APPROVED", "PLANNED", "ONGOING", "DELAYED", "COMPLETED", "VERIFIED"}
PROJECT_STATUSES = {
    "PROPOSED", "SUBMITTED_FOR_APPROVAL", "APPROVED", "PLANNED",
    "ONGOING", "DELAYED", "COMPLETED", "VERIFIED", "CANCELLED",
}
STATUS_TRANSITIONS = {
    "PROPOSED": {"SUBMITTED_FOR_APPROVAL", "CANCELLED"},
    "SUBMITTED_FOR_APPROVAL": {"APPROVED", "PROPOSED", "CANCELLED"},
    "APPROVED": {"PLANNED", "CANCELLED"},
    "PLANNED": {"ONGOING", "CANCELLED"},
    "ONGOING": {"DELAYED", "COMPLETED", "CANCELLED"},
    "DELAYED": {"ONGOING", "COMPLETED", "CANCELLED"},
    "COMPLETED": {"VERIFIED", "ONGOING"},
    "VERIFIED": set(),
    "CANCELLED": set(),
}


def _col():
    db = get_db()
    return db["development_projects"] if db is not None else None


def _load() -> list[dict]:
    if not _STORE.exists():
        return []
    try:
        items = json.loads(_STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read development project records: {exc}") from exc
    if not isinstance(items, list):
        raise RuntimeError("Development project store must contain a JSON list")
    return items


def _save(items: list[dict]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(items[-5000:], indent=2), encoding="utf-8")


def _matches(project: dict, filters: dict[str, str | None]) -> bool:
    return all(
        not value or str(project.get(key) or "").strip().casefold() == value.strip().casefold()
        for key, value in filters.items()
    )


def list_projects(
    *,
    district: str | None = None,
    taluk: str | None = None,
    local_body: str | None = None,
    ward: str | None = None,
    status: str | None = None,
    include_private: bool = False,
    limit: int = 100,
) -> list[dict]:
    filters = {
        "district": district,
        "taluk": taluk,
        "local_body": local_body,
        "ward": ward,
    }
    query = {
        key: {"$regex": f"^{_escape_regex(value)}$", "$options": "i"}
        for key, value in filters.items() if value
    }
    query["archived_at"] = None
    if status:
        query["status"] = status
    col = _col()
    if col is not None:
        items = list(col.find(query, {"_id": 0}).sort("updated_at", -1).limit(limit * 2))
    else:
        with _LOCK:
            items = _load()
        items = [
            item for item in items
            if item.get("archived_at") is None and _matches(item, filters)
        ]
        if status:
            items = [item for item in items if item.get("status") == status]
        items.sort(key=lambda item: item.get("updated_at", 0), reverse=True)
    if not include_private:
        items = [item for item in items if item.get("status") in PUBLIC_STATUSES]
    return items[:limit]


def _escape_regex(value: str) -> str:
    import re
    return re.escape(value)


def get_project(project_id: str) -> dict | None:
    col = _col()
    if col is not None:
        return col.find_one({"id": project_id}, {"_id": 0})
    with _LOCK:
        return next((item for item in _load() if item.get("id") == project_id), None)


def create_project(
    values: dict,
    actor: dict,
    *,
    is_demo_sample: bool = False,
    demo_seed_key: str | None = None,
) -> dict:
    now = time.time()
    project = {
        **values,
        "id": "PRJ-" + str(uuid.uuid4())[:8].upper(),
        "status": values.get("status", "PROPOSED"),
        "progress": values.get("progress", 0),
        "milestones": [],
        "expenditures": [],
        "status_history": [{
            "status": values.get("status", "PROPOSED"),
            "ts": now,
            "actor_id": actor["sub"],
            "actor_name": actor.get("name", ""),
            "note": "Project record created",
        }],
        "created_by": actor["sub"],
        "created_at": now,
        "updated_at": now,
        "archived_at": None,
        "is_demo_sample": is_demo_sample,
        "demo_seed_key": demo_seed_key,
    }
    col = _col()
    if col is not None:
        col.insert_one(dict(project))
    else:
        with _LOCK:
            items = _load()
            items.append(project)
            _save(items)
    return project


def update_project(project_id: str, values: dict, actor: dict) -> dict | None:
    col = _col()
    if col is not None:
        project = col.find_one({"id": project_id, "archived_at": None}, {"_id": 0})
        if not project:
            return None
        updates = _updates_for_project(project, values, actor)
        from pymongo import ReturnDocument
        updated = col.find_one_and_update(
            {
                "id": project_id,
                "archived_at": None,
                "status": project.get("status", "PROPOSED"),
                "updated_at": project.get("updated_at"),
            },
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if updated is None:
            raise ValueError("Project changed while saving; reload and try again")
        return updated
    with _LOCK:
        items = _load()
        for item in items:
            if item.get("id") == project_id and item.get("archived_at") is None:
                updates = _updates_for_project(item, values, actor)
                item.update(updates)
                _save(items)
                return item
    return None


def _updates_for_project(project: dict, values: dict, actor: dict) -> dict:
    now = time.time()
    updates = {**values, "updated_at": now}
    old_status = project.get("status", "PROPOSED")
    new_status = updates.get("status", old_status)
    if new_status != old_status:
        if new_status not in PROJECT_STATUSES or new_status not in STATUS_TRANSITIONS.get(old_status, set()):
            raise ValueError(f"Project status cannot transition from {old_status} to {new_status}")
        updates["status_history"] = project.get("status_history", []) + [{
            "status": new_status,
            "ts": now,
            "actor_id": actor["sub"],
            "actor_name": actor.get("name", ""),
            "note": values.get("status_note", "Project status updated"),
        }]
    updates.pop("status_note", None)
    if new_status == "COMPLETED" and "actual_completion_date" not in updates:
        updates["actual_completion_date"] = time.strftime("%Y-%m-%d", time.gmtime(now))
    return updates


def add_milestone(project_id: str, values: dict, actor: dict) -> dict | None:
    now = time.time()
    entry = {
        **values,
        "id": "MIL-" + str(uuid.uuid4())[:8].upper(),
        "created_by": actor["sub"],
        "created_at": now,
        "completed_at": now if values.get("completed") else None,
    }
    return _append_entry(project_id, "milestones", entry)


def update_milestone(project_id: str, milestone_id: str, values: dict, actor: dict) -> dict | None:
    now = time.time()
    updates = {**values, "updated_by": actor["sub"], "updated_at": now}
    if updates.get("completed"):
        updates["completed_at"] = now
    else:
        updates["completed_at"] = None
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        return col.find_one_and_update(
            {"id": project_id, "archived_at": None, "milestones.id": milestone_id},
            {"$set": {f"milestones.$.{key}": value for key, value in updates.items()}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _load()
        for project in items:
            if project.get("id") != project_id or project.get("archived_at") is not None:
                continue
            for milestone in project.get("milestones", []):
                if milestone.get("id") == milestone_id:
                    milestone.update(updates)
                    project["updated_at"] = now
                    _save(items)
                    return project
    return None


def add_expenditure(project_id: str, values: dict, actor: dict) -> dict | None:
    entry = {
        **values,
        "id": "EXP-" + str(uuid.uuid4())[:8].upper(),
        "recorded_by": actor["sub"],
        "recorded_at": time.time(),
    }
    amount = float(entry["amount_lakh"])
    col = _col()
    if col is not None:
        project = col.find_one({"id": project_id, "archived_at": None}, {"_id": 0})
        if not project:
            return None
        current = float(project.get("actual_expenditure_lakh", 0))
        estimated = project.get("estimated_cost_lakh")
        if estimated is not None and current + amount > float(estimated):
            raise ValueError("Recorded expenditure cannot exceed the estimated project cost")
        from pymongo import ReturnDocument
        updated = col.find_one_and_update(
            {
                "id": project_id,
                "archived_at": None,
                "actual_expenditure_lakh": project.get("actual_expenditure_lakh"),
                "estimated_cost_lakh": estimated,
            },
            {
                "$push": {"expenditures": entry},
                "$inc": {"actual_expenditure_lakh": amount},
                "$set": {"updated_at": time.time()},
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if updated is None:
            raise ValueError("Project changed while recording expenditure; reload and try again")
        return updated
    with _LOCK:
        items = _load()
        for project in items:
            if project.get("id") != project_id or project.get("archived_at") is not None:
                continue
            current = float(project.get("actual_expenditure_lakh", 0))
            estimated = project.get("estimated_cost_lakh")
            if estimated is not None and current + amount > float(estimated):
                raise ValueError("Recorded expenditure cannot exceed the estimated project cost")
            project.setdefault("expenditures", []).append(entry)
            project["actual_expenditure_lakh"] = current + amount
            project["updated_at"] = time.time()
            _save(items)
            return project
    return None


def _append_entry(project_id: str, field: str, entry: dict) -> dict | None:
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        return col.find_one_and_update(
            {"id": project_id, "archived_at": None},
            {"$push": {field: entry}, "$set": {"updated_at": time.time()}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _load()
        for project in items:
            if project.get("id") == project_id and project.get("archived_at") is None:
                project.setdefault(field, []).append(entry)
                project["updated_at"] = time.time()
                _save(items)
                return project
    return None


def archive_project(project_id: str, actor: dict) -> dict | None:
    project = get_project(project_id)
    if not project or project.get("archived_at") is not None:
        return None
    now = time.time()
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        return col.find_one_and_update(
            {"id": project_id, "archived_at": None},
            {"$set": {"archived_at": now, "updated_at": now, "archived_by": actor["sub"]}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _load()
        for item in items:
            if item.get("id") == project_id and item.get("archived_at") is None:
                item.update({"archived_at": now, "updated_at": now, "archived_by": actor["sub"]})
                _save(items)
                return item
    return None
