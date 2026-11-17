# DATA DICTIONARY

> All data is SIMULATED. Not real-world data.

## datasets/raw/corridors.csv
| Column | Type | Description |
|--------|------|-------------|
| corridor_id | str | Unique corridor identifier (C0000–C0599) |
| lat, lon | float | Centroid coordinates (simulated Chennai bounding box) |
| grid_cell | str | 12×12 grid cell label (A1–L12) |
| ward | int | Ward 0–15 (4×4 blocks of grid cells) |
| road_class | str | arterial / sub_arterial / local |
| daily_traffic | int | Simulated daily PCU count |
| nearest_junction | int | Index of nearest of 6 simulated junctions |
| mobilisation_cost_lakh | float | Fixed cost to open this corridor (lakh INR) |
| corridor_frailty | float | Shared N(0,1) frailty term (ASSUMPTION: within-corridor risk correlation) |
| corridor_vintage_years | float | Shared corridor age factor (ASSUMPTION) |

## datasets/raw/assets.csv
| Column | Type | Description |
|--------|------|-------------|
| asset_id | str | Unique asset identifier (A00000–) |
| corridor_id | str | Parent corridor |
| asset_type | str | road / pipe / streetlight / bridge |
| material | str | Type-specific material |
| road_class | str | Inherited from corridor |
| install_age_years | float | Simulated installation age |
| criticality | int | 1–5 (simulated) |
| repair_hours | float | Estimated repair duration |
| work_cost_lakh | float | Repair work cost (lognormal, simulated) |
| lat, lon | float | Asset location (corridor + tiny jitter) |
| ward | int | Ward 0–15 |
| nearest_junction | int | Nearest traffic junction |
| daily_traffic | int | Inherited from corridor |
| corridor_frailty | float | Shared frailty (ASSUMPTION) |
| corridor_vintage_years | float | Shared vintage (ASSUMPTION) |

## datasets/processed/asset_month_panel.csv
One row per (asset, month). Features used for ML training.

| Column | Description |
|--------|-------------|
| asset_id, corridor_id, month | Identifiers |
| asset_type, material, road_class | Categorical features |
| age_years | Age at this month |
| condition_score | Last inspection condition (noisy, stale) |
| months_since_inspection | Staleness of inspection |
| sensor_reading | Noisy sensor (5% missing → NaN) |
| months_since_repair | Time since last repair |
| previous_failures | Cumulative failure count |
| maintenance_count | Routine maintenance count |
| daily_traffic | Corridor traffic |
| rainfall_mm | Climatological normal (NOT realised rain — no leakage) |
| dma_leak_score | Share of flagged days in 14-day window before month (pipes only) |
| failed_30d | **Label**: 1 if asset failed this month (NEVER used as input feature) |
