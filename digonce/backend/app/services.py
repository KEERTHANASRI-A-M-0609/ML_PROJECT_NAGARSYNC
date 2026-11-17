"""
backend/app/services.py — Business logic: load data/models, serve endpoints.
"""
from __future__ import annotations

import json
import joblib
import logging
from collections.abc import Callable
import numpy as np
import pandas as pd

from ml.config import DATA_RAW, DATA_PROC, MODELS_DIR, REPORTS_DIR, district_name
from ml.health import health_score, health_band, occlusion_attribution
from ml.optimizer import (
    oldest_first, risk_first, ml_per_rupee,
    greedy_coordinated, digonce_ilp, compute_plan_cost,
)
from ml.scheduling import schedule_plan
from backend.app.demo_analytics import DemoPriorityScorer, encode_demo_features

logger = logging.getLogger(__name__)


# ── Singleton data store ──────────────────────────────────────────────────

class AppState:
    corridors: pd.DataFrame
    assets: pd.DataFrame
    snapshot: pd.DataFrame          # current risk snapshot
    water_df: pd.DataFrame
    traffic_profiles: pd.DataFrame
    risk_model: object
    risk_model_no_leak: object
    model_metrics: dict
    experiments: dict
    leak_scores_latest: dict        # {ward: score} for latest month
    background: np.ndarray          # median feature vector for occlusion
    demo_mode: bool
    score_mode: str
    encode: Callable[[pd.DataFrame], pd.DataFrame]

    def load(self) -> None:
        self.corridors = pd.read_csv(DATA_RAW / "corridors.csv")
        self.assets = pd.read_csv(DATA_RAW / "assets.csv")
        from ml.risk_model import _encode
        self.encode = _encode
        self.demo_mode = False
        self.score_mode = "calibrated_ml"

        # Merge mobilisation cost into assets
        mob_map = self.corridors.set_index("corridor_id")["mobilisation_cost_lakh"]
        self.assets["mobilisation_cost_lakh"] = self.assets["corridor_id"].map(mob_map)

        self.snapshot = self._build_snapshot()
        self.water_df = pd.read_csv(DATA_RAW / "water_daily.csv")
        self.traffic_profiles = self._load_traffic_profiles()
        self.risk_model = joblib.load(MODELS_DIR / "risk_model.joblib")
        self.risk_model_no_leak = joblib.load(MODELS_DIR / "risk_model_no_leak.joblib")

        with open(MODELS_DIR / "model_metrics.json") as f:
            self.model_metrics = json.load(f)
        with open(REPORTS_DIR / "experiments.json") as f:
            self.experiments = json.load(f)

        self.leak_scores_latest = self._latest_leak_scores()
        self.background = self._compute_background()

    def load_demo(self) -> None:
        """Load the pre-generated 37-district fixture without blocked ML binaries."""
        self.corridors = pd.read_csv(DATA_RAW / "corridors.csv")
        self.assets = pd.read_csv(DATA_RAW / "assets.csv")
        self.snapshot = pd.read_csv(DATA_PROC / "current_snapshot.csv")
        mob_map = self.corridors.set_index("corridor_id")["mobilisation_cost_lakh"]
        self.assets["mobilisation_cost_lakh"] = self.assets["corridor_id"].map(mob_map)
        self.water_df = pd.read_csv(DATA_RAW / "water_daily.csv")
        traffic = pd.read_csv(DATA_RAW / "traffic_hourly.csv")
        self.traffic_profiles = (
            traffic.groupby(["junction", "is_weekend", "hour"], as_index=False)["count"]
            .mean()
            .rename(columns={"count": "mean_count"})
        )
        self.risk_model = DemoPriorityScorer()
        self.risk_model_no_leak = self.risk_model
        self.encode = encode_demo_features
        self.demo_mode = True
        self.score_mode = "simulated_condition_priority"

        with open(MODELS_DIR / "model_metrics.json", encoding="utf-8") as file:
            self.model_metrics = json.load(file)
        with open(REPORTS_DIR / "experiments.json", encoding="utf-8") as file:
            self.experiments = json.load(file)

        leak_flags = self.water_df
        latest_month = int(leak_flags["month"].max())
        recent = leak_flags[leak_flags["month"] >= latest_month - 1]
        self.leak_scores_latest = (
            recent.groupby("dma")["leak_flag"].mean().to_dict()
        )
        self.snapshot["dma_leak_score"] = (
            self.snapshot["ward"].map(self.leak_scores_latest).fillna(0.0)
        )
        encoded = self.encode(self.snapshot)
        features = encoded[self.risk_model.feature_cols].fillna(0.0)
        self.snapshot["risk_score"] = self.risk_model.predict_proba(features.to_numpy())
        self.background = features.median().to_numpy()

    def _build_snapshot(self) -> pd.DataFrame:
        """Load processed snapshot, merge mobilisation cost, and compute risk scores."""
        snap = pd.read_csv(DATA_PROC / "current_snapshot.csv")
        mob_map = self.corridors.set_index("corridor_id")["mobilisation_cost_lakh"]
        snap["mobilisation_cost_lakh"] = snap["corridor_id"].map(mob_map)

        # Compute risk scores using the loaded model
        model = joblib.load(MODELS_DIR / "risk_model.joblib")
        df_enc = self.encode(snap)
        feat_cols = model.feature_cols
        X = df_enc[feat_cols].fillna(df_enc[feat_cols].median()).values
        snap["risk_score"] = model.predict_proba(X)
        return snap

    def _load_traffic_profiles(self) -> pd.DataFrame:
        """Generate traffic profiles with the saved model; never train during API startup."""
        try:
            from ml.traffic import load_traffic_profiles
            traffic_df = pd.read_csv(DATA_RAW / "traffic_hourly.csv")
            return load_traffic_profiles(traffic_df)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            logger.warning("Traffic profiles unavailable; traffic-aware scheduling is disabled: %s", exc)
            return pd.DataFrame()

    def _latest_leak_scores(self) -> dict:
        """Latest DMA leak scores from water data."""
        try:
            leak_model = joblib.load(MODELS_DIR / "leak_detector.joblib")
            from ml.leak_detection import compute_leak_scores
            from ml.config import TOTAL_MONTHS, N_DMAS
            scores = compute_leak_scores(self.water_df, leak_model, TOTAL_MONTHS)
            latest_month = max(m for (_, m) in scores.keys())
            return {dma: scores.get((dma, latest_month), 0.0) for dma in range(N_DMAS)}
        except Exception:
            return {}

    def _compute_background(self) -> np.ndarray:
        """Median/mode background vector for occlusion attribution."""
        feat_cols = self.risk_model.feature_cols
        df_enc = self.encode(self.snapshot)
        X = df_enc[feat_cols].fillna(0)
        return X.median().values


_state = AppState()
_runtime_ready = False
_runtime_error: Exception | None = None
_runtime_demo_mode = False


class AnalyticsUnavailable(RuntimeError):
    """Raised when an endpoint requires an analytics runtime that did not start."""


def initialize_runtime() -> AppState:
    global _runtime_ready, _runtime_error, _runtime_demo_mode
    try:
        try:
            _state.load()
            _runtime_demo_mode = False
        except ImportError as exc:
            if "Application Control policy has blocked this file" not in str(exc):
                raise
            logger.warning(
                "Blocked native ML dependency; loading explicitly simulated demo analytics instead: %s",
                exc,
            )
            _state.load_demo()
            _runtime_demo_mode = True
    except Exception as exc:
        _runtime_ready = False
        _runtime_error = exc
        _runtime_demo_mode = False
        raise
    _runtime_error = None
    _runtime_ready = True
    return _state


def mark_runtime_unavailable(error: Exception) -> None:
    global _runtime_ready, _runtime_error, _runtime_demo_mode
    _runtime_ready = False
    _runtime_error = error
    _runtime_demo_mode = False


def get_state() -> AppState:
    if _runtime_error is not None:
        raise AnalyticsUnavailable("Analytics runtime failed to initialize") from _runtime_error
    if not _runtime_ready:
        raise AnalyticsUnavailable("Analytics runtime is not initialized")
    return _state


def analytics_runtime_status() -> dict[str, bool | str]:
    available = _runtime_ready and _runtime_error is None
    return {
        "available": available,
        "mode": "simulated_demo" if available and _runtime_demo_mode else "trained_model" if available else "unavailable",
        "demo_only": available and _runtime_demo_mode,
    }


# ── Service functions ─────────────────────────────────────────────────────

def summary_kpis(state: AppState) -> dict:
    snap = state.snapshot
    exp = state.experiments["summary"]
    digonce_failures = exp.get("digonce", {}).get("failures", {}).get("mean", 0)
    mlpr_failures = exp.get("ml_per_rupee", {}).get("failures", {}).get("mean", 0)
    reactive_failures = exp.get("reactive_only", {}).get("failures", {}).get("mean", 0)
    digonce_spend = exp.get("digonce", {}).get("total_spend", {}).get("mean", 0)
    mlpr_spend = exp.get("ml_per_rupee", {}).get("total_spend", {}).get("mean", 0)
    calibrated_ece = (
        state.model_metrics.get("risk_model", {})
        .get("calibrated", {})
        .get("ece")
    )
    return {
        "total_assets": int(len(snap)),
        "critical_assets": int((snap["risk_score"] > 0.15).sum()),
        "mean_risk": round(float(snap["risk_score"].mean()), 4),
        "data_mode": "simulated_demo" if state.demo_mode else "production_model",
        "score_mode": state.score_mode,
        "digonce_vs_mlpr_failure_reduction": round(float(mlpr_failures - digonce_failures), 1),
        "research_metrics": {
            "digonce_failure_reduction_vs_reactive_pct": (
                round((reactive_failures - digonce_failures) / reactive_failures * 100, 1)
                if reactive_failures
                else None
            ),
            "spend_difference_vs_ml_per_rupee_lakh": round(mlpr_spend - digonce_spend, 1),
            "calibrated_ece": calibrated_ece,
        },
        "n_wards": int(snap["ward"].nunique()),
        "n_districts": int(snap["ward"].nunique()),
        "n_corridors": int(snap["corridor_id"].nunique()),
        "region": "Tamil Nadu",
        "asset_types": snap["asset_type"].value_counts().to_dict(),
    }


def corridors_geojson(state: AppState) -> list[dict]:
    snap = state.snapshot
    cor_risk = snap.groupby("corridor_id")["risk_score"].max().reset_index()
    cor_risk.columns = ["corridor_id", "max_risk"]
    merged = state.corridors.merge(cor_risk, on="corridor_id", how="left")
    merged["max_risk"] = merged["max_risk"].fillna(0)

    features = []
    for _, row in merged.iterrows():
        hs = health_score(float(row["max_risk"]))
        features.append({
            "corridor_id": row["corridor_id"],
            "lat": row["lat"],
            "lon": row["lon"],
            "ward": int(row["ward"]),
            "district": district_name(int(row["ward"])),
            "road_class": row["road_class"],
            "max_risk": round(float(row["max_risk"]), 4),
            "health_score": hs,
            "health_band": health_band(hs),
            "mobilisation_cost_lakh": float(row["mobilisation_cost_lakh"]),
        })
    return features


def assets_list(
    state: AppState,
    asset_type: str | None = None,
    ward: int | None = None,
    min_risk: float = 0.0,
    limit: int = 200,
    corridor_id: str | None = None,
) -> list[dict]:
    snap = state.snapshot.copy()
    if asset_type:
        snap = snap[snap["asset_type"] == asset_type]
    if ward is not None:
        snap = snap[snap["ward"] == ward]
    if corridor_id:
        snap = snap[snap["corridor_id"] == corridor_id]
    snap = snap[snap["risk_score"] >= min_risk]
    snap = snap.nlargest(limit, "risk_score")

    result = []
    for _, row in snap.iterrows():
        hs = health_score(float(row["risk_score"]))
        result.append({
            "asset_id": row["asset_id"],
            "corridor_id": row["corridor_id"],
            "asset_type": row["asset_type"],
            "ward": int(row["ward"]),
            "district": district_name(int(row["ward"])),
            "risk_score": round(float(row["risk_score"]), 4),
            "health_score": hs,
            "health_band": health_band(hs),
            "criticality": int(row["criticality"]),
            "lat": float(state.assets.loc[state.assets["asset_id"] == row["asset_id"], "lat"].iloc[0]),
            "lon": float(state.assets.loc[state.assets["asset_id"] == row["asset_id"], "lon"].iloc[0]),
        })
    return result


def asset_detail(asset_id: str, state: AppState) -> dict | None:
    snap = state.snapshot
    row = snap[snap["asset_id"] == asset_id]
    if len(row) == 0:
        return None
    row = row.iloc[0]

    # Attribution
    feat_cols = state.risk_model.feature_cols
    df_enc = state.encode(snap)
    asset_row = df_enc[df_enc["asset_id"] == asset_id]
    if len(asset_row) == 0:
        return None
    X_asset = asset_row[feat_cols].fillna(0).values[0]
    attribution = occlusion_attribution(state.risk_model, X_asset, state.background)

    # Neighbours in same corridor
    neighbours_df = snap[
        (snap["corridor_id"] == row["corridor_id"]) & (snap["asset_id"] != asset_id)
    ]
    neighbours = [
        {"asset_id": r["asset_id"], "asset_type": r["asset_type"],
         "risk_score": round(float(r["risk_score"]), 4)}
        for _, r in neighbours_df.iterrows()
    ]

    # Leak status for pipes
    leak_status = None
    if row["asset_type"] == "pipe":
        leak_status = state.leak_scores_latest.get(int(row["ward"]), 0.0)

    # Recommendation
    n_neighbours_at_risk = sum(1 for n in neighbours if n["risk_score"] > 0.10)
    rec = (
        "Coordinate repair with neighbours in this corridor to save mobilisation cost."
        if n_neighbours_at_risk >= 1
        else "No high-risk neighbours — independent repair is cost-effective."
    )

    assets_row = state.assets[state.assets["asset_id"] == asset_id].iloc[0]
    hs = health_score(float(row["risk_score"]))
    return {
        "asset_id": asset_id,
        "corridor_id": row["corridor_id"],
        "asset_type": row["asset_type"],
        "score_mode": state.score_mode,
        "material": assets_row["material"],
        "road_class": assets_row["road_class"],
        "age_years": float(row["age_years"]),
        "condition_score": float(row["condition_score"]),
        "risk_score": round(float(row["risk_score"]), 4),
        "health_score": hs,
        "health_band": health_band(hs),
        "criticality": int(row["criticality"]),
        "work_cost_lakh": float(assets_row["work_cost_lakh"]),
        "mobilisation_cost_lakh": float(row["mobilisation_cost_lakh"]),
        "ward": int(row["ward"]),
        "district": district_name(int(row["ward"])),
        "lat": float(assets_row["lat"]),
        "lon": float(assets_row["lon"]),
        "attribution": attribution,
        "neighbours": neighbours,
        "leak_status": leak_status,
        "recommendation": rec,
    }


def wards_summary(state: AppState) -> list[dict]:
    snap = state.snapshot
    result = []
    for ward_id, grp in snap.groupby("ward"):
        result.append({
            "ward": int(ward_id),
            "district": district_name(int(ward_id)),
            "n_assets": int(len(grp)),
            "mean_risk": round(float(grp["risk_score"].mean()), 4),
            "max_risk": round(float(grp["risk_score"].max()), 4),
            "critical_count": int((grp["risk_score"] > 0.15).sum()),
            "leak_score": round(float(state.leak_scores_latest.get(int(ward_id), 0.0)), 4),
        })
    return result


def leaks_summary(state: AppState) -> list[dict]:
    water = state.water_df
    result = []
    for dma, grp in water.groupby("dma"):
        recent = grp[grp["month"] >= grp["month"].max() - 1]
        result.append({
            "dma": int(dma),
            "leak_score": round(float(state.leak_scores_latest.get(int(dma), 0.0)), 4),
            "recent_leak_days": int(recent["leak_flag"].sum()),
            "mean_mnf": round(float(recent["mnf_ls"].mean()), 2),
            "mean_pressure": round(float(recent["pressure_bar"].mean()), 3),
            "mnf_series": recent.groupby("day")["mnf_ls"].mean().round(2).tolist()[-30:],
        })
    return result


def traffic_summary(state: AppState) -> list[dict]:
    if len(state.traffic_profiles) == 0:
        return []
    result = []
    for (junc, is_wknd), grp in state.traffic_profiles.groupby(["junction", "is_weekend"]):
        result.append({
            "junction": int(junc),
            "is_weekend": bool(is_wknd),
            "hourly_profile": grp.sort_values("hour")["mean_count"].round(1).tolist(),
        })
    return result


def run_plan(
    budget_lakh: float,
    strategy: str,
    mobilisation_scale: float,
    min_ward_share: float,
    state: AppState,
) -> dict:
    snap = state.snapshot.copy()
    snap["mobilisation_cost_lakh"] *= mobilisation_scale

    strategy_map = {
        "oldest_first": oldest_first,
        "risk_first": risk_first,
        "ml_per_rupee": ml_per_rupee,
        "greedy_coordinated": greedy_coordinated,
        "digonce_ilp": lambda s, b: digonce_ilp(s, b, min_ward_share=min_ward_share),
    }
    fn = strategy_map.get(strategy, lambda s, b: digonce_ilp(s, b, min_ward_share=min_ward_share))
    selected = fn(snap, budget_lakh)

    coordinated = strategy in ("greedy_coordinated", "digonce_ilp")
    plan_cost = compute_plan_cost(selected, coordinated=coordinated)

    # Uncoordinated baseline (ml_per_rupee)
    snap_base = state.snapshot.copy()
    snap_base["mobilisation_cost_lakh"] *= mobilisation_scale
    uncoord = ml_per_rupee(snap_base, budget_lakh)
    uncoord_cost = compute_plan_cost(uncoord, coordinated=False)

    risk_reduction = float(selected["risk_score"].sum()) if len(selected) > 0 else 0.0
    uncoord_risk = float(uncoord["risk_score"].sum()) if len(uncoord) > 0 else 0.0
    saving = risk_reduction - uncoord_risk

    # Schedule
    scheduled = schedule_plan(selected, state.traffic_profiles) if len(selected) > 0 else selected

    assets_out = []
    if len(scheduled) > 0:
        for _, row in scheduled.iterrows():
            assets_out.append({
                "asset_id": row["asset_id"],
                "corridor_id": row["corridor_id"],
                "asset_type": row["asset_type"],
                "risk_score": round(float(row["risk_score"]), 4),
                "work_cost_lakh": float(row["work_cost_lakh"]),
                "best_start_hour": int(row.get("best_start_hour", 9)),
                "saving_vh": float(row.get("saving_vh", 0)),
                "ward": int(row["ward"]),
            })

    return {
        "strategy": strategy,
        "budget_lakh": budget_lakh,
        "selected_count": len(selected),
        "corridors_opened": int(selected["corridor_id"].nunique()) if len(selected) > 0 else 0,
        "planned_spend": round(plan_cost, 2),
        "risk_reduction": round(risk_reduction, 3),
        "saving_vs_uncoordinated": round(saving, 3),
        "assets": assets_out,
        "uncoordinated_spend": round(uncoord_cost, 2),
        "uncoordinated_count": len(uncoord),
    }


def score_asset(asset_id: str, state: AppState) -> dict | None:
    return asset_detail(asset_id, state)
