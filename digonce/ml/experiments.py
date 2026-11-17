"""
ml/experiments.py — Multi-seed simulation, sensitivity, equity experiments.

All data is SIMULATED.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

from ml.config import (
    N_SEEDS, N_SEEDS_FAST, REPORTS_DIR, FIGURES_DIR,
    ANNUAL_BUDGET_FRACTION,
)
from ml.simulation import run_simulation
from ml.optimizer import digonce_ilp, ml_per_rupee, greedy_coordinated, compute_plan_cost


STRATEGIES = [
    "reactive_only", "oldest_first", "risk_first", "ml_per_rupee",
    "greedy_coordinated", "digonce",
]
ABLATIONS = [
    "digonce_no_calibration", "digonce_no_leak_link", "digonce_default_schedule",
]


def _ci95(arr: list[float]) -> tuple[float, float]:
    if len(arr) < 2:
        return (arr[0], arr[0]) if arr else (0.0, 0.0)
    se = stats.sem(arr)
    m = np.mean(arr)
    return (round(m - 1.96 * se, 3), round(m + 1.96 * se, 3))


def run_all_experiments(
    assets: pd.DataFrame,
    corridors: pd.DataFrame,
    risk_model,
    risk_model_no_leak,
    leak_scores: dict,
    traffic_profiles: pd.DataFrame,
    fast: bool = False,
) -> dict:
    """Run all experiments and return results dict."""
    n_seeds = N_SEEDS_FAST if fast else N_SEEDS
    total_replacement = float(assets["work_cost_lakh"].sum())
    annual_budget = total_replacement * ANNUAL_BUDGET_FRACTION
    monthly_budget = annual_budget / 12

    # ── Main simulation ──────────────────────────────────────────────────
    results: dict[str, list[dict]] = {s: [] for s in STRATEGIES + ABLATIONS}

    for seed in range(n_seeds):
        for strat in STRATEGIES:
            use_cal = True
            use_leak = True
            use_sched = True
            actual_strat = strat
            if strat == "digonce_no_calibration":
                use_cal = False
                actual_strat = "digonce"
            elif strat == "digonce_no_leak_link":
                use_leak = False
                actual_strat = "digonce"
            elif strat == "digonce_default_schedule":
                use_sched = False
                actual_strat = "digonce"

            r = run_simulation(
                assets, corridors, risk_model, risk_model_no_leak,
                leak_scores, traffic_profiles,
                seed=seed, strategy=actual_strat,
                monthly_budget=monthly_budget,
                use_calibration=use_cal,
                use_leak_link=use_leak,
                use_traffic_schedule=use_sched,
            )
            results[strat].append(r)

        for abl in ABLATIONS:
            use_cal = abl != "digonce_no_calibration"
            use_leak = abl != "digonce_no_leak_link"
            use_sched = abl != "digonce_default_schedule"
            r = run_simulation(
                assets, corridors, risk_model, risk_model_no_leak,
                leak_scores, traffic_profiles,
                seed=seed, strategy="digonce",
                monthly_budget=monthly_budget,
                use_calibration=use_cal,
                use_leak_link=use_leak,
                use_traffic_schedule=use_sched,
            )
            results[abl].append(r)

    # Summarise
    summary = {}
    for strat, runs in results.items():
        metrics = {}
        for key in runs[0].keys():
            vals = [r[key] for r in runs]
            metrics[key] = {
                "mean": round(float(np.mean(vals)), 3),
                "ci95": _ci95(vals),
            }
        # Paired differences vs ml_per_rupee and reactive_only
        for ref in ["ml_per_rupee", "reactive_only"]:
            if ref in results and strat != ref:
                ref_vals = [r["failures"] for r in results[ref]]
                strat_vals = [r["failures"] for r in runs]
                diffs = [s - rv for s, rv in zip(strat_vals, ref_vals)]
                metrics[f"failures_diff_vs_{ref}"] = {
                    "mean": round(float(np.mean(diffs)), 3),
                    "ci95": _ci95(diffs),
                }
        summary[strat] = metrics

    # ── Sensitivity: mobilisation scale ─────────────────────────────────
    mob_scales = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
    sensitivity_mob = []
    snap = _build_month36_snapshot(assets, corridors, risk_model, leak_scores)
    for scale in mob_scales:
        snap_s = snap.copy()
        snap_s["mobilisation_cost_lakh"] *= scale
        sel_digonce = digonce_ilp(snap_s, monthly_budget * 12)
        sel_mlpr = ml_per_rupee(snap_s, monthly_budget * 12)
        cost_d = compute_plan_cost(sel_digonce, coordinated=True)
        cost_m = compute_plan_cost(sel_mlpr, coordinated=False)
        ben_d = float(sel_digonce["risk_score"].sum() * sel_digonce["criticality"].mean()) if len(sel_digonce) > 0 else 0
        ben_m = float(sel_mlpr["risk_score"].sum() * sel_mlpr["criticality"].mean()) if len(sel_mlpr) > 0 else 0
        sensitivity_mob.append({
            "mob_scale": scale,
            "digonce_benefit": round(ben_d, 3),
            "mlpr_benefit": round(ben_m, 3),
            "saving": round(ben_d - ben_m, 3),
        })

    # Break-even
    breakeven = next(
        (s["mob_scale"] for s in sensitivity_mob if s["saving"] <= 0),
        mob_scales[-1]
    )

    # ── Sensitivity: budget ──────────────────────────────────────────────
    budget_fracs = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40]
    sensitivity_budget = []
    for frac in budget_fracs:
        b = total_replacement * frac
        sel_d = digonce_ilp(snap, b)
        sel_m = ml_per_rupee(snap, b)
        ben_d = float(sel_d["risk_score"].sum()) if len(sel_d) > 0 else 0
        ben_m = float(sel_m["risk_score"].sum()) if len(sel_m) > 0 else 0
        sensitivity_budget.append({
            "budget_frac": frac,
            "digonce_benefit": round(ben_d, 3),
            "mlpr_benefit": round(ben_m, 3),
            "saving": round(ben_d - ben_m, 3),
        })

    # ── Equity sweep ─────────────────────────────────────────────────────
    equity_results = []
    ward_shares = [0.0, 0.25, 0.50, 0.75, 1.0]
    for ws in ward_shares:
        sel = digonce_ilp(snap, monthly_budget * 12, min_ward_share=ws)
        total_ben = float(sel["risk_score"].sum()) if len(sel) > 0 else 0
        ward_spend = sel.groupby("ward")["work_cost_lakh"].sum() if len(sel) > 0 else pd.Series(dtype=float)
        all_wards = snap["ward"].unique()
        spend_arr = np.array([ward_spend.get(w, 0.0) for w in all_wards])
        gini = _gini(spend_arr)
        equity_results.append({
            "min_ward_share": ws,
            "total_benefit": round(total_ben, 3),
            "gini_ward_spend": round(gini, 4),
        })

    output = {
        "summary": summary,
        "sensitivity_mobilisation": sensitivity_mob,
        "breakeven_mob_scale": breakeven,
        "sensitivity_budget": sensitivity_budget,
        "equity_tradeoff": equity_results,
    }

    # Save
    REPORTS_DIR.mkdir(exist_ok=True)
    with open(REPORTS_DIR / "experiments.json", "w") as f:
        json.dump(output, f, indent=2)

    _make_figures(output, summary, results)
    return output


def _build_month36_snapshot(assets, corridors, risk_model, leak_scores) -> pd.DataFrame:
    """Build a snapshot at month 36 for sensitivity experiments."""
    from ml.risk_model import _encode
    import numpy as np

    rng = np.random.default_rng(42)
    n = len(assets)
    snap = assets.reset_index(drop=True).copy()
    # Merge mobilisation cost from corridors if missing
    if "mobilisation_cost_lakh" not in snap.columns:
        mob_map = corridors.set_index("corridor_id")["mobilisation_cost_lakh"]
        snap["mobilisation_cost_lakh"] = snap["corridor_id"].map(mob_map)
    snap["age_years"] = assets["install_age_years"].values + 3.0
    snap["condition_score"] = rng.uniform(0.3, 0.9, n)
    snap["months_since_inspection"] = rng.integers(1, 12, n).astype(float)
    snap["sensor_reading"] = snap["condition_score"] + rng.normal(0, 0.03, n)
    snap["months_since_repair"] = rng.integers(1, 24, n).astype(float)
    snap["previous_failures"] = rng.integers(0, 4, n)
    snap["maintenance_count"] = rng.integers(0, 10, n)
    snap["rainfall_mm"] = 55.0
    snap["dma_leak_score"] = [
        leak_scores.get((int(w), 36), 0.0) if at == "pipe" else 0.0
        for w, at in zip(assets["ward"].values, assets["asset_type"].values)
    ]
    snap["month"] = 36

    df_enc = _encode(snap)
    feat_cols = risk_model.feature_cols
    X = df_enc[feat_cols].fillna(df_enc[feat_cols].median()).values
    snap["risk_score"] = risk_model.predict_proba(X)
    return snap


def _gini(arr: np.ndarray) -> float:
    arr = np.sort(arr.clip(0))
    n = len(arr)
    if n == 0 or arr.sum() == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float((2 * (idx * arr).sum() / (n * arr.sum())) - (n + 1) / n)


def _make_figures(output: dict, summary: dict, results: dict) -> None:
    FIGURES_DIR.mkdir(exist_ok=True)

    # 1. Strategy comparison (failures mean + CI)
    strats = [s for s in STRATEGIES if s in summary]
    means = [summary[s]["failures"]["mean"] for s in strats]
    cis = [summary[s]["failures"]["ci95"] for s in strats]
    errs = [[m - ci[0] for m, ci in zip(means, cis)],
            [ci[1] - m for m, ci in zip(means, cis)]]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(strats, means, yerr=errs, capsize=5, color="#4C72B0", alpha=0.8)
    ax.set_ylabel("Total Failures (12 months)")
    ax.set_title("Strategy Comparison — Simulated Data")
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "strategy_comparison.png", dpi=120)
    plt.close()

    # 2. Sensitivity: mobilisation scale
    mob_data = output["sensitivity_mobilisation"]
    scales = [d["mob_scale"] for d in mob_data]
    savings = [d["saving"] for d in mob_data]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(scales, savings, "o-", color="#DD8452")
    ax.axhline(0, color="gray", linestyle="--")
    ax.set_xlabel("Mobilisation Scale")
    ax.set_ylabel("Benefit Saving (NagarSync vs ml_per_rupee)")
    ax.set_title("Sensitivity: Mobilisation Scale — Simulated Data")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "sensitivity_mobilisation.png", dpi=120)
    plt.close()

    # 3. Equity trade-off
    eq = output["equity_tradeoff"]
    ginis = [d["gini_ward_spend"] for d in eq]
    bens = [d["total_benefit"] for d in eq]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(ginis, bens, "s-", color="#55A868")
    ax.set_xlabel("Gini of Ward Spend")
    ax.set_ylabel("Total Risk Reduction (benefit)")
    ax.set_title("Equity Trade-off — Simulated Data")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "equity_tradeoff.png", dpi=120)
    plt.close()

    # 4. Ablation bar
    abl_strats = ["digonce"] + ABLATIONS
    abl_means = [summary[s]["failures"]["mean"] for s in abl_strats if s in summary]
    abl_labels = [s for s in abl_strats if s in summary]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(abl_labels, abl_means, color="#C44E52", alpha=0.8)
    ax.set_ylabel("Total Failures")
    ax.set_title("Ablation Study — Simulated Data")
    ax.tick_params(axis="x", rotation=20)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "ablation.png", dpi=120)
    plt.close()
