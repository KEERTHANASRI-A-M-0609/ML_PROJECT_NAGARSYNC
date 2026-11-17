"""
ml/risk_model.py — P(asset fails within 30 days).

Splits: train 0–23, calibration 24–29, test 30–35.
Calibrated with isotonic regression.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss,
    precision_score, recall_score, f1_score
)
from sklearn.preprocessing import LabelEncoder

from ml.config import TRAIN_END, CALIB_END, TEST_END, MODELS_DIR
from ml.model_registry import save_model_artifact

FEATURE_COLS = [
    "asset_type_enc", "material_enc", "road_class_enc",
    "age_years", "condition_score", "months_since_inspection",
    "sensor_reading", "months_since_repair", "previous_failures",
    "maintenance_count", "daily_traffic", "rainfall_mm", "dma_leak_score",
]

FEATURE_COLS_NO_LEAK = [c for c in FEATURE_COLS if c != "dma_leak_score"]


def _encode(panel: pd.DataFrame) -> pd.DataFrame:
    """Label-encode categorical columns."""
    df = panel.copy()
    for col, new_col in [
        ("asset_type", "asset_type_enc"),
        ("material", "material_enc"),
        ("road_class", "road_class_enc"),
    ]:
        le = LabelEncoder()
        df[new_col] = le.fit_transform(df[col].astype(str))
    return df


def _split(df: pd.DataFrame) -> tuple[pd.DataFrame, ...]:
    train = df[df["month"] < TRAIN_END]
    calib = df[(df["month"] >= TRAIN_END) & (df["month"] < CALIB_END)]
    test = df[(df["month"] >= CALIB_END) & (df["month"] < TEST_END)]
    return train, calib, test


def _metrics(y_true: np.ndarray, proba: np.ndarray) -> dict:
    roc = float(roc_auc_score(y_true, proba))
    pr = float(average_precision_score(y_true, proba))
    brier = float(brier_score_loss(y_true, proba))
    preds = (proba >= 0.5).astype(int)
    prec = float(precision_score(y_true, preds, zero_division=0))
    rec = float(recall_score(y_true, preds, zero_division=0))
    f1 = float(f1_score(y_true, preds, zero_division=0))

    # ECE (10 bins)
    bins = np.linspace(0, 1, 11)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (proba >= lo) & (proba < hi)
        if mask.sum() > 0:
            ece += mask.sum() / len(y_true) * abs(y_true[mask].mean() - proba[mask].mean())

    # Recall @ top 5% and 10%
    n5 = max(1, int(0.05 * len(y_true)))
    n10 = max(1, int(0.10 * len(y_true)))
    top5_idx = np.argsort(proba)[-n5:]
    top10_idx = np.argsort(proba)[-n10:]
    r5 = float(y_true[top5_idx].sum() / max(1, y_true.sum()))
    r10 = float(y_true[top10_idx].sum() / max(1, y_true.sum()))

    return {
        "roc_auc": round(roc, 4),
        "pr_auc": round(pr, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "brier": round(brier, 4),
        "ece": round(ece, 4),
        "recall_top5pct": round(r5, 4),
        "recall_top10pct": round(r10, 4),
    }


class CalibratedRisk:
    """Picklable wrapper: raw model + isotonic calibrator."""

    def __init__(self, base_model, feature_cols: list[str]):
        self.base_model = base_model
        self.feature_cols = feature_cols
        self.calibrator: CalibratedClassifierCV | None = None

    def fit_calibrator(self, X_calib: np.ndarray, y_calib: np.ndarray) -> None:
        from sklearn.isotonic import IsotonicRegression
        raw = self.base_model.predict_proba(X_calib)[:, 1]
        self.calibrator = IsotonicRegression(out_of_bounds="clip")
        self.calibrator.fit(raw, y_calib)

    def predict_raw(self, X: np.ndarray) -> np.ndarray:
        return self.base_model.predict_proba(X)[:, 1]

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.calibrator is None:
            return self.predict_raw(X)
        raw = self.predict_raw(X)
        return self.calibrator.predict(raw)


def _get_xy(df: pd.DataFrame, feat_cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    X = df[feat_cols].fillna(df[feat_cols].median()).values
    y = df["failed_30d"].values
    return X, y


def train_risk_model(panel: pd.DataFrame, with_leak: bool = True) -> tuple[CalibratedRisk, dict]:
    """Train, calibrate, and evaluate the risk model."""
    df = _encode(panel)
    train, calib, test = _split(df)
    feat_cols = FEATURE_COLS if with_leak else FEATURE_COLS_NO_LEAK

    X_tr, y_tr = _get_xy(train, feat_cols)
    X_cal, y_cal = _get_xy(calib, feat_cols)
    X_te, y_te = _get_xy(test, feat_cols)

    candidates = {
        "logistic": LogisticRegression(max_iter=2000, random_state=42),
        "random_forest": RandomForestClassifier(n_estimators=120, random_state=42, n_jobs=-1, max_depth=12),
        "hist_gb": HistGradientBoostingClassifier(
            random_state=42, max_iter=250, learning_rate=0.08, max_depth=6,
            l2_regularization=0.1, early_stopping=True, validation_fraction=0.1,
        ),
    }
    try:
        from xgboost import XGBClassifier
        candidates["xgboost"] = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric="logloss",
            verbosity=0,
        )
    except ImportError:
        pass

    # Select by validation PR-AUC
    best_name, best_pr, best_model = "", -1.0, None
    val_results = {}
    for name, clf in candidates.items():
        clf.fit(X_tr, y_tr)
        p = clf.predict_proba(X_cal)[:, 1]
        pr = float(average_precision_score(y_cal, p))
        val_results[name] = round(pr, 4)
        if pr > best_pr:
            best_pr, best_name, best_model = pr, name, clf

    wrapper = CalibratedRisk(best_model, feat_cols)
    wrapper.fit_calibrator(X_cal, y_cal)

    raw_proba = wrapper.predict_raw(X_te)
    cal_proba = wrapper.predict_proba(X_te)

    raw_metrics = _metrics(y_te, raw_proba)
    cal_metrics = _metrics(y_te, cal_proba)

    # Reliability diagram data
    bins = np.linspace(0, 1, 11)
    reliability = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (cal_proba >= lo) & (cal_proba < hi)
        if mask.sum() > 0:
            reliability.append({
                "bin_mid": round((lo + hi) / 2, 2),
                "mean_pred": round(float(cal_proba[mask].mean()), 4),
                "frac_pos": round(float(y_te[mask].mean()), 4),
                "count": int(mask.sum()),
            })

    metrics = {
        "best_model": best_name,
        "val_pr_auc_by_model": val_results,
        "raw": raw_metrics,
        "calibrated": cal_metrics,
        "reliability_diagram": reliability,
    }

    suffix = "" if with_leak else "_no_leak"
    artifact_name = f"risk_model{suffix}"
    save_model_artifact(
        artifact_name,
        wrapper,
        feat_cols,
        metrics,
        training_data_version="simulated-v1",
        random_seed=42,
    )
    joblib.dump(wrapper, MODELS_DIR / f"{artifact_name}.joblib")
    return wrapper, metrics
