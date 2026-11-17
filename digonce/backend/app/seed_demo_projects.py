"""Opt-in seed for explicitly fictional local project-tracking scenarios."""
from __future__ import annotations

import argparse
import os

from backend.app import projects

_ACTOR = {"sub": "DEMO-SAMPLE-SYSTEM", "name": "NagarSync illustrative scenario"}
_SCENARIOS = (
    {
        "key": "sample-project-chennai-01",
        "title": "Sample neighbourhood drainage upgrade",
        "category": "Drainage",
        "district": "Chennai",
        "taluk": "Demo Taluk - Chennai",
        "local_body": "Demo Municipal Council - Chennai",
        "ward": "Demo Ward 01",
        "department": "Illustrative public works department",
        "estimated_cost_lakh": 450,
        "actual_expenditure_lakh": 210,
        "start_date": "2026-04-01",
        "expected_completion_date": "2027-03-31",
        "progress": 46,
        "status": "ONGOING",
        "note": "Fictional workflow data; not an approved or active public project.",
    },
    {
        "key": "sample-project-coimbatore-01",
        "title": "Sample streetlight maintenance programme",
        "category": "Streetlights",
        "district": "Coimbatore",
        "taluk": "Demo Taluk - Coimbatore",
        "local_body": "Demo Municipal Council - Coimbatore",
        "ward": "Demo Ward 01",
        "department": "Illustrative municipal maintenance",
        "estimated_cost_lakh": 180,
        "actual_expenditure_lakh": 95,
        "start_date": "2026-02-01",
        "expected_completion_date": "2026-12-31",
        "progress": 52,
        "status": "DELAYED",
        "delay_reason": "Illustrative delay reason for the sample workflow.",
        "note": "Fictional workflow data; not an approved or active public project.",
    },
    {
        "key": "sample-project-madurai-01",
        "title": "Sample local road resurfacing",
        "category": "Roads",
        "district": "Madurai",
        "taluk": "Demo Taluk - Madurai",
        "local_body": "Demo Municipal Council - Madurai",
        "ward": "Demo Ward 01",
        "department": "Illustrative roads department",
        "estimated_cost_lakh": 320,
        "actual_expenditure_lakh": 298,
        "start_date": "2025-11-01",
        "expected_completion_date": "2026-09-30",
        "progress": 100,
        "status": "VERIFIED",
        "actual_completion_date": "2026-09-10",
        "note": "Fictional workflow data; no real road work is represented.",
    },
)


def _advance(project: dict, target_status: str, progress: int, note: str) -> dict:
    path = {
        "ONGOING": ("SUBMITTED_FOR_APPROVAL", "APPROVED", "PLANNED", "ONGOING"),
        "DELAYED": ("SUBMITTED_FOR_APPROVAL", "APPROVED", "PLANNED", "ONGOING", "DELAYED"),
        "VERIFIED": (
            "SUBMITTED_FOR_APPROVAL", "APPROVED", "PLANNED", "ONGOING",
            "COMPLETED", "VERIFIED",
        ),
    }[target_status]
    current = project
    for status in path:
        values = {"status": status, "status_note": note}
        if status == target_status:
            values["progress"] = progress
            if status == "COMPLETED":
                values["actual_completion_date"] = "2026-09-10"
        current = projects.update_project(project["id"], values, _ACTOR)
        if not current:
            raise RuntimeError(f"Could not update sample project {project['id']}")
    return current


def seed_demo_projects() -> int:
    if os.getenv("MONGODB_URI"):
        raise RuntimeError(
            "Refusing to seed while MONGODB_URI is configured. "
            "Use an isolated local JSON-backed development environment."
        )
    existing = {
        item.get("demo_seed_key")
        for item in projects.list_projects(include_private=True, limit=500)
        if item.get("demo_seed_key")
    }
    created = 0
    for scenario in _SCENARIOS:
        if scenario["key"] in existing:
            continue
        values = {key: value for key, value in scenario.items() if key not in {"key", "note", "actual_expenditure_lakh"}}
        values["status"] = "PROPOSED"
        project = projects.create_project(
            values,
            _ACTOR,
            is_demo_sample=True,
            demo_seed_key=scenario["key"],
        )
        _advance(project, scenario["status"], scenario["progress"], scenario["note"])
        if scenario["actual_expenditure_lakh"]:
            projects.add_expenditure(
                project["id"],
                {
                    "amount_lakh": scenario["actual_expenditure_lakh"],
                    "description": "Illustrative sample expenditure; not a verified payment.",
                    "expenditure_date": scenario["expected_completion_date"],
                    "funding_source": "Illustrative sample funding",
                    "reference": "SAMPLE-ONLY",
                },
                _ACTOR,
            )
        projects.add_milestone(
            project["id"],
            {
                "title": "Illustrative inspection milestone",
                "description": "Sample-only demonstration record; not a real inspection.",
                "due_date": scenario["expected_completion_date"],
                "completed": scenario["status"] == "VERIFIED",
            },
            _ACTOR,
        )
        created += 1
    return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed clearly fictional development project scenarios in local JSON storage."
    )
    parser.add_argument(
        "--confirm-local-demo",
        action="store_true",
        help="Required confirmation; refuses to run when MONGODB_URI is configured.",
    )
    args = parser.parse_args()
    if not args.confirm_local_demo:
        parser.error("Pass --confirm-local-demo to confirm this is an isolated local demo.")
    try:
        count = seed_demo_projects()
    except RuntimeError as exc:
        parser.error(str(exc))
    print(f"Added {count} sample project records. Every record is marked as illustrative data.")
