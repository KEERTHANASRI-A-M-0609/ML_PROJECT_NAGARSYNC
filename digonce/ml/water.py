"""
ml/water.py — Simulated daily MNF and pressure for TN district DMAs.

All data is SIMULATED.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.config import TOTAL_MONTHS, N_DMAS
from ml.city import RAINFALL_NORMALS


def generate_water_data(rng: np.random.Generator, n_dmas: int | None = None) -> pd.DataFrame:
    """
    Generate daily MNF (L/s) and pressure (bar) for each DMA (one per district).
    Leak events: ~1 per 300 days per DMA, duration 10–50 days,
    +10–30% extra flow, -0.05–0.15 bar pressure drop.
    """
    if n_dmas is None:
        n_dmas = N_DMAS
    total_days = TOTAL_MONTHS * 30   # approximate
    records = []

    for dma in range(n_dmas):
        base_mnf = rng.uniform(80, 200)       # L/s baseline
        base_pressure = rng.uniform(2.5, 4.5) # bar

        # Seasonal MNF variation (higher in summer)
        day_idx = np.arange(total_days)
        month_idx = (day_idx // 30) % 12
        seasonal = 1.0 + 0.15 * np.sin(2 * np.pi * (month_idx - 3) / 12)

        mnf = base_mnf * seasonal * rng.lognormal(0, 0.05, total_days)
        pressure = base_pressure * (1.0 - 0.05 * (seasonal - 1.0)) + rng.normal(0, 0.05, total_days)

        # Inject leak events
        n_leaks = max(1, total_days // 300)
        leak_flag = np.zeros(total_days, dtype=int)
        for _ in range(n_leaks):
            start = int(rng.integers(0, max(1, total_days - 50)))
            dur = int(rng.integers(10, 51))
            end = min(total_days, start + dur)
            leak_flag[start:end] = 1
            mnf[start:end] *= 1.0 + rng.uniform(0.10, 0.30)
            pressure[start:end] -= rng.uniform(0.05, 0.15)

        for d in range(total_days):
            records.append({
                "dma": dma,
                "day": d,
                "month": d // 30,
                "mnf_ls": round(float(mnf[d]), 2),
                "pressure_bar": round(float(pressure[d]), 3),
                "leak_flag": int(leak_flag[d]),
                "rainfall_mm": float(RAINFALL_NORMALS[month_idx[d]] / 30.0),
            })

    return pd.DataFrame(records)
