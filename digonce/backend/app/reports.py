"""
backend/app/reports.py — Citizen infrastructure reports with full workflow.

Statuses: new → triaged → accepted / rejected
Accepted reports trigger asset assessment and incident creation.
"""
from __future__ import annotations

import json
import base64
import binascii
import re
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Optional

from ml.config import REPORTS_DIR
from backend.app.db import get_db

_STORE = REPORTS_DIR / "citizen_reports.json"
_UPLOAD_DIR = REPORTS_DIR / "report_uploads"
_LOCK = Lock()
MAX_IMAGE_BYTES = 4 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

VALID_CATEGORIES = {"pothole", "water_leak", "streetlight", "bridge_damage", "drainage", "waste", "other"}
VALID_STATUSES = {"new", "triaged", "accepted", "rejected", "merged"}
REPORT_TRANSITIONS = {
    "new": {"triaged", "rejected"},
    "triaged": {"accepted", "rejected", "merged"},
    "accepted": set(),
    "rejected": set(),
    "merged": set(),
}


def _col():
    db = get_db()
    return db["citizen_reports"] if db is not None else None


def _file_load() -> list[dict]:
    if not _STORE.exists():
        return []
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _file_save(items: list[dict]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(items[-1000:], indent=2), encoding="utf-8")


def create_report(
    *,
    citizen_id: str,
    citizen_name: str,
    category: str,
    description: str,
    lat: Optional[float],
    lon: Optional[float],
    location_text: Optional[str],
    district: Optional[str] = None,
    taluk: Optional[str] = None,
    block: Optional[str] = None,
    local_body: Optional[str] = None,
    local_body_type: Optional[str] = None,
    ward: Optional[str] = None,
    village: Optional[str] = None,
    locality: Optional[str] = None,
    pincode: Optional[str] = None,
    state: Optional[str] = "Tamil Nadu",
    severity: Optional[str] = "medium",
    hierarchy_source: Optional[str] = None,
    image_filename: Optional[str],
    image_data_url: Optional[str],  # base64 preview stored separately
    evidence_data_url: Optional[str] = None,
    evidence_filename: Optional[str] = None,
    is_demo_sample: bool = False,
    demo_seed_key: Optional[str] = None,
) -> dict:
    if category not in VALID_CATEGORIES:
        raise ValueError("Unsupported report category")
    if lat is None or lon is None:
        raise ValueError("Select an exact map location (latitude and longitude)")
    report_id = "RPT-" + str(uuid.uuid4())[:8].upper()
    image_path = None
    image_mime = None
    stored_image_filename = None
    if image_data_url:
        try:
            header, encoded = image_data_url.split(",", 1)
            image_mime = header[5:].split(";", 1)[0].lower()
            extension = ALLOWED_IMAGE_TYPES.get(image_mime)
            if not header.lower().endswith(";base64") or extension is None:
                raise ValueError("Only JPEG, PNG, and WebP image uploads are supported")
            image_bytes = base64.b64decode(encoded, validate=True)
            if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
                raise ValueError("Image must be no larger than 4 MB")
            if not (
                (image_mime == "image/jpeg" and image_bytes.startswith(b"\xff\xd8\xff"))
                or (image_mime == "image/png" and image_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
                or (image_mime == "image/webp" and image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP")
            ):
                raise ValueError("Image content does not match its declared format")
            _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            image_path = _UPLOAD_DIR / f"{report_id}{extension}"
            image_path.write_bytes(image_bytes)
            stored_image_filename = image_path.name
        except (ValueError, binascii.Error) as exc:
            raise ValueError(str(exc)) from exc
    # optional secondary evidence (video/photo) stored as file when small/base64
    evidence_path = None
    evidence_mime = None
    stored_evidence_filename = None
    evidence_url = None
    if evidence_data_url:
        try:
            header, encoded = evidence_data_url.split(",", 1)
            evidence_mime = header[5:].split(";", 1)[0].lower()
            ext_map = {
                "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
                "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
            }
            extension = ext_map.get(evidence_mime)
            if not header.lower().endswith(";base64") or extension is None:
                raise ValueError("Unsupported evidence format")
            evidence_bytes = base64.b64decode(encoded, validate=True)
            if not evidence_bytes or len(evidence_bytes) > 8 * 1024 * 1024:
                raise ValueError("Evidence file must be no larger than 8 MB")
            _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            evidence_path = _UPLOAD_DIR / f"{report_id}_evidence{extension}"
            evidence_path.write_bytes(evidence_bytes)
            stored_evidence_filename = evidence_path.name
            evidence_url = f"/api/reports/{report_id}/evidence"
        except (ValueError, binascii.Error):
            # do not block report if optional evidence invalid; caller should validate, but keep resilient
            evidence_path = None
            stored_evidence_filename = None
            evidence_url = None
            evidence_mime = None
    ward_value = (ward or village or "").strip()[:120]
    locality_value = (locality or "").strip()[:200]
    report = {
        "id": report_id,
        "citizen_id": citizen_id,
        "citizen_name": citizen_name,
        "category": category,
        "severity": (severity or "medium").strip()[:20],
        "description": description.strip()[:2000],
        "lat": lat,
        "lon": lon,
        "location_text": (location_text or "").strip()[:300],
        "state": (state or "Tamil Nadu").strip()[:100],
        "district": (district or "").strip()[:100],
        "taluk": (taluk or "").strip()[:100],
        "block": (block or "").strip()[:100],
        "local_body": (local_body or "").strip()[:120],
        "local_body_type": (local_body_type or "").strip()[:80],
        "ward": ward_value,
        "village": (village or "").strip()[:120],
        "ward_or_village": ward_value,
        "locality": locality_value,
        "pincode": (pincode or "").strip()[:20],
        "hierarchy_source": (hierarchy_source or "").strip()[:80],
        "jurisdiction": {
            "state": (state or "Tamil Nadu").strip()[:100],
            "district": (district or "").strip()[:100],
            "taluk": (taluk or "").strip()[:100],
            "block": (block or "").strip()[:100],
            "local_body": (local_body or "").strip()[:120],
            "ward_or_village": ward_value,
            "locality": locality_value,
        },
        "image_filename": stored_image_filename,
        "image_mime": image_mime,
        "has_image": bool(image_path),
        "image_url": f"/api/reports/{report_id}/image" if image_path else None,
        "evidence_filename": stored_evidence_filename,
        "evidence_mime": evidence_mime,
        "has_evidence": bool(evidence_path),
        "evidence_url": evidence_url,
        "status": "new",
        "status_history": [{"status": "new", "ts": time.time(), "actor": citizen_id, "note": "Submitted"}],
        "matched_asset_id": None,
        "incident_id": None,
        "admin_note": None,
        "is_demo_sample": is_demo_sample,
        "demo_seed_key": demo_seed_key,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    col = _col()
    if col is not None:
        col.insert_one(dict(report))
    else:
        with _LOCK:
            items = _file_load()
            items.append(report)
            _file_save(items)
    return report


def image_path_for_report(report_id: str) -> tuple[Path, str] | None:
    report = get_report(report_id)
    if not report or not report.get("has_image"):
        return None
    filename = report.get("image_filename")
    if not filename or Path(filename).name != filename:
        return None
    path = _UPLOAD_DIR / filename
    if not path.is_file():
        return None
    return path, report.get("image_mime") or "application/octet-stream"


def evidence_path_for_report(report_id: str) -> tuple[Path, str] | None:
    report = get_report(report_id)
    if not report or not report.get("has_evidence"):
        return None
    filename = report.get("evidence_filename")
    if not filename or Path(filename).name != filename:
        return None
    path = _UPLOAD_DIR / filename
    if not path.is_file():
        return None
    return path, report.get("evidence_mime") or "application/octet-stream"


def attach_incident(report_id: str, incident_id: str) -> dict | None:
    ts = time.time()
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        return col.find_one_and_update(
            {"id": report_id, "incident_id": None},
            {"$set": {"incident_id": incident_id, "updated_at": ts}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _file_load()
        for report in items:
            if report["id"] == report_id:
                if report.get("incident_id") is not None:
                    return report
                report["incident_id"] = incident_id
                report["updated_at"] = ts
                _file_save(items)
                return report
    return None


def list_reports(
    citizen_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    include_archived: bool = False,
    area: Optional[dict[str, str]] = None,
) -> list[dict]:
    col = _col()
    if col is not None:
        q: dict = {}
        if citizen_id:
            q["citizen_id"] = citizen_id
        if status:
            q["status"] = status
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
    if citizen_id:
        items = [r for r in items if r["citizen_id"] == citizen_id]
    if status:
        items = [r for r in items if r["status"] == status]
    if area:
        items = [
            r for r in items
            if all(str(r.get(key) or "").strip().casefold() == value.casefold() for key, value in area.items())
        ]
    if not include_archived:
        items = [r for r in items if r.get("archived_at") is None]
    return list(reversed(items))[:limit]


def get_report(report_id: str) -> dict | None:
    col = _col()
    if col is not None:
        return col.find_one({"id": report_id}, {"_id": 0})
    with _LOCK:
        items = _file_load()
    return next((r for r in items if r["id"] == report_id), None)


def update_report_fields(report_id: str, values: dict, actor_id: str) -> dict | str | None:
    report = get_report(report_id)
    if not report:
        return None
    ts = time.time()
    edit_entry = {"status": report["status"], "ts": ts, "actor": actor_id, "note": "Report details updated"}
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        return col.find_one_and_update(
            {"id": report_id},
            {"$set": {**values, "updated_at": ts}, "$push": {"status_history": edit_entry}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _file_load()
        for item in items:
            if item["id"] == report_id:
                item.update(values)
                item["updated_at"] = ts
                item.setdefault("status_history", []).append(edit_entry)
                _file_save(items)
                return item
    return None


def set_archived(report_id: str, archived: bool) -> dict | None:
    ts = time.time()
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        return col.find_one_and_update(
            {"id": report_id},
            {"$set": {"archived_at": ts if archived else None, "updated_at": ts}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    with _LOCK:
        items = _file_load()
        for report in items:
            if report["id"] == report_id:
                report["archived_at"] = ts if archived else None
                report["updated_at"] = ts
                _file_save(items)
                return report
    return None


def update_report_status(
    report_id: str,
    new_status: str,
    actor_id: str,
    note: str = "",
    matched_asset_id: Optional[str] = None,
) -> dict | str | None:
    if new_status not in VALID_STATUSES:
        return "Invalid report status"
    report = get_report(report_id)
    if not report:
        return None
    if new_status not in REPORT_TRANSITIONS.get(report["status"], set()):
        return f"Cannot transition report from {report['status']} to {new_status}"
    ts = time.time()
    history_entry = {"status": new_status, "ts": ts, "actor": actor_id, "note": note}
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        update: dict = {
            "$set": {"status": new_status, "updated_at": ts, "admin_note": note},
            "$push": {"status_history": history_entry},
        }
        if matched_asset_id:
            update["$set"]["matched_asset_id"] = matched_asset_id
        updated = col.find_one_and_update(
            {"id": report_id, "status": report["status"]},
            update,
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        return updated or "Report status changed concurrently; reload and retry"
    with _LOCK:
        items = _file_load()
        for r in items:
            if r["id"] == report_id:
                if r.get("status") != report["status"]:
                    return "Report status changed concurrently; reload and retry"
                r["status"] = new_status
                r["updated_at"] = ts
                r["admin_note"] = note
                r.setdefault("status_history", []).append(history_entry)
                if matched_asset_id:
                    r["matched_asset_id"] = matched_asset_id
                _file_save(items)
                return r
    return None


def check_duplicate(
    lat: Optional[float],
    lon: Optional[float],
    category: str,
    radius_deg: float = 0.002,  # ~200m
    hours: int = 48,
) -> list[dict]:
    """Find possible duplicate reports nearby within time window."""
    if lat is None or lon is None:
        return []
    cutoff = time.time() - hours * 3600
    col = _col()
    candidates = []
    if col is not None:
        candidates = list(col.find(
            {"category": category, "created_at": {"$gte": cutoff}, "status": {"$nin": ["rejected"]}},
            {"_id": 0},
        ))
    else:
        with _LOCK:
            items = _file_load()
        candidates = [
            r for r in items
            if r["category"] == category
            and r["created_at"] >= cutoff
            and r["status"] != "rejected"
        ]
    return [
        r for r in candidates
        if r.get("lat") is not None
        and abs(r["lat"] - lat) < radius_deg
        and abs(r["lon"] - lon) < radius_deg
    ]


def nearby_reports(
    lat: float,
    lon: float,
    radius_km: float = 3.0,
    limit: int = 50,
    exclude_citizen_id: Optional[str] = None,
) -> list[dict]:
    """Privacy-safe nearby reports for citizen awareness (no reporter identity/contacts)."""
    items = list_reports(limit=500)
    radius_deg = max(0.001, radius_km / 111.0)
    out = []
    for r in items:
        rlat, rlon = r.get("lat"), r.get("lon")
        if rlat is None or rlon is None:
            continue
        if abs(float(rlat) - lat) > radius_deg or abs(float(rlon) - lon) > radius_deg:
            continue
        if exclude_citizen_id and r.get("citizen_id") == exclude_citizen_id:
            pass  # include own reports
        out.append({
            "id": r.get("id"),
            "category": r.get("category"),
            "severity": r.get("severity"),
            "description": (r.get("description") or "")[:220],
            "status": r.get("status"),
            "lat": round(float(rlat), 5),
            "lon": round(float(rlon), 5),
            "district": r.get("district"),
            "taluk": r.get("taluk"),
            "block": r.get("block"),
            "local_body": r.get("local_body"),
            "ward": r.get("ward") or r.get("ward_or_village"),
            "locality": r.get("locality"),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
            "has_image": bool(r.get("has_image")),
            "work_status": None,
            "is_own": bool(exclude_citizen_id and r.get("citizen_id") == exclude_citizen_id),
        })
        if len(out) >= limit:
            break
    return out
