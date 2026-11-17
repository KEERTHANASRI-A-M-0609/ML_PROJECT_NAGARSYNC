from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class SurvivalResult:
    available: bool
    status: str
    survival_probability: float | None = None
    hazard: float | None = None
    estimated_failure_horizon_months: float | None = None
    message: str = ""
    model_name: str | None = None


class SurvivalModelAdapter:
    """Optional Weibull/AFT wrapper; never fails the app if lifelines is missing."""

    def __init__(self) -> None:
        self.model = None
        self.model_name = "unavailable"
        self.available = False
        try:
            import lifelines  # noqa: F401
            from lifelines import WeibullAFTFitter
            self.model_name = "WeibullAFTFitter"
            self.WeibullAFTFitter = WeibullAFTFitter
            self.available = True
        except Exception:
            self.available = False
            self.model_name = "unavailable"

    def fit(self, timeline_df: pd.DataFrame, duration_col: str = "time_to_failure_months", event_col: str = "failed") -> Any | None:
        if not self.available:
            return None
        if self.model is not None:
            return self.model
        model = self.WeibullAFTFitter()
        features = [c for c in timeline_df.columns if c not in {duration_col, event_col, "asset_id"}]
        if not features:
            return None
        model.fit(timeline_df[[duration_col, event_col] + features], duration_col=duration_col, event_col=event_col)
        self.model = model
        return self.model

    def predict(self, row: pd.Series | dict[str, Any]) -> SurvivalResult:
        if not self.available or self.model is None:
            return SurvivalResult(
                available=False,
                status="unavailable",
                message="Survival model dependency unavailable; RUL unavailable.",
            )
        if isinstance(row, dict):
            row = pd.Series(row)
        features = row.to_dict()
        try:
            pred = self.model.predict_expectation(pd.DataFrame([features]))
            surv = float(np.clip(pred.iloc[0], 0.0, 1.0)) if len(pred) else 1.0
            hazard = max(0.0, 1.0 - surv)
            horizon = float(np.nan) if np.isnan(surv) else max(0.0, (1.0 - surv) * 36.0)
            return SurvivalResult(
                available=True,
                status="ok",
                survival_probability=surv,
                hazard=hazard,
                estimated_failure_horizon_months=horizon,
                model_name=self.model_name,
            )
        except Exception:
            return SurvivalResult(
                available=False,
                status="error",
                message="Survival prediction unavailable for the given row.",
            )


def generate_failure_timelines(panel: pd.DataFrame, asset_id_col: str = "asset_id", month_col: str = "month") -> pd.DataFrame:
    """Create failure timeline rows using the existing simulated history data."""
    df = panel.copy()
    if "failed_30d" in df.columns:
        df["failed"] = df["failed_30d"].astype(int)
    elif "failure_flag" in df.columns:
        df["failed"] = df["failure_flag"].astype(int)
    else:
        df["failed"] = 0
    df["time_to_failure_months"] = 1
    return df[[asset_id_col, month_col, "failed", "time_to_failure_months"]].rename(columns={month_col: "month"})
