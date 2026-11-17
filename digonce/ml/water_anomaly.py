from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


FEATURES = [
    "pressure",
    "flow",
    "minimum_night_flow",
    "consumption",
    "rolling_mean",
    "rolling_std",
    "pressure_change",
    "flow_change",
]


def build_anomaly_features(water_df: pd.DataFrame) -> pd.DataFrame:
    """Create the required anomaly features from the simulated water telemetry."""
    df = water_df.copy().sort_values(["dma", "day"]).reset_index(drop=True)
    df["pressure"] = df["pressure_bar"].astype(float)
    df["flow"] = df["mnf_ls"].astype(float)
    df["minimum_night_flow"] = df["mnf_ls"].astype(float)
    df["consumption"] = df["mnf_ls"].astype(float) * 0.75
    df["rolling_mean"] = df.groupby("dma")["flow"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    df["rolling_std"] = df.groupby("dma")["flow"].transform(lambda s: s.rolling(7, min_periods=1).std().fillna(0.0))
    df["pressure_change"] = df.groupby("dma")["pressure"].transform(lambda s: s.diff().fillna(0.0))
    df["flow_change"] = df.groupby("dma")["flow"].transform(lambda s: s.diff().fillna(0.0))
    return df


def train_water_anomaly_model(water_df: pd.DataFrame, contamination: float = 0.10) -> tuple[IsolationForest, dict[str, Any]]:
    df = build_anomaly_features(water_df)
    X = df[FEATURES].fillna(0.0).values
    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    model.fit(X)
    scores = -model.score_samples(X)
    severity = scores / max(np.max(scores), 1e-9)
    metrics = {
        "feature_names": FEATURES,
        "anomaly_score_mean": round(float(scores.mean()), 6),
        "severity_mean": round(float(severity.mean()), 6),
        "contamination": contamination,
    }
    return model, metrics


def predict_anomaly(model: IsolationForest, water_df: pd.DataFrame) -> pd.DataFrame:
    df = build_anomaly_features(water_df)
    X = df[FEATURES].fillna(0.0).values
    scores = -model.score_samples(X)
    flags = (model.predict(X) == -1).astype(int)
    df["anomaly_score"] = scores
    df["anomaly_flag"] = flags
    df["severity"] = np.clip(scores / max(np.max(scores), 1e-9), 0.0, 1.0)
    return df
