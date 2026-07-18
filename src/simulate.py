from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS
from linearmodels.panel.results import PanelEffectsResults

from src import panel_base


def resample_entities(
    df: pd.DataFrame,
    entity_col: str,
    rng: np.random.Generator,
) -> pd.DataFrame:
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

    baseline = pd.to_numeric(
        df[df["year"] == baseline_year].set_index(entity_col)[indep_var],
        errors="coerce",
    )
    historical_min = float(pd.to_numeric(df[indep_var], errors="coerce").min())

    results: dict = {}
    for pct in reduction_pcts:
        delta = pct * baseline
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


def fit_interaction_model(
    df: pd.DataFrame,
    dep_var: str,
    indep_var: str,
    group_col: str,
    cov_type: str = "clustered",
    **cov_config,
) -> PanelEffectsResults:
    indexed = df.set_index(["country_code", "year"]).copy()
    for column in [dep_var, indep_var]:
        indexed[column] = pd.to_numeric(indexed[column], errors="coerce")

    formula = (
        f'Q("{dep_var}") ~ 1 + Q("{indep_var}") : C({group_col}) '
        "+ EntityEffects + TimeEffects"
    )
    model = PanelOLS.from_formula(formula, data=indexed)

    if cov_type == "clustered" and not cov_config:
        cov_config = {"cluster_entity": True}
    return model.fit(cov_type=cov_type, **cov_config)
