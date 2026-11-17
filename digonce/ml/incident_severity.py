from __future__ import annotations

import numpy as np


def incident_severity(
    failure_risk: float,
    anomaly_severity: float,
    asset_criticality: int,
    traffic_impact: float,
    service_impact: float,
) -> dict[str, float | str]:
    """Explainable incident severity score without a dedicated ML model."""
    score = (
        0.35 * float(failure_risk)
        + 0.25 * float(anomaly_severity)
        + 0.15 * min(float(asset_criticality) / 5.0, 1.0)
        + 0.15 * float(traffic_impact)
        + 0.10 * float(service_impact)
    )
    severity = round(float(np.clip(score, 0.0, 1.0)), 4)
    if severity >= 0.75:
        level = "critical"
    elif severity >= 0.5:
        level = "high"
    elif severity >= 0.3:
        level = "moderate"
    else:
        level = "low"
    return {"severity_score": severity, "severity_level": level}
