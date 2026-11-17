from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN


def cluster_high_risk_assets(
    snapshot: pd.DataFrame,
    risk_threshold: float = 0.15,
    eps_km: float = 4.0,
    min_samples: int = 2,
) -> pd.DataFrame:
    """DBSCAN cluster high-risk assets by geography. This is for coordination analysis only."""
    df = snapshot[snapshot["risk_score"] >= risk_threshold].copy()
    if df.empty:
        return pd.DataFrame(columns=["cluster_id", "asset_id", "lat", "lon", "risk_score"])
    coords = df[["lat", "lon"]].values.astype(float)
    km_lat = 111.0
    km_lon = 111.0 * np.cos(np.deg2rad(df["lat"].mean()))
    eps = eps_km / max(km_lat, 1e-3)
    scan = DBSCAN(eps=eps, min_samples=min_samples)
    labels = scan.fit_predict(coords)
    df["cluster_id"] = labels
    return df[["asset_id", "corridor_id", "lat", "lon", "risk_score", "cluster_id"]]


def cluster_incidents(
    records: pd.DataFrame,
    eps_km: float = 8.0,
    min_samples: int = 2,
) -> pd.DataFrame:
    """Group incident/leak hotspots into spatial clusters."""
    if records.empty:
        return records.copy()
    coords = records[["lat", "lon"]].values.astype(float)
    lat_scale = 111.0
    lon_scale = 111.0 * np.cos(np.deg2rad(records["lat"].mean()))
    eps = eps_km / max(lat_scale, 1e-3)
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(coords)
    out = records.copy()
    out["cluster_id"] = labels
    return out
