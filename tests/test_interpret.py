"""Tests for src/interpret.py: the parametric ML-interpretability module --
shared multivariate RandomForest feeding SHAP (INTERP-04), partial-dependence
plots (INTERP-05), and its own out-of-bag score as the predictive reference
metric (INTERP-06), preceded by a VIF/correlation table (D-05, D-06, D-07).

RF training here is NOT panel-indexed (no (country_code, year) MultiIndex --
unlike src/panel_base.py's fixtures) -- shap_analysis trains a plain
cross-sectional RandomForestRegressor over complete-case rows, mirroring
04-RESEARCH.md's live-verified Pattern 3.

n_jobs=1 is mandatory for REPRO-02 (04-RESEARCH.md Pitfall #2: n_jobs=-1
breaks determinism even with a fixed random_state, live-verified against this
project's pinned scikit-learn==1.9.0).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import interpret

DEP_VAR = "8.1.1"
NUMERIC_PREDICTORS = ["6.4.2", "6.4.1", "8.2.1"]
CAT_PREDICTORS = ["is_ldc", "is_lldc", "is_sids", "region"]
FEATURE_VARS = NUMERIC_PREDICTORS + CAT_PREDICTORS
SEED = 42


def _make_synthetic_ml_fixture(n_rows: int = 50, seed: int = 0) -> pd.DataFrame:
    """A synthetic, non-panel-indexed fixture carrying the RF predictor
    columns used by D-05 (6.4.2, 6.4.1, 8.2.1, is_ldc, is_lldc, is_sids,
    region) plus a dependent column ("8.1.1") with a known linear-ish
    relationship to the numeric predictors -- analogous in spirit to
    tests/test_panel_base.py's ``_make_synthetic_panel`` but WITHOUT
    (country_code, year) panel structure, since RF training here is a plain
    cross-sectional fit (04-RESEARCH.md Pattern 3).

    The three numeric predictors are drawn independently (uncorrelated by
    construction) so compute_vif_table's fixture-level VIFs stay finite and
    close to 1 -- a clean non-collinear case, mirroring the real Phase-2
    finding that these predictors are only weakly correlated globally
    (04-RESEARCH.md Pitfall #5).
    """
    rng = np.random.default_rng(seed)
    regions = ["Africa", "Asia", "Europe", "Americas"]

    water_stress = rng.normal(30, 10, size=n_rows)  # "6.4.2"
    water_efficiency = rng.normal(15, 5, size=n_rows)  # "6.4.1"
    labor_productivity = rng.normal(50, 12, size=n_rows)  # "8.2.1"
    is_ldc = rng.integers(0, 2, size=n_rows)
    is_lldc = rng.integers(0, 2, size=n_rows)
    is_sids = rng.integers(0, 2, size=n_rows)
    region = rng.choice(regions, size=n_rows)

    noise = rng.normal(0, 1, size=n_rows)
    dep_var = (
        0.05 * water_stress
        + 0.10 * water_efficiency
        + 0.20 * labor_productivity
        + noise
    )

    return pd.DataFrame(
        {
            "country_code": [f"C{i:02d}" for i in range(n_rows)],
            "6.4.2": water_stress,
            "6.4.1": water_efficiency,
            "8.2.1": labor_productivity,
            "is_ldc": is_ldc,
            "is_lldc": is_lldc,
            "is_sids": is_sids,
            "region": region,
            DEP_VAR: dep_var,
        }
    )


# --- shap_analysis() ------------------------------------------------------


def test_shap_values_shape():
    """INTERP-04: shap_analysis on a tiny synthetic fixture returns SHAP
    values with shape (n_samples, n_features) matching the one-hot-encoded
    feature matrix X (region is one-hot encoded with drop_first=True, so
    n_features = 3 numeric + 3 binary typology flags + (len(regions)-1))."""
    df = _make_synthetic_ml_fixture(n_rows=50, seed=0)

    rf, shap_values, X, explainer = interpret.shap_analysis(
        df, DEP_VAR, FEATURE_VARS, seed=SEED
    )

    assert shap_values.shape == X.shape
    assert shap_values.shape[0] == len(X)
    assert shap_values.shape[1] == X.shape[1]


def test_oob_score_present():
    """INTERP-06 (D-07): the trained RF exposes oob_score_ as a real float
    (not NaN/None) -- the shared predictive-reference metric, no separate
    GBM/train-test split needed."""
    df = _make_synthetic_ml_fixture(n_rows=50, seed=0)

    rf, _, _, _ = interpret.shap_analysis(df, DEP_VAR, FEATURE_VARS, seed=SEED)

    assert rf.oob_score_ is not None
    assert isinstance(rf.oob_score_, float)
    assert not np.isnan(rf.oob_score_)


def test_rf_determinism():
    """REPRO-02 (04-RESEARCH.md Pitfall #2): fitting the RF twice with the
    same seed and n_jobs=1 on the same fixture gives identical
    feature_importances_ -- directly guards against the n_jobs=-1
    non-determinism bug, live-verified against this project's pinned
    scikit-learn==1.9.0."""
    df = _make_synthetic_ml_fixture(n_rows=50, seed=0)

    rf1, _, _, _ = interpret.shap_analysis(df, DEP_VAR, FEATURE_VARS, seed=SEED)
    rf2, _, _, _ = interpret.shap_analysis(df, DEP_VAR, FEATURE_VARS, seed=SEED)

    assert np.array_equal(rf1.feature_importances_, rf2.feature_importances_)
    assert rf1.oob_score_ == rf2.oob_score_


# --- compute_vif_table() ---------------------------------------------------


def test_vif_table():
    """INTERP-04: compute_vif_table returns a table with one VIF row per
    numeric predictor, all finite for a non-collinear fixture (the three
    numeric predictors are drawn independently by construction -- see
    _make_synthetic_ml_fixture docstring)."""
    df = _make_synthetic_ml_fixture(n_rows=50, seed=0)

    vif_table = interpret.compute_vif_table(df, NUMERIC_PREDICTORS)

    assert len(vif_table) == len(NUMERIC_PREDICTORS)
    assert set(vif_table["variable"]) == set(NUMERIC_PREDICTORS)
    assert np.isfinite(vif_table["VIF"]).all()
