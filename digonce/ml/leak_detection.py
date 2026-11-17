"""
ml/leak_detection.py — Unsupervised IsolationForest leak detector on MNF/pressure.

contamination=0.10 is set a priori as an alert budget (not tuned on labels).
Fit only on history days (month < HISTORY_MONTHS).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

from ml.config import HISTORY_MONTHS, LEAK_CONTAMINATION, LEAK_SCORE_WINDOW, MODELS_DIR


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Features match the required anomaly module specification while remaining compatible with simulated data."""
    out = df.copy().sort_values(["dma", "day"]).reset_index(drop=True)
    out["pressure"] = out["pressure_bar"].astype(float)
    out["flow"] = out["mnf_ls"].astype(float)
    out["minimum_night_flow"] = out["mnf_ls"].astype(float)
    out["consumption"] = out["mnf_ls"].astype(float) * 0.75
    out["rolling_mean"] = out.groupby("dma")["flow"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    out["rolling_std"] = out.groupby("dma")["flow"].transform(lambda s: s.rolling(7, min_periods=1).std().fillna(0.0))
    out["pressure_change"] = out.groupby("dma")["pressure"].transform(lambda s: s.diff().fillna(0.0))
    out["flow_change"] = out.groupby("dma")["flow"].transform(lambda s: s.diff().fillna(0.0))
    return out


FEATURE_COLS = [
    "pressure", "flow", "minimum_night_flow", "consumption",
    "rolling_mean", "rolling_std", "pressure_change", "flow_change",
]


def train_leak_detector(water_df: pd.DataFrame) -> tuple[IsolationForest, dict]:
    """Fit IsolationForest on history days only; return model and metrics."""
    df = _build_features(water_df)
    history_mask = df["month"] < HISTORY_MONTHS

    X_train = df.loc[history_mask, FEATURE_COLS].fillna(0).values
    model = IsolationForest(
        contamination=LEAK_CONTAMINATION,
        random_state=42,
        n_estimators=200,
    )
    model.fit(X_train)

    # Evaluate on all data (day-level)
    X_all = df[FEATURE_COLS].fillna(0).values
    scores = -model.score_samples(X_all)   # higher = more anomalous
    preds = (model.predict(X_all) == -1).astype(int)
    y_true = df["leak_flag"].values

    metrics = {
        "day_precision": round(float(precision_score(y_true, preds, zero_division=0)), 4),
        "day_recall": round(float(recall_score(y_true, preds, zero_division=0)), 4),
        "day_f1": round(float(f1_score(y_true, preds, zero_division=0)), 4),
        "day_auc": round(float(roc_auc_score(y_true, scores)), 4),
    }

    # Event-level: detection rate and mean delay
    detected_events, total_events, delays = 0, 0, []
    for dma, grp in df.groupby("dma"):
        grp = grp.sort_values("day").reset_index(drop=True)
        leak = grp["leak_flag"].values
        pred = (model.predict(grp[FEATURE_COLS].fillna(0).values) == -1).astype(int)
        # Find contiguous leak events
        in_event = False
        event_start = 0
        for d in range(len(leak)):
            if leak[d] == 1 and not in_event:
                in_event = True
                event_start = d
                total_events += 1
            elif leak[d] == 0 and in_event:
                in_event = False
                # Check if any day in event was flagged
                if pred[event_start:d].any():
                    detected_events += 1
                    first_flag = event_start + int(np.argmax(pred[event_start:d]))
                    delays.append(first_flag - event_start)

    metrics["event_detection_rate"] = round(detected_events / max(total_events, 1), 4)
    metrics["mean_detection_delay_days"] = round(float(np.mean(delays)) if delays else 0.0, 2)

    joblib.dump(model, MODELS_DIR / "leak_detector.joblib")
    return model, metrics


def compute_leak_scores(
    water_df: pd.DataFrame,
    model: IsolationForest,
    total_months: int,
) -> dict[tuple[int, int], float]:
    """
    For each (dma, month): share of flagged days in the LEAK_SCORE_WINDOW days
    before the month starts.
    """
    df = _build_features(water_df)
    X = df[FEATURE_COLS].fillna(0).values
    df = df.copy()
    df["flagged"] = (model.predict(X) == -1).astype(int)

    scores: dict[tuple[int, int], float] = {}
    for dma, grp in df.groupby("dma"):
        grp = grp.sort_values("day").reset_index(drop=True)
        for m in range(total_months):
            month_start_day = m * 30
            window_start = max(0, month_start_day - LEAK_SCORE_WINDOW)
            window = grp.loc[
                (grp["day"] >= window_start) & (grp["day"] < month_start_day),
                "flagged"
            ]
            scores[(int(dma), m)] = float(window.mean()) if len(window) > 0 else 0.0

    return scores
