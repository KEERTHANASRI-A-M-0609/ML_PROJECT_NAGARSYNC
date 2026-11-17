"""
ml/simulation.py — Rolling 12-month simulation with common random numbers.

All data is SIMULATED.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit

from ml.config import (
    HISTORY_MONTHS, SIM_MONTHS, TOTAL_MONTHS,
    ANNUAL_BUDGET_FRACTION,
)
from ml.city import RAINFALL_NORMALS, DETR_RATE, HAZARD_INTERCEPT
from ml.optimizer import (
    oldest_first, risk_first, ml_per_rupee,
    greedy_coordinated, digonce_ilp, compute_plan_cost,
)
from ml.scheduling import schedule_plan, best_window


def _realised_rain(month_idx: int, rng: np.random.Generator) -> float:
    normal = RAINFALL_NORMALS[month_idx % 12]
    return max(0.0, normal + rng.normal(0, normal * 0.3))


def _build_snapshot(
    assets: pd.DataFrame,
    state: dict,
    month: int,
    risk_model,
    leak_scores: dict,
    use_leak: bool = True,
) -> pd.DataFrame:
    """Build current-month feature snapshot and attach risk scores."""
    from ml.risk_model import _encode

    n = len(assets)
    snap = assets.reset_index(drop=True).copy()
    snap["age_years"] = state["age"]
    snap["condition_score"] = state["last_insp_condition"]
    snap["months_since_inspection"] = state["months_since_insp"]
    snap["sensor_reading"] = state["sensor"]
    snap["months_since_repair"] = state["months_since_repair"]
    snap["previous_failures"] = state["prev_failures"]
    snap["maintenance_count"] = state["maint_count"]
    snap["rainfall_mm"] = RAINFALL_NORMALS[month % 12]
    snap["dma_leak_score"] = [
        leak_scores.get((int(w), month), 0.0) if at == "pipe" else 0.0
        for w, at in zip(assets["ward"].values, assets["asset_type"].values)
    ]
    snap["month"] = month

    df_enc = _encode(snap)
    feat_cols = risk_model.feature_cols
    X = df_enc[feat_cols].fillna(df_enc[feat_cols].median()).values
    snap["risk_score"] = risk_model.predict_proba(X)
    return snap


def run_simulation(
    assets: pd.DataFrame,
    corridors: pd.DataFrame,
    risk_model,
    risk_model_no_leak,
    leak_scores: dict,
    traffic_profiles: pd.DataFrame,
    seed: int,
    strategy: str,
    monthly_budget: float,
    use_calibration: bool = True,
    use_leak_link: bool = True,
    use_traffic_schedule: bool = True,
) -> dict:
    """
    Simulate SIM_MONTHS months starting from HISTORY_MONTHS state.
    Returns per-month and aggregate metrics.
    """
    rng = np.random.default_rng(seed)

    # Ensure mobilisation_cost_lakh is present (merge from corridors if needed)
    if "mobilisation_cost_lakh" not in assets.columns:
        mob_map = corridors.set_index("corridor_id")["mobilisation_cost_lakh"]
        assets = assets.copy()
        assets["mobilisation_cost_lakh"] = assets["corridor_id"].map(mob_map)

    n = len(assets)

    # Initialise state from end of history (approximate)
    state = {
        "condition": rng.uniform(0.4, 1.0, n),
        "age": assets["install_age_years"].values.copy() + HISTORY_MONTHS / 12,
        "prev_failures": np.zeros(n, dtype=int),
        "maint_count": np.zeros(n, dtype=int),
        "months_since_repair": rng.integers(1, 24, n).astype(float),
        "months_since_insp": rng.integers(1, 12, n).astype(float),
        "last_insp_condition": rng.uniform(0.4, 1.0, n),
        "sensor": rng.uniform(0.4, 1.0, n),
    }

    asset_frailty = rng.normal(0, 0.5, n)
    cor_frailty = assets["corridor_frailty"].values
    cor_vintage = assets["corridor_vintage_years"].values
    asset_type = assets["asset_type"].values
    traffic = assets["daily_traffic"].values.astype(float)
    ward = assets["ward"].values.astype(int)

    # Track recent repairs for re-dig detection
    last_repair_month: dict[str, int] = {}

    agg = {
        "failures": 0, "crit_weighted_failures": 0.0,
        "planned_spend": 0.0, "emergency_spend": 0.0,
        "planned_visits": 0, "reactive_visits": 0,
        "total_road_closures": 0, "re_dig_events": 0,
        "vehicle_hours_disrupted": 0.0,
    }

    model = risk_model if use_leak_link else risk_model_no_leak
    use_leak = use_leak_link

    carryover = 0.0

    for sim_m in range(SIM_MONTHS):
        month_abs = HISTORY_MONTHS + sim_m
        rain = _realised_rain(month_abs, rng)
        budget_this_month = monthly_budget + carryover

        # Build snapshot & predict
        snap = _build_snapshot(
            assets, state, month_abs, model, leak_scores, use_leak
        )
        if not use_calibration:
            # Use raw (uncalibrated) probabilities from the same model
            from ml.risk_model import _encode
            feat_cols = model.feature_cols
            df_enc = _encode(snap)
            X = df_enc[feat_cols].fillna(df_enc[feat_cols].median()).values
            snap["risk_score"] = model.predict_raw(X)

        # Select repairs
        selected = _select(snap, strategy, budget_this_month)
        plan_cost = compute_plan_cost(selected, coordinated=(strategy in ("greedy_coordinated", "digonce_ilp")))
        carryover = max(0.0, budget_this_month - plan_cost)

        # Traffic-aware scheduling
        if use_traffic_schedule and len(selected) > 0 and len(traffic_profiles) > 0:
            for _, row in selected.iterrows():
                w = best_window(
                    float(row["daily_traffic"]),
                    int(row.get("nearest_junction", 0)),
                    float(row["repair_hours"]),
                    traffic_profiles,
                )
                agg["vehicle_hours_disrupted"] += w["best_disruption_vh"]
        elif len(selected) > 0:
            # Default 09:00 start
            for _, row in selected.iterrows():
                wl = max(1, int(np.ceil(row["repair_hours"])))
                profile = np.array([
                    0.5, 0.3, 0.2, 0.2, 0.3, 0.6, 1.5, 2.5, 2.8, 2.0,
                    1.5, 1.4, 1.6, 1.5, 1.4, 1.6, 2.2, 2.8, 2.5, 1.8,
                    1.4, 1.1, 0.8, 0.6,
                ], dtype=float)
                profile /= profile.sum()
                agg["vehicle_hours_disrupted"] += float(
                    row["daily_traffic"] * profile[9:9 + wl].sum()
                )

        # Apply planned repairs
        selected_ids = set(selected["asset_id"].tolist()) if len(selected) > 0 else set()
        repair_mask = np.array([aid in selected_ids for aid in assets["asset_id"].values])
        state["condition"][repair_mask] = rng.uniform(0.7, 1.0, repair_mask.sum())
        state["months_since_repair"][repair_mask] = 0
        for aid in selected_ids:
            last_repair_month[aid] = sim_m

        agg["planned_spend"] += plan_cost
        agg["planned_visits"] += int(selected.groupby("corridor_id").ngroups) if len(selected) > 0 else 0
        agg["total_road_closures"] += len(selected_ids)

        # Deterioration
        detr = np.array([DETR_RATE[t] for t in asset_type])
        traffic_eff = np.where(np.isin(asset_type, ["road", "bridge"]), traffic / 50_000 * 0.005, 0.0)
        state["condition"] -= detr + traffic_eff + rain / 200 * 0.003
        state["condition"] = state["condition"].clip(0, 1)
        state["age"] += 1 / 12

        # Failure hazard
        intercept = np.array([HAZARD_INTERCEPT[t] for t in asset_type])
        logit = (
            intercept
            + 0.3 * (1 - state["condition"])
            + 0.02 * state["age"]
            + np.where(np.isin(asset_type, ["road", "bridge"]), traffic / 50_000, 0.0)
            + 0.5 * (rain / 200)
            + 0.15 * state["prev_failures"].clip(0, 5)
            + 0.3 * asset_frailty
            + 0.2 * cor_frailty
            + 0.01 * cor_vintage
        )
        for i, (w, at) in enumerate(zip(ward, asset_type)):
            if at == "pipe":
                logit[i] += 1.5 * leak_scores.get((int(w), month_abs), 0.0)

        prob = expit(logit)
        # Common random numbers: use seed-based draw
        crn_rng = np.random.default_rng(seed * 10000 + sim_m)
        failed = crn_rng.random(n) < prob

        # Don't double-count planned repairs as failures
        failed = failed & ~repair_mask

        # Reactive repairs
        n_fail = int(failed.sum())
        agg["failures"] += n_fail
        agg["crit_weighted_failures"] += float(
            (failed * assets["criticality"].values).sum()
        )

        react_cost = float(
            (assets.loc[failed, "work_cost_lakh"] * 1.5 +
             assets.loc[failed, "mobilisation_cost_lakh"]).sum()
        )
        agg["emergency_spend"] += react_cost
        agg["reactive_visits"] += n_fail

        # Re-dig: reactive failure in corridor that had repair in last 6 months
        for i, (aid, is_fail) in enumerate(zip(assets["asset_id"].values, failed)):
            if is_fail:
                cid = assets.iloc[i]["corridor_id"]
                # Check if any asset in this corridor was repaired in last 6 months
                corridor_assets = assets[assets["corridor_id"] == cid]["asset_id"].values
                for ca in corridor_assets:
                    if last_repair_month.get(ca, -99) >= sim_m - 6:
                        agg["re_dig_events"] += 1
                        break

        # Apply reactive repairs
        state["condition"][failed] = rng.uniform(0.7, 1.0, n_fail)
        state["prev_failures"][failed] += 1
        state["months_since_repair"][failed] = 0
        state["months_since_repair"][~failed] += 1

        # Routine maintenance
        maintained = (~failed) & (~repair_mask) & (rng.random(n) < 0.01)
        state["condition"][maintained] = (state["condition"][maintained] + 0.1).clip(0, 1)
        state["maint_count"][maintained] += 1

        # Inspection update
        inspected = rng.random(n) < 0.20
        state["last_insp_condition"] = np.where(
            inspected,
            state["condition"] + rng.normal(0, 0.05, n),
            state["last_insp_condition"]
        ).clip(0, 1)
        state["months_since_insp"] = np.where(inspected, 0.0, state["months_since_insp"] + 1)
        state["sensor"] = np.where(
            rng.random(n) < 0.05, np.nan,
            state["condition"] + rng.normal(0, 0.03, n)
        )

    agg["total_spend"] = agg["planned_spend"] + agg["emergency_spend"]
    return agg


def _select(snap: pd.DataFrame, strategy: str, budget: float) -> pd.DataFrame:
    if strategy == "reactive_only":
        return pd.DataFrame()
    elif strategy == "oldest_first":
        return oldest_first(snap, budget)
    elif strategy == "risk_first":
        return risk_first(snap, budget)
    elif strategy == "ml_per_rupee":
        return ml_per_rupee(snap, budget)
    elif strategy == "greedy_coordinated":
        return greedy_coordinated(snap, budget)
    elif strategy in ("digonce", "digonce_ilp"):
        return digonce_ilp(snap, budget)
    return pd.DataFrame()
