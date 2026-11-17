"""District intelligence, officer, office, and public service directory.

Stores persistent records (MongoDB with JSON file fallback). No officer/contact
records are invented; only explicitly entered/verified records are returned.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from threading import Lock

from backend.app.db import get_db
from ml.config import REPORTS_DIR

DATA_DIR = Path(__file__).parent / "data"
_LOCK = Lock()

OFFICERS_STORE = REPORTS_DIR / "officers.json"
OFFICES_STORE = REPORTS_DIR / "offices.json"
SERVICES_STORE = REPORTS_DIR / "public_services.json"
ANNOUNCEMENTS_STORE = REPORTS_DIR / "announcements.json"
DISTRICT_PROFILE_PATH = DATA_DIR / "district_profiles.json"


def _col(name: str):
    db = get_db()
    return db[name] if db is not None else None


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")[:120]


def _now() -> float:
    return time.time()


def _paginate(items: list[dict], page: int, page_size: int) -> dict:
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start: start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
    }


def load_district_profiles() -> dict:
    data = _load_json(DISTRICT_PROFILE_PATH, {"districts": [], "source": {}})
    districts = data.get("districts") or []
    by_id = {}
    for d in districts:
        did = d.get("id") or _slug(d.get("name", ""))
        by_id[did] = {**d, "id": did}
    try:
        from backend.app.geography import tn_districts
        for ref in tn_districts():
            did = _slug(ref["name"])
            if did not in by_id:
                by_id[did] = {
                    "id": did, "name": ref["name"], "headquarters": "",
                    "lat": ref.get("lat"), "lon": ref.get("lon"),
                    "official_portal": "", "overview": "", "data_status": "reference_only",
                }
            else:
                by_id[did].setdefault("lat", ref.get("lat"))
                by_id[did].setdefault("lon", ref.get("lon"))
                by_id[did].setdefault("name", ref["name"])
    except Exception:
        pass
    items = sorted(by_id.values(), key=lambda x: (x.get("name") or ""))
    return {"districts": items, "source": data.get("source") or {}}


def get_district_profile(district_id_or_name: str) -> dict | None:
    key = _slug(district_id_or_name)
    data = load_district_profiles()
    for d in data["districts"]:
        if d.get("id") == key or _slug(d.get("name", "")) == key or (d.get("name") or "").casefold() == (district_id_or_name or "").casefold():
            return d
    return None


def _list_records(col_name: str, store_path: Path, filters: dict | None = None, include_archived: bool = False) -> list[dict]:
    filters = filters or {}
    col = _col(col_name)
    if col is not None:
        q = {}
        if not include_archived:
            q["archived_at"] = None
        for k, v in filters.items():
            if v is None or v == "":
                continue
            q[k] = {"$regex": f"^{re.escape(str(v))}$", "$options": "i"}
        return list(col.find(q, {"_id": 0}).sort("updated_at", -1))
    with _LOCK:
        items = _load_json(store_path, [])
    if not include_archived:
        items = [i for i in items if i.get("archived_at") is None]
    def match(item):
        for k, v in (filters or {}).items():
            if v is None or v == "":
                continue
            if str(item.get(k) or "").casefold() != str(v).casefold():
                return False
        return True
    return [i for i in items if match(i)]


def _get_record(col_name: str, store_path: Path, rec_id: str) -> dict | None:
    col = _col(col_name)
    if col is not None:
        return col.find_one({"id": rec_id}, {"_id": 0})
    with _LOCK:
        items = _load_json(store_path, [])
    return next((i for i in items if i.get("id") == rec_id), None)


def _save_record(col_name: str, store_path: Path, record: dict) -> dict:
    col = _col(col_name)
    if col is not None:
        col.replace_one({"id": record["id"]}, record, upsert=True)
        return record
    with _LOCK:
        items = _load_json(store_path, [])
        for idx, item in enumerate(items):
            if item.get("id") == record["id"]:
                items[idx] = record
                _save_json(store_path, items)
                return record
        items.append(record)
        _save_json(store_path, items)
    return record


def _archive_record(col_name: str, store_path: Path, rec_id: str, actor: dict) -> dict | None:
    rec = _get_record(col_name, store_path, rec_id)
    if not rec or rec.get("archived_at") is not None:
        return None
    rec["archived_at"] = _now()
    rec["archived_by"] = actor.get("sub")
    rec["updated_at"] = _now()
    return _save_record(col_name, store_path, rec)


OFFICER_COLLECTION = "officers"
OFFICE_COLLECTION = "government_offices"
SERVICE_COLLECTION = "public_services"
ANNOUNCEMENT_COLLECTION = "announcements"


def list_officers(filters: dict | None = None, q: str | None = None, page: int = 1, page_size: int = 20, include_archived: bool = False) -> dict:
    items = _list_records(OFFICER_COLLECTION, OFFICERS_STORE, filters, include_archived)
    if q:
        ql = q.casefold()
        def hay(i):
            return " ".join(str(i.get(k) or "") for k in ("name", "designation", "department", "district", "taluk", "local_body", "ward", "village", "locality", "office_name", "jurisdiction")).casefold()
        items = [i for i in items if ql in hay(i)]
    items.sort(key=lambda x: (str(x.get("district") or ""), str(x.get("department") or ""), str(x.get("designation") or ""), str(x.get("name") or "")))
    return _paginate(items, page, page_size)


def get_officer(officer_id: str) -> dict | None:
    return _get_record(OFFICER_COLLECTION, OFFICERS_STORE, officer_id)


def upsert_officer(values: dict, actor: dict, officer_id: str | None = None) -> dict:
    now = _now()
    existing = get_officer(officer_id) if officer_id else None
    rec = {
        **(existing or {}),
        **{k: v for k, v in values.items() if v is not None},
        "id": existing["id"] if existing else ("OFF-" + str(uuid.uuid4())[:8].upper()),
        "created_at": existing.get("created_at", now) if existing else now,
        "updated_at": now,
        "updated_by": actor.get("sub"),
        "archived_at": existing.get("archived_at") if existing else None,
    }
    rec.setdefault("verification_status", "unverified")
    rec.setdefault("source_name", "")
    rec.setdefault("source_url", "")
    rec.setdefault("last_verified", "")
    return _save_record(OFFICER_COLLECTION, OFFICERS_STORE, rec)


def archive_officer(officer_id: str, actor: dict) -> dict | None:
    return _archive_record(OFFICER_COLLECTION, OFFICERS_STORE, officer_id, actor)


def list_offices(filters: dict | None = None, q: str | None = None, page: int = 1, page_size: int = 20, include_archived: bool = False) -> dict:
    items = _list_records(OFFICE_COLLECTION, OFFICES_STORE, filters, include_archived)
    if q:
        ql = q.casefold()
        def hay(i):
            return " ".join(str(i.get(k) or "") for k in ("name", "office_type", "department", "district", "taluk", "local_body", "ward", "village", "locality", "address", "jurisdiction")).casefold()
        items = [i for i in items if ql in hay(i)]
    items.sort(key=lambda x: (str(x.get("district") or ""), str(x.get("office_type") or ""), str(x.get("name") or "")))
    return _paginate(items, page, page_size)


def get_office(office_id: str) -> dict | None:
    return _get_record(OFFICE_COLLECTION, OFFICES_STORE, office_id)


def upsert_office(values: dict, actor: dict, office_id: str | None = None) -> dict:
    now = _now()
    existing = get_office(office_id) if office_id else None
    rec = {
        **(existing or {}),
        **{k: v for k, v in values.items() if v is not None},
        "id": existing["id"] if existing else ("OFC-" + str(uuid.uuid4())[:8].upper()),
        "created_at": existing.get("created_at", now) if existing else now,
        "updated_at": now,
        "updated_by": actor.get("sub"),
        "archived_at": existing.get("archived_at") if existing else None,
    }
    rec.setdefault("verification_status", "unverified")
    rec.setdefault("source_name", "")
    rec.setdefault("source_url", "")
    rec.setdefault("last_verified", "")
    return _save_record(OFFICE_COLLECTION, OFFICES_STORE, rec)


def archive_office(office_id: str, actor: dict) -> dict | None:
    return _archive_record(OFFICE_COLLECTION, OFFICES_STORE, office_id, actor)


def default_service_categories() -> list[dict]:
    return [
        {"id": "roads", "label": "Potholes and damaged roads", "department": "Roads / Highways / Municipal Engineering", "office_types": ["Municipal Corporation Office", "Municipality Office", "Town Panchayat Office", "Village Panchayat Office", "Highways Department Office", "Public Works Department Office"], "issue_category": "pothole", "grievance_portal": "", "note": "Jurisdiction depends on road type (urban local body vs highways/PWD)."},
        {"id": "water", "label": "Water leakage and drinking water supply", "department": "Water Supply / TWAD / Municipal Water", "office_types": ["Municipality Office", "Municipal Corporation Office", "Town Panchayat Office", "Village Panchayat Office", "Water Supply Office"], "issue_category": "water_leak", "grievance_portal": "", "note": "Responsibility may be with the local body or water supply authority."},
        {"id": "streetlight", "label": "Broken streetlights", "department": "Municipal / Local Body Electrical", "office_types": ["Municipal Corporation Office", "Municipality Office", "Town Panchayat Office", "Village Panchayat Office", "Electricity Distribution Office"], "issue_category": "streetlight", "grievance_portal": "", "note": "Streetlights are usually maintained by the local body; supply faults may involve the electricity utility."},
        {"id": "drainage", "label": "Drainage and sewage problems", "department": "Sanitation / Sewerage / Municipal Engineering", "office_types": ["Municipal Corporation Office", "Municipality Office", "Town Panchayat Office", "Sanitation Office"], "issue_category": "drainage", "grievance_portal": "", "note": "Sewage and stormwater responsibility varies by local body."},
        {"id": "waste", "label": "Garbage and sanitation", "department": "Sanitation / Solid Waste Management", "office_types": ["Municipal Corporation Office", "Municipality Office", "Town Panchayat Office", "Village Panchayat Office", "Sanitation Office"], "issue_category": "waste", "grievance_portal": "", "note": "Report to local body sanitation or solid waste management."},
        {"id": "bridge", "label": "Damaged bridges", "department": "Public Works / Highways / Rural Development", "office_types": ["Public Works Department Office", "Highways Department Office", "District Collectorate"], "issue_category": "bridge_damage", "grievance_portal": "", "note": "Bridge ownership may be PWD, highways, rural development, or local body."},
        {"id": "maintenance", "label": "Public infrastructure maintenance", "department": "Relevant local body / engineering department", "office_types": ["Municipality Office", "Municipal Corporation Office", "Town Panchayat Office", "Village Panchayat Office", "Public Works Department Office"], "issue_category": "other", "grievance_portal": "", "note": "Select the closest issue type for accurate routing."},
        {"id": "other", "label": "Other civic services", "department": "Local administration / grievance cell", "office_types": ["District Collectorate", "Taluk Office", "Municipality Office", "Village Panchayat Office"], "issue_category": "other", "grievance_portal": "https://cmhelpline.tnega.org/", "note": "Use official grievance portals when available; NagarSync can also record the issue for local follow-up."},
    ]


def list_public_services(q: str | None = None) -> list[dict]:
    stored = _list_records(SERVICE_COLLECTION, SERVICES_STORE, {}, False)
    by_id = {s["id"]: s for s in default_service_categories()}
    for s in stored:
        sid = s.get("service_id") or s.get("id")
        if sid and sid in by_id:
            by_id[sid] = {**by_id[sid], **s}
        elif sid:
            by_id[sid] = s
    items = list(by_id.values())
    if q:
        ql = q.casefold()
        items = [i for i in items if ql in " ".join(str(i.get(k) or "") for k in ("label", "department", "note")).casefold()]
    return items


def upsert_public_service(values: dict, actor: dict, service_id: str | None = None) -> dict:
    now = _now()
    existing = _get_record(SERVICE_COLLECTION, SERVICES_STORE, service_id) if service_id else None
    rec = {
        **(existing or {}),
        **{k: v for k, v in values.items() if v is not None},
        "id": existing["id"] if existing else (service_id or ("SVC-" + str(uuid.uuid4())[:8].upper())),
        "created_at": existing.get("created_at", now) if existing else now,
        "updated_at": now,
        "updated_by": actor.get("sub"),
        "archived_at": None,
    }
    return _save_record(SERVICE_COLLECTION, SERVICES_STORE, rec)


def list_announcements(filters: dict | None = None, page: int = 1, page_size: int = 20) -> dict:
    items = _list_records(ANNOUNCEMENT_COLLECTION, ANNOUNCEMENTS_STORE, filters, False)
    items.sort(key=lambda x: x.get("published_at") or x.get("created_at") or 0, reverse=True)
    return _paginate(items, page, page_size)


def upsert_announcement(values: dict, actor: dict, ann_id: str | None = None) -> dict:
    now = _now()
    existing = _get_record(ANNOUNCEMENT_COLLECTION, ANNOUNCEMENTS_STORE, ann_id) if ann_id else None
    rec = {
        **(existing or {}),
        **{k: v for k, v in values.items() if v is not None},
        "id": existing["id"] if existing else ("ANN-" + str(uuid.uuid4())[:8].upper()),
        "created_at": existing.get("created_at", now) if existing else now,
        "updated_at": now,
        "updated_by": actor.get("sub"),
        "archived_at": None,
    }
    return _save_record(ANNOUNCEMENT_COLLECTION, ANNOUNCEMENTS_STORE, rec)


def archive_announcement(ann_id: str, actor: dict) -> dict | None:
    return _archive_record(ANNOUNCEMENT_COLLECTION, ANNOUNCEMENTS_STORE, ann_id, actor)


def _score_match(item: dict, area: dict) -> int:
    score = 0
    for key, weight in (("district", 4), ("taluk", 3), ("local_body", 3), ("block", 2), ("ward", 2), ("village", 2), ("locality", 1)):
        av = str(area.get(key) or "").casefold()
        iv = str(item.get(key) or "").casefold()
        ij = str(item.get("jurisdiction") or "").casefold()
        if av and iv and av == iv:
            score += weight
        elif av and ij and av == ij:
            score += weight
        elif av and (av in iv or av in ij):
            score += max(1, weight - 1)
    return score


def find_local_contacts(area: dict, service_id: str | None = None, limit: int = 20) -> dict:
    district = (area.get("district") or "").strip()
    officers = _list_records(OFFICER_COLLECTION, OFFICERS_STORE, {"district": district} if district else {}, False)
    offices = _list_records(OFFICE_COLLECTION, OFFICES_STORE, {"district": district} if district else {}, False)
    svc = None
    if service_id:
        for s in list_public_services():
            if s.get("id") == service_id or s.get("service_id") == service_id:
                svc = s
                break
    def filter_service(items, role_key="designation"):
        if not svc:
            return items
        types = [str(t).casefold() for t in (svc.get("office_types") or [])]
        dept = str(svc.get("department") or "").casefold()
        out = []
        for it in items:
            it_type = str(it.get("office_type") or it.get(role_key) or "").casefold()
            it_dept = str(it.get("department") or "").casefold()
            if types and any(t in it_type or it_type in t for t in types):
                out.append(it)
            elif dept and any(part.strip() and part.strip() in it_dept for part in dept.split("/")):
                out.append(it)
        return out or items
    ranked_officers = sorted(filter_service(officers, "designation"), key=lambda i: (_score_match(i, area), 1 if i.get("verification_status") == "verified" else 0, i.get("updated_at") or 0), reverse=True)
    ranked_offices = sorted(filter_service(offices, "office_type"), key=lambda i: (_score_match(i, area), 1 if i.get("verification_status") == "verified" else 0, i.get("updated_at") or 0), reverse=True)
    best_exact = any(_score_match(i, area) >= 6 for i in ranked_officers + ranked_offices)
    limitation = ""
    if not district:
        limitation = "Select a district or pinpoint a location to identify responsible administration."
    elif not ranked_officers and not ranked_offices:
        limitation = "No verified officer or office records are available for this jurisdiction yet. Use the official district portal or state grievance channels as the best available contact path."
    elif not best_exact:
        limitation = "Exact jurisdiction-level records are unavailable; showing the best available district-level contacts. Verify responsibility with the listed office."
    return {
        "area": area,
        "service": svc,
        "officers": ranked_officers[:limit],
        "offices": ranked_offices[:limit],
        "exact_jurisdiction_match": best_exact,
        "limitation": limitation,
        "record_count": {"officers": len(ranked_officers), "offices": len(ranked_offices)},
    }


def district_summary(district_name: str) -> dict:
    profile = get_district_profile(district_name)
    dname = (profile or {}).get("name") or district_name
    officers = _list_records(OFFICER_COLLECTION, OFFICERS_STORE, {"district": dname}, False)
    offices = _list_records(OFFICE_COLLECTION, OFFICES_STORE, {"district": dname}, False)
    announcements = _list_records(ANNOUNCEMENT_COLLECTION, ANNOUNCEMENTS_STORE, {"district": dname}, False)
    announcements.sort(key=lambda x: x.get("published_at") or x.get("updated_at") or 0, reverse=True)
    intel = {}
    try:
        from backend.app import governance as gov_mod
        intel = gov_mod.district_overview(dname)
    except Exception:
        intel = {"available": False, "note": "Governance intelligence unavailable."}
    projects = []
    try:
        from backend.app import projects as projects_mod
        projects = projects_mod.list_projects(district=dname, include_private=False, limit=100)
    except Exception:
        projects = []
    return {
        "profile": profile or {"name": dname, "id": _slug(dname), "data_status": "reference_only", "headquarters": "", "overview": "", "official_portal": ""},
        "officers": officers,
        "offices": offices,
        "announcements": announcements[:20],
        "intelligence": intel,
        "projects": projects,
        "counts": {"officers": len(officers), "offices": len(offices), "announcements": len(announcements), "projects": len(projects)},
    }
