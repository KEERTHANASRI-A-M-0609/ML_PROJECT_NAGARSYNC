"""
ml/run_pipeline.py — Orchestrates all phases.

Usage:
  python -m ml.run_pipeline --phase all
  python -m ml.run_pipeline --phase data
  python -m ml.run_pipeline --phase train
  python -m ml.run_pipeline --phase simulate
  python -m ml.run_pipeline --fast
"""
from __future__ import annotations

import argparse
import json
import time
import numpy as np
import pandas as pd

from ml.config import (
    SEED, DATA_RAW, DATA_PROC, MODELS_DIR, REPORTS_DIR, FIGURES_DIR,
    HISTORY_MONTHS, TOTAL_MONTHS, ANNUAL_BUDGET_FRACTION,
)


def phase_data(rng: np.random.Generator) -> tuple:
    print("-- Phase 1: Generating simulated city data --")
    from ml.city import generate_corridors, generate_assets, simulate_city
    from ml.water import generate_water_data

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_PROC.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    corridors = generate_corridors(rng)
    assets = generate_assets(corridors, rng)
    water_df = generate_water_data(rng)

    corridors.to_csv(DATA_RAW / "corridors.csv", index=False)
    assets.to_csv(DATA_RAW / "assets.csv", index=False)
    water_df.to_csv(DATA_RAW / "water_daily.csv", index=False)

    print(f"  Corridors: {len(corridors)}, Assets: {len(assets)}")

    # Phase 2a: Leak detection (needed before city simulation)
    print("-- Phase 2a: Leak detection --")
    from ml.leak_detection import train_leak_detector, compute_leak_scores
    leak_model, leak_metrics = train_leak_detector(water_df)
    leak_scores = compute_leak_scores(water_df, leak_model, TOTAL_MONTHS)
    print(f"  Leak AUC: {leak_metrics['day_auc']}, Event detection: {leak_metrics['event_detection_rate']}")

    # Phase 2b: Traffic
    print("-- Phase 2b: Traffic model --")
    from ml.traffic import generate_traffic_data, train_traffic_model
    traffic_df = generate_traffic_data(rng)
    traffic_df.to_csv(DATA_RAW / "traffic_hourly.csv", index=False)
    traffic_model, traffic_metrics, traffic_profiles = train_traffic_model(traffic_df)
    print(f"  Traffic MAE: {traffic_metrics['mae_model']} vs yesterday: {traffic_metrics['mae_yesterday_baseline']}")

    # Simulate city with leak scores
    print("-- Phase 1b: Simulating city dynamics --")
    panel = simulate_city(assets, corridors, rng, leak_scores)
    panel.to_csv(DATA_PROC / "asset_month_panel.csv", index=False)

    # Current snapshot (month 35 = last history month)
    snapshot = panel[panel["month"] == HISTORY_MONTHS - 1].copy()
    snapshot.to_csv(DATA_PROC / "current_snapshot.csv", index=False)
    print(f"  Panel rows: {len(panel)}, Snapshot rows: {len(snapshot)}")

    # Save rainfall normals
    from ml.city import RAINFALL_NORMALS
    rain_df = pd.DataFrame({
        "month_name": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
        "rainfall_mm_normal": RAINFALL_NORMALS,
    })
    rain_df.to_csv(DATA_RAW / "rainfall_monthly.csv", index=False)

    return corridors, assets, water_df, traffic_df, traffic_profiles, leak_scores, panel, snapshot, leak_metrics, traffic_metrics


def phase_train(panel: pd.DataFrame) -> tuple:
    print("-- Phase 3: Training risk models --")
    from ml.risk_model import train_risk_model
    from ml.explain import permutation_importance
    from ml.traffic_forecast import train_traffic_forecast_model
    from ml.water_anomaly import train_water_anomaly_model
    from ml.survival import SurvivalModelAdapter, generate_failure_timelines

    risk_model, risk_metrics = train_risk_model(panel, with_leak=True)
    risk_model_no_leak, risk_metrics_no_leak = train_risk_model(panel, with_leak=False)

    perm_imp = permutation_importance(risk_model, panel)

    traffic_model, traffic_metrics = train_traffic_forecast_model(pd.read_csv(DATA_RAW / "traffic_hourly.csv"), horizon_hours=1)
    anomaly_model, anomaly_metrics = train_water_anomaly_model(pd.read_csv(DATA_RAW / "water_daily.csv"))
    surv_adapter = SurvivalModelAdapter()
    timeline = generate_failure_timelines(panel)
    surv_model = surv_adapter.fit(timeline)

    metrics = {
        "risk_model": risk_metrics,
        "risk_model_no_leak": risk_metrics_no_leak,
        "permutation_importance": perm_imp,
        "traffic_forecast": traffic_metrics,
        "water_anomaly": anomaly_metrics,
        "survival": {
            "available": surv_adapter.available,
            "model_name": surv_adapter.model_name,
            "status": "trained" if surv_model is not None else "unavailable",
        },
    }
    with open(MODELS_DIR / "model_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"  Best model: {risk_metrics['best_model']}")
    print(f"  Test ROC-AUC: {risk_metrics['calibrated']['roc_auc']}")
    print(f"  Test PR-AUC:  {risk_metrics['calibrated']['pr_auc']}")
    print(f"  ECE raw: {risk_metrics['raw']['ece']} -> calibrated: {risk_metrics['calibrated']['ece']}")
    return risk_model, risk_model_no_leak, metrics


def phase_simulate(
    assets, corridors, risk_model, risk_model_no_leak,
    leak_scores, traffic_profiles, fast: bool = False
) -> dict:
    print("-- Phase 5: Running experiments --")
    from ml.experiments import run_all_experiments
    results = run_all_experiments(
        assets, corridors, risk_model, risk_model_no_leak,
        leak_scores, traffic_profiles, fast=fast,
    )
    print(f"  Experiments saved to reports/experiments.json")
    _print_summary(results)
    return results


def _print_summary(results: dict) -> None:
    print("\n-- Final Metrics Table (Simulated Data) --")
    print(f"{'Strategy':<30} {'Failures':>10} {'Total Spend':>14} {'Re-digs':>8}")
    print("-" * 65)
    for strat, metrics in results["summary"].items():
        f = metrics["failures"]["mean"]
        s = metrics["total_spend"]["mean"]
        r = metrics["re_dig_events"]["mean"]
        print(f"{strat:<30} {f:>10.1f} {s:>14.1f} {r:>8.1f}")
    print(f"\nBreak-even mobilisation scale: {results['breakeven_mob_scale']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["data", "train", "simulate", "all"], default="all")
    parser.add_argument("--fast", action="store_true", help="Use fewer seeds")
    args = parser.parse_args()

    rng = np.random.default_rng(SEED)
    t0 = time.time()

    if args.phase in ("data", "all"):
        (corridors, assets, water_df, traffic_df, traffic_profiles,
         leak_scores, panel, snapshot, leak_metrics, traffic_metrics) = phase_data(rng)

    if args.phase in ("train", "all"):
        if args.phase == "train":
            panel = pd.read_csv(DATA_PROC / "asset_month_panel.csv")
        risk_model, risk_model_no_leak, model_metrics = phase_train(panel)

    if args.phase in ("simulate", "all"):
        if args.phase == "simulate":
            import joblib
            assets = pd.read_csv(DATA_RAW / "assets.csv")
            corridors = pd.read_csv(DATA_RAW / "corridors.csv")
            risk_model = joblib.load(MODELS_DIR / "risk_model.joblib")
            risk_model_no_leak = joblib.load(MODELS_DIR / "risk_model_no_leak.joblib")
            leak_model = joblib.load(MODELS_DIR / "leak_detector.joblib")
            water_df = pd.read_csv(DATA_RAW / "water_daily.csv")
            from ml.leak_detection import compute_leak_scores
            leak_scores = compute_leak_scores(water_df, leak_model, TOTAL_MONTHS)
            traffic_df = pd.read_csv(DATA_RAW / "traffic_hourly.csv")
            from ml.traffic import train_traffic_model
            _, _, traffic_profiles = train_traffic_model(traffic_df)

        phase_simulate(
            assets, corridors, risk_model, risk_model_no_leak,
            leak_scores, traffic_profiles, fast=args.fast,
        )

    print(f"\nTotal time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
