"""Parametric block-bootstrap counterfactual and interaction-term
heterogeneity module, designed to be shared, unmodified, by Model 1 (Phase
4, dep_var="8.1.1") and Model 2 (Phase 6, dep_var="2.3.1") -- D-12
(04-CONTEXT.md). Every public function is dependent-variable-agnostic.

Bootstrap methodology (INTERP-01):
- D-01: resamples whole entities (countries) with replacement -- a block
  bootstrap by country, not an i.i.d. row bootstrap -- to respect both the
  within-country temporal dependence and the cross-sectional dependence the
  Pesaran CD test detected in Phase 3 (p=0.0014, 03-VERIFICATION.md).
- D-02: 1000 replicas is the intended production default (n_replicas
  parameter), academically standard for stable 2.5/97.5 percentile CIs.
- D-03: each scenario's reduction is applied to each country's
  last-observed-year (2022) water-stress value, not its historical mean.
- D-04: a country is EXCLUDED from a scenario (never capped/truncated) if
  its simulated level falls below the panel's global historical minimum.

`resample_entities` fixes a silent, live-verified bug (04-RESEARCH.md
Pitfall #1): concatenating a resampled country's rows under its ORIGINAL
`country_code` produces a non-unique (entity, year) MultiIndex that
`PanelOLS` does not error on -- it silently collapses duplicate-drawn
countries into a single fixed-effect bucket (171 draws with repeats -> 109
recognized entities without the fix). Every draw is relabeled to a unique
synthetic entity id (`f"{entity}__b{i}"`) before concatenation.

Interaction-term heterogeneity (INTERP-03, D-09/D-10/D-11):
`fit_interaction_model` adds a `water_stress : C(group)` (colon, NOT `*`)
term to the same two-way fixed-effects `PanelOLS` specification. The
standalone `C(group)` main effect is deliberately omitted -- it is
time-invariant per entity and fully absorbed by EntityEffects, which
otherwise raises `AbsorbingEffectError` (live-verified, 04-RESEARCH.md
Pattern 2). Results are reported ONLY as a per-group coefficient table with
SE/CI (D-11) -- never a per-country predicted value.

Does NOT modify src/panel_base.py -- `bootstrap_counterfactual` imports and
calls `panel_base.fit_panel_model` unmodified once per replica (D-12).
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from linearmodels.panel.results import PanelEffectsResults

from src import panel_base


def resample_entities(
    df: pd.DataFrame,
    entity_col: str,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Draw entities (e.g. countries) with replacement -- the same number of
    draws as unique entities in ``df`` -- and relabel EACH draw to a unique
    synthetic entity id (``f"{entity}__b{i}"``) before concatenation.

    Without this relabeling step, ``PanelOLS`` silently collapses
    duplicate-drawn entities into a single fixed-effect bucket instead of
    raising an error (04-RESEARCH.md Pitfall #1, live-verified: 171 draws
    with 43 repeats -> only 109 recognized entities without relabeling; 171
    with it). This is the mandatory fix for D-01's block bootstrap by
    entity, not an optional refinement.
    """
    entities = df[entity_col].unique()
    draws = rng.choice(entities, size=len(entities), replace=True)
    parts = []
    for i, entity in enumerate(draws):
        sub = df[df[entity_col] == entity].copy()
        sub[entity_col] = f"{entity}__b{i}"
        parts.append(sub)
    return pd.concat(parts, ignore_index=True)


def check_non_extrapolation(
    baseline: pd.Series,
    simulated_level: pd.Series,
    historical_min: float,
) -> tuple[pd.Series, list]:
    """Pure decision rule (D-04): a country SURVIVES a scenario only if its
    simulated level is still at or above the panel's global historical
    minimum -- otherwise it is EXCLUDED from that scenario (never
    capped/truncated to the floor). ``baseline``/``simulated_level`` must
    share the same (entity) index.

    Returns ``(survives, excluded)`` where ``survives`` is a boolean
    ``pd.Series`` aligned to ``baseline.index`` and ``excluded`` is the list
    of excluded entity ids (D-04: "el número/lista de países excluidos por
    escenario debe documentarse explícitamente").
    """
    survives = simulated_level >= historical_min
    excluded = baseline.index[~survives].tolist()
    return survives, excluded


def bootstrap_counterfactual(
    fitted_results: PanelEffectsResults,
    df: pd.DataFrame,
    dep_var: str,
    indep_var: str,
    reduction_pcts: list[float] | None = None,
    baseline_year: int = 2022,
    n_replicas: int = 1000,
    seed: int = 42,
    entity_col: str = "country_code",
) -> dict:
    """Block bootstrap counterfactual (INTERP-01, D-01..D-04): refits
    ``panel_base.fit_panel_model`` (unmodified, D-12) once per replica on an
    entity-resampled draw of ``df`` (via ``resample_entities``), collecting
    the ``indep_var`` coefficient across ``n_replicas`` draws.

    ``fitted_results`` (the real-data fit) is accepted for API symmetry with
    the notebook's "fit once on real data, then bootstrap" workflow but is
    not itself refit here -- each replica is an independent
    ``fit_panel_model`` call on resampled data.

    Each scenario in ``reduction_pcts`` (default ``[-0.10, -0.20, -0.30]``,
    i.e. reductions expressed as signed fractions) is applied to each
    country's ``baseline_year`` (2022, D-03) ``indep_var`` value:
    ``simulated_level = baseline * (1 + pct)``. The scenario EFFECT is the
    marginal-effect sensitivity ``coef_replica * delta`` (never an absolute
    ``.predict()``ed level -- ``linearmodels`` does not support
    out-of-sample prediction with entity effects, 04-RESEARCH.md Pitfall
    #3). ``check_non_extrapolation`` (D-04) excludes any country whose
    simulated level falls below the panel's global historical minimum of
    ``indep_var``, per scenario.

    Uses ``numpy.random.SeedSequence(seed).spawn(n_replicas)`` for
    independent, reproducible per-replica RNGs (REPRO-02, D-02) -- two calls
    with the same ``seed`` produce bit-identical results.

    Returns a ``dict`` keyed by each ``pct`` in ``reduction_pcts``, each
    value a dict with ``effect_draws`` (``n_replicas x n_surviving_countries``
    array), ``ci_2.5``/``ci_97.5`` (percentile CIs per surviving country),
    and ``excluded_countries`` (list, D-04).
    """
    if reduction_pcts is None:
        reduction_pcts = [-0.10, -0.20, -0.30]

    ss = np.random.SeedSequence(seed)
    child_seeds = ss.spawn(n_replicas)
    coefs = []
    for child in child_seeds:
        rng = np.random.default_rng(child)
        boot_df = resample_entities(df, entity_col, rng)
        res = panel_base.fit_panel_model(
            boot_df,
            dep_var,
            [indep_var],
            entity_effects=True,
            time_effects=True,
            cov_type="unadjusted",
        )
        coefs.append(res.params[indep_var])
    coefs = np.array(coefs)

    baseline = (
        df[df["year"] == baseline_year].set_index(entity_col)[indep_var].astype(float)
    )
    historical_min = float(df[indep_var].min())

    results: dict = {}
    for pct in reduction_pcts:
        delta = pct * baseline  # e.g. pct=-0.10 -> -10% of the 2022 level
        simulated_level = baseline + delta
        survives, excluded = check_non_extrapolation(baseline, simulated_level, historical_min)

        if not survives.any():
            warnings.warn(
                f"bootstrap_counterfactual: scenario pct={pct} excludes ALL "
                "countries (every simulated level falls below the historical "
                "minimum) -- returning an empty effect array for this scenario",
                UserWarning,
                stacklevel=2,
            )

        effect_draws = np.outer(coefs, delta[survives].to_numpy())
        results[pct] = {
            "effect_draws": effect_draws,
            "ci_2.5": np.percentile(effect_draws, 2.5, axis=0),
            "ci_97.5": np.percentile(effect_draws, 97.5, axis=0),
            "excluded_countries": excluded,
        }
    return results
