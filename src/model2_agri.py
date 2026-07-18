from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from linearmodels.panel import RandomEffects
from linearmodels.panel.results import PanelEffectsResults
from sqlalchemy import Engine

from src import interpret, panel_base, simulate

DEP_VAR = "2.3.1"
INDEP_VAR = "6.4.2"
MIN_YEARS = 3

SHAP_FEATURE_VARS = ["6.4.2", "6.4.1", "8.2.1", "is_ldc", "is_lldc", "is_sids", "region"]


def build_model2_panel(panel_clean: pd.DataFrame, min_years: int = MIN_YEARS) -> pd.DataFrame:
    return panel_base.filter_by_min_years(panel_clean, DEP_VAR, [INDEP_VAR], min_years)


def build_coverage_table(panel_clean: pd.DataFrame, min_years: int = MIN_YEARS) -> pd.DataFrame:
    dep_numeric = pd.to_numeric(panel_clean[DEP_VAR], errors="coerce")
    countries_with_dep = sorted(panel_clean.loc[dep_numeric.notna(), "country_code"].unique())

    subset = panel_clean[panel_clean["country_code"].isin(countries_with_dep)]
    variables = [DEP_VAR, INDEP_VAR]
    numeric = subset[variables].apply(pd.to_numeric, errors="coerce")
    all_nonnull = numeric.notna().all(axis=1)
    years_available = all_nonnull.groupby(subset["country_code"]).sum()
    years_available = years_available.reindex(countries_with_dep, fill_value=0)

    included = years_available >= min_years
    reason = included.map(
        {
            True: f"incluido: >={min_years} años observados",
            False: f"excluido: <{min_years} años observados con {INDEP_VAR} y {DEP_VAR}",
        }
    )

    return pd.DataFrame(
        {
            "country_code": years_available.index,
            "years_available": years_available.to_numpy(),
            "included": included.to_numpy(),
            "reason": reason.to_numpy(),
        }
    )


def fit_model2(panel_m2: pd.DataFrame) -> tuple[PanelEffectsResults, dict[str, Any]]:
    fe_res_for_hausman = panel_base.fit_panel_model(
        panel_m2,
        DEP_VAR,
        [INDEP_VAR],
        entity_effects=True,
        time_effects=True,
        cov_type="unadjusted",
    )

    indexed = panel_m2.set_index(["country_code", "year"]).copy()
    indexed[DEP_VAR] = pd.to_numeric(indexed[DEP_VAR], errors="coerce")
    indexed[INDEP_VAR] = pd.to_numeric(indexed[INDEP_VAR], errors="coerce")
    exog_with_const = indexed[[INDEP_VAR]].assign(const=1.0)
    re_res = RandomEffects(indexed[DEP_VAR], exog_with_const).fit(cov_type="unadjusted")

    hausman = panel_base.hausman_test(fe_res_for_hausman, re_res)
    pesaran = panel_base.pesaran_cd_test(fe_res_for_hausman.resids)
    cov_type, cov_config = panel_base.choose_cov_type(pesaran)

    final_fitted = panel_base.fit_panel_model(
        panel_m2,
        DEP_VAR,
        [INDEP_VAR],
        entity_effects=True,
        time_effects=True,
        cov_type=cov_type,
        **cov_config,
    )

    diagnostics: dict[str, Any] = {
        "hausman": hausman,
        "pesaran": pesaran,
        "cov_type": cov_type,
        "cov_config": cov_config,
    }
    return final_fitted, diagnostics


def run_robustness_no_covid(
    panel_m2: pd.DataFrame,
    cov_type: str = "clustered",
    **cov_config: Any,
) -> PanelEffectsResults:
    sub = panel_m2[panel_m2["year"] < 2020]
    return panel_base.fit_panel_model(
        sub,
        DEP_VAR,
        [INDEP_VAR],
        entity_effects=True,
        time_effects=True,
        cov_type=cov_type,
        **cov_config,
    )


def run_bootstrap(fitted: PanelEffectsResults, panel_m2: pd.DataFrame) -> dict:
    return simulate.bootstrap_counterfactual(
        fitted,
        panel_m2,
        DEP_VAR,
        INDEP_VAR,
        n_replicas=1000,
        seed=42,
    )


def run_heterogeneity(panel_m2: pd.DataFrame) -> PanelEffectsResults:
    return simulate.fit_interaction_model(panel_m2, DEP_VAR, INDEP_VAR, group_col="is_ldc")


def run_shap(panel_clean: pd.DataFrame) -> tuple[Any, Any, pd.DataFrame, Any]:
    return interpret.shap_analysis(panel_clean, DEP_VAR, feature_vars=SHAP_FEATURE_VARS)


def serialize_artifacts(
    fitted: PanelEffectsResults,
    rf: Any,
    model_path: str = "data/modelos/model2_agri.pkl",
    rf_path: str = "data/modelos/rf_shap_model_m2.pkl",
) -> None:
    for path in (model_path, rf_path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(fitted, f)
    with open(rf_path, "wb") as f:
        pickle.dump(rf, f)


def write_coverage_table(engine: Engine, coverage_df: pd.DataFrame) -> None:
    coverage_df.to_sql("model2_coverage", engine, if_exists="replace", index=False)


def _main() -> None:
    from src import db

    engine = db.get_engine("data/panel.db")
    panel_clean = pd.read_sql("SELECT * FROM panel_clean", engine)

    coverage_table = build_coverage_table(panel_clean, MIN_YEARS)
    panel_m2 = build_model2_panel(panel_clean, MIN_YEARS)

    fitted, diagnostics = fit_model2(panel_m2)
    robustness = run_robustness_no_covid(
        panel_m2, cov_type=diagnostics["cov_type"], **diagnostics["cov_config"]
    )
    run_bootstrap(fitted, panel_m2)
    run_heterogeneity(panel_m2)
    rf, _shap_values, _X, _explainer = run_shap(panel_clean)

    serialize_artifacts(fitted, rf)
    write_coverage_table(engine, coverage_table)

    n_included = int(coverage_table["included"].sum())
    print(f"model2_coverage: {n_included} countries included (D-01, expected 39)")
    print(f"Chosen cov_type: {diagnostics['cov_type']} {diagnostics['cov_config']}")
    print(f"Hausman: {diagnostics['hausman']}")
    print(f"Pesaran CD: {diagnostics['pesaran']}")
    print(f"Robustness (sin-COVID, year<2020): nobs={robustness.nobs}")


if __name__ == "__main__":
    _main()
