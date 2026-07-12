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
    if cov_type == "clustered" and not cov_config:
        # linearmodels silently degrades an unconfigured "clustered" covariance
        # to a per-observation (i.e. plain "robust"/White) covariance -- make
        # the entity-clustering intent implied by the parameter name explicit
        # rather than relying on that fallback (see 03-REVIEW.md CR-01).
        cov_config = {"cluster_entity": True}
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


def hausman_test(
    fe_results: PanelEffectsResults,
    re_results: RandomEffectsResults,
) -> dict[str, float]:
    """Manual FE-vs-RE Hausman test (03-RESEARCH.md Finding 2 -- neither
    ``linearmodels`` nor ``statsmodels`` provides this test for panel data).

    Restricted to ``fe_results.params.index`` -- FE has no intercept, so this
    is exactly the regressor set common to both FE and RE (do NOT use RE's
    ``params.index``, which would include a ``const`` entry FE lacks whenever
    RE/Pooled are fit with an explicit constant column).

    ``H = (b_FE - b_RE)' [Var(b_FE) - Var(b_RE)]^-1 (b_FE - b_RE) ~ chi2(k)``

    Falls back to ``numpy.linalg.pinv`` (with an explicit warning) if
    ``var_diff`` is singular -- a documented, known small-sample pathology of
    this test, not a bug to hide.
    """
    common = fe_results.params.index
    diff = fe_results.params[common].values - re_results.params[common].values
    var_diff = (
        fe_results.cov.loc[common, common].values - re_results.cov.loc[common, common].values
    )

    try:
        inv_var_diff = np.linalg.inv(var_diff)
    except np.linalg.LinAlgError:
        warnings.warn(
            "Hausman test: var_diff is singular, using pseudo-inverse (pinv) "
            "-- known small-sample pathology, not a bug",
            UserWarning,
            stacklevel=2,
        )
        inv_var_diff = np.linalg.pinv(var_diff)

    statistic = float(diff @ inv_var_diff @ diff)
    if statistic < 0:
        warnings.warn(
            "Hausman test: negative test statistic (Var(FE) - Var(RE) is not "
            "positive semi-definite) -- the classical chi2 approximation is "
            "not valid here, likely because both sides were fit with a "
            "non-classical (robust/clustered/kernel) covariance estimator; "
            "treat this result as uninterpretable, not as evidence for H0",
            UserWarning,
            stacklevel=2,
        )
    degrees_of_freedom = len(common)
    pvalue = float(1 - stats.chi2.cdf(statistic, degrees_of_freedom))
    return {"statistic": statistic, "df": degrees_of_freedom, "pvalue": pvalue}


def pesaran_cd_test(residuals: pd.Series) -> dict[str, float]:
    """Manual Pesaran cross-sectional-dependence test (03-RESEARCH.md
    Finding 2 -- neither ``linearmodels`` nor ``statsmodels`` provides this).

    ``residuals`` must carry a ``(entity, time)`` MultiIndex (e.g.
    ``fe_results.resids``, directly usable without transformation).
    ``unstack(level=0)`` unstacks the OUTER index level (``entity``, given
    the ``(country_code, year)`` MultiIndex ``fit_panel_model`` builds),
    producing a (time x entity) wide frame -- verified against a
    hand-computable 3-entity fixture.

    ``CD = sqrt(2/(N(N-1))) * sum_{i<j} sqrt(T_ij) * rho_hat_ij ~ N(0,1)``

    Handles unbalanced panels natively via per-pair ``.dropna()`` -- included
    countries can still have individually-missing years within their
    qualifying span even after D-02's country-level exclusion.
    """
    wide = residuals.unstack(level=0)  # index=time, columns=entity
    n_entities = wide.shape[1]

    total = 0.0
    for i in range(n_entities):
        for j in range(i + 1, n_entities):
            pair = wide.iloc[:, [i, j]].dropna()
            if len(pair) < 2:
                continue
            rho = pair.iloc[:, 0].corr(pair.iloc[:, 1])
            if pd.notna(rho):
                total += np.sqrt(len(pair)) * rho

    cd_statistic = float(np.sqrt(2.0 / (n_entities * (n_entities - 1))) * total)
    pvalue = float(2 * (1 - stats.norm.cdf(abs(cd_statistic))))
    return {"statistic": cd_statistic, "pvalue": pvalue}


def choose_cov_type(
    pesaran_result: dict[str, float],
    alpha: float = 0.05,
) -> tuple[str, dict[str, Any]]:
    """Pure decision rule (Claude's Discretion, 03-CONTEXT.md): returns
    ``("kernel", {"kernel": "bartlett"})`` (Driscoll-Kraay) if the Pesaran
    test rejects H0 of no cross-sectional dependence
    (``pesaran_result["pvalue"] < alpha``), else
    ``("clustered", {"cluster_entity": True})``. The returned tuple's second
    element is the exact ``**cov_config`` to splat into
    ``fit_panel_model(..., cov_type=result[0], **result[1])``.
    """
    if pesaran_result["pvalue"] < alpha:
        return "kernel", {"kernel": "bartlett"}
    return "clustered", {"cluster_entity": True}
