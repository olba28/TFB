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
    variables = [dep_var, *indep_vars]
    excluded_countries = set(
        exclusions.loc[exclusions["indicator_code"].isin(variables), "country_code"]
    )
    return df[~df["country_code"].isin(excluded_countries)]


def filter_by_min_years(
    df: pd.DataFrame,
    dep_var: str,
    indep_vars: list[str],
    min_years: int = 3,
) -> pd.DataFrame:
    variables = [dep_var, *indep_vars]
    numeric = df[variables].apply(pd.to_numeric, errors="coerce")
    all_nonnull = numeric.notna().all(axis=1)
    years_observed = all_nonnull.groupby(df["country_code"]).sum()
    kept_countries = years_observed[years_observed >= min_years].index
    return df[df["country_code"].isin(kept_countries)]


def _build_panel_index(df: pd.DataFrame, dep_var: str, indep_vars: list[str]) -> pd.DataFrame:
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
    indexed = _build_panel_index(df, dep_var, indep_vars)
    if cov_type == "clustered" and not cov_config:
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
    indexed = _build_panel_index(df, dep_var, indep_vars)
    dependent = indexed[dep_var]
    exog = indexed[indep_vars]
    exog_with_const = exog.assign(const=1.0)

    pooled_res = PooledOLS(dependent, exog_with_const).fit(cov_type="unadjusted")
    re_res = RandomEffects(dependent, exog_with_const).fit(cov_type="unadjusted")
    fe_res = PanelOLS(dependent, exog, entity_effects=True, time_effects=True).fit(
        cov_type="unadjusted"
    )

    return compare({"Pooled": pooled_res, "RE": re_res, "FE": fe_res})


def hausman_test(
    fe_results: PanelEffectsResults,
    re_results: RandomEffectsResults,
) -> dict[str, float]:
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
    wide = residuals.unstack(level=0)
    n_entities = wide.shape[1]
    if n_entities < 2:
        raise ValueError(
            f"pesaran_cd_test requires at least 2 entities, got {n_entities}"
        )

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
    if pesaran_result["pvalue"] < alpha:
        return "kernel", {"kernel": "bartlett"}
    return "clustered", {"cluster_entity": True}
