"""Dependency-light analytics for the explicitly simulated local demo."""
from __future__ import annotations

import numpy as np
import pandas as pd


DEMO_FEATURE_COLUMNS = [
    "age_years",
    "condition_score",
    "months_since_inspection",
    "sensor_reading",
    "previous_failures",
    "rainfall_mm",
    "dma_leak_score",
    "criticality",
]


def encode_demo_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep the numeric inputs used by the transparent demo scoring rule."""
    encoded = frame.copy()
    for column in DEMO_FEATURE_COLUMNS:
        if column not in encoded:
            encoded[column] = 0.0
    return encoded


class DemoPriorityScorer:
    """Deterministic condition-priority scorer; this is not a trained risk model."""

    feature_cols = DEMO_FEATURE_COLUMNS

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        values = np.asarray(features, dtype=float)
        if values.ndim == 1:
            values = values.reshape(1, -1)
        columns = {name: values[:, index] for index, name in enumerate(self.feature_cols)}

        def normalized(name: str, scale: float) -> np.ndarray:
            return np.clip(columns[name] / scale, 0.0, 1.0)

        score = (
            0.01
            + 0.16 * (1.0 - np.clip(columns["condition_score"], 0.0, 1.0))
            + 0.12 * np.clip(columns["sensor_reading"], 0.0, 1.0)
            + 0.06 * normalized("age_years", 50.0)
            + 0.04 * normalized("previous_failures", 5.0)
            + 0.025 * normalized("months_since_inspection", 36.0)
            + 0.05 * np.clip(columns["dma_leak_score"], 0.0, 1.0)
            + 0.02 * normalized("rainfall_mm", 250.0)
            + 0.015 * normalized("criticality", 5.0)
        )
        return np.clip(score, 0.0, 1.0)
