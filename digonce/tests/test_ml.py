"""
tests/test_ml.py — ML unit tests.
"""
import numpy as np
import pandas as pd
import pytest
import joblib

from ml.config import SEED, DATA_RAW, DATA_PROC, MODELS_DIR, ANNUAL_BUDGET_FRACTION
from ml.city import generate_corridors, generate_assets
from ml.optimizer import (
    oldest_first, risk_first, ml_per_rupee,
    greedy_coordinated, digonce_ilp, compute_plan_cost,
)


@pytest.fixture(scope="module")
def rng():
    return np.random.default_rng(SEED)


@pytest.fixture(scope="module")
def corridors(rng):
    return generate_corridors(rng)


@pytest.fixture(scope="module")
def assets(corridors, rng):
    a = generate_assets(corridors, rng)
    mob_map = corridors.set_index("corridor_id")["mobilisation_cost_lakh"]
    a["mobilisation_cost_lakh"] = a["corridor_id"].map(mob_map)
    return a


@pytest.fixture(scope="module")
def snapshot():
    """Load the processed snapshot with risk scores."""
    snap = pd.read_csv(DATA_PROC / "current_snapshot.csv")
    risk_model = joblib.load(MODELS_DIR / "risk_model.joblib")
    corridors = pd.read_csv(DATA_RAW / "corridors.csv")
    mob_map = corridors.set_index("corridor_id")["mobilisation_cost_lakh"]
    snap["mobilisation_cost_lakh"] = snap["corridor_id"].map(mob_map)

    from ml.risk_model import _encode
    df_enc = _encode(snap)
    feat_cols = risk_model.feature_cols
    X = df_enc[feat_cols].fillna(df_enc[feat_cols].median()).values
    snap["risk_score"] = risk_model.predict_proba(X)
    return snap


# ── Determinism ───────────────────────────────────────────────────────────

def test_city_generation_deterministic():
    rng1 = np.random.default_rng(SEED)
    rng2 = np.random.default_rng(SEED)
    c1 = generate_corridors(rng1)
    c2 = generate_corridors(rng2)
    pd.testing.assert_frame_equal(c1, c2)


# ── No label leakage ──────────────────────────────────────────────────────

def test_no_label_leakage_in_features():
    """failed_30d must not appear in FEATURE_COLS."""
    from ml.risk_model import FEATURE_COLS
    assert "failed_30d" not in FEATURE_COLS
    assert "risk_score" not in FEATURE_COLS


# ── Optimiser budget constraint ───────────────────────────────────────────

@pytest.mark.parametrize("strategy_fn", [oldest_first, risk_first, ml_per_rupee])
def test_uncoordinated_never_exceeds_budget(snapshot, strategy_fn):
    budget = 1000.0
    selected = strategy_fn(snapshot, budget)
    if len(selected) == 0:
        return
    cost = compute_plan_cost(selected, coordinated=False)
    assert cost <= budget + 1e-6, f"Cost {cost} exceeds budget {budget}"


def test_greedy_coordinated_never_exceeds_budget(snapshot):
    budget = 1000.0
    selected = greedy_coordinated(snapshot, budget)
    if len(selected) == 0:
        return
    cost = compute_plan_cost(selected, coordinated=True)
    assert cost <= budget + 1e-6


def test_ilp_never_exceeds_budget(snapshot):
    budget = 1000.0
    selected = digonce_ilp(snapshot, budget)
    if len(selected) == 0:
        return
    cost = compute_plan_cost(selected, coordinated=True)
    assert cost <= budget + 1e-6


# ── ILP benefit >= greedy >= ml_per_rupee when mobilisation > 0 ──────────

def test_ilp_benefit_ordering(snapshot):
    """ILP benefit >= greedy_coordinated >= ml_per_rupee at same budget (mob > 0)."""
    budget = 2000.0
    snap = snapshot.copy()
    # Ensure mobilisation > 0
    assert snap["mobilisation_cost_lakh"].mean() > 0

    sel_ilp = digonce_ilp(snap, budget)
    sel_gc = greedy_coordinated(snap, budget)
    sel_mlpr = ml_per_rupee(snap, budget)

    ben_ilp = float(sel_ilp["risk_score"].sum()) if len(sel_ilp) > 0 else 0
    ben_gc = float(sel_gc["risk_score"].sum()) if len(sel_gc) > 0 else 0
    ben_mlpr = float(sel_mlpr["risk_score"].sum()) if len(sel_mlpr) > 0 else 0

    # ILP should be >= greedy (allow small tolerance for ILP gap)
    assert ben_ilp >= ben_gc - 0.5, f"ILP {ben_ilp:.3f} < greedy {ben_gc:.3f}"
    # Greedy coordinated should be >= uncoordinated (or equal)
    assert ben_gc >= ben_mlpr - 0.5, f"Greedy {ben_gc:.3f} < mlpr {ben_mlpr:.3f}"


def test_zero_mobilisation_no_extra_saving(snapshot):
    """With zero mobilisation cost, coordination gives no extra saving."""
    budget = 2000.0
    snap = snapshot.copy()
    snap["mobilisation_cost_lakh"] = 0.0

    sel_gc = greedy_coordinated(snap, budget)
    sel_mlpr = ml_per_rupee(snap, budget)

    ben_gc = float(sel_gc["risk_score"].sum()) if len(sel_gc) > 0 else 0
    ben_mlpr = float(sel_mlpr["risk_score"].sum()) if len(sel_mlpr) > 0 else 0

    # With zero mob cost, both should select similar assets (within tolerance)
    assert abs(ben_gc - ben_mlpr) < ben_mlpr * 0.05 + 0.1, \
        f"Zero mob: gc={ben_gc:.3f} mlpr={ben_mlpr:.3f} differ too much"


# ── Calibration ECE ───────────────────────────────────────────────────────

def test_calibrated_ece_le_raw():
    metrics = joblib.load(MODELS_DIR / "risk_model.joblib")
    import json
    with open(MODELS_DIR / "model_metrics.json") as f:
        m = json.load(f)
    raw_ece = m["risk_model"]["raw"]["ece"]
    cal_ece = m["risk_model"]["calibrated"]["ece"]
    assert cal_ece <= raw_ece + 0.005, f"Calibrated ECE {cal_ece} > raw ECE {raw_ece}"
