"""Parametric panel-regression module shared, unmodified, by Model 1
(Phase 3, dep_var="8.1.1") and Model 2 (Phase 6, dep_var="2.3.1") -- D-05
(03-CONTEXT.md). Every function is dependent-variable-agnostic.

Country-level exclusion semantics (D-01/D-02): a country is either fully
included or fully excluded from a given (dep_var, indep_vars) specification
-- never row-filtered per year ("panel balanceado respecto a las variables
del modelo, no fila a fila"). ``fit_panel_model`` does NOT apply this filter
itself -- callers pass an already-filtered DataFrame via
``filter_by_exclusions``, keeping the fit function a thin, single-
responsibility wrapper reusable across specifications.

Hausman and Pesaran cross-sectional-dependence tests are implemented
manually here -- neither ``linearmodels`` nor ``statsmodels`` provides them
(03-RESEARCH.md Finding 2, verified by searching both packages' installed
source for "hausman"/"pesaran": the only hits are an unrelated IV-context
Hausman test and an unrelated Pesaran-Shin-Smith cointegration test).
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS, PooledOLS, RandomEffects, compare
from linearmodels.panel.results import (
    PanelEffectsResults,
    PanelModelComparison,
    RandomEffectsResults,
)
from scipy import stats


def filter_by_exclusions(
    df: pd.DataFrame,
    exclusions: pd.DataFrame,
    dep_var: str,
    indep_vars: list[str],
) -> pd.DataFrame:
    """Drop a country's ENTIRE row set if it fails the 70%-coverage
    threshold on ``dep_var`` OR any of ``indep_vars`` (D-01/D-02) -- a
    country either fully survives (all its rows kept) or is fully dropped
    (zero rows), never partially filtered row-by-row.

    ``df`` must still contain a plain ``country_code`` column (not yet
    indexed) -- indexing into the ``(entity, time)`` MultiIndex happens
    inside ``fit_panel_model``/``compare_specifications``, not here.
    """
    variables = [dep_var, *indep_vars]
    excluded_countries = set(
        exclusions.loc[exclusions["indicator_code"].isin(variables), "country_code"]
    )
    return df[~df["country_code"].isin(excluded_countries)]


def _build_panel_index(df: pd.DataFrame, dep_var: str, indep_vars: list[str]) -> pd.DataFrame:
    """Build the ``(country_code, year)`` MultiIndex and defensively coerce
    the model's dependent/independent columns to numeric (03-RESEARCH.md
    Finding 3 -- a ``LIMIT``-sampled dtype check can mislead; always coerce
    the columns actually used by the model regardless of the DataFrame's
    reported dtype).
    """
    indexed = df.set_index(["country_code", "year"]).copy()
    for column in [dep_var, *indep_vars]:
        indexed[column] = pd.to_numeric(indexed[column], errors="coerce")
    return indexed


def fit_panel_model(
    df: pd.DataFrame,
    dep_var: str,
    indep_vars: list[str],
    entity_effects: bool = True,
    time_effects: bool = True,
    cov_type: str = "clustered",
    **cov_config: Any,
) -> PanelEffectsResults:
    """The D-05-mandated public entry point: a thin wrapper around
    ``PanelOLS(...).fit(...)``. Does NOT call ``filter_by_exclusions``
    internally -- the caller is responsible for passing an already-filtered
    ``df`` (keeps this function testable independently of the exclusion
    logic, and reusable by Model 2 with a completely different exclusion
    set if ever needed).
    """
    indexed = _build_panel_index(df, dep_var, indep_vars)
    model = PanelOLS(
        indexed[dep_var],
        indexed[indep_vars],
        entity_effects=entity_effects,
        time_effects=time_effects,
    )
    return model.fit(cov_type=cov_type, **cov_config)


def compare_specifications(
    df: pd.DataFrame,
    dep_var: str,
    indep_vars: list[str],
) -> PanelModelComparison:
    """Fit ``PooledOLS``, ``RandomEffects``, and two-way-effects ``PanelOLS``
    on the same ``(dep_var, indep_vars)`` (all with ``cov_type="unadjusted"``
    -- comparison is about coefficient/R-squared differences across
    estimators, not SE methodology, which is ``fit_panel_model``'s own
    concern) and return ``linearmodels.panel.compare(...)``'s side-by-side
    comparison table (03-RESEARCH.md Finding 1 -- verified live, directly
    embeddable).
    """
    indexed = _build_panel_index(df, dep_var, indep_vars)
    dependent = indexed[dep_var]
    exog = indexed[indep_vars]

    pooled_res = PooledOLS(dependent, exog).fit(cov_type="unadjusted")
    re_res = RandomEffects(dependent, exog).fit(cov_type="unadjusted")
    fe_res = PanelOLS(dependent, exog, entity_effects=True, time_effects=True).fit(
        cov_type="unadjusted"
    )

    return compare({"Pooled": pooled_res, "RE": re_res, "FE": fe_res})
