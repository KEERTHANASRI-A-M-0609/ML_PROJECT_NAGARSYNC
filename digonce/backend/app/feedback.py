"""Public usability feedback — MongoDB with JSON file fallback."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from threading import Lock

from pymongo import ReturnDocument

from ml.config import REPORTS_DIR
from backend.app.db import feedback_col

_STORE = REPORTS_DIR / "public_feedback.json"
_LOCK = Lock()


def _file_load() -> list[dict]:
    if not _STORE.exists():
        return []
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _file_save(items: list[dict]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(items[-500:], indent=2), encoding="utf-8")


def list_feedback(status: str | None = None, limit: int = 50) -> list[dict]:
    col = feedback_col()
    if col is not None:
        q = {"status": status} if status else {}
        return list(col.find(q, {"_id": 0}).sort("ts", -1).limit(limit))
    with _LOCK:
        items = _file_load()
    if status:
        items = [x for x in items if x.get("status") == status]
    return list(reversed(items))[:limit]


def add_feedback(
    *,
    kind: str,
    message: str,
    asset_id: str | None = None,
    district: str | None = None,
    name: str | None = None,
) -> dict:
    item = {
        "id": str(uuid.uuid4())[:8],
        "kind": kind,
        "message": message.strip()[:1000],
        "asset_id": asset_id,
        "district": district,
        "name": (name or "Public").strip()[:80],
        "status": "open" if kind != "completed" else "done",
        "ts": time.time(),
        "updated_at": time.time(),
    }
    col = feedback_col()
    if col is not None:
        col.insert_one(dict(item))
        return item
    with _LOCK:
        items = _file_load()
        items.append(item)
        _file_save(items)
    return item


def update_feedback(fid: str, status: str) -> dict | None:
    if status not in ("open", "in_progress", "done"):
        return None
    col = feedback_col()
    if col is not None:
        return col.find_one_and_update(
            {"id": fid},
            {"$set": {"status": status, "updated_at": time.time()}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _file_load()
        for it in items:
            if it["id"] == fid:
                it["status"] = status
                it["updated_at"] = time.time()
                _file_save(items)
                return it
    return None
