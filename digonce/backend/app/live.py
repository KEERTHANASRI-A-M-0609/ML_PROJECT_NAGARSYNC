"""
backend/app/live.py — Real-time city pulse + ML recommender.

Simulates streaming sensor ticks, re-scores assets with the calibrated
risk model, and broadcasts updates over WebSockets.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from collections import deque

import numpy as np
import pandas as pd

from ml.config import district_name
from ml.health import health_score, health_band
from ml.optimizer import (
    oldest_first, risk_first, ml_per_rupee,
    greedy_coordinated, digonce_ilp, compute_plan_cost,
)
from ml.scheduling import schedule_plan


class LiveEngine:
    """Mutates snapshot in-place and fans out events to WS clients."""

    def __init__(self) -> None:
        self.tick: int = 0
        self.started_at: float = time.time()
        self.clients: set[asyncio.Queue] = set()
        self.event_log: deque[dict] = deque(maxlen=40)
        self.alerts: deque[dict] = deque(maxlen=25)
        self._task: asyncio.Task | None = None
        self._rng = np.random.default_rng(42)
        self.last_recs: list[dict] = []

    def attach(self, state) -> None:
        self.state = state
        if not hasattr(state, "live_meta"):
            state.live_meta = {
                "tick": 0,
                "sensor_drift": 0.0,
                "rescored_count": 0,
                "last_tick_at": time.time(),
                "data_mode": "simulated_demo" if state.demo_mode else "trained_model",
                "score_mode": state.score_mode,
            }

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.clients.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.clients.discard(q)

    async def _broadcast(self, payload: dict) -> None:
        dead = []
        raw = json.dumps(payload, default=str)
        for q in self.clients:
            try:
                q.put_nowait(raw)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                    q.put_nowait(raw)
                except Exception:
                    dead.append(q)
        for q in dead:
            self.clients.discard(q)

    async def _loop(self) -> None:
        while True:
            try:
                event = self._advance_tick()
                await self._broadcast(event)
            except Exception as exc:
                await self._broadcast({"type": "error", "message": str(exc)})
            await asyncio.sleep(3.0)

    def _advance_tick(self) -> dict:
        state = self.state
        snap = state.snapshot
        n = len(snap)
        if n == 0:
            return {"type": "tick", "tick": self.tick}

        self.tick += 1
        k = max(8, n // 40)
        idx = self._rng.choice(n, size=min(k, n), replace=False)

        # Sensor / weather / condition drift (bounded)
        snap.loc[snap.index[idx], "sensor_reading"] = (
            snap.loc[snap.index[idx], "sensor_reading"].astype(float)
            + self._rng.normal(0, 0.04, size=len(idx))
        ).clip(0, 1)

        if "condition_score" in snap.columns:
            snap.loc[snap.index[idx], "condition_score"] = (
                snap.loc[snap.index[idx], "condition_score"].astype(float)
                + self._rng.normal(-0.002, 0.008, size=len(idx))
            ).clip(0.05, 1.0)

        if "rainfall_mm" in snap.columns:
            snap.loc[snap.index[idx], "rainfall_mm"] = (
                snap.loc[snap.index[idx], "rainfall_mm"].astype(float)
                * (1 + self._rng.normal(0, 0.03, size=len(idx)))
            ).clip(0, None)

        if "dma_leak_score" in snap.columns:
            # Refresh a few districts' leak scores with mild noise
            n_dmas = max(1, int(self.state.snapshot["ward"].nunique()))
            pick = min(5, n_dmas)
            for ward in self._rng.choice(n_dmas, size=pick, replace=False):
                base = float(state.leak_scores_latest.get(int(ward), 0.05))
                new_v = float(np.clip(base + self._rng.normal(0, 0.02), 0, 1))
                state.leak_scores_latest[int(ward)] = new_v
                mask = snap["ward"] == int(ward)
                if "dma_leak_score" in snap.columns:
                    snap.loc[mask, "dma_leak_score"] = new_v

        # Re-score drifted rows with the live risk model
        self._rescore_rows(snap, idx)

        # Build alerts for newly critical assets
        new_alerts = []
        for i in idx:
            row = snap.iloc[i]
            risk = float(row["risk_score"])
            if risk > 0.18:
                alert = {
                    "id": f"A{self.tick}-{row['asset_id']}",
                    "tick": self.tick,
                    "asset_id": str(row["asset_id"]),
                    "asset_type": str(row["asset_type"]),
                    "ward": int(row["ward"]),
                    "risk_score": round(risk, 4),
                    "severity": "critical" if risk > 0.25 else "high",
                    "message": (
                        f"{row['asset_type'].title()} {row['asset_id']} in "
                        f"{district_name(int(row['ward']))} "
                        f"{'priority score' if state.demo_mode else 'risk'} rose to {risk*100:.1f}%"
                    ),
                    "ts": time.time(),
                }
                self.alerts.appendleft(alert)
                new_alerts.append(alert)

        # Top live recommendations (fast greedy slice)
        recs = self.quick_recommendations(limit=8)
        self.last_recs = recs

        state.live_meta = {
            "tick": self.tick,
            "sensor_drift": round(float(self._rng.random() * 0.05), 4),
            "rescored_count": int(len(idx)),
            "last_tick_at": time.time(),
            "uptime_s": int(time.time() - self.started_at),
            "clients": len(self.clients),
            "data_mode": "simulated_demo" if state.demo_mode else "trained_model",
            "score_mode": state.score_mode,
        }

        payload = {
            "type": "tick",
            "tick": self.tick,
            "ts": time.time(),
            "meta": state.live_meta,
            "kpis": {
                "mean_risk": round(float(snap["risk_score"].mean()), 4),
                "critical_assets": int((snap["risk_score"] > 0.15).sum()),
                "total_assets": int(len(snap)),
                "max_risk": round(float(snap["risk_score"].max()), 4),
            },
            "alerts": new_alerts,
            "recommendations": recs,
            "top_wards": self._top_wards(5),
        }
        self.event_log.appendleft({"tick": self.tick, "alerts": len(new_alerts), "ts": time.time()})
        return payload

    def _rescore_rows(self, snap: pd.DataFrame, idx: np.ndarray) -> None:
        model = self.state.risk_model
        feat_cols = model.feature_cols
        sub = snap.iloc[idx].copy()
        df_enc = self.state.encode(sub)
        for c in feat_cols:
            if c not in df_enc.columns:
                df_enc[c] = 0.0
        X = df_enc[feat_cols].fillna(df_enc[feat_cols].median()).values
        proba = model.predict_proba(X)
        snap.iloc[idx, snap.columns.get_loc("risk_score")] = proba

    def _top_wards(self, k: int = 5) -> list[dict]:
        snap = self.state.snapshot
        rows = []
        for ward_id, grp in snap.groupby("ward"):
            rows.append({
                "ward": int(ward_id),
                "district": district_name(int(ward_id)),
                "mean_risk": round(float(grp["risk_score"].mean()), 4),
                "critical_count": int((grp["risk_score"] > 0.15).sum()),
                "leak_score": round(float(self.state.leak_scores_latest.get(int(ward_id), 0.0)), 4),
            })
        rows.sort(key=lambda r: (-r["critical_count"], -r["mean_risk"]))
        return rows[:k]

    def quick_recommendations(self, limit: int = 8) -> list[dict]:
        """Fast ML ranking for live rail — benefit/cost with leak + criticality."""
        snap = self.state.snapshot.copy()
        if len(snap) == 0:
            return []
        snap["benefit"] = snap["risk_score"] * snap["criticality"].astype(float)
        snap["unit_cost"] = snap["work_cost_lakh"].astype(float) + (
            snap["mobilisation_cost_lakh"].astype(float) * 0.35
        )
        snap["score"] = snap["benefit"] / snap["unit_cost"].clip(lower=0.05)

        # Boost pipes in leaky DMAs
        leak_boost = snap["ward"].map(
            lambda w: 1.0 + 0.6 * float(self.state.leak_scores_latest.get(int(w), 0.0))
        )
        pipe_mask = snap["asset_type"] == "pipe"
        snap.loc[pipe_mask, "score"] *= leak_boost[pipe_mask]

        top = snap.nlargest(limit, "score")
        out = []
        for rank, (_, row) in enumerate(top.iterrows(), start=1):
            hs = health_score(float(row["risk_score"]))
            reasons = []
            if float(row["risk_score"]) > 0.15:
                reasons.append(
                    "Elevated simulated condition-priority score"
                    if self.state.demo_mode
                    else "Elevated failure probability from calibrated risk model"
                )
            if int(row["criticality"]) >= 4:
                reasons.append("High criticality asset")
            if row["asset_type"] == "pipe" and self.state.leak_scores_latest.get(int(row["ward"]), 0) > 0.1:
                reasons.append("DMA leak detector elevated")
            neighbours = snap[
                (snap["corridor_id"] == row["corridor_id"]) & (snap["asset_id"] != row["asset_id"])
            ]
            at_risk = int((neighbours["risk_score"] > 0.10).sum())
            if at_risk:
                reasons.append(f"Bundle with {at_risk} co-located assets — shared mobilisation savings")
            if not reasons:
                reasons.append("Strong benefit-per-rupee under current live scores")

            out.append({
                "rank": rank,
                "asset_id": str(row["asset_id"]),
                "corridor_id": str(row["corridor_id"]),
                "asset_type": str(row["asset_type"]),
                "ward": int(row["ward"]),
                "district": district_name(int(row["ward"])),
                "risk_score": round(float(row["risk_score"]), 4),
                "score_mode": self.state.score_mode,
                "health_score": hs,
                "health_band": health_band(hs),
                "criticality": int(row["criticality"]),
                "work_cost_lakh": round(float(row["work_cost_lakh"]), 2),
                "ml_score": round(float(row["score"]), 4),
                "reasons": reasons,
                "action": "Coordinate corridor visit" if at_risk else "Schedule independent repair",
            })
        return out

    def status(self) -> dict:
        snap = self.state.snapshot
        return {
            "tick": self.tick,
            "uptime_s": int(time.time() - self.started_at),
            "clients": len(self.clients),
            "meta": getattr(self.state, "live_meta", {}),
            "kpis": {
                "mean_risk": round(float(snap["risk_score"].mean()), 4) if len(snap) else 0,
                "critical_assets": int((snap["risk_score"] > 0.15).sum()) if len(snap) else 0,
                "total_assets": int(len(snap)),
            },
            "recent_alerts": list(self.alerts)[:10],
            "recommendations": self.last_recs or self.quick_recommendations(8),
            "event_log": list(self.event_log)[:10],
            "data_mode": "simulated_demo" if self.state.demo_mode else "trained_model",
            "score_mode": self.state.score_mode,
        }


_engine = LiveEngine()


def get_engine() -> LiveEngine:
    return _engine


def flexible_recommend(
    state,
    *,
    budget_lakh: float = 5000,
    strategy: str = "digonce_ilp",
    mobilisation_scale: float = 1.0,
    min_ward_share: float = 0.0,
    ward: int | None = None,
    asset_type: str | None = None,
    min_risk: float = 0.0,
    prefer_coordination: bool = True,
    traffic_aware: bool = True,
    urgency: str = "balanced",
    limit: int = 40,
) -> dict[str, Any]:
    """
    Full flexible ML recommender: filter → optional urgency reweight →
    optimiser → traffic-aware schedule → explainable cards.
    """
    snap = state.snapshot.copy()
    snap["mobilisation_cost_lakh"] = snap["mobilisation_cost_lakh"].astype(float) * mobilisation_scale

    if ward is not None:
        snap = snap[snap["ward"] == ward]
    if asset_type:
        snap = snap[snap["asset_type"] == asset_type]
    if min_risk > 0:
        snap = snap[snap["risk_score"] >= min_risk]

    if len(snap) == 0:
        return {
            "strategy": strategy,
            "selected_count": 0,
            "assets": [],
            "message": "No assets match filters",
            "filters": {"ward": ward, "asset_type": asset_type, "min_risk": min_risk},
            "data_mode": "simulated_demo" if state.demo_mode else "trained_model",
            "score_mode": state.score_mode,
        }

    # Urgency modes reweight risk for selection
    work = snap.copy()
    if urgency == "critical_first":
        work["risk_score"] = work["risk_score"] * (1 + 0.5 * (work["risk_score"] > 0.15).astype(float))
    elif urgency == "leak_focus":
        boost = work["ward"].map(lambda w: 1.0 + float(state.leak_scores_latest.get(int(w), 0.0)))
        work.loc[work["asset_type"] == "pipe", "risk_score"] *= boost[work["asset_type"] == "pipe"]
    elif urgency == "equity":
        min_ward_share = max(min_ward_share, 0.08)

    if prefer_coordination and strategy not in ("greedy_coordinated", "digonce_ilp"):
        strategy = "digonce_ilp"

    # Live UI: keep ILP responsive by capping candidate pool via greedy prefilter
    work_opt = work
    if strategy == "digonce_ilp" and len(work) > 500:
        work_opt = work.assign(
            _bc=work["risk_score"] * work["criticality"].astype(float)
            / work["work_cost_lakh"].astype(float).clip(lower=0.05)
        ).nlargest(500, "_bc").drop(columns=["_bc"])

    strategy_map = {
        "oldest_first": oldest_first,
        "risk_first": risk_first,
        "ml_per_rupee": ml_per_rupee,
        "greedy_coordinated": greedy_coordinated,
        "digonce_ilp": lambda s, b: digonce_ilp(s, b, min_ward_share=min_ward_share),
    }
    fn = strategy_map.get(strategy, strategy_map["digonce_ilp"])
    selected = fn(work_opt, budget_lakh)
    coordinated = strategy in ("greedy_coordinated", "digonce_ilp")
    plan_cost = compute_plan_cost(selected, coordinated=coordinated)

    baseline = ml_per_rupee(work, budget_lakh)
    base_cost = compute_plan_cost(baseline, coordinated=False)

    if traffic_aware and len(selected) > 0 and len(state.traffic_profiles) > 0:
        scheduled = schedule_plan(selected, state.traffic_profiles)
    else:
        scheduled = selected
        if len(scheduled) > 0 and "best_start_hour" not in scheduled.columns:
            scheduled = scheduled.copy()
            scheduled["best_start_hour"] = 9
            scheduled["saving_vh"] = 0.0

    # Corridor bundling stats
    corridor_counts = (
        scheduled.groupby("corridor_id").size().to_dict() if len(scheduled) else {}
    )

    assets_out = []
    if len(scheduled) > 0:
        for _, row in scheduled.head(limit).iterrows():
            cid = row["corridor_id"]
            bundle = int(corridor_counts.get(cid, 1))
            leak = float(state.leak_scores_latest.get(int(row["ward"]), 0.0))
            reasons = [
                (
                    f"Simulated condition-priority score = {float(row['risk_score'])*100:.1f}%"
                    if state.demo_mode
                    else f"Calibrated P(fail) = {float(row['risk_score'])*100:.1f}%"
                ),
                f"Criticality {int(row['criticality'])}/5",
            ]
            if bundle > 1:
                reasons.append(f"Coordinated bundle: {bundle} assets share corridor mobilisation")
            if row["asset_type"] == "pipe" and leak > 0.08:
                reasons.append(
                    f"{'Simulated' if state.demo_mode else 'Leak model'} DMA score {leak*100:.0f}%"
                )
            if float(row.get("saving_vh", 0)) > 0:
                reasons.append(f"Traffic model saves ~{float(row['saving_vh']):.0f} vehicle-hours vs 09:00")

            hs = health_score(float(row["risk_score"]))
            assets_out.append({
                "asset_id": str(row["asset_id"]),
                "corridor_id": str(cid),
                "asset_type": str(row["asset_type"]),
                "ward": int(row["ward"]),
                "district": district_name(int(row["ward"])),
                "risk_score": round(float(row["risk_score"]), 4),
                "score_mode": state.score_mode,
                "health_score": hs,
                "health_band": health_band(hs),
                "work_cost_lakh": round(float(row["work_cost_lakh"]), 2),
                "best_start_hour": int(row.get("best_start_hour", 9)),
                "saving_vh": float(row.get("saving_vh", 0)),
                "bundle_size": bundle,
                "reasons": reasons,
                "action": "Coordinate corridor visit" if bundle > 1 else "Independent repair",
            })

    risk_reduction = float(selected["risk_score"].sum()) if len(selected) else 0.0
    uncoord_risk = float(baseline["risk_score"].sum()) if len(baseline) else 0.0

    return {
        "strategy": strategy,
        "urgency": urgency,
        "budget_lakh": budget_lakh,
        "selected_count": int(len(selected)),
        "corridors_opened": int(selected["corridor_id"].nunique()) if len(selected) else 0,
        "planned_spend": round(plan_cost, 2),
        "risk_reduction": round(risk_reduction, 3),
        "saving_vs_uncoordinated": round(risk_reduction - uncoord_risk, 3),
        "uncoordinated_spend": round(base_cost, 2),
        "uncoordinated_count": int(len(baseline)),
        "mobilisation_scale": mobilisation_scale,
        "min_ward_share": min_ward_share,
        "filters": {
            "ward": ward,
            "asset_type": asset_type,
            "min_risk": min_risk,
            "prefer_coordination": prefer_coordination,
            "traffic_aware": traffic_aware,
        },
        "tick": get_engine().tick,
        "data_mode": "simulated_demo" if state.demo_mode else "trained_model",
        "score_mode": state.score_mode,
        "model": {
            "risk": "transparent_demo_rule" if state.demo_mode else "calibrated_hist_gb",
            "leak": "simulated_recent_flags" if state.demo_mode else "isolation_forest",
            "traffic": "profile_window_optimiser",
            "planner": strategy,
        },
        "assets": assets_out,
    }
