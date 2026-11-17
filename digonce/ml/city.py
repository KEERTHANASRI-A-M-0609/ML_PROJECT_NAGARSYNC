"""
ml/city.py — Simulated Tamil Nadu state infrastructure: corridors, assets, dynamics.

Corridors are clustered around district hubs across the full TN bounding box
(not Chennai-only). ASSUMPTION: shared corridor frailty + vintage age factor
correlate failure risk within a street segment.

All data is SIMULATED.
"""
from __future__ import annotations

import string
import numpy as np
import pandas as pd
from scipy.special import expit   # sigmoid

from ml.config import (
    SEED, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX,
    GRID_ROWS, GRID_COLS, DISTRICTS, N_DISTRICTS,
    N_CORRIDORS, N_JUNCTIONS, MOBILISATION, WORK_COST,
    HISTORY_MONTHS, SIM_MONTHS, TOTAL_MONTHS, TARGET_FAILURE_RATE,
)

# ── Tamil Nadu rainfall normals (mm) — statewide blend ─────────────────────
# NE monsoon peak Oct–Dec; SW monsoon Jun–Sep inland; dry Jan–May
RAINFALL_NORMALS = np.array([
    20, 12, 18, 35, 55, 70, 95, 110, 120, 190, 195, 80
], dtype=float)   # Jan–Dec


# ──────────────────────────────────────────────────────────────────────────
# Grid helpers
# ──────────────────────────────────────────────────────────────────────────

def _grid_cell(row: int, col: int) -> str:
    """Return grid cell label like 'A1', 'L12'."""
    letter = string.ascii_uppercase[row % 26]
    if row >= 26:
        letter = f"A{letter}"
    return f"{letter}{col + 1}"


# ──────────────────────────────────────────────────────────────────────────
# Corridor generation — statewide district hubs
# ──────────────────────────────────────────────────────────────────────────

def generate_corridors(rng: np.random.Generator) -> pd.DataFrame:
    """Generate ~N_CORRIDORS corridors clustered around TN district capitals."""
    weights = np.array([d[3] for d in DISTRICTS], dtype=float)
    weights /= weights.sum()
    district_ids = rng.choice(N_DISTRICTS, size=N_CORRIDORS, p=weights)

    # Hub-centred jitter (larger spread for state-scale cities)
    hub_sigma = 0.085
    lats = np.empty(N_CORRIDORS)
    lons = np.empty(N_CORRIDORS)
    for i, did in enumerate(district_ids):
        _, hlat, hlon, _ = DISTRICTS[int(did)]
        lats[i] = float(np.clip(rng.normal(hlat, hub_sigma), LAT_MIN, LAT_MAX))
        lons[i] = float(np.clip(rng.normal(hlon, hub_sigma), LON_MIN, LON_MAX))

    lat_step = (LAT_MAX - LAT_MIN) / GRID_ROWS
    lon_step = (LON_MAX - LON_MIN) / GRID_COLS
    rows_idx = ((lats - LAT_MIN) / lat_step).astype(int).clip(0, GRID_ROWS - 1)
    cols_idx = ((lons - LON_MIN) / lon_step).astype(int).clip(0, GRID_COLS - 1)
    grid_cells = [_grid_cell(r, c) for r, c in zip(rows_idx, cols_idx)]

    # Road class denser near each district hub
    road_class = []
    daily_traffic = []
    for i, did in enumerate(district_ids):
        _, hlat, hlon, _ = DISTRICTS[int(did)]
        dist = np.sqrt((lats[i] - hlat) ** 2 + (lons[i] - hlon) ** 2)
        rc = "arterial" if dist < 0.04 else ("sub_arterial" if dist < 0.09 else "local")
        road_class.append(rc)
        base = {"arterial": 35_000, "sub_arterial": 15_000, "local": 5_000}[rc]
        daily_traffic.append(int(base * rng.lognormal(0, 0.2)))

    # Junctions spread across TN (4×3 grid)
    j_lats = np.linspace(LAT_MIN + 0.4, LAT_MAX - 0.4, 4)
    j_lons = np.linspace(LON_MIN + 0.4, LON_MAX - 0.4, 3)
    jlat_grid, jlon_grid = np.meshgrid(j_lats, j_lons, indexing="ij")
    j_coords = np.column_stack([jlat_grid.ravel(), jlon_grid.ravel()])[:N_JUNCTIONS]

    dists_to_j = np.sqrt(
        (lats[:, None] - j_coords[:, 0]) ** 2 +
        (lons[:, None] - j_coords[:, 1]) ** 2
    )
    nearest_junction = dists_to_j.argmin(axis=1)

    mob_cost = np.array([MOBILISATION[rc] for rc in road_class])
    corridor_frailty = rng.normal(0, 1, N_CORRIDORS)
    corridor_vintage = rng.uniform(0, 40, N_CORRIDORS)
    district_names = [DISTRICTS[int(d)][0] for d in district_ids]

    return pd.DataFrame({
        "corridor_id": [f"C{i:04d}" for i in range(N_CORRIDORS)],
        "lat": lats,
        "lon": lons,
        "grid_cell": grid_cells,
        "ward": district_ids.astype(int),          # district id (compat)
        "district": district_names,
        "road_class": road_class,
        "daily_traffic": daily_traffic,
        "nearest_junction": nearest_junction,
        "mobilisation_cost_lakh": mob_cost,
        "corridor_frailty": corridor_frailty,
        "corridor_vintage_years": corridor_vintage,
    })


# ──────────────────────────────────────────────────────────────────────────
# Asset generation
# ──────────────────────────────────────────────────────────────────────────

def _work_cost(asset_type: str, road_class: str, rng: np.random.Generator) -> float:
    key = f"{asset_type}_{road_class}" if asset_type == "road" else asset_type
    base, sigma = WORK_COST.get(key, WORK_COST["pipe"])
    return float(np.exp(np.log(base) + rng.normal(0, sigma)))


def generate_assets(corridors: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Generate ~2000 assets across corridors."""
    records = []
    asset_idx = 0

    pipe_materials = ["cast_iron", "ductile_iron", "pvc", "asbestos_cement"]
    road_materials = ["bitumen", "concrete", "gravel"]
    sl_materials = ["sodium_vapour", "led", "metal_halide"]

    for _, cor in corridors.iterrows():
        rc = cor["road_class"]

        # Road (always 1)
        records.append(_asset_record(
            asset_idx, cor, "road", rc,
            rng.choice(road_materials), rng, rc
        ))
        asset_idx += 1

        # Pipes: 0–2
        for _ in range(rng.integers(0, 3)):
            records.append(_asset_record(
                asset_idx, cor, "pipe", rc,
                rng.choice(pipe_materials), rng, rc
            ))
            asset_idx += 1

        # Streetlights: 0–2
        for _ in range(rng.integers(0, 3)):
            records.append(_asset_record(
                asset_idx, cor, "streetlight", rc,
                rng.choice(sl_materials), rng, rc
            ))
            asset_idx += 1

        # Bridge: ~5% of corridors
        if rng.random() < 0.05:
            records.append(_asset_record(
                asset_idx, cor, "bridge", rc,
                "reinforced_concrete", rng, rc
            ))
            asset_idx += 1

    return pd.DataFrame(records)


def _asset_record(
    idx: int, cor: pd.Series, asset_type: str,
    road_class: str, material: str,
    rng: np.random.Generator, rc: str
) -> dict:
    install_age = float(rng.uniform(1, 40))
    criticality = int(rng.integers(1, 6))
    repair_hours = {
        "road": rng.uniform(8, 48),
        "pipe": rng.uniform(6, 24),
        "streetlight": rng.uniform(2, 8),
        "bridge": rng.uniform(24, 120),
    }[asset_type]

    return {
        "asset_id": f"A{idx:05d}",
        "corridor_id": cor["corridor_id"],
        "asset_type": asset_type,
        "material": material,
        "road_class": rc,
        "install_age_years": round(install_age, 1),
        "criticality": criticality,
        "repair_hours": round(repair_hours, 1),
        "work_cost_lakh": round(_work_cost(asset_type, rc, rng), 3),
        "lat": cor["lat"] + rng.uniform(-0.001, 0.001),
        "lon": cor["lon"] + rng.uniform(-0.001, 0.001),
        "ward": cor["ward"],
        "nearest_junction": cor["nearest_junction"],
        "daily_traffic": cor["daily_traffic"],
        "corridor_frailty": cor["corridor_frailty"],
        "corridor_vintage_years": cor["corridor_vintage_years"],
    }


# ──────────────────────────────────────────────────────────────────────────
# Monthly dynamics
# ──────────────────────────────────────────────────────────────────────────

# Type-specific deterioration rates (condition units / month)
DETR_RATE = {"road": 0.012, "pipe": 0.008, "streetlight": 0.006, "bridge": 0.004}

# Hazard intercepts per type (calibrated to ~2.5% mean failure rate)
HAZARD_INTERCEPT = {"road": -4.2, "pipe": -4.5, "streetlight": -5.0, "bridge": -5.5}


def _realised_rainfall(month_idx: int, rng: np.random.Generator) -> float:
    """Realised rainfall = normal + noise (mm)."""
    normal = RAINFALL_NORMALS[month_idx % 12]
    return max(0.0, normal + rng.normal(0, normal * 0.3))


def simulate_city(
    assets: pd.DataFrame,
    corridors: pd.DataFrame,
    rng: np.random.Generator,
    leak_scores: dict[tuple[int, int], float] | None = None,
) -> pd.DataFrame:
    """
    Simulate TOTAL_MONTHS months of asset dynamics.
    Returns asset-month panel with features and failed_30d label.
    leak_scores: {(ward, month_idx): score} — injected after leak detection.
    """
    n = len(assets)
    records = []

    # Mutable state arrays
    condition = rng.uniform(0.4, 1.0, n).astype(float)
    age = assets["install_age_years"].values.copy().astype(float)
    prev_failures = np.zeros(n, dtype=int)
    maint_count = np.zeros(n, dtype=int)
    months_since_repair = rng.integers(1, 24, n).astype(float)
    months_since_insp = rng.integers(1, 12, n).astype(float)
    last_insp_condition = condition.copy()

    asset_frailty = rng.normal(0, 0.5, n)
    cor_frailty = assets["corridor_frailty"].values
    cor_vintage = assets["corridor_vintage_years"].values
    asset_type = assets["asset_type"].values
    traffic = assets["daily_traffic"].values.astype(float)
    ward = assets["ward"].values.astype(int)

    for m in range(TOTAL_MONTHS):
        rain = _realised_rainfall(m, rng)
        rain_normal = RAINFALL_NORMALS[m % 12]

        # Deterioration
        detr = np.array([DETR_RATE[t] for t in asset_type])
        traffic_effect = np.where(
            np.isin(asset_type, ["road", "bridge"]),
            traffic / 50_000 * 0.005, 0.0
        )
        rain_effect = rain / 200 * 0.003
        condition -= detr + traffic_effect + rain_effect
        condition = condition.clip(0.0, 1.0)
        age += 1 / 12

        # Failure hazard
        intercept = np.array([HAZARD_INTERCEPT[t] for t in asset_type])
        logit = (
            intercept
            + 0.3 * (1 - condition)
            + 0.02 * age
            + np.where(np.isin(asset_type, ["road", "bridge"]), traffic / 50_000, 0.0)
            + 0.5 * (rain / 200)
            + 0.15 * prev_failures.clip(0, 5)
            + 0.3 * asset_frailty
            + 0.2 * cor_frailty
            + 0.01 * cor_vintage
        )

        # Water-leak boost for pipes
        if leak_scores:
            for i, (w, at) in enumerate(zip(ward, asset_type)):
                if at == "pipe":
                    logit[i] += 1.5 * leak_scores.get((int(w), m), 0.0)

        prob = expit(logit)
        failed = rng.random(n) < prob

        # Routine maintenance (~1%/month)
        maintained = (~failed) & (rng.random(n) < 0.01)

        # Stale/noisy inspection (update ~20% of assets per month)
        inspected = rng.random(n) < 0.20
        last_insp_condition = np.where(
            inspected, condition + rng.normal(0, 0.05, n), last_insp_condition
        ).clip(0, 1)
        months_since_insp = np.where(inspected, 0.0, months_since_insp + 1)

        # Sensor reading (5% missing → NaN)
        sensor = condition + rng.normal(0, 0.03, n)
        sensor = np.where(rng.random(n) < 0.05, np.nan, sensor)

        # Leak score feature (pipes only, uses climatological normal for features)
        dma_leak_feat = np.zeros(n)
        if leak_scores:
            for i, (w, at) in enumerate(zip(ward, asset_type)):
                if at == "pipe":
                    dma_leak_feat[i] = leak_scores.get((int(w), m), 0.0)

        # Record features BEFORE applying repairs
        for i in range(n):
            records.append({
                "asset_id": assets.iloc[i]["asset_id"],
                "corridor_id": assets.iloc[i]["corridor_id"],
                "month": m,
                "asset_type": asset_type[i],
                "material": assets.iloc[i]["material"],
                "road_class": assets.iloc[i]["road_class"],
                "age_years": round(float(age[i]), 2),
                "condition_score": round(float(last_insp_condition[i]), 4),
                "months_since_inspection": round(float(months_since_insp[i]), 1),
                "sensor_reading": round(float(sensor[i]), 4) if not np.isnan(sensor[i]) else None,
                "months_since_repair": round(float(months_since_repair[i]), 1),
                "previous_failures": int(prev_failures[i]),
                "maintenance_count": int(maint_count[i]),
                "daily_traffic": int(traffic[i]),
                "rainfall_mm": round(float(rain_normal), 1),   # climatological normal
                "dma_leak_score": round(float(dma_leak_feat[i]), 4),
                "ward": int(ward[i]),
                "criticality": int(assets.iloc[i]["criticality"]),
                "work_cost_lakh": float(assets.iloc[i]["work_cost_lakh"]),
                "mobilisation_cost_lakh": float(corridors.loc[
                    corridors["corridor_id"] == assets.iloc[i]["corridor_id"],
                    "mobilisation_cost_lakh"
                ].iloc[0]),
                "repair_hours": float(assets.iloc[i]["repair_hours"]),
                "failed_30d": int(failed[i]),
            })

        # Apply reactive repairs for failed assets
        condition[failed] = rng.uniform(0.7, 1.0, failed.sum())
        prev_failures[failed] += 1
        months_since_repair[failed] = 0
        months_since_repair[~failed] += 1

        # Apply maintenance
        condition[maintained] = (condition[maintained] + 0.1).clip(0, 1)
        maint_count[maintained] += 1

    return pd.DataFrame(records)
