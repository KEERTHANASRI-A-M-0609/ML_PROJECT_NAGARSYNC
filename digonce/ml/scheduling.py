"""
ml/scheduling.py — Traffic-aware work window selection.

Per corridor: pick the contiguous 8-hour window minimising vehicle-hours disrupted.
Compare with default 09:00 start.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _hourly_profile(
    junction: int,
    is_weekend: bool,
    traffic_profiles: pd.DataFrame,
) -> np.ndarray:
    """Return 24-hour count profile for a junction/day-type."""
    mask = (
        (traffic_profiles["junction"] == junction) &
        (traffic_profiles["is_weekend"] == int(is_weekend))
    )
    sub = traffic_profiles[mask].sort_values("hour")
    if len(sub) == 0:
        return np.ones(24) / 24
    profile = sub["mean_count"].values
    return profile / profile.sum() if profile.sum() > 0 else np.ones(24) / 24


def best_window(
    corridor_daily_traffic: float,
    junction: int,
    repair_hours: float,
    traffic_profiles: pd.DataFrame,
    is_weekend: bool = False,
) -> dict:
    """
    Find contiguous window of ceil(repair_hours) hours minimising vehicle-hours disrupted.
    Returns best start hour, vehicle-hours disrupted, and default (09:00) disruption.
    """
    window_len = max(1, int(np.ceil(repair_hours)))
    profile = _hourly_profile(junction, is_weekend, traffic_profiles)
    hourly_vehicles = corridor_daily_traffic * profile

    # Cyclic rolling sum
    extended = np.concatenate([hourly_vehicles, hourly_vehicles])
    disruptions = np.array([
        extended[h:h + window_len].sum() for h in range(24)
    ])

    best_start = int(np.argmin(disruptions))
    default_disruption = float(extended[9:9 + window_len].sum())

    return {
        "best_start_hour": best_start,
        "best_disruption_vh": round(float(disruptions[best_start]), 1),
        "default_disruption_vh": round(default_disruption, 1),
        "saving_vh": round(default_disruption - float(disruptions[best_start]), 1),
    }


def schedule_plan(
    selected: pd.DataFrame,
    traffic_profiles: pd.DataFrame,
    is_weekend: bool = False,
) -> pd.DataFrame:
    """Add scheduling columns to selected repair plan."""
    rows = []
    for _, row in selected.iterrows():
        w = best_window(
            corridor_daily_traffic=float(row["daily_traffic"]),
            junction=int(row.get("nearest_junction", 0)),
            repair_hours=float(row["repair_hours"]),
            traffic_profiles=traffic_profiles,
            is_weekend=is_weekend,
        )
        rows.append({**row.to_dict(), **w})
    return pd.DataFrame(rows)
