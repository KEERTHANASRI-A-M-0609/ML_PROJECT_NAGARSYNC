"""
backend/app/notifications.py — In-app notification center.

Persists notification records for citizens, admins, and field engineers.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Optional

from ml.config import REPORTS_DIR
from backend.app.db import get_db

_STORE = REPORTS_DIR / "notifications.json"
_LOCK = Lock()


def _col():
    db = get_db()
    return db["notifications"] if db is not None else None


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


def create_notification(
    recipient_id: str,
    title: str,
    message: str,
    kind: str = "info",  # info | alert | assignment | verification
    link: Optional[str] = None,
) -> dict:
    notif = {
        "id": "NOTIF-" + str(uuid.uuid4())[:8].upper(),
        "recipient_id": recipient_id,
        "title": title[:200],
        "message": message[:1000],
        "kind": kind,
        "link": link,
        "read": False,
        "created_at": time.time(),
    }
    col = _col()
    if col is not None:
        col.insert_one(dict(notif))
    else:
        with _LOCK:
            items = _file_load()
            items.append(notif)
            _file_save(items)
    return notif


def list_notifications(recipient_id: str, unread_only: bool = False, limit: int = 50) -> list[dict]:
    col = _col()
    if col is not None:
        query = {"recipient_id": recipient_id}
        if unread_only:
            query["read"] = False
        items = list(col.find(query, {"_id": 0}).sort("created_at", -1).limit(limit))
        return items
    with _LOCK:
        items = _file_load()
        user_items = [n for n in items if n.get("recipient_id") == recipient_id]
        if unread_only:
            user_items = [n for n in user_items if not n.get("read")]
        user_items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return user_items[:limit]


def mark_as_read(notif_id: str, recipient_id: str) -> bool:
    col = _col()
    if col is not None:
        res = col.update_one({"id": notif_id, "recipient_id": recipient_id}, {"$set": {"read": True}})
        return res.matched_count == 1
    with _LOCK:
        items = _file_load()
        for n in items:
            if n.get("id") == notif_id and n.get("recipient_id") == recipient_id:
                n["read"] = True
                _file_save(items)
                return True
    return False


def mark_all_read(recipient_id: str) -> int:
    col = _col()
    if col is not None:
        res = col.update_many({"recipient_id": recipient_id, "read": False}, {"$set": {"read": True}})
        return res.modified_count
    with _LOCK:
        items = _file_load()
        count = 0
        for n in items:
            if n.get("recipient_id") == recipient_id and not n.get("read"):
                n["read"] = True
                count += 1
        if count:
            _file_save(items)
        return count
