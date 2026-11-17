"""
backend/app/governance.py — District / municipality / taluk / ward governance aggregation.

Provides read-only summary views used by the public governance portal:
  - state_overview()        → all districts, counts, status breakdown
  - district_overview(d)    → taluks + local bodies inside a district
  - area_overview(area)     → ward/local-body level detail with timeline
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional

from ml.config import DISTRICTS
from backend.app import reports as rpt
from backend.app import incidents as inc_mod


CLOSED_STATUSES = {"CLOSED", "VERIFIED"}
ACTIVE_STATUSES = {"NEW", "TRIAGED", "INSPECTION_REQUIRED", "INSPECTED",
                   "PLAN_PROPOSED", "APPROVED", "ASSIGNED", "IN_PROGRESS",
                   "COMPLETION_SUBMITTED", "ESCALATED", "REOPENED"}
REPORT_RESOLVED = {"accepted", "merged"}
REPORT_OPEN = {"new", "triaged"}


def _bucket_incidents(items: list[dict]) -> dict:
    total = len(items)
    resolved = sum(1 for i in items if i.get("status") in CLOSED_STATUSES)
    active = sum(1 for i in items if i.get("status") in ACTIVE_STATUSES)
    by_severity: dict[str, int] = defaultdict(int)
    for i in items:
        by_severity[i.get("severity", "medium")] += 1
    return {
        "total_work_orders": total,
        "resolved": resolved,
        "active": active,
        "by_severity": dict(by_severity),
        "sample_records": sum(bool(item.get("is_demo_sample")) for item in items),
    }


def _bucket_reports(items: list[dict]) -> dict:
    total = len(items)
    resolved = sum(1 for r in items if r.get("status") in REPORT_RESOLVED)
    open_count = sum(1 for r in items if r.get("status") in REPORT_OPEN)
    by_category: dict[str, int] = defaultdict(int)
    for r in items:
        by_category[r.get("category", "other")] += 1
    return {
        "total_reports": total,
        "resolved_reports": resolved,
        "open_reports": open_count,
        "by_category": dict(by_category),
        "sample_records": sum(bool(item.get("is_demo_sample")) for item in items),
    }


def _recent_timeline(incidents: list[dict], limit: int = 10) -> list[dict]:
    """Last `limit` status-change events across all incidents, newest first."""
    events = []
    for inc in incidents:
        for event in inc.get("status_history", []):
            events.append({
                "incident_id": inc["id"],
                "title": inc.get("title", ""),
                "status": event.get("status"),
                "ts": event.get("ts"),
                "note": event.get("note", ""),
                "severity": inc.get("severity"),
                "is_demo_sample": bool(inc.get("is_demo_sample")),
            })
    events.sort(key=lambda e: e.get("ts") or 0, reverse=True)
    return events[:limit]


def state_overview() -> dict:
    """Aggregate all districts — for the state-level governance dashboard."""
    all_reports = rpt.list_reports(limit=2000)
    all_incidents = inc_mod.list_incidents(limit=2000)

    # Group by district
    district_reports: dict[str, list] = defaultdict(list)
    for r in all_reports:
        d = (r.get("district") or "").strip()
        if d:
            district_reports[d].append(r)

    district_incidents: dict[str, list] = defaultdict(list)
    for i in all_incidents:
        d = (i.get("district") or "").strip()
        if d:
            district_incidents[d].append(i)

    all_districts = [name for name, *_ in DISTRICTS]
    all_districts.extend(sorted(
        (set(district_reports) | set(district_incidents)) - set(all_districts),
        key=str.casefold,
    ))

    districts = []
    for d in all_districts:
        r_stats = _bucket_reports(district_reports[d])
        i_stats = _bucket_incidents(district_incidents[d])
        districts.append({
            "district": d,
            **r_stats,
            **i_stats,
            "sample_records": r_stats["sample_records"] + i_stats["sample_records"],
            "current_issues": i_stats["active"] + r_stats["open_reports"],
        })

    # State totals
    total_reports = len(all_reports)
    total_incidents = len(all_incidents)
    resolved_incidents = sum(1 for i in all_incidents if i.get("status") in CLOSED_STATUSES)
    open_reports = sum(1 for r in all_reports if r.get("status") in REPORT_OPEN)

    return {
        "generated_at": time.time(),
        "total_districts": len(all_districts),
        "total_reports": total_reports,
        "total_work_orders": total_incidents,
        "resolved_work_orders": resolved_incidents,
        "open_reports": open_reports,
        "sample_records": sum(bool(item.get("is_demo_sample")) for item in all_reports + all_incidents),
        "data_mode": "recorded_reports_and_work_orders",
        "scope_note": "Counts are records in this NagarSync instance, including clearly labeled sample scenarios; this is not an official government reporting feed.",
        "districts": districts,
        "recent_activity": _recent_timeline(all_incidents, 15),
    }


def district_overview(district: str) -> dict:
    """Aggregate taluks and local bodies within a district."""
    all_reports = rpt.list_reports(area={"district": district}, limit=2000)
    all_incidents = inc_mod.list_incidents(area={"district": district}, limit=2000)

    # Group by taluk
    taluk_reports: dict[str, list] = defaultdict(list)
    taluk_incidents: dict[str, list] = defaultdict(list)
    for r in all_reports:
        t = (r.get("taluk") or "").strip() or "_unspecified"
        taluk_reports[t].append(r)
    for i in all_incidents:
        t = (i.get("taluk") or "").strip() or "_unspecified"
        taluk_incidents[t].append(i)

    # Group by local_body
    lb_reports: dict[str, list] = defaultdict(list)
    lb_incidents: dict[str, list] = defaultdict(list)
    for r in all_reports:
        lb = (r.get("local_body") or "").strip() or "_unspecified"
        lb_reports[lb].append(r)
    for i in all_incidents:
        lb = (i.get("local_body") or "").strip() or "_unspecified"
        lb_incidents[lb].append(i)

    all_taluks = sorted(set(list(taluk_reports.keys()) + list(taluk_incidents.keys())))
    all_lbs = sorted(set(list(lb_reports.keys()) + list(lb_incidents.keys())))

    taluks = []
    for t in all_taluks:
        r_stats = _bucket_reports(taluk_reports[t])
        i_stats = _bucket_incidents(taluk_incidents[t])
        taluks.append({"taluk": t, **r_stats, **i_stats})

    municipalities = []
    for lb in all_lbs:
        r_stats = _bucket_reports(lb_reports[lb])
        i_stats = _bucket_incidents(lb_incidents[lb])
        municipalities.append({"local_body": lb, **r_stats, **i_stats})

    return {
        "district": district,
        "generated_at": time.time(),
        **_bucket_reports(all_reports),
        **_bucket_incidents(all_incidents),
        "sample_records": (
            _bucket_reports(all_reports)["sample_records"]
            + _bucket_incidents(all_incidents)["sample_records"]
        ),
        "taluks": taluks,
        "municipalities": municipalities,
        "recent_activity": _recent_timeline(all_incidents, 20),
    }


def area_overview(district: str, taluk: Optional[str], local_body: Optional[str], ward: Optional[str]) -> dict:
    """Ward / local-body level detail — issues right now, resolved, development timeline."""
    area: dict[str, str] = {"district": district}
    if taluk:
        area["taluk"] = taluk
    if local_body:
        area["local_body"] = local_body
    if ward:
        area["ward"] = ward

    all_reports = rpt.list_reports(area=area, limit=500)
    all_incidents = inc_mod.list_incidents(area=area, limit=500)

    # Current open issues
    open_issues = [
        {
            "id": r["id"],
            "type": "report",
            "category": r.get("category"),
            "description": r.get("description", "")[:200],
            "status": r.get("status"),
            "location": r.get("location_text") or "",
            "created_at": r.get("created_at"),
            "is_demo_sample": bool(r.get("is_demo_sample")),
        }
        for r in all_reports if r.get("status") in REPORT_OPEN
    ] + [
        {
            "id": i["id"],
            "type": "work_order",
            "category": i.get("asset_type") or "infrastructure",
            "description": i.get("title", "")[:200],
            "status": i.get("status"),
            "severity": i.get("severity"),
            "location": i.get("ward") or i.get("local_body") or "",
            "created_at": i.get("created_at"),
            "is_demo_sample": bool(i.get("is_demo_sample")),
        }
        for i in all_incidents if i.get("status") in ACTIVE_STATUSES
    ]
    open_issues.sort(key=lambda x: x.get("created_at") or 0, reverse=True)

    # Resolved / completed work
    resolved_work = [
        {
            "id": i["id"],
            "title": i.get("title", ""),
            "severity": i.get("severity"),
            "status": i.get("status"),
            "created_at": i.get("created_at"),
            "resolved_at": next(
                (e["ts"] for e in reversed(i.get("status_history", [])) if e.get("status") in CLOSED_STATUSES),
                None,
            ),
            "is_demo_sample": bool(i.get("is_demo_sample")),
        }
        for i in all_incidents if i.get("status") in CLOSED_STATUSES
    ]
    resolved_work.sort(key=lambda x: x.get("resolved_at") or 0, reverse=True)

    # Development timeline — all status changes, newest first
    timeline = _recent_timeline(all_incidents, 30)

    # Resource monitoring — count assets by category from incidents
    resource_counts: dict[str, int] = defaultdict(int)
    for i in all_incidents:
        asset_type = (i.get("asset_type") or i.get("category") or "other").lower()
        resource_counts[asset_type] += 1

    return {
        "area": area,
        "generated_at": time.time(),
        **_bucket_reports(all_reports),
        **_bucket_incidents(all_incidents),
        "sample_records": (
            _bucket_reports(all_reports)["sample_records"]
            + _bucket_incidents(all_incidents)["sample_records"]
        ),
        "open_issues": open_issues[:50],
        "resolved_work": resolved_work[:30],
        "development_timeline": timeline,
        "resource_monitoring": dict(resource_counts),
        "resource_source": "recorded_work_orders",
        "resource_note": "Counts summarize work-order categories only; no live sensor feed or verified municipal asset inventory is connected.",
    }
