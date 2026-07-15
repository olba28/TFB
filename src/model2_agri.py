"""Model 2 (Phase 6, stretch): agricultural-productivity pipeline
(``dep_var="2.3.1"``) built ENTIRELY as pure parametric reuse of the
Phase 3/4 shared modules (``src/panel_base.py``, ``src/simulate.py``,
``src/interpret.py``) -- none of the three is modified by this module
(D-05 03-CONTEXT.md, D-12 04-CONTEXT.md, cited again in 06-CONTEXT.md).

Every call below is an EXISTING function invoked with ``dep_var="2.3.1"``,
``indep_var="6.4.2"`` instead of Model 1's ``dep_var="8.1.1"`` -- no
estimation, bootstrap, or SHAP math is re-implemented here.

Coverage (MODEL2-01, MODEL2-02):
- D-01: the Model 1 70%-of-years threshold (``panel_exclusions``) leaves the
  ``2.3.1`` panel at ZERO countries (indicator 2.3.1 is reported in ~3-year
  waves, max real coverage 26%). Model 2's own criterion is >=3 OBSERVED
  years with both ``2.3.1`` and ``6.4.2`` non-null -- 39 countries survive
  (live-verified, plan 06-01).
- D-02: this criterion is computed via ``panel_base.filter_by_min_years``
  (added in plan 06-01) directly on ``panel_clean`` -- never on the
  ``panel_exclusions`` table, which is fixed to the 70% rule.
- D-03: the reduced coverage is documented in a dedicated ``model2_coverage``
  table (this module's ``build_coverage_table``/``write_coverage_table``),
  same style as ``panel_exclusions`` (country_code, years_available,
  included, reason).

Diagnostics + robustness + heterogeneity + SHAP (MODEL2-03, D-09):
- D-04: the SAME Hausman/Pesaran-CD diagnostics as Model 1, run via
  ``panel_base.hausman_test``/``pesaran_cd_test``/``choose_cov_type``
  unmodified -- "warn, don't hide" on any numerically degenerate result on
  this sparse (~3.5 obs/country) panel.
- D-05: bootstrap uses the SAME ``n_replicas=1000`` as Model 1
  (``simulate.bootstrap_counterfactual``), even though only ~39 entities are
  resampled -- the wider CI is a documented Model 2 limitation, not
  disguised by cutting replicas.
- D-06: SHAP (``interpret.shap_analysis``) uses the SAME 3 numeric
  predictors + typology as Model 1 (``6.4.2``, ``6.4.1``, ``8.2.1``,
  ``is_ldc``, ``is_lldc``, ``is_sids``, ``region``) so the two models'
  relative water-stress weight is directly comparable in the memoria.
- D-09: robustness (D-10, sin-COVID) and heterogeneity (D-11, ``is_ldc``
  only) are included for FULL parity with Model 1, even though the Phase 6
  Success Criterion only mandates two-way FE + clustered SEs + diagnostics.
- D-10: robustness uses the SAME sin-COVID criterion as Model 1
  (sub-sample ``year < 2020``, ~35/39 countries survive) -- not the
  alternative-controls variant Model 1 considered and rejected.
- D-11: heterogeneity uses ``group_col="is_ldc"`` ONLY -- region is
  abandoned (degenerate, N=1-per-group among the 39 countries).
"""

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

# Same 3 numeric predictors + typology as Model 1 (D-06) -- 2.3.1 (this
# model's own dep_var) is deliberately excluded from the feature set.
SHAP_FEATURE_VARS = ["6.4.2", "6.4.1", "8.2.1", "is_ldc", "is_lldc", "is_sids", "region"]


def build_model2_panel(panel_clean: pd.DataFrame, min_years: int = MIN_YEARS) -> pd.DataFrame:
    """Model 2's own >=N-observed-years coverage panel (D-01/D-02): a thin
    call to ``panel_base.filter_by_min_years`` (added in plan 06-01),
    NOT ``filter_by_exclusions`` (the 70%-of-years rule leaves this panel
    at zero countries). Returns the 39-country panel at the default
    ``min_years=3``.
    """
    return panel_base.filter_by_min_years(panel_clean, DEP_VAR, [INDEP_VAR], min_years)


def build_coverage_table(panel_clean: pd.DataFrame, min_years: int = MIN_YEARS) -> pd.DataFrame:
    """Model 2's dedicated coverage/exclusions table (D-03), same style as
    ``panel_exclusions``: one row for EVERY country with at least one
    non-null ``2.3.1`` observation (not every country in ``panel_clean``),
    with columns ``country_code``, ``years_available`` (count of years where
    BOTH ``2.3.1`` and ``6.4.2`` are simultaneously non-null),
    ``included`` (bool, ``years_available >= min_years``), and a
    human-readable ``reason``.

    Accepts the SAME ``min_years`` parameter as ``build_model2_panel`` (fixed
    06-REVIEW.md WR-01: previously this hardcoded the module-level
    ``MIN_YEARS`` constant regardless of what ``build_model2_panel`` was
    actually called with, so the ``model2_coverage`` table written by
    ``write_coverage_table`` could silently disagree with which countries
    appear in the fitted panel -- undermining the traceability the table
    exists to provide, D-03). ``_main()`` threads the same ``min_years``
    value through both calls.

    Indicator columns are coerced via ``pd.to_numeric(errors="coerce")``
    before the non-null test (matches ``filter_by_min_years``'s and
    ``_build_panel_index``'s numeric-coercion convention).
    """
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
    """Fit Model 2's two-way fixed-effects PanelOLS via
    ``panel_base.fit_panel_model`` UNMODIFIED with ``dep_var=DEP_VAR``,
    ``indep_vars=[INDEP_VAR]`` -- the identical specification as Model 1
    (D-04).

    Runs the SAME diagnostic sequence as Model 1: a ``RandomEffects`` fit for
    Hausman input, built with an explicit constant column (mirroring
    ``panel_base.compare_specifications``'s own RE pattern -- RE's
    quasi-demeaning still needs an explicit intercept, unlike PanelOLS's
    two-way demeaning, which fit_panel_model already handles). Both the
    Hausman-input FE fit and the RE fit use ``cov_type="unadjusted"``
    (classical covariances -- the Hausman statistic's chi2 approximation
    assumes this; matches ``tests/test_panel_base.py``'s own Hausman
    fixtures). ``panel_base.hausman_test``, ``panel_base.pesaran_cd_test``,
    and ``panel_base.choose_cov_type`` then drive the final covariance
    estimator choice (clustered or Driscoll-Kraay) -- exactly Model 1's
    decision flow (D-04, D-09).

    Does NOT suppress warnings -- ``hausman_test``/``pesaran_cd_test``'s own
    ``warnings.warn`` calls (singular ``var_diff``, negative statistic, etc.)
    propagate to the caller (D-04, "warn, don't hide").

    Returns ``(final_fitted, diagnostics)`` where ``diagnostics`` is a dict
    with keys ``"hausman"``, ``"pesaran"``, ``"cov_type"``, ``"cov_config"``.
    """
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
    """Sin-COVID robustness check (D-10): refit the SAME two-way FE
    specification via ``panel_base.fit_panel_model`` on the ``year < 2020``
    sub-sample (~35/39 countries survive, live-verified in 06-CONTEXT.md) --
    the identical sin-COVID criterion Model 1 used, NOT the
    alternative-controls variant Model 1 considered and rejected, so the two
    models' robustness checks stay directly comparable in the memoria.

    ``cov_type``/``cov_config`` default to ``fit_panel_model``'s own
    defaults but are exposed so ``_main()`` can pass the SAME
    ``cov_type``/``cov_config`` chosen by ``fit_model2``'s
    ``choose_cov_type`` call, for a like-for-like comparison against the
    main fit.
    """
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
    """Counterfactual bootstrap (D-05): calls
    ``simulate.bootstrap_counterfactual`` UNMODIFIED with
    ``n_replicas=1000`` -- the SAME replica count as Model 1, even though
    the block bootstrap by country resamples only ~39 entities here (vs.
    171 for Model 1). The resulting wider confidence interval is a
    documented Model 2 limitation, never disguised by reducing replicas.
    """
    return simulate.bootstrap_counterfactual(
        fitted,
        panel_m2,
        DEP_VAR,
        INDEP_VAR,
        n_replicas=1000,
        seed=42,
    )


def run_heterogeneity(panel_m2: pd.DataFrame) -> PanelEffectsResults:
    """Heterogeneity by UN typology (D-11): calls
    ``simulate.fit_interaction_model`` UNMODIFIED with
    ``group_col="is_ldc"`` ONLY -- region interaction is abandoned because,
    among the 39 Model 2 countries, region is severely unbalanced (several
    regions have N=1), making a region interaction term unidentifiable
    (collinear with entity fixed effects).
    """
    return simulate.fit_interaction_model(panel_m2, DEP_VAR, INDEP_VAR, group_col="is_ldc")


def run_shap(panel_clean: pd.DataFrame) -> tuple[Any, Any, pd.DataFrame, Any]:
    """SHAP interpretability (D-06): calls ``interpret.shap_analysis``
    UNMODIFIED with ``dep_var=DEP_VAR`` and the SAME 3 numeric predictors +
    typology as Model 1 (``SHAP_FEATURE_VARS``) -- ``2.3.1`` is the target,
    never included among the features. Uses the full (unfiltered by
    ``build_model2_panel``) ``panel_clean`` as input, since ``shap_analysis``
    performs its own complete-case ``.dropna()`` over ``feature_vars +
    [dep_var]`` and the RF's predictors have much broader coverage than
    ``2.3.1`` alone (171/173 complete rows, per 06-CONTEXT.md D-06).

    Returns ``(rf, shap_values, X, explainer)`` -- same 4-tuple contract as
    ``interpret.shap_analysis`` itself.
    """
    return interpret.shap_analysis(panel_clean, DEP_VAR, feature_vars=SHAP_FEATURE_VARS)


def serialize_artifacts(
    fitted: PanelEffectsResults,
    rf: Any,
    model_path: str = "data/modelos/model2_agri.pkl",
    rf_path: str = "data/modelos/rf_shap_model_m2.pkl",
) -> None:
    """Serialize Model 2's fitted ``PanelEffectsResults`` and its SHAP
    RandomForest to ``data/modelos/`` -- the SAME round-trip-verified pickle
    pattern already established for ``model1_gdp.pkl``/``rf_shap_model.pkl``
    (Phase 3/4). Creates the parent directory if it does not yet exist.
    """
    for path in (model_path, rf_path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(fitted, f)
    with open(rf_path, "wb") as f:
        pickle.dump(rf, f)


def write_coverage_table(engine: Engine, coverage_df: pd.DataFrame) -> None:
    """Write ``coverage_df`` to the dedicated ``model2_coverage`` table
    (D-03), mirroring ``panel_build.rebuild_clean_panel``'s
    ``if_exists="replace"`` write pattern -- always fully regenerated, never
    appended.
    """
    coverage_df.to_sql("model2_coverage", engine, if_exists="replace", index=False)


def _main() -> None:
    """CLI entry: ``python -m src.model2_agri``. Runs the full Model 2
    pipeline against the real ``data/panel.db`` and prints a short summary
    (included-country count, chosen covariance type, Hausman/Pesaran
    statistics) for the memoria's limitations section.
    """
    from src import db

    engine = db.get_engine("data/panel.db")
    panel_clean = pd.read_sql("SELECT * FROM panel_clean", engine)

    # Both calls share the SAME min_years value (WR-01) -- keeps
    # model2_coverage traceable to exactly which countries panel_m2 contains.
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
