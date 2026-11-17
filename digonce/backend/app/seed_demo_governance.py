"""Opt-in local-only seed for clearly identified governance demo scenarios."""
from __future__ import annotations

import argparse
import os

from backend.app import admin_assets, incidents, reports

_AREAS = (
    {
        "district": "Chennai",
        "taluk": "Demo Taluk - Chennai",
        "local_body": "Demo Municipal Council - Chennai",
        "ward": "Demo Ward 01",
    },
    {
        "district": "Coimbatore",
        "taluk": "Demo Taluk - Coimbatore",
        "local_body": "Demo Municipal Council - Coimbatore",
        "ward": "Demo Ward 01",
    },
    {
        "district": "Madurai",
        "taluk": "Demo Taluk - Madurai",
        "local_body": "Demo Municipal Council - Madurai",
        "ward": "Demo Ward 01",
    },
)

_BULK_SCENARIOS = (
    ("salem-01", "Salem", "pothole", "SAMPLE ONLY: road-surface report in an illustrative Salem ward.", "Demo road inspection - Salem", "high", ("TRIAGED", "INSPECTION_REQUIRED", "INSPECTED", "PLAN_PROPOSED", "APPROVED", "ASSIGNED", "IN_PROGRESS")),
    ("tiruchirappalli-01", "Tiruchirappalli", "streetlight", "SAMPLE ONLY: streetlight report in an illustrative Tiruchirappalli ward.", "Demo streetlight check - Tiruchirappalli", "medium", ("TRIAGED", "INSPECTION_REQUIRED", "INSPECTED", "PLAN_PROPOSED", "APPROVED", "ASSIGNED")),
    ("tirunelveli-01", "Tirunelveli", "water_leak", "SAMPLE ONLY: water-line report in an illustrative Tirunelveli ward.", "Demo water-line inspection - Tirunelveli", "critical", ("TRIAGED", "INSPECTION_REQUIRED", "ESCALATED")),
    ("erode-01", "Erode", "bridge_damage", "SAMPLE ONLY: bridge inspection report in an illustrative Erode ward.", "Demo bridge assessment - Erode", "high", ("TRIAGED", "INSPECTION_REQUIRED", "INSPECTED", "PLAN_PROPOSED", "APPROVED", "ASSIGNED", "IN_PROGRESS", "COMPLETION_SUBMITTED", "VERIFIED", "CLOSED")),
    ("tiruppur-01", "Tiruppur", "streetlight", "SAMPLE ONLY: lighting report in an illustrative Tiruppur ward.", "Demo lighting check - Tiruppur", "low", ("TRIAGED",)),
    ("vellore-01", "Vellore", "pothole", "SAMPLE ONLY: road-surface report in an illustrative Vellore ward.", "Demo road inspection - Vellore", "medium", ("TRIAGED", "INSPECTION_REQUIRED", "INSPECTED", "PLAN_PROPOSED")),
    ("thanjavur-01", "Thanjavur", "water_leak", "SAMPLE ONLY: water-service report in an illustrative Thanjavur ward.", "Demo water-service check - Thanjavur", "high", ("CANCELLED",)),
    ("dindigul-01", "Dindigul", "other", "SAMPLE ONLY: public-works report in an illustrative Dindigul ward.", "Demo public-works inspection - Dindigul", "medium", ("TRIAGED", "INSPECTION_REQUIRED", "INSPECTED", "PLAN_PROPOSED", "APPROVED", "ASSIGNED", "IN_PROGRESS")),
    ("thoothukudi-01", "Thoothukudi", "streetlight", "SAMPLE ONLY: streetlight report in an illustrative Thoothukudi ward.", None, "low", ()),
    ("cuddalore-01", "Cuddalore", "pothole", "SAMPLE ONLY: road report in an illustrative Cuddalore ward.", None, "medium", ()),
    ("kanchipuram-01", "Kanchipuram", "water_leak", "SAMPLE ONLY: water-service report in an illustrative Kanchipuram ward.", None, "high", ()),
    ("tiruvannamalai-01", "Tiruvannamalai", "other", "SAMPLE ONLY: public-works report in an illustrative Tiruvannamalai ward.", None, "low", ()),
)

_ASSET_SCENARIOS = (
    ("SAMPLE - North ward road segment", "road", "Salem", 1, 8, 0.62, 3, 24),
    ("SAMPLE - Central water main", "water_pipe", "Coimbatore", 2, 16, 0.48, 5, 38),
    ("SAMPLE - East ward streetlight", "streetlight", "Madurai", 3, 6, 0.71, 2, 8),
    ("SAMPLE - Canal-side drain", "drainage", "Chennai", 4, 22, 0.39, 4, 31),
    ("SAMPLE - Market approach road", "road", "Erode", 5, 12, 0.55, 3, 18),
    ("SAMPLE - South water main", "water_pipe", "Tirunelveli", 6, 19, 0.44, 5, 42),
    ("SAMPLE - Bus stand lighting", "streetlight", "Tiruchirappalli", 7, 9, 0.67, 2, 12),
    ("SAMPLE - Ward drainage link", "drainage", "Thanjavur", 8, 14, 0.58, 3, 21),
    ("SAMPLE - Riverside bridge approach", "bridge", "Vellore", 9, 27, 0.36, 5, 56),
    ("SAMPLE - Community road segment", "road", "Tiruppur", 10, 11, 0.73, 2, 16),
)


def _sample_report(seed_key: str, area: dict, category: str, description: str) -> dict:
    return reports.create_report(
        citizen_id="DEMO-SAMPLE-SYSTEM",
        citizen_name="NagarSync illustrative scenario",
        category=category,
        description=description,
        lat=None,
        lon=None,
        location_text="Illustrative demo location; not a verified address",
        **area,
        image_filename=None,
        image_data_url=None,
        is_demo_sample=True,
        demo_seed_key=seed_key,
    )


def _sample_incident(seed_key: str, report: dict, title: str, description: str, severity: str) -> dict:
    incident = incidents.create_incident(
        asset_id=None,
        report_id=report["id"],
        title=title,
        description=description,
        severity=severity,
        created_by="DEMO-SAMPLE-SYSTEM",
        district=report["district"],
        taluk=report["taluk"],
        local_body=report["local_body"],
        ward=report["ward"],
        asset_type=report["category"],
        is_demo_sample=True,
        demo_seed_key=seed_key,
    )
    reports.attach_incident(report["id"], incident["id"])
    reports.update_report_fields(
        report["id"],
        {"status": "triaged"},
        "DEMO-SAMPLE-SYSTEM",
    )
    reports.update_report_fields(
        report["id"],
        {"status": "accepted"},
        "DEMO-SAMPLE-SYSTEM",
    )
    return incident


def _advance(incident_id: str, statuses: tuple[str, ...]) -> None:
    for status in statuses:
        result = incidents.transition_incident(
            incident_id,
            status,
            "DEMO-SAMPLE-SYSTEM",
            "Illustrative sample workflow only; not a real municipal update.",
        )
        if isinstance(result, str):
            raise RuntimeError(f"Unable to seed sample workflow: {result}")


def seed_demo_governance() -> int:
    if os.getenv("MONGODB_URI"):
        raise RuntimeError(
            "Refusing to seed while MONGODB_URI is configured. "
            "Use a local development environment without a shared database."
        )

    existing_reports = {
        item.get("demo_seed_key"): item
        for item in reports.list_reports(limit=1000, include_archived=True)
        if item.get("demo_seed_key")
    }
    existing_incidents = {
        item.get("demo_seed_key"): item
        for item in incidents.list_incidents(limit=1000, include_archived=True)
        if item.get("demo_seed_key")
    }
    existing_assets = {
        item.get("demo_seed_key")
        for item in admin_assets.list_assets(include_archived=True)
        if item.get("demo_seed_key")
    }
    created = 0

    chennai_report = existing_reports.get("sample-report-chennai-01")
    if chennai_report is None:
        chennai_report = _sample_report(
            "sample-report-chennai-01", _AREAS[0], "streetlight",
            "Illustrative scenario: a resident reports a streetlight for demonstration.",
        )
        created += 1
    if "sample-work-chennai-01" not in existing_incidents:
        incident = _sample_incident(
            "sample-work-chennai-01",
            chennai_report,
            "Demo streetlight inspection",
            "Sample work order showing a completed workflow; not a real repair.",
            "medium",
        )
        _advance(
            incident["id"],
            (
                "TRIAGED", "INSPECTION_REQUIRED", "INSPECTED", "PLAN_PROPOSED",
                "APPROVED", "ASSIGNED", "IN_PROGRESS", "COMPLETION_SUBMITTED",
                "VERIFIED", "CLOSED",
            ),
        )
        created += 1

    coimbatore_report = existing_reports.get("sample-report-coimbatore-01")
    if coimbatore_report is None:
        coimbatore_report = _sample_report(
            "sample-report-coimbatore-01", _AREAS[1], "pothole",
            "Illustrative scenario: a resident reports a road issue for demonstration.",
        )
        created += 1
    if "sample-work-coimbatore-01" not in existing_incidents:
        incident = _sample_incident(
            "sample-work-coimbatore-01",
            coimbatore_report,
            "Demo road inspection",
            "Sample work order showing an in-progress workflow; not a real repair.",
            "high",
        )
        _advance(
            incident["id"],
            ("TRIAGED", "INSPECTION_REQUIRED", "INSPECTED", "PLAN_PROPOSED",
             "APPROVED", "ASSIGNED", "IN_PROGRESS"),
        )
        created += 1

    if "sample-report-madurai-01" not in existing_reports:
        _sample_report(
            "sample-report-madurai-01",
            _AREAS[2],
            "water_leak",
            "Illustrative scenario: a resident reports a water issue for demonstration.",
        )
        created += 1

    for key, district, category, description, title, severity, statuses in _BULK_SCENARIOS:
        report_key = f"sample-report-{key}"
        report = existing_reports.get(report_key)
        if report is None:
            area = {
                "district": district,
                "taluk": f"Demo Taluk - {district}",
                "local_body": f"Demo Municipal Council - {district}",
                "ward": "Demo Ward 02",
            }
            report = _sample_report(report_key, area, category, description)
            created += 1
        incident_key = f"sample-work-{key}"
        if title and incident_key not in existing_incidents:
            incident = _sample_incident(
                incident_key,
                report,
                title,
                "SAMPLE ONLY: illustrative workflow record; not a real municipal work order.",
                severity,
            )
            if statuses:
                _advance(incident["id"], statuses)
            created += 1

    for index, asset in enumerate(_ASSET_SCENARIOS, start=1):
        name, asset_type, district, ward, age, condition, criticality, work_cost = asset
        seed_key = f"sample-asset-{index:02d}"
        if seed_key in existing_assets:
            continue
        admin_assets.create_asset(
            {
                "name": name,
                "asset_type": asset_type,
                "district": district,
                "ward": ward,
                "lat": None,
                "lon": None,
                "age_years": age,
                "condition_score": condition,
                "criticality": criticality,
                "work_cost_lakh": work_cost,
                "is_demo_sample": True,
                "demo_seed_key": seed_key,
            },
            "DEMO-SAMPLE-SYSTEM",
        )
        created += 1

    return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add clearly labeled sample governance records to local JSON stores."
    )
    parser.add_argument(
        "--confirm-local-demo",
        action="store_true",
        help="Required confirmation; refuses to run when MONGODB_URI is configured.",
    )
    args = parser.parse_args()
    if not args.confirm_local_demo:
        parser.error("Pass --confirm-local-demo to confirm this is a local demo database.")
    try:
        count = seed_demo_governance()
    except RuntimeError as exc:
        parser.error(str(exc))
    print(f"Added {count} sample records. They are labeled as illustrative demo data.")
