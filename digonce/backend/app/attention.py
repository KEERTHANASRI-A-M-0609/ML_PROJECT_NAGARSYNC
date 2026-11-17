"""
backend/app/attention.py — Infrastructure & Areas Needing Attention.

Pipeline:
Events/Reports → Asset Matching → Data Validation → Feature Update →
Risk Assessment → Impact Assessment → Spatial Grouping → Priority Ranking → Repair Planning

Calculates a documented, normalized multi-factor Priority Score (0–100)
distinguishing priority ranking from budget-constrained repair selection.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from typing import Any

from ml.config import district_name
from ml.health import health_score, health_band
from backend.app.incidents import list_incidents
from backend.app.reports import list_reports


def calculate_priority_scores(state) -> pd.DataFrame:
    """
    Computes documented, normalized Priority Score (0–100) for all assets.
    
    Weights:
    - Risk/condition signal (35%): Model probability or demo priority signal, normalized by 0.30
    - Asset Criticality (25%): 1-5 scale normalized to 0-1
    - Service Disruption Impact (15%): Road class (arterial=1.0, sub=0.7, local=0.4) + traffic weight
    - Maintenance Urgency (15%): Physical condition degradation + inspection staleness
    - Citizen & Event Evidence (10%): Active citizen reports or DMA water leak alert
    """
    snap = state.snapshot.copy()
    if len(snap) == 0:
        return pd.DataFrame()

    # 1. Model-risk or simulated condition-priority component (0-1)
    risk_comp = (snap["risk_score"].astype(float) / 0.30).clip(0.0, 1.0)

    # 2. Criticality component (0-1)
    crit_comp = (snap["criticality"].astype(float) / 5.0).clip(0.0, 1.0)

    # 3. Disruption component (0-1)
    road_class_map = {"arterial": 1.0, "sub_arterial": 0.7, "local": 0.4}
    road_factor = snap["road_class"].astype(str).map(lambda c: road_class_map.get(c, 0.5))
    traffic_norm = (snap["daily_traffic"].astype(float) / 60_000.0).clip(0.0, 1.0)
    disruption_comp = (0.6 * road_factor + 0.4 * traffic_norm).clip(0.0, 1.0)

    # 4. Maintenance urgency (0-1)
    cond_factor = (1.0 - snap["condition_score"].astype(float)).clip(0.0, 1.0)
    stale_factor = (snap["months_since_inspection"].astype(float) / 24.0).clip(0.0, 1.0)
    maint_comp = (0.6 * cond_factor + 0.4 * stale_factor).clip(0.0, 1.0)

    # 5. Evidence component (0-1)
    # Check open citizen reports matched to assets
    open_reports = list_reports(limit=500)
    reported_asset_ids = {
        r.get("matched_asset_id") for r in open_reports 
        if r.get("matched_asset_id") and r.get("status") in ("new", "triaged", "accepted")
    }
    has_citizen_report = snap["asset_id"].isin(reported_asset_ids).astype(float)

    # Check DMA leak score for pipes
    leak_scores = snap["ward"].map(lambda w: float(state.leak_scores_latest.get(int(w), 0.0)))
    pipe_leak_evidence = ((snap["asset_type"] == "pipe") & (leak_scores > 0.08)).astype(float)
    evidence_comp = (0.6 * has_citizen_report + 0.4 * pipe_leak_evidence).clip(0.0, 1.0)

    # Final weighted score [0, 100]
    priority = (
        0.35 * risk_comp +
        0.25 * crit_comp +
        0.15 * disruption_comp +
        0.15 * maint_comp +
        0.10 * evidence_comp
    ) * 100.0

    snap["priority_score"] = priority.round(1)
    snap["comp_risk"] = (risk_comp * 100).round(1)
    snap["comp_criticality"] = (crit_comp * 100).round(1)
    snap["comp_disruption"] = (disruption_comp * 100).round(1)
    snap["comp_maintenance"] = (maint_comp * 100).round(1)
    snap["comp_evidence"] = (evidence_comp * 100).round(1)
    snap["has_active_report"] = has_citizen_report.astype(bool)

    return snap


def get_areas_needing_attention(
    state,
    limit: int = 50,
    ward: int | None = None,
    asset_type: str | None = None,
    min_priority: float = 30.0,
) -> dict[str, Any]:
    """
    Returns ranked attention areas with reasons, incident stage,
    spatial corridor clusters, and actionable recommendations.
    """
    scored = calculate_priority_scores(state)
    if len(scored) == 0:
        return {"items": [], "corridor_clusters": [], "total_flagged": 0}

    # Filter
    df = scored[scored["priority_score"] >= min_priority].copy()
    if ward is not None:
        df = df[df["ward"] == ward]
    if asset_type:
        df = df[df["asset_type"] == asset_type]

    # Map current active incident stages
    open_incidents = list_incidents(limit=1000)
    asset_incident_map = {}
    for inc in open_incidents:
        a_id = inc.get("asset_id")
        if a_id and inc.get("status") not in ("CLOSED", "CANCELLED", "REJECTED"):
            asset_incident_map[a_id] = {
                "incident_id": inc.get("id"),
                "status": inc.get("status"),
                "severity": inc.get("severity"),
                "assigned_to": inc.get("assigned_to"),
            }

    top_assets = df.nlargest(limit, "priority_score")
    asset_coords = state.assets.set_index("asset_id")[["lat", "lon"]]

    items = []
    for rank, (_, row) in enumerate(top_assets.iterrows(), start=1):
        a_id = str(row["asset_id"])
        corridor_id = str(row["corridor_id"])
        risk = float(row["risk_score"])
        hs = health_score(risk)
        w = int(row["ward"])

        # Fetch lat/lon
        lat, lon = None, None
        if a_id in asset_coords.index:
            c = asset_coords.loc[a_id]
            lat = float(c["lat"]) if not np.isnan(c["lat"]) else None
            lon = float(c["lon"]) if not np.isnan(c["lon"]) else None

        # Build transparent explanation reasons
        reasons = []
        if risk > 0.15:
            reasons.append(
                f"Simulated condition-priority score elevated ({risk*100:.1f}%)"
                if state.demo_mode
                else f"Calibrated 30d failure probability elevated ({risk*100:.1f}%)"
            )
        if int(row["criticality"]) >= 4:
            reasons.append(f"Tier-{row['criticality']} Critical infrastructure component")
        if row["road_class"] == "arterial":
            reasons.append("High-disruption arterial corridor (high traffic volume)")
        if float(row["condition_score"]) < 0.35:
            reasons.append(f"Severe physical degradation (condition index {row['condition_score']:.2f})")
        if int(row["months_since_inspection"]) > 12:
            reasons.append(f"Inspection overdue ({int(row['months_since_inspection'])} months stale)")
        if row["has_active_report"]:
            reasons.append("Active citizen report filed for this location")
        if row["asset_type"] == "pipe" and state.leak_scores_latest.get(w, 0) > 0.08:
            reasons.append(
                "Simulated recent water leak flags nearby"
                if state.demo_mode
                else "DMA minimum-night-flow anomaly detected nearby"
            )

        # Incident status
        inc_info = asset_incident_map.get(a_id, {"status": "NO_INCIDENT"})

        # Action recommendation
        if inc_info["status"] == "NO_INCIDENT":
            if risk > 0.20 or int(row["criticality"]) >= 4:
                recommendation = "Create Incident & Schedule Inspection"
            else:
                recommendation = "Bundle into Coordinated Corridor Plan"
        elif inc_info["status"] in ("NEW", "TRIAGED"):
            recommendation = "Admin Approval & Plan Proposal"
        elif inc_info["status"] == "APPROVED":
            recommendation = "Assign to Available Field Crew"
        elif inc_info["status"] == "ASSIGNED":
            recommendation = "Field Worker Dispatched (Pending Start)"
        elif inc_info["status"] == "IN_PROGRESS":
            recommendation = "Repair Underway (Awaiting Evidence)"
        elif inc_info["status"] == "COMPLETION_SUBMITTED":
            recommendation = "Field Evidence Submitted (Awaiting Verification)"
        elif inc_info["status"] == "VERIFIED":
            recommendation = "Verified (Ready for Administrative Closure)"
        else:
            recommendation = "Monitor Sensor Pulse"

        items.append({
            "rank": rank,
            "asset_id": a_id,
            "corridor_id": corridor_id,
            "asset_type": str(row["asset_type"]),
            "ward": w,
            "district": district_name(w),
            "priority_score": float(row["priority_score"]),
            "risk_score": round(risk, 4),
            "health_score": hs,
            "health_band": health_band(hs),
            "criticality": int(row["criticality"]),
            "work_cost_lakh": round(float(row["work_cost_lakh"]), 2),
            "mobilisation_cost_lakh": round(float(row["mobilisation_cost_lakh"]), 2),
            "road_class": str(row["road_class"]),
            "daily_traffic": int(row["daily_traffic"]),
            "lat": lat,
            "lon": lon,
            "reasons": reasons,
            "incident": inc_info,
            "recommendation": recommendation,
            "components": {
                "risk": float(row["comp_risk"]),
                "criticality": float(row["comp_criticality"]),
                "disruption": float(row["comp_disruption"]),
                "maintenance": float(row["comp_maintenance"]),
                "evidence": float(row["comp_evidence"]),
            },
        })

    # Spatial corridor grouping (Corridor Work Zones needing attention)
    corridor_groups = []
    for cor_id, grp in df.groupby("corridor_id"):
        if len(grp) >= 2 or grp["priority_score"].max() >= 65:
            mean_pri = float(grp["priority_score"].mean())
            max_pri = float(grp["priority_score"].max())
            cor_row = state.corridors[state.corridors["corridor_id"] == cor_id]
            lat = float(cor_row["lat"].iloc[0]) if len(cor_row) else None
            lon = float(cor_row["lon"].iloc[0]) if len(cor_row) else None
            w = int(cor_row["ward"].iloc[0]) if len(cor_row) else 0
            mob = float(cor_row["mobilisation_cost_lakh"].iloc[0]) if len(cor_row) else 2.8

            corridor_groups.append({
                "corridor_id": cor_id,
                "ward": w,
                "district": district_name(w),
                "lat": lat,
                "lon": lon,
                "n_vulnerable_assets": int(len(grp)),
                "asset_types": list(grp["asset_type"].unique()),
                "mean_priority": round(mean_pri, 1),
                "max_priority": round(max_pri, 1),
                "shared_mobilisation_lakh": mob,
                "estimated_coordination_saving_lakh": round(mob * (len(grp) - 1), 2),
                "assets": grp[["asset_id", "asset_type", "priority_score", "risk_score"]].to_dict(orient="records"),
            })

    corridor_groups.sort(key=lambda x: -x["mean_priority"])

    return {
        "items": items,
        "corridor_clusters": corridor_groups[:20],
        "total_flagged": int(len(df)),
        "data_mode": "simulated_demo" if state.demo_mode else "trained_model",
        "score_mode": state.score_mode,
    }
