from __future__ import annotations

import numpy as np


def health_components(
    risk: float,
    anomaly: float,
    condition: float,
    age_years: float,
    failure_history: int = 0,
    maintenance_history: int = 0,
) -> dict[str, float]:
    """Transparent 0-100 health score decomposition for explainability."""
    risk_component = float(np.clip(1.0 - risk, 0.0, 1.0)) * 35.0
    anomaly_component = float(np.clip(1.0 - anomaly, 0.0, 1.0)) * 20.0
    condition_component = float(np.clip(condition, 0.0, 1.0)) * 20.0
    age_component = float(np.clip(1.0 - min(age_years / 40.0, 1.0), 0.0, 1.0)) * 10.0
    fail_component = float(np.clip(1.0 - min(failure_history / 5.0, 1.0), 0.0, 1.0)) * 10.0
    maint_component = float(np.clip(min(maintenance_history / 4.0, 1.0), 0.0, 1.0)) * 5.0
    total = risk_component + anomaly_component + condition_component + age_component + fail_component + maint_component
    return {
        "risk": round(float(risk_component), 3),
        "anomaly": round(float(anomaly_component), 3),
        "condition": round(float(condition_component), 3),
        "age": round(float(age_component), 3),
        "failure_history": round(float(fail_component), 3),
        "maintenance_history": round(float(maint_component), 3),
        "health_score": round(float(np.clip(total, 0.0, 100.0)), 3),
    }


def health_band(score: float) -> str:
    if score >= 80:
        return "Healthy"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Degrading"
    return "Critical"


def health_score(risk: float) -> float:
    """Map calibrated failure probability to the legacy 0–100 display score."""
    return round(100 * (1 - np.sqrt(min(1.0, risk / 0.30))), 1)


def occlusion_attribution(wrapper, asset_features: np.ndarray, background: np.ndarray) -> list[dict]:
    """Explain a prediction by replacing each feature with its baseline value."""
    feature_columns = wrapper.feature_cols
    base_probability = float(wrapper.predict_proba(asset_features.reshape(1, -1))[0])
    attributions = []

    for index, feature in enumerate(feature_columns):
        occluded_features = asset_features.copy()
        occluded_features[index] = background[index]
        occluded_probability = float(wrapper.predict_proba(occluded_features.reshape(1, -1))[0])
        attributions.append({
            "feature": feature,
            "base_prob": round(base_probability, 4),
            "occluded_prob": round(occluded_probability, 4),
            "delta_pp": round((base_probability - occluded_probability) * 100, 3),
        })

    return sorted(attributions, key=lambda item: -abs(item["delta_pp"]))
