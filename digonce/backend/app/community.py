"""Area-scoped public report discussion and notification subscriptions."""
from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock

from ml.config import REPORTS_DIR
from backend.app.db import get_db

_STORE = REPORTS_DIR / "community.json"
_LOCK = Lock()
AREA_FIELDS = ("district", "taluk", "block", "local_body", "ward", "locality")


def _col(name: str):
    db = get_db()
    return db[name] if db is not None else None


def normalize_area(values: dict, *, allow_district_only: bool = False) -> dict[str, str]:
    # accept legacy/synonym keys
    aliases = {
        "ward_or_village": "ward",
        "village": "ward",
        "municipality": "local_body",
        "panchayat": "local_body",
    }
    merged = {}
    for key in (*AREA_FIELDS, *aliases.keys()):
        val = str(values.get(key) or "").strip()[:120]
        if not val:
            continue
        target = aliases.get(key, key)
        if target in AREA_FIELDS and target not in merged:
            merged[target] = val
    if not merged.get("district"):
        raise ValueError("District is required")
    if not allow_district_only and not any(merged.get(key) for key in ("taluk", "block", "local_body", "ward", "locality")):
        raise ValueError("Select at least one subdivision (taluk, block, local body, ward/village, or locality)")
    return {k: v for k, v in merged.items() if k in AREA_FIELDS}


def area_matches(record: dict, area: dict[str, str]) -> bool:
    return all(
        str(record.get(key) or "").strip().casefold() == value.casefold()
        for key, value in area.items()
    )


def same_area(left: dict[str, str], right: dict[str, str]) -> bool:
    return len(left) == len(right) and area_matches(left, right) and area_matches(right, left)


def _load() -> dict:
    if not _STORE.exists():
        return {"reports": {}, "subscriptions": {}}
    try:
        value = json.loads(_STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"reports": {}, "subscriptions": {}}
    return {
        "reports": value.get("reports", {}),
        "subscriptions": value.get("subscriptions", {}),
    }


def _save(value: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(value, indent=2), encoding="utf-8")


def report_engagement(report_id: str, user_id: str) -> dict:
    col = _col("community_reports")
    if col is not None:
        item = col.find_one({"report_id": report_id}, {"_id": 0}) or {}
    else:
        with _LOCK:
            item = _load()["reports"].get(report_id, {})
    comments = [
        {"message": entry["message"], "created_at": entry["created_at"], "author": "Community member"}
        for entry in item.get("comments", [])
    ]
    return {
        "acknowledgement_count": len(set(item.get("acknowledgements", []))),
        "acknowledged": user_id in item.get("acknowledgements", []),
        "comments": comments,
    }


def acknowledge_report(report_id: str, user_id: str) -> dict:
    col = _col("community_reports")
    if col is not None:
        col.update_one(
            {"report_id": report_id},
            {"$setOnInsert": {"report_id": report_id, "comments": []},
             "$addToSet": {"acknowledgements": user_id}},
            upsert=True,
        )
    else:
        with _LOCK:
            data = _load()
            item = data["reports"].setdefault(
                report_id, {"report_id": report_id, "acknowledgements": [], "comments": []}
            )
            if user_id not in item["acknowledgements"]:
                item["acknowledgements"].append(user_id)
                _save(data)
    return report_engagement(report_id, user_id)


def add_comment(report_id: str, user_id: str, message: str) -> dict:
    entry = {
        "author_id": user_id,
        "message": message.strip()[:1000],
        "created_at": time.time(),
    }
    col = _col("community_reports")
    if col is not None:
        col.update_one(
            {"report_id": report_id},
            {"$setOnInsert": {"report_id": report_id, "acknowledgements": []},
             "$push": {"comments": {"$each": [entry], "$slice": -200}}},
            upsert=True,
        )
    else:
        with _LOCK:
            data = _load()
            item = data["reports"].setdefault(
                report_id, {"report_id": report_id, "acknowledgements": [], "comments": []}
            )
            item["comments"].append(entry)
            item["comments"] = item["comments"][-200:]
            _save(data)
    return report_engagement(report_id, user_id)


def get_subscription(user_id: str) -> dict | None:
    col = _col("community_subscriptions")
    if col is not None:
        item = col.find_one({"user_id": user_id}, {"_id": 0, "user_id": 0})
        return item.get("area") if item else None
    with _LOCK:
        return _load()["subscriptions"].get(user_id)


def set_subscription(user_id: str, area: dict[str, str] | None) -> dict | None:
    col = _col("community_subscriptions")
    if col is not None:
        if area is None:
            col.delete_one({"user_id": user_id})
            return None
        col.update_one(
            {"user_id": user_id},
            {"$set": {"area": area, "updated_at": time.time()}},
            upsert=True,
        )
        return area
    with _LOCK:
        data = _load()
        if area is None:
            data["subscriptions"].pop(user_id, None)
        else:
            data["subscriptions"][user_id] = area
        _save(data)
        return area


def subscribed_users(area: dict[str, str]) -> list[str]:
    col = _col("community_subscriptions")
    if col is not None:
        return [
            item["user_id"] for item in col.find({}, {"user_id": 1, "area": 1, "_id": 0})
            if item.get("user_id") and area_matches(area, item.get("area", {}))
        ]
    with _LOCK:
        subscriptions = _load()["subscriptions"]
    return [
        user_id for user_id, subscribed_area in subscriptions.items()
        if area_matches(area, subscribed_area)
    ]
