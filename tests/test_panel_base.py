"""Tests for src/panel_base.py: the parametric panel-regression module shared
by Model 1 (Phase 3) and Model 2 (Phase 6) -- MODEL1-01, MODEL1-03, MODEL1-04.

Country-level exclusion semantics (D-01/D-02, 03-CONTEXT.md): a country is
either fully included or fully excluded from a specification, never
row-filtered per year. Hausman and Pesaran CD tests are manually implemented
(neither linearmodels nor statsmodels provides them, 03-RESEARCH.md Finding 2)
and verified here against a hand-computable fixture and qualitative
null-hypothesis expectations on synthetic data with no true cross-sectional
dependence or entity-effect/regressor correlation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import panel_base

DEP_VAR = "y"
INDEP_VARS = ["x"]


def _make_synthetic_panel(
    n_entities: int = 10,
    n_years: int = 10,
    seed: int = 0,
    beta: float = 2.0,
    entity_effect_sd: float = 1.0,
    noise_sd: float = 0.5,
) -> pd.DataFrame:
    """A synthetic (country_code, year) panel with a known dep_var/indep_var
    relationship (y = beta * x + entity_effect + noise). The entity effect is
    drawn independently of x (uncorrelated with the regressor), giving both
    FE and RE consistent estimators on this data -- a clean null case for the
    Hausman/Pesaran tests (mirrors 03-RESEARCH.md's verified synthetic setup).
    """
    rng = np.random.default_rng(seed)
    entities = [f"C{i:02d}" for i in range(n_entities)]
    years = list(range(2000, 2000 + n_years))
    entity_effects = {c: rng.normal(0, entity_effect_sd) for c in entities}

    rows = []
    for country in entities:
        for year in years:
            x = rng.normal(5, 1)
            y = beta * x + entity_effects[country] + rng.normal(0, noise_sd)
            rows.append({"country_code": country, "year": year, "x": x, "y": y})
    return pd.DataFrame(rows)


def _make_exclusions(excluded_on_dep: list[str], excluded_on_indep: list[str]) -> pd.DataFrame:
    """A synthetic panel_exclusions-shaped DataFrame (real schema:
    country_code, indicator_code, years_available, years_required,
    coverage_pct, excluded, reason -- filter_by_exclusions only reads the
    first two columns)."""
    rows = []
    for country in excluded_on_dep:
        rows.append(
            {
                "country_code": country,
                "indicator_code": DEP_VAR,
                "years_available": 3,
                "years_required": 17,
                "coverage_pct": 0.13,
                "excluded": True,
                "reason": "coverage_below_70pct_threshold",
            }
        )
    for country in excluded_on_indep:
        rows.append(
            {
                "country_code": country,
                "indicator_code": INDEP_VARS[0],
                "years_available": 2,
                "years_required": 17,
                "coverage_pct": 0.09,
                "excluded": True,
                "reason": "coverage_below_70pct_threshold",
            }
        )
    return pd.DataFrame(rows)


# --- filter_by_exclusions() ----------------------------------------------------


def test_filter_by_exclusions_drops_full_country_not_row_level():
    df = _make_synthetic_panel(n_entities=10, n_years=10)
    excluded_on_dep = ["C00", "C01"]
    excluded_on_indep = ["C02"]
    exclusions = _make_exclusions(excluded_on_dep, excluded_on_indep)

    filtered = panel_base.filter_by_exclusions(df, exclusions, DEP_VAR, INDEP_VARS)

    excluded_countries = set(excluded_on_dep) | set(excluded_on_indep)
    assert set(filtered["country_code"].unique()).isdisjoint(excluded_countries)
    # every excluded country's rows are ALL gone, not partially filtered
    for country in excluded_countries:
        assert (filtered["country_code"] == country).sum() == 0


def test_filter_by_exclusions_keeps_surviving_countries_full_year_range():
    df = _make_synthetic_panel(n_entities=10, n_years=10)
    exclusions = _make_exclusions(["C00", "C01"], ["C02"])

    filtered = panel_base.filter_by_exclusions(df, exclusions, DEP_VAR, INDEP_VARS)

    surviving = set(df["country_code"].unique()) - {"C00", "C01", "C02"}
    assert set(filtered["country_code"].unique()) == surviving
    for country in surviving:
        assert (filtered["country_code"] == country).sum() == 10  # full 10-year range intact


def test_filter_by_exclusions_ignores_indicators_not_in_this_specification():
    """An exclusion recorded against an unrelated indicator (not dep_var or
    indep_vars) must not remove any country from this specification's fit."""
    df = _make_synthetic_panel(n_entities=5, n_years=5)
    exclusions = pd.DataFrame(
        [
            {
                "country_code": "C00",
                "indicator_code": "unrelated_indicator",
                "years_available": 1,
                "years_required": 17,
                "coverage_pct": 0.04,
                "excluded": True,
                "reason": "coverage_below_70pct_threshold",
            }
        ]
    )

    filtered = panel_base.filter_by_exclusions(df, exclusions, DEP_VAR, INDEP_VARS)

    assert "C00" in set(filtered["country_code"].unique())


# --- filter_by_min_years() -------------------------------------------------------


def _make_sparse_panel(year_presence: dict[str, list[int]]) -> pd.DataFrame:
    """A synthetic (country_code, year) panel where ``year_presence`` maps
    each country to the list of years for which it has BOTH dep_var and
    indep_var non-null (D-01/D-02, 06-CONTEXT.md). All years 2000-2009 are
    present as rows for every country, but years not listed in
    ``year_presence[country]`` get an explicit NaN in the indep_var column
    -- controlling each country's observed-year count precisely without
    depending on panel_exclusions or filter_by_exclusions."""
    all_years = list(range(2000, 2010))
    rows = []
    for country, present_years in year_presence.items():
        for year in all_years:
            indep_value = 1.0 if year in present_years else np.nan
            rows.append(
                {"country_code": country, "year": year, "y": 5.0, "x": indep_value}
            )
    return pd.DataFrame(rows)


def test_filter_by_min_years_keeps_countries_at_or_above_threshold():
    """Country A has 4 qualifying years, B has 2, C has 3 -- min_years=3
    keeps A and C, drops B entirely (0 rows), keeps ALL of A's and C's
    rows (country-level, not row-level, semantics -- D-01)."""
    df = _make_sparse_panel(
        {
            "A": [2000, 2001, 2002, 2003],
            "B": [2000, 2001],
            "C": [2000, 2001, 2002],
        }
    )

    filtered = panel_base.filter_by_min_years(df, DEP_VAR, INDEP_VARS, min_years=3)

    assert set(filtered["country_code"].unique()) == {"A", "C"}
    assert (filtered["country_code"] == "B").sum() == 0
    assert (filtered["country_code"] == "A").sum() == 10  # full original row count kept
    assert (filtered["country_code"] == "C").sum() == 10


def test_filter_by_min_years_counts_only_all_vars_nonnull_years():
    """A year with dep_var present but indep_var NaN must NOT count toward
    min_years -- only years where EVERY variable in [dep_var, *indep_vars]
    is simultaneously non-null qualify (D-01)."""
    df = _make_sparse_panel({"A": [2000, 2001, 2002]})
    # Null out dep_var for one of A's "present" years -- that year no longer
    # qualifies even though indep_var (x) is non-null there.
    df.loc[(df["country_code"] == "A") & (df["year"] == 2002), "y"] = np.nan

    filtered = panel_base.filter_by_min_years(df, DEP_VAR, INDEP_VARS, min_years=3)

    # Only 2 qualifying years remain (2000, 2001) -- below min_years=3, so A is dropped.
    assert "A" not in set(filtered["country_code"].unique())


def test_filter_by_min_years_drops_country_fully():
    """Excluded countries contribute zero rows to the result -- identical
    country-level (never row-level) exclusion semantics as
    filter_by_exclusions."""
    df = _make_sparse_panel({"A": [2000, 2001, 2002, 2003], "B": [2000]})

    filtered = panel_base.filter_by_min_years(df, DEP_VAR, INDEP_VARS, min_years=3)

    assert (filtered["country_code"] == "B").sum() == 0


def test_filter_by_min_years_default_is_three():
    """Calling without the min_years kwarg uses the Model 2 default of 3
    (D-01). Also guards D-02's 'coexist, never wrap filter_by_exclusions'
    rule: the function's only inputs are df, dep_var, indep_vars, min_years
    -- no panel_exclusions-shaped frame is passed or required."""
    import inspect

    signature = inspect.signature(panel_base.filter_by_min_years)
    assert list(signature.parameters.keys()) == ["df", "dep_var", "indep_vars", "min_years"]

    df = _make_sparse_panel(
        {
            "A": [2000, 2001, 2002],  # exactly 3 -- kept under default
            "B": [2000, 2001],  # 2 -- dropped under default
        }
    )

    filtered = panel_base.filter_by_min_years(df, DEP_VAR, INDEP_VARS)

    assert set(filtered["country_code"].unique()) == {"A"}


# --- fit_panel_model() ---------------------------------------------------------


def test_fit_panel_model_recovers_known_coefficient_sign_and_significance():
    df = _make_synthetic_panel(n_entities=10, n_years=10, beta=2.0)

    result = panel_base.fit_panel_model(df, DEP_VAR, INDEP_VARS)

    assert result.params["x"] > 0
    assert result.pvalues["x"] < 0.05


def test_fit_panel_model_effects_flags_change_the_fit():
    """entity_effects=False, time_effects=False (explicit) must produce a
    measurably different rsquared than the default two-way-effects fit --
    proving the flags actually take hold. Direction is intentionally NOT
    asserted: this synthetic panel's entity effect is uncorrelated with the
    regressor by construction (needed for a clean Hausman/Pesaran null case),
    so the coefficient itself may barely move -- asserting a direction would
    risk flakiness tied to the random draw."""
    df = _make_synthetic_panel(n_entities=10, n_years=10)

    with_effects = panel_base.fit_panel_model(df, DEP_VAR, INDEP_VARS)
    without_effects = panel_base.fit_panel_model(
        df, DEP_VAR, INDEP_VARS, entity_effects=False, time_effects=False
    )

    assert with_effects.rsquared != pytest.approx(without_effects.rsquared)


def test_fit_panel_model_builds_index_internally_not_left_to_caller():
    """df arrives with a plain country_code/year column pair, not pre-indexed
    -- fit_panel_model must build the MultiIndex itself."""
    df = _make_synthetic_panel(n_entities=5, n_years=5)
    assert not isinstance(df.index, pd.MultiIndex)

    result = panel_base.fit_panel_model(df, DEP_VAR, INDEP_VARS)

    assert "x" in result.params.index


# --- compare_specifications() --------------------------------------------------


def test_compare_specifications_includes_all_three_estimators():
    df = _make_synthetic_panel(n_entities=10, n_years=10)

    comparison = panel_base.compare_specifications(df, DEP_VAR, INDEP_VARS)

    rendered = str(comparison)
    assert "PooledOLS" in rendered
    assert "RandomEffects" in rendered
    assert "PanelOLS" in rendered


# --- hausman_test() -------------------------------------------------------------


def test_hausman_test_fails_to_reject_null_on_uncorrelated_entity_effect():
    """The synthetic panel's entity effect is uncorrelated with x by
    construction -- both FE and RE are consistent estimators here, so the
    Hausman test should fail to reject H0 (03-RESEARCH.md Finding 2: verified
    stat=0.0605, p=0.806 on an equivalent synthetic setup -- generous
    tolerance here since exact reproduction across a different random draw
    isn't guaranteed)."""
    df = _make_synthetic_panel(n_entities=30, n_years=20, seed=1)

    from linearmodels.panel import PanelOLS, RandomEffects

    indexed = df.set_index(["country_code", "year"])
    fe_res = PanelOLS(
        indexed[DEP_VAR], indexed[INDEP_VARS], entity_effects=True, time_effects=True
    ).fit(cov_type="unadjusted")
    re_res = RandomEffects(indexed[DEP_VAR], indexed[INDEP_VARS]).fit(cov_type="unadjusted")

    result = panel_base.hausman_test(fe_res, re_res)

    assert result["pvalue"] > 0.05
    assert result["df"] == 1


def test_hausman_test_falls_back_to_pinv_on_singular_var_diff():
    """A degenerate var_diff (all-zero, guaranteed singular) must trigger the
    pinv fallback with a warning, not crash."""
    import numpy as np

    class _FakeResult:
        def __init__(self, params, cov):
            self.params = params
            self.cov = cov

    common = pd.Index(["x"])
    params = pd.Series([1.0], index=common)
    cov = pd.DataFrame([[0.0]], index=common, columns=common)
    fe_res = _FakeResult(params, cov)
    re_res = _FakeResult(params, cov)

    with pytest.warns(UserWarning, match="pinv"):
        result = panel_base.hausman_test(fe_res, re_res)

    assert result["statistic"] == pytest.approx(0.0)


# --- pesaran_cd_test() ----------------------------------------------------------


def test_pesaran_cd_test_hand_computable_fixture_returns_exact_expected_statistic():
    """3 entities x 3 periods, hand-verified: A=[1,2,3], B=[1,2,3] (rho=1
    with A), C=[3,2,1] (rho=-1 with A). Every pair shares T_ij=3 overlapping
    periods. Expected CD = sqrt(2/(3*2)) * [sqrt(3)*1 + sqrt(3)*(-1) +
    sqrt(3)*(-1)] = sqrt(1/3) * sqrt(3) * (-1) = -1.0 exactly. This verifies
    `unstack(level=0)` is the correct level to separate entities into
    columns for a Series indexed (entity, time)."""
    idx = pd.MultiIndex.from_tuples(
        [
            ("A", 1), ("A", 2), ("A", 3),
            ("B", 1), ("B", 2), ("B", 3),
            ("C", 1), ("C", 2), ("C", 3),
        ],
        names=["country_code", "year"],
    )
    residuals = pd.Series([1, 2, 3, 1, 2, 3, 3, 2, 1], index=idx, dtype=float)

    result = panel_base.pesaran_cd_test(residuals)

    assert result["statistic"] == pytest.approx(-1.0, abs=1e-9)


def test_pesaran_cd_test_fails_to_reject_null_on_no_true_cross_sectional_dependence():
    """Residuals from a correctly-specified FE model on this synthetic panel
    have no true cross-sectional dependence by construction -- the test
    should fail to reject H0 (03-RESEARCH.md Finding 2: verified CD=-0.2814,
    p=0.778 on an equivalent setup).

    Uses entity_effects only (time_effects=False) to generate the residuals:
    a two-way (entity+time) FE fit forces sum_i(resid_it) == 0 within every
    period for a balanced panel, which mechanically induces a small negative
    average pairwise correlation across entities -- a well-documented
    structural artifact of time-demeaning (De Hoyos & Sarafidis 2006), not
    true cross-sectional dependence. Verified live: with N=30/T=20 and
    time_effects=True this mechanical artifact reliably makes the CD test
    reject (p < 0.01) regardless of random seed, which would test the
    artifact rather than the formula. entity_effects-only residuals avoid
    that confound and match the qualitative p > 0.05 expectation."""
    df = _make_synthetic_panel(n_entities=30, n_years=20, seed=1)

    from linearmodels.panel import PanelOLS

    indexed = df.set_index(["country_code", "year"])
    fe_res = PanelOLS(
        indexed[DEP_VAR], indexed[INDEP_VARS], entity_effects=True, time_effects=False
    ).fit(cov_type="unadjusted")

    result = panel_base.pesaran_cd_test(fe_res.resids)

    assert result["pvalue"] > 0.05


# --- choose_cov_type() ----------------------------------------------------------


def test_choose_cov_type_clustered_when_pesaran_does_not_reject():
    cov_type, cov_config = panel_base.choose_cov_type({"statistic": 0.1, "pvalue": 0.8})
    assert cov_type == "clustered"
    assert cov_config == {"cluster_entity": True}


def test_choose_cov_type_kernel_when_pesaran_rejects():
    cov_type, cov_config = panel_base.choose_cov_type({"statistic": 5.0, "pvalue": 0.001})
    assert cov_type == "kernel"
    assert cov_config == {"kernel": "bartlett"}
