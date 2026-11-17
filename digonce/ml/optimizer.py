"""
ml/optimizer.py — Five repair-selection strategies.

Cost model (fixed-charge):
  Coordinated: pay M_c once per corridor + sum of work costs.
  Uncoordinated: pay M_c for EVERY asset (separate departments).

benefit_i = calibrated_risk_i * criticality_i
"""
from __future__ import annotations

import os
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds

from ml.config import ILP_TIME_LIMIT, ILP_MIP_GAP, ILP_MAX_CANDIDATES


def _benefit(df: pd.DataFrame) -> np.ndarray:
    return df["risk_score"].values * df["criticality"].values


def oldest_first(snapshot: pd.DataFrame, budget: float) -> pd.DataFrame:
    """Uncoordinated: sort by age descending, each asset pays its own mobilisation."""
    df = snapshot.sort_values("age_years", ascending=False).copy()
    df["total_cost"] = df["work_cost_lakh"] + df["mobilisation_cost_lakh"]
    return _greedy_uncoordinated(df, budget)


def risk_first(snapshot: pd.DataFrame, budget: float) -> pd.DataFrame:
    """Uncoordinated: sort by risk descending."""
    df = snapshot.sort_values("risk_score", ascending=False).copy()
    df["total_cost"] = df["work_cost_lakh"] + df["mobilisation_cost_lakh"]
    return _greedy_uncoordinated(df, budget)


def ml_per_rupee(snapshot: pd.DataFrame, budget: float) -> pd.DataFrame:
    """Uncoordinated: sort by benefit/(work+M) descending."""
    df = snapshot.copy()
    df["total_cost"] = df["work_cost_lakh"] + df["mobilisation_cost_lakh"]
    df["ratio"] = _benefit(df) / df["total_cost"].clip(lower=0.01)
    df = df.sort_values("ratio", ascending=False)
    return _greedy_uncoordinated(df, budget)


def _greedy_uncoordinated(df: pd.DataFrame, budget: float) -> pd.DataFrame:
    selected, spent = [], 0.0
    for _, row in df.iterrows():
        cost = row["work_cost_lakh"] + row["mobilisation_cost_lakh"]
        if spent + cost <= budget:
            selected.append(row["asset_id"])
            spent += cost
    return df[df["asset_id"].isin(selected)]


def greedy_coordinated(snapshot: pd.DataFrame, budget: float) -> pd.DataFrame:
    """
    Coordinated greedy: once a corridor is open, subsequent assets in it
    pay only work cost (no extra mobilisation).
    """
    df = snapshot.copy()
    df["benefit"] = _benefit(df)
    open_corridors: set[str] = set()
    selected_ids: list[str] = []
    spent = 0.0

    # Sort by marginal benefit/cost
    def marginal_cost(row: pd.Series) -> float:
        if row["corridor_id"] in open_corridors:
            return row["work_cost_lakh"]
        return row["work_cost_lakh"] + row["mobilisation_cost_lakh"]

    # Iterative greedy (re-sort each pass is expensive; use one-pass approximation)
    df["init_cost"] = df.apply(marginal_cost, axis=1)
    df["ratio"] = df["benefit"] / df["init_cost"].clip(lower=0.01)
    df = df.sort_values("ratio", ascending=False)

    for _, row in df.iterrows():
        cost = marginal_cost(row)
        if spent + cost <= budget:
            selected_ids.append(row["asset_id"])
            open_corridors.add(row["corridor_id"])
            spent += cost

    return df[df["asset_id"].isin(selected_ids)]


def digonce_ilp(
    snapshot: pd.DataFrame,
    budget: float,
    min_ward_share: float = 0.0,
) -> pd.DataFrame:
    """
    ILP: binary x_i per asset, binary y_c per corridor.
    Maximise sum b_i x_i
    s.t. sum w_i x_i + sum M_c y_c <= budget
         x_i <= y_c(i)  for all i
         optional per-ward minimum spend
    Falls back to greedy_coordinated on solver failure.
    """
    df = snapshot.copy()
    df["benefit"] = _benefit(df)

    # Prune candidates
    df["ratio_w"] = df["benefit"] / (df["work_cost_lakh"] + df["mobilisation_cost_lakh"]).clip(0.01)
    df["ratio_wonly"] = df["benefit"] / df["work_cost_lakh"].clip(0.01)
    top_w = df.nlargest(ILP_MAX_CANDIDATES, "ratio_w")["asset_id"]
    top_wo = df.nlargest(ILP_MAX_CANDIDATES, "ratio_wonly")["asset_id"]
    candidates = df[df["asset_id"].isin(set(top_w) | set(top_wo))].copy().reset_index(drop=True)

    if len(candidates) == 0:
        return greedy_coordinated(snapshot, budget)

    corridors = candidates["corridor_id"].unique()
    cor_idx = {c: i for i, c in enumerate(corridors)}
    n_assets = len(candidates)
    n_cors = len(corridors)
    n_vars = n_assets + n_cors   # [x_0..x_{n-1}, y_0..y_{m-1}]

    # Objective: maximise benefit → minimise -benefit
    c_obj = np.concatenate([-candidates["benefit"].values, np.zeros(n_cors)])

    # Budget constraint: sum w_i x_i + sum M_c y_c <= budget
    mob_per_cor = (
        candidates.groupby("corridor_id")["mobilisation_cost_lakh"].first()
        .reindex(corridors).values
    )
    budget_row = np.concatenate([
        candidates["work_cost_lakh"].values,
        mob_per_cor,
    ])

    # x_i <= y_c(i): x_i - y_c(i) <= 0
    link_rows = []
    for i, row in candidates.iterrows():
        r = np.zeros(n_vars)
        r[i] = 1.0
        r[n_assets + cor_idx[row["corridor_id"]]] = -1.0
        link_rows.append(r)

    A_rows = [budget_row] + link_rows
    b_lo = np.concatenate([[-np.inf], np.full(n_assets, -np.inf)])
    b_up = np.concatenate([[budget], np.zeros(n_assets)])

    # Ward equity constraints (optional)
    if min_ward_share > 0:
        wards = candidates["ward"].unique()
        equal_share = budget / max(len(wards), 1)
        min_spend = min_ward_share * equal_share
        for w in wards:
            mask = candidates["ward"] == w
            r = np.zeros(n_vars)
            r[:n_assets][mask.values] = candidates.loc[mask, "work_cost_lakh"].values
            # Add mobilisation for corridors in this ward
            ward_cors = candidates.loc[mask, "corridor_id"].unique()
            for wc in ward_cors:
                r[n_assets + cor_idx[wc]] = mob_per_cor[cor_idx[wc]]
            A_rows.append(r)
            b_lo = np.append(b_lo, min_spend)
            b_up = np.append(b_up, np.inf)

    A = np.array(A_rows)
    constraints = LinearConstraint(A, b_lo, b_up)
    integrality = np.ones(n_vars)   # all binary
    bounds = Bounds(lb=0, ub=1)

    try:
        solver_options = {"time_limit": ILP_TIME_LIMIT, "mip_rel_gap": ILP_MIP_GAP}
        if os.name == "nt":
            # Avoid HiGHS worker-thread teardown crashes on Windows.
            solver_options["threads"] = 1
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"Unrecognized options detected: \{'threads'\}.*",
                    category=RuntimeWarning,
                )
                result = milp(
                    c_obj,
                    constraints=constraints,
                    integrality=integrality,
                    bounds=bounds,
                    options=solver_options,
                )
        else:
            result = milp(
                c_obj,
                constraints=constraints,
                integrality=integrality,
                bounds=bounds,
                options=solver_options,
            )
        if result.success or (result.status in (0, 3)):
            x = result.x[:n_assets]
            selected_ids = candidates.loc[x > 0.5, "asset_id"].tolist()
            if selected_ids:
                return snapshot[snapshot["asset_id"].isin(selected_ids)]
    except Exception:
        pass

    # Fallback
    return greedy_coordinated(snapshot, budget)


STRATEGIES = {
    "oldest_first": oldest_first,
    "risk_first": risk_first,
    "ml_per_rupee": ml_per_rupee,
    "greedy_coordinated": greedy_coordinated,
    "digonce_ilp": digonce_ilp,
}


def compute_plan_cost(selected: pd.DataFrame, coordinated: bool = True) -> float:
    """Compute total cost of a repair plan."""
    if len(selected) == 0:
        return 0.0
    if coordinated:
        mob = selected.groupby("corridor_id")["mobilisation_cost_lakh"].first().sum()
        return float(selected["work_cost_lakh"].sum() + mob)
    return float((selected["work_cost_lakh"] + selected["mobilisation_cost_lakh"]).sum())


def joint_repair_duration(hours: np.ndarray) -> float:
    """Joint repair = max(hours) + 0.25 * sum(rest)."""
    if len(hours) == 0:
        return 0.0
    h = np.sort(hours)[::-1]
    return float(h[0] + 0.25 * h[1:].sum())
