"""
ml/traffic.py — Simulated hourly traffic + day-ahead HistGradientBoosting forecaster.

All data is SIMULATED.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from ml.config import SEED, N_JUNCTIONS, TOTAL_MONTHS, HISTORY_MONTHS, MODELS_DIR
from ml.city import RAINFALL_NORMALS

logger = logging.getLogger(__name__)


def generate_traffic_data(rng: np.random.Generator) -> pd.DataFrame:
    """Generate hourly traffic counts for N_JUNCTIONS junctions."""
    total_days = TOTAL_MONTHS * 30
    records = []

    # Base daily volumes per junction (PCU/day)
    base_volumes = rng.uniform(20_000, 60_000, N_JUNCTIONS)

    # Rush-hour profile (24 hours)
    hour_profile = np.array([
        0.5, 0.3, 0.2, 0.2, 0.3, 0.6,
        1.5, 2.5, 2.8, 2.0, 1.5, 1.4,
        1.6, 1.5, 1.4, 1.6, 2.2, 2.8,
        2.5, 1.8, 1.4, 1.1, 0.8, 0.6,
    ], dtype=float)
    hour_profile /= hour_profile.sum()   # normalise to sum=1

    # Holiday list (approx Indian holidays, day-of-year)
    holidays = {1, 26, 89, 90, 91, 185, 234, 265, 279, 310, 358, 359}

    for j in range(N_JUNCTIONS):
        for day in range(total_days):
            month_idx = (day // 30) % 12
            rain = max(0, RAINFALL_NORMALS[month_idx] / 30 + rng.normal(0, 2))
            dow = day % 7
            is_weekend = int(dow >= 5)
            is_holiday = int((day % 365) in holidays)

            # Special event (~2% of days)
            is_event = int(rng.random() < 0.02)

            daily_scale = (
                base_volumes[j]
                * (0.75 if is_weekend else 1.0)
                * (0.60 if is_holiday else 1.0)
                * (1.15 if is_event else 1.0)
                * max(0.7, 1 - rain / 100 * 0.15)
            )

            for hour in range(24):
                count = daily_scale * hour_profile[hour] * rng.lognormal(0, 0.08)
                records.append({
                    "junction": j,
                    "day": day,
                    "month": day // 30,
                    "hour": hour,
                    "dow": dow,
                    "is_weekend": is_weekend,
                    "is_holiday": is_holiday,
                    "is_event": is_event,
                    "rain_mm": round(float(rain), 2),
                    "count": round(float(count), 0),
                })

    return pd.DataFrame(records)


def _make_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag features (all >= 24h) per junction."""
    df = df.sort_values(["junction", "day", "hour"]).copy()
    df["time_idx"] = df["day"] * 24 + df["hour"]

    out_parts = []
    for j, grp in df.groupby("junction"):
        g = grp.sort_values("time_idx").copy()
        c = g["count"].values
        g["lag_24"] = np.concatenate([np.full(24, np.nan), c[:-24]])
        g["lag_48"] = np.concatenate([np.full(48, np.nan), c[:-48]])
        g["lag_168"] = np.concatenate([np.full(168, np.nan), c[:-168]])
        # Same-hour 7-day mean (lags 24,48,...,168)
        same_hour_mean = np.full(len(g), np.nan)
        for i in range(168, len(g)):
            same_hour_mean[i] = np.mean([c[i - k] for k in [24, 48, 72, 96, 120, 144, 168]])
        g["same_hour_7d_mean"] = same_hour_mean
        out_parts.append(g)

    return pd.concat(out_parts)


LAG_FEATURES = ["lag_24", "lag_48", "lag_168", "same_hour_7d_mean",
                 "hour", "dow", "is_holiday", "rain_mm", "junction"]


def train_traffic_model(traffic_df: pd.DataFrame) -> tuple[HistGradientBoostingRegressor, dict]:
    """Train day-ahead forecaster; compare against naive baselines."""
    df = _make_lag_features(traffic_df)
    df = df.dropna(subset=LAG_FEATURES)

    # Time-based split: train on history months, test on remaining
    train_mask = df["month"] < HISTORY_MONTHS
    X_train = df.loc[train_mask, LAG_FEATURES]
    y_train = df.loc[train_mask, "count"]
    X_test = df.loc[~train_mask, LAG_FEATURES]
    y_test = df.loc[~train_mask, "count"]

    model = HistGradientBoostingRegressor(random_state=SEED, max_iter=200)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae_model = float(mean_absolute_error(y_test, preds))

    # Naive baselines
    mae_yesterday = float(mean_absolute_error(y_test, df.loc[~train_mask, "lag_24"]))
    mae_lastweek = float(mean_absolute_error(y_test, df.loc[~train_mask, "lag_168"]))

    metrics = {
        "mae_model": round(mae_model, 2),
        "mae_yesterday_baseline": round(mae_yesterday, 2),
        "mae_lastweek_baseline": round(mae_lastweek, 2),
    }

    # Export typical weekday/weekend hourly profile per junction from held-out predictions
    df_test = df.loc[~train_mask].copy()
    df_test["pred"] = preds
    profiles = (
        df_test.groupby(["junction", "is_weekend", "hour"])["pred"]
        .mean()
        .reset_index()
        .rename(columns={"pred": "mean_count"})
    )

    joblib.dump(model, MODELS_DIR / "traffic_model.joblib")
    profiles.to_csv(MODELS_DIR / "traffic_profiles.csv", index=False)
    return model, metrics, profiles


def load_traffic_profiles(traffic_df: pd.DataFrame) -> pd.DataFrame:
    """Load saved forecast profiles or derive a quick observed-traffic fallback."""
    profiles_path = MODELS_DIR / "traffic_profiles.csv"
    if profiles_path.exists():
        return pd.read_csv(profiles_path)

    logger.warning("Saved traffic profiles not found; using observed held-out traffic averages")
    observed = traffic_df.loc[traffic_df["month"] >= HISTORY_MONTHS]
    if observed.empty:
        raise ValueError("Traffic data has no held-out rows for profile generation")
    return (
        observed.groupby(["junction", "is_weekend", "hour"])["count"]
        .mean()
        .reset_index()
        .rename(columns={"count": "mean_count"})
    )
