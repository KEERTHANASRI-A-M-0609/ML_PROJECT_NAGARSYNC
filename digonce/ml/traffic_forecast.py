from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

try:
    from xgboost import XGBRegressor
except Exception:  # pragma: no cover
    XGBRegressor = None


def _historical_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["junction", "day", "hour"]).copy()
    out["weekday"] = out["dow"]
    out["weekend"] = out["is_weekend"].astype(int)
    out["rainfall"] = out["rain_mm"].fillna(0.0)
    out["road_capacity"] = out["junction"].map({j: 1000 + j * 100 for j in range(int(out["junction"].max()) + 1)})
    out["incidents"] = out["is_event"].astype(int)
    out["construction"] = 0
    out["nearby_events"] = out["is_holiday"].astype(int)
    out["lag_1h"] = out.groupby("junction")["count"].shift(1)
    out["lag_6h"] = out.groupby("junction")["count"].shift(6)
    out["lag_24h"] = out.groupby("junction")["count"].shift(24)
    return out.dropna(subset=["lag_1h", "lag_6h", "lag_24h"]).reset_index(drop=True)


def train_traffic_forecast_model(traffic_df: pd.DataFrame, horizon_hours: int = 1) -> tuple[Any, dict[str, Any]]:
    df = _historical_features(traffic_df)
    target = "count"
    feature_cols = [
        "lag_1h", "lag_6h", "lag_24h",
        "hour", "weekday", "weekend",
        "rainfall", "road_capacity", "incidents",
        "construction", "nearby_events",
    ]
    train_mask = df["month"] < 24
    X_train = df.loc[train_mask, feature_cols]
    y_train = df.loc[train_mask, target]
    X_test = df.loc[~train_mask, feature_cols]
    y_test = df.loc[~train_mask, target]

    if XGBRegressor is not None:
        model = XGBRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=6,
            random_state=42,
            objective="reg:squarederror",
            n_jobs=1,
        )
        model.fit(X_train, y_train)
    else:
        from sklearn.ensemble import HistGradientBoostingRegressor
        model = HistGradientBoostingRegressor(random_state=42)
        model.fit(X_train, y_train)

    pred = model.predict(X_test)
    mae = float(np.mean(np.abs(y_test - pred)))
    rmse = float(np.sqrt(np.mean((y_test - pred) ** 2)))
    mape = float(np.mean(np.abs((y_test - pred) / np.clip(y_test, 1e-6, None)))) * 100.0
    metrics = {
        "horizon_hours": horizon_hours,
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 4),
        "model_name": model.__class__.__name__,
    }
    return model, metrics
