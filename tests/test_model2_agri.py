"""Tests for src/model2_agri.py: deterministic bookkeeping only (no live DB
needed for these) -- MODEL2-01, MODEL2-02.

Mirrors tests/test_panel_base.py's synthetic-sparse-panel construction style
(_make_sparse_panel), but uses the REAL Model 2 column names (2.3.1 / 6.4.2)
so build_coverage_table/build_model2_panel are exercised against their real
column contract (D-01, 06-CONTEXT.md).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from linearmodels.panel.results import PanelEffectsResults

from src import db, model2_agri

DEP_VAR = model2_agri.DEP_VAR
INDEP_VAR = model2_agri.INDEP_VAR


def _make_sparse_m2_panel(year_presence: dict[str, list[int]]) -> pd.DataFrame:
    """All years 2000-2009 are present as rows for every country; years not
    listed in ``year_presence[country]`` get an explicit NaN in BOTH the
    dep_var and indep_var columns -- controlling each country's
    joint-non-null-year count precisely, without depending on
    panel_exclusions or filter_by_exclusions (same rationale as
    tests/test_panel_base.py's _make_sparse_panel)."""
    all_years = list(range(2000, 2010))
    rows = []
    for country, present_years in year_presence.items():
        for year in all_years:
            value = 1.0 if year in present_years else np.nan
            rows.append(
                {
                    "country_code": country,
                    "year": year,
                    DEP_VAR: value,
                    INDEP_VAR: value,
                }
            )
    return pd.DataFrame(rows)


# --- build_coverage_table() -------------------------------------------------


def test_build_coverage_table_has_expected_columns():
    df = _make_sparse_m2_panel({"A": [2000, 2001, 2002], "B": [2000]})

    coverage = model2_agri.build_coverage_table(df)

    assert list(coverage.columns) == ["country_code", "years_available", "included", "reason"]
    assert set(coverage["country_code"]) == {"A", "B"}


def test_build_coverage_table_marks_included_iff_at_or_above_min_years():
    df = _make_sparse_m2_panel(
        {
            "A": [2000, 2001, 2002],  # 3 joint-non-null years -- included
            "B": [2000, 2001],  # 2 -- excluded
        }
    )

    coverage = model2_agri.build_coverage_table(df).set_index("country_code")

    assert bool(coverage.loc["A", "included"]) is True
    assert int(coverage.loc["A", "years_available"]) == 3
    assert bool(coverage.loc["B", "included"]) is False
    assert int(coverage.loc["B", "years_available"]) == 2


def test_build_coverage_table_honors_non_default_min_years():
    """WR-01 regression test (06-REVIEW.md): build_coverage_table must use
    the passed min_years, not the hardcoded module-level MIN_YEARS constant
    -- otherwise the model2_coverage table would disagree with a
    build_model2_panel call using a non-default min_years."""
    df = _make_sparse_m2_panel(
        {
            "A": [2000, 2001, 2002, 2003],  # 4 joint-non-null years
            "B": [2000, 2001],  # 2
        }
    )

    coverage = model2_agri.build_coverage_table(df, min_years=4).set_index("country_code")

    assert bool(coverage.loc["A", "included"]) is True
    assert bool(coverage.loc["B", "included"]) is False
    # With the default min_years=3, A would still be included, but B's
    # `reason` text must reflect the min_years actually passed (4), not the
    # module-level default (3).
    assert "excluido: <4 años observados" in coverage.loc["B", "reason"]


def test_build_coverage_table_default_min_years_matches_build_model2_panel():
    """Same min_years default (MIN_YEARS=3) as build_model2_panel, so calling
    both with no explicit min_years stays mutually consistent (D-03)."""
    df = _make_sparse_m2_panel({"A": [2000, 2001, 2002], "B": [2000, 2001]})

    coverage = model2_agri.build_coverage_table(df).set_index("country_code")
    filtered = model2_agri.build_model2_panel(df)

    assert bool(coverage.loc["A", "included"]) is True
    assert "A" in set(filtered["country_code"].unique())
    assert bool(coverage.loc["B", "included"]) is False
    assert "B" not in set(filtered["country_code"].unique())


def test_build_coverage_table_excludes_countries_with_zero_dep_var_observations():
    """A country with NO 2.3.1 data at all must not appear in the coverage
    table -- it documents every country with ANY 2.3.1 data, not every
    country present in panel_clean (D-03)."""
    df = _make_sparse_m2_panel({"A": [2000, 2001, 2002]})
    all_nan_rows = pd.DataFrame(
        [
            {"country_code": "Z", "year": year, DEP_VAR: np.nan, INDEP_VAR: 1.0}
            for year in range(2000, 2010)
        ]
    )
    df = pd.concat([df, all_nan_rows], ignore_index=True)

    coverage = model2_agri.build_coverage_table(df)

    assert "Z" not in set(coverage["country_code"])


# --- build_model2_panel() ---------------------------------------------------


def test_build_model2_panel_keeps_only_countries_meeting_threshold():
    df = _make_sparse_m2_panel(
        {
            "A": [2000, 2001, 2002, 2003],
            "B": [2000, 2001],
        }
    )

    filtered = model2_agri.build_model2_panel(df, min_years=3)

    assert set(filtered["country_code"].unique()) == {"A"}
    assert (filtered["country_code"] == "B").sum() == 0


def test_build_model2_panel_default_min_years_is_three():
    df = _make_sparse_m2_panel(
        {
            "A": [2000, 2001, 2002],  # exactly 3 -- kept under default
            "B": [2000, 2001],  # 2 -- dropped under default
        }
    )

    filtered = model2_agri.build_model2_panel(df)

    assert set(filtered["country_code"].unique()) == {"A"}


# --- fit_model2() / run_robustness_no_covid() / run_bootstrap() /
# --- run_heterogeneity() / run_shap() / serialize_artifacts() /
# --- write_coverage_table() (06-REVIEW.md WR-04) ---------------------------
#
# Prior to this section, these 7 orchestration functions had NO test
# coverage at all -- only build_coverage_table/build_model2_panel (pure
# bookkeeping) were exercised. Adds a synthetic-panel smoke test per
# function, mirroring tests/test_panel_base.py's/tests/test_simulate.py's
# _make_synthetic_panel construction style, adapted to Model 2's real
# column names (2.3.1/6.4.2) so the real column contract is exercised.


def _make_synthetic_m2_panel(
    n_entities: int = 15,
    n_years: int = 10,
    seed: int = 0,
    beta: float = 2.0,
    entity_effect_sd: float = 1.0,
    noise_sd: float = 0.5,
) -> pd.DataFrame:
    """A synthetic (country_code, year) panel with a known DEP_VAR/INDEP_VAR
    relationship (y = beta * x + entity_effect + noise), using Model 2's real
    column names -- large/varied enough for fit_model2's RandomEffects +
    Hausman + Pesaran-CD diagnostics to run without a degenerate result.
    Years span 2015-2024 (straddling 2020) so run_robustness_no_covid's
    sin-COVID sub-sample has both surviving and dropped years to assert on.
    Every third entity is flagged is_ldc=True, giving run_heterogeneity's
    C(is_ldc) interaction both group values to work with.
    """
    rng = np.random.default_rng(seed)
    entities = [f"C{i:02d}" for i in range(n_entities)]
    years = list(range(2015, 2015 + n_years))
    entity_effects = {c: rng.normal(0, entity_effect_sd) for c in entities}

    rows = []
    for i, country in enumerate(entities):
        for year in years:
            x = rng.normal(5, 1)
            y = beta * x + entity_effects[country] + rng.normal(0, noise_sd)
            rows.append(
                {
                    "country_code": country,
                    "year": year,
                    DEP_VAR: y,
                    INDEP_VAR: x,
                    "is_ldc": bool(i % 3 == 0),
                }
            )
    return pd.DataFrame(rows)


def test_fit_model2_returns_results_and_diagnostics_with_expected_keys():
    """fit_model2 must return (PanelEffectsResults, dict) with the
    documented diagnostics keys and a cov_type from choose_cov_type's
    contract ("clustered" or "kernel") -- guards against a future edit
    accidentally reusing the wrong cov_type for the Hausman-input fit."""
    panel_m2 = _make_synthetic_m2_panel()

    fitted, diagnostics = model2_agri.fit_model2(panel_m2)

    assert isinstance(fitted, PanelEffectsResults)
    assert set(diagnostics.keys()) == {"hausman", "pesaran", "cov_type", "cov_config"}
    assert diagnostics["cov_type"] in {"clustered", "kernel"}
    assert set(diagnostics["hausman"].keys()) == {"statistic", "df", "pvalue"}
    assert set(diagnostics["pesaran"].keys()) == {"statistic", "pvalue"}
    assert INDEP_VAR in fitted.params.index


def test_run_robustness_no_covid_drops_year_2020_and_later():
    """D-10: run_robustness_no_covid must fit on the year < 2020 sub-sample
    only -- asserted directly via nobs, which must equal the row count of
    the sub-sample actually passed to fit_panel_model."""
    panel_m2 = _make_synthetic_m2_panel()
    expected_nobs = int((panel_m2["year"] < 2020).sum())

    result = model2_agri.run_robustness_no_covid(panel_m2, cov_type="unadjusted")

    assert isinstance(result, PanelEffectsResults)
    assert result.nobs == expected_nobs
    assert expected_nobs < len(panel_m2)  # sanity: some rows were actually dropped


def test_run_bootstrap_delegates_to_simulate_bootstrap_counterfactual(monkeypatch):
    """run_bootstrap must call simulate.bootstrap_counterfactual UNMODIFIED
    (D-05/D-12) with n_replicas=1000, seed=42, and Model 2's DEP_VAR/
    INDEP_VAR -- verified via a monkeypatched capture rather than actually
    running 1000 real refits (too slow for a unit test)."""
    captured: dict = {}

    def _fake_bootstrap_counterfactual(fitted, df, dep_var, indep_var, **kwargs):
        captured["fitted"] = fitted
        captured["df"] = df
        captured["dep_var"] = dep_var
        captured["indep_var"] = indep_var
        captured["kwargs"] = kwargs
        return {"sentinel": True}

    monkeypatch.setattr(
        model2_agri.simulate, "bootstrap_counterfactual", _fake_bootstrap_counterfactual
    )

    panel_m2 = _make_synthetic_m2_panel()
    fake_fitted = object()

    result = model2_agri.run_bootstrap(fake_fitted, panel_m2)

    assert result == {"sentinel": True}
    assert captured["fitted"] is fake_fitted
    assert captured["df"] is panel_m2
    assert captured["dep_var"] == DEP_VAR
    assert captured["indep_var"] == INDEP_VAR
    assert captured["kwargs"] == {"n_replicas": 1000, "seed": 42}


def test_run_heterogeneity_calls_fit_interaction_model_with_is_ldc_group(monkeypatch):
    """D-11: run_heterogeneity must call simulate.fit_interaction_model with
    group_col="is_ldc" ONLY (region interaction is deliberately abandoned,
    D-11) -- verified via a monkeypatched capture."""
    captured: dict = {}

    def _fake_fit_interaction_model(df, dep_var, indep_var, group_col, **kwargs):
        captured["dep_var"] = dep_var
        captured["indep_var"] = indep_var
        captured["group_col"] = group_col
        return "sentinel_result"

    monkeypatch.setattr(
        model2_agri.simulate, "fit_interaction_model", _fake_fit_interaction_model
    )

    panel_m2 = _make_synthetic_m2_panel()
    result = model2_agri.run_heterogeneity(panel_m2)

    assert result == "sentinel_result"
    assert captured["dep_var"] == DEP_VAR
    assert captured["indep_var"] == INDEP_VAR
    assert captured["group_col"] == "is_ldc"


def test_run_shap_calls_shap_analysis_with_model2_dep_var_and_shap_feature_vars(monkeypatch):
    """D-06: run_shap must call interpret.shap_analysis with dep_var=DEP_VAR
    and feature_vars=SHAP_FEATURE_VARS (the SAME 3 numeric predictors +
    typology as Model 1) -- verified via a monkeypatched capture."""
    captured: dict = {}

    def _fake_shap_analysis(df, dep_var, feature_vars, **kwargs):
        captured["dep_var"] = dep_var
        captured["feature_vars"] = feature_vars
        return "sentinel_shap_result"

    monkeypatch.setattr(model2_agri.interpret, "shap_analysis", _fake_shap_analysis)

    panel_clean = _make_synthetic_m2_panel()
    result = model2_agri.run_shap(panel_clean)

    assert result == "sentinel_shap_result"
    assert captured["dep_var"] == DEP_VAR
    assert captured["feature_vars"] == model2_agri.SHAP_FEATURE_VARS


class _FakeRf:
    """Module-level (not local-function-scoped) so pickle can locate it by
    qualified name during serialize_artifacts's round-trip test below --
    pickle cannot serialize a class defined inside a function body."""

    oob_score_ = 0.5


def test_serialize_artifacts_writes_both_pickles_round_trip(tmp_path):
    """serialize_artifacts must write BOTH the fitted PanelEffectsResults and
    the RF to their given paths, creating parent directories as needed, such
    that pickle.load round-trips each object back (mirrors the Phase 3/4
    round-trip contract this function documents itself as reusing)."""
    import pickle

    panel_m2 = _make_synthetic_m2_panel()
    fitted, _diagnostics = model2_agri.fit_model2(panel_m2)

    rf = _FakeRf()
    model_path = tmp_path / "nested" / "model2_agri.pkl"
    rf_path = tmp_path / "nested" / "rf_shap_model_m2.pkl"

    model2_agri.serialize_artifacts(fitted, rf, str(model_path), str(rf_path))

    assert model_path.exists()
    assert rf_path.exists()
    with open(model_path, "rb") as f:
        loaded_fitted = pickle.load(f)
    with open(rf_path, "rb") as f:
        loaded_rf = pickle.load(f)
    assert loaded_fitted.params[INDEP_VAR] == pytest.approx(fitted.params[INDEP_VAR])
    assert loaded_rf.oob_score_ == 0.5


def test_write_coverage_table_writes_model2_coverage_table():
    """write_coverage_table must write coverage_df to the model2_coverage
    table, always fully regenerated (if_exists="replace") -- verified by
    reading it back from a real in-memory engine."""
    engine = db.get_engine(":memory:")
    coverage_df = pd.DataFrame(
        {
            "country_code": ["A", "B"],
            "years_available": [5, 1],
            "included": [True, False],
            "reason": ["incluido: >=3 años observados", "excluido: <3 años observados"],
        }
    )

    model2_agri.write_coverage_table(engine, coverage_df)

    written = pd.read_sql("SELECT * FROM model2_coverage", engine)
    assert set(written["country_code"]) == {"A", "B"}
    assert list(written.columns) == ["country_code", "years_available", "included", "reason"]
