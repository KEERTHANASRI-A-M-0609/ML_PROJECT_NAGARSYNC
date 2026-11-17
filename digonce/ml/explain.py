"""
ml/explain.py — Global permutation importance + per-asset occlusion attribution.
Health score computation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from ml.risk_model import CalibratedRisk, FEATURE_COLS, _encode, _get_xy
from ml.config import TEST_END, CALIB_END
from ml.health import health_band, health_score, health_components, occlusion_attribution


def permutation_importance(
    wrapper: CalibratedRisk,
    panel: pd.DataFrame,
    n_repeats: int = 5,
    rng: np.random.Generator | None = None,
) -> list[dict]:
    """Global permutation importance on test set (PR-AUC drop)."""
    if rng is None:
        rng = np.random.default_rng(42)

    df = _encode(panel)
    test = df[(df["month"] >= CALIB_END) & (df["month"] < TEST_END)]
    feat_cols = wrapper.feature_cols
    X, y = _get_xy(test, feat_cols)

    base_score = float(average_precision_score(y, wrapper.predict_proba(X)))
    results = []

    for i, feat in enumerate(feat_cols):
        drops = []
        for _ in range(n_repeats):
            X_perm = X.copy()
            rng.shuffle(X_perm[:, i])
            score = float(average_precision_score(y, wrapper.predict_proba(X_perm)))
            drops.append(base_score - score)
        results.append({
            "feature": feat,
            "importance_mean": round(float(np.mean(drops)), 5),
            "importance_std": round(float(np.std(drops)), 5),
        })

    return sorted(results, key=lambda x: -x["importance_mean"])




def explain_with_shap(
    model,
    X: pd.DataFrame | np.ndarray,
    feature_names: list[str] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Use SHAP if available, otherwise fall back to model-native feature importance."""
    try:
        import shap  # type: ignore
        if isinstance(X, pd.DataFrame):
            df = X.copy()
        else:
            if feature_names is None:
                feature_names = [f"f{i}" for i in range(X.shape[1])]
            df = pd.DataFrame(X, columns=feature_names)
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(df)
        if isinstance(values, list):
            values = values[-1]
        if values.ndim == 2:
            idxs = np.argsort(np.abs(values[0]))[::-1][:top_k]
            out = []
            for i in idxs:
                name = feature_names[i] if feature_names is not None else str(i)
                out.append({"feature": name, "value": round(float(values[0, i]), 6)})
            return out
    except Exception:
        pass
    if hasattr(model, "feature_importances_"):
        importances = getattr(model, "feature_importances_")
        names = feature_names or [f"f{i}" for i in range(len(importances))]
        idxs = np.argsort(importances)[::-1][:top_k]
        return [{"feature": names[i], "value": round(float(importances[i]), 6)} for i in idxs]
    return []
