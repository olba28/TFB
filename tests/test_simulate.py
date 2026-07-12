"""Tests for src/simulate.py: the parametric block-bootstrap counterfactual
and interaction-term heterogeneity module shared, unmodified, by Model 1
(Phase 4, dep_var="8.1.1") and Model 2 (Phase 6, dep_var="2.3.1") -- D-12
(04-CONTEXT.md).

Covers INTERP-01 (block bootstrap + non-extrapolation exclusion, D-01/D-04),
INTERP-03 (interaction-term heterogeneity, D-09/D-10), and REPRO-02
(bootstrap determinism via numpy.random.SeedSequence). Mirrors
tests/test_panel_base.py's fixture style: a synthetic (country_code, year)
panel via np.random.default_rng, f"C{i:02d}" naming, docstring-per-test.

Wave 0 requirement (04-VALIDATION.md): fast fixture-based unit tests only --
never the real 171-country data/panel.db panel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import panel_base, simulate

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
    relationship (y = beta * x + entity_effect + noise) -- identical
    generator to tests/test_panel_base.py's helper, reused here so
    simulate.py's bootstrap can be exercised against a fast, deterministic
    fixture instead of the real 171-country panel (Wave 0 requirement).
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


def _make_synthetic_panel_with_group(
    n_entities: int = 20,
    n_years: int = 10,
    seed: int = 0,
    beta: float = 2.0,
    entity_effect_sd: float = 1.0,
    noise_sd: float = 0.5,
) -> pd.DataFrame:
    """Same synthetic (country_code, year) panel as _make_synthetic_panel,
    plus a time-invariant binary ``group`` column (a stand-in for
    region/is_ldc, D-10) assigned per entity -- needed for
    fit_interaction_model's interaction-only formula (INTERP-03, D-09).
    """
    rng = np.random.default_rng(seed)
    entities = [f"C{i:02d}" for i in range(n_entities)]
    years = list(range(2000, 2000 + n_years))
    entity_effects = {c: rng.normal(0, entity_effect_sd) for c in entities}
    group = {c: i % 2 for i, c in enumerate(entities)}  # time-invariant, binary

    rows = []
    for country in entities:
        for year in years:
            x = rng.normal(5, 1)
            y = beta * x + entity_effects[country] + rng.normal(0, noise_sd)
            rows.append(
                {
                    "country_code": country,
                    "year": year,
                    "x": x,
                    "y": y,
                    "group": group[country],
                }
            )
    return pd.DataFrame(rows)


def _make_extrapolation_panel() -> pd.DataFrame:
    """5 entities x 3 years (2020-2022) with explicit, hand-picked x/water-
    stress values: C00's 2022 (baseline) value of 4.0 is just above the
    panel's global historical minimum of 3.0 (set by C01's 2020 value), so
    a -30% reduction (delta = -1.2) pushes C00's simulated level to 2.8,
    below the floor -- while every other country's baseline stays far above
    3.0 even after the same -30% reduction. Used to test
    bootstrap_counterfactual's per-scenario, per-country non-extrapolation
    exclusion (D-04) deterministically, independent of any bootstrap
    coefficient randomness.
    """
    x_by_country_year = {
        "C00": {2020: 5.0, 2021: 4.5, 2022: 4.0},
        "C01": {2020: 3.0, 2021: 12.0, 2022: 12.5},
        "C02": {2020: 11.0, 2021: 11.5, 2022: 12.0},
        "C03": {2020: 10.0, 2021: 10.5, 2022: 11.0},
        "C04": {2020: 9.0, 2021: 9.5, 2022: 10.0},
    }
    entity_effect = {"C00": 0.5, "C01": -0.3, "C02": 0.2, "C03": -0.1, "C04": 0.4}
    rows = []
    for country, year_map in x_by_country_year.items():
        for year, x in year_map.items():
            y = 2.0 * x + entity_effect[country] + 0.01 * (year - 2020)
            rows.append({"country_code": country, "year": year, "x": x, "y": y})
    return pd.DataFrame(rows)


# --- resample_entities() --------------------------------------------------------


def test_resample_entities_unique_index():
    """10 synthetic entities, drawn with replacement via a fixed rng, must
    relabel each draw to a unique synthetic id so exactly 10 recognized
    entities result -- a scaled-down replication of 04-RESEARCH.md's
    live-verified finding (171 draws with repeats silently collapsed to 109
    recognized entities without relabeling; 171 with relabeling). Seed 7 is
    independently confirmed (via a fresh Generator of the same seed) to
    produce at least one repeat draw over these 10 entities, so this test
    genuinely exercises the collision fix rather than trivially passing on
    an all-unique draw (D-01, INTERP-01).
    """
    df = _make_synthetic_panel(n_entities=10, n_years=5, seed=3)
    entities = df["country_code"].unique()

    check_rng = np.random.default_rng(7)
    draws = check_rng.choice(entities, size=len(entities), replace=True)
    assert len(set(draws)) < len(draws), "seed must produce >=1 repeat draw to test the fix"

    call_rng = np.random.default_rng(7)
    resampled = simulate.resample_entities(df, "country_code", call_rng)

    assert resampled["country_code"].nunique() == len(entities)
    # relabeling actually happened -- no post-relabel id collides with an
    # original entity id
    assert set(resampled["country_code"].unique()).isdisjoint(set(entities))
    # every relabeled entity carries the full n_years row block (5 years)
    counts = resampled["country_code"].value_counts()
    assert (counts == 5).all()


# --- bootstrap_counterfactual() / non-extrapolation (D-04) ---------------------


def test_non_extrapolation_exclusion():
    """A country whose simulated water-stress level for a scenario falls
    below the panel's global historical minimum must be excluded from that
    scenario -- listed in `excluded_countries` and dropped from that
    scenario's `effect_draws` array -- never capped/truncated (D-04,
    INTERP-01). Uses a fully deterministic fixture (no bootstrap noise
    affects which country is excluded, since exclusion depends only on
    baseline values and the historical floor).
    """
    df = _make_extrapolation_panel()
    fitted = panel_base.fit_panel_model(df, "y", ["x"], cov_type="unadjusted")

    results = simulate.bootstrap_counterfactual(
        fitted,
        df,
        dep_var="y",
        indep_var="x",
        reduction_pcts=[-0.30],
        baseline_year=2022,
        n_replicas=5,
        seed=42,
    )

    scenario = results[-0.30]
    assert scenario["excluded_countries"] == ["C00"]
    # 5 countries total, 1 excluded -> 4 columns survive in the effect array
    assert scenario["effect_draws"].shape[1] == 4


def test_bootstrap_determinism():
    """Two calls to bootstrap_counterfactual with the same seed on the same
    synthetic panel must return bit-identical coefficient/effect draws
    (REPRO-02) -- exact equality via np.array_equal, NOT pytest.approx.
    """
    df = _make_synthetic_panel(n_entities=10, n_years=10, seed=2)
    fitted = panel_base.fit_panel_model(df, DEP_VAR, INDEP_VARS, cov_type="unadjusted")

    results_1 = simulate.bootstrap_counterfactual(
        fitted,
        df,
        DEP_VAR,
        INDEP_VARS[0],
        reduction_pcts=[-0.10, -0.20],
        baseline_year=2009,
        n_replicas=20,
        seed=42,
    )
    results_2 = simulate.bootstrap_counterfactual(
        fitted,
        df,
        DEP_VAR,
        INDEP_VARS[0],
        reduction_pcts=[-0.10, -0.20],
        baseline_year=2009,
        n_replicas=20,
        seed=42,
    )

    for pct in (-0.10, -0.20):
        assert np.array_equal(
            results_1[pct]["effect_draws"], results_2[pct]["effect_draws"]
        )
        assert np.array_equal(results_1[pct]["ci_2.5"], results_2[pct]["ci_2.5"])
        assert np.array_equal(results_1[pct]["ci_97.5"], results_2[pct]["ci_97.5"])


# --- fit_interaction_model() (INTERP-03) ----------------------------------------


def test_interaction_formula():
    """fit_interaction_model on a synthetic panel with a binary time-
    invariant `group` column must return one water-stress coefficient PER
    group value (never a per-country prediction, D-11), with std_errors and
    conf_int available, and must raise no AbsorbingEffectError -- the
    standalone C(group) main effect must be omitted from the formula
    because it is fully absorbed by EntityEffects (live-verified,
    04-RESEARCH.md Pattern 2, D-09).
    """
    df = _make_synthetic_panel_with_group(n_entities=20, n_years=10, seed=5)

    result = simulate.fit_interaction_model(df, "y", "x", "group")

    # one water-stress coefficient PER group value (0 and 1) -- D-11's
    # coefficient table -- identified by the interaction term name, tolerant
    # of whether an intercept row is also present alongside them.
    interaction_params = [p for p in result.params.index if "C(group)" in p]
    assert len(interaction_params) == 2
    assert result.std_errors is not None
    assert all(p in result.std_errors.index for p in interaction_params)
    conf_int = result.conf_int()
    assert conf_int is not None
    assert all(p in conf_int.index for p in interaction_params)
