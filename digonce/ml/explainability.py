from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def explain_prediction(
    model: Any,
    X: pd.DataFrame | np.ndarray,
    feature_names: list[str] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """Return SHAP-style explanation when shap is available; otherwise use feature importance."""
    try:
        import shap  # type: ignore

        if isinstance(X, pd.DataFrame):
            explain_df = X.copy()
        else:
            feature_names = feature_names or [f"f{i}" for i in range(X.shape[1])]
            explain_df = pd.DataFrame(X, columns=feature_names)

        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(explain_df)
        if isinstance(values, list):
            values = values[-1]
        if values.ndim == 2:
            contribution = np.abs(values[0])
            ranking = np.argsort(contribution)[::-1][:top_k]
            features = []
            for idx in ranking:
                name = feature_names[idx] if feature_names is not None else str(idx)
                val = float(values[0, idx])
                features.append({"feature": name, "contribution": round(val, 6)})
            return {"source": "shap", "features": features}
    except Exception:
        pass

    if hasattr(model, "feature_names_in_"):
        feature_names = list(model.feature_names_in_)
    elif feature_names is None:
        feature_names = [f"f{i}" for i in range(np.asarray(X).shape[1])]

    if hasattr(model, "feature_importances_"):
        importance = model.feature_importances_
        ranking = np.argsort(importance)[::-1][:top_k]
        features = []
        for idx in ranking:
            features.append({
                "feature": feature_names[idx],
                "contribution": round(float(importance[idx]), 6),
            })
        return {"source": "feature_importance", "features": features}
    return {"source": "unavailable", "features": []}
