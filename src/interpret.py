"""Parametric ML-interpretability module -- a shared multivariate
RandomForest feeding SHAP (INTERP-04), partial-dependence plots (INTERP-05),
and its own out-of-bag score as the predictive reference metric (INTERP-06),
preceded by a VIF/correlation table (INTERP-04 precedence check).

D-05 (04-CONTEXT.md): the RF is multivariate -- predictors are 6.4.2 (water
stress), 6.4.1 (water efficiency), 8.2.1 (labor productivity), plus country
typology (is_ldc, is_lldc, is_sids, region one-hot) -- so SHAP can show
water stress's relative weight against other variables, which Model 1's
parsimonious PanelOLS specification cannot answer by design.

D-06: 2.3.1 (agricultural productivity) is deliberately EXCLUDED from the
RF's predictors -- it is Model 2's (Phase 6) own dependent variable, not a
predictor of GDP per capita here, and its reduced coverage (50 vs. 171
countries) would drastically shrink the available sample if included.

D-07: the SAME RandomForest trained for SHAP is reused as INTERP-06's
predictive reference metric (via oob_score_) -- no separate Gradient
Boosting model is trained, avoiding duplicated training/validation/
documentation for a requirement that does not demand two ML models.

D-08: shap_analysis returns the fitted rf so the Phase-4 notebook (Plan 03)
can serialize it to data/modelos/rf_shap_model.pkl, following the same
round-trip-verified pattern already established for model1_gdp.pkl
(Phase 3).

D-12: every public function here is dependent-variable-agnostic (dep_var,
feature_vars are parameters, never hardcoded), so Phase 6 (Model 2) can call
shap_analysis(df, dep_var="2.3.1", feature_vars=[...]) unmodified.

REPRO-02: RandomForestRegressor is trained with n_jobs=1 -- n_jobs=-1 breaks
reproducibility even with a fixed random_state (04-RESEARCH.md Pitfall #2,
live-verified against this project's pinned scikit-learn==1.9.0). This is
not optional.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import PartialDependenceDisplay
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools import add_constant


def compute_vif_table(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    """VIF per numeric predictor, reusing
    ``statsmodels.stats.outliers_influence.variance_inflation_factor`` -- do
    NOT hand-roll VIF math (04-RESEARCH.md "Don't Hand-Roll" table). Mirrors
    the helper pattern already validated in Phase 2's
    ``notebook/2_1_construccion_panel_eda.ipynb`` (cells 13-15), promoted
    here so interpret.py can call it programmatically (INTERP-04 precedence:
    this table must be computed and reportable BEFORE SHAP output).

    A constant column is added via ``statsmodels.tools.add_constant`` before
    computing VIF -- the same methodological choice Phase 2's notebook made
    explicitly ("omitir la constante cambia los valores de VIF resultantes",
    cell 11) -- and excluded from the returned table (its own VIF has no
    interpretation). Without this the VIF values are numerically different
    from (and not comparable to) Phase 2's committed numbers.

    Rows with missing values in ``numeric_cols`` are dropped complete-case
    before computing VIF -- ``variance_inflation_factor`` requires a
    complete numeric matrix.

    Emits a UserWarning (stacklevel=2) if any VIF is undefined (perfect
    collinearity, e.g. a zero-variance or exactly-collinear column) --
    matches this project's "warn, don't hide" convention
    (src/panel_base.py's hausman_test/pesaran_cd_test).
    """
    complete = df[numeric_cols].dropna()
    design = add_constant(complete, has_constant="add")

    vifs = []
    for col in numeric_cols:
        vif = variance_inflation_factor(design.to_numpy(dtype=float), design.columns.get_loc(col))
        vifs.append(vif)
        if not np.isfinite(vif):
            warnings.warn(
                f"compute_vif_table: VIF for '{col}' is not finite "
                "(perfect or near-perfect collinearity) -- treat this "
                "predictor's VIF as undefined, not as a bug",
                UserWarning,
                stacklevel=2,
            )

    return pd.DataFrame({"variable": numeric_cols, "VIF": vifs})


def shap_analysis(
    df: pd.DataFrame,
    dep_var: str,
    feature_vars: list[str],
    seed: int = 42,
    check_additivity: bool = True,
    rf: RandomForestRegressor | None = None,
    explain_sample_size: int | None = None,
) -> tuple[RandomForestRegressor, np.ndarray, pd.DataFrame, shap.TreeExplainer]:
    """Train a multivariate RandomForestRegressor (D-05) on complete-case
    rows and compute SHAP values via shap.TreeExplainer (INTERP-04).

    Selects complete-case rows via ``.dropna()`` on
    ``feature_vars + [dep_var]``, one-hot encodes ``region`` (if present in
    ``feature_vars``) with ``pd.get_dummies(..., columns=["region"],
    drop_first=True)``, and trains
    ``RandomForestRegressor(n_estimators=300, random_state=seed, n_jobs=1,
    oob_score=True)``. ``n_jobs`` MUST be 1 -- REPRO-02, 04-RESEARCH.md
    Pitfall #2 (live-verified: n_jobs=-1 breaks reproducibility even with a
    fixed random_state).

    Returns the fitted ``rf`` (so the caller can serialize it -- D-08 -- and
    read ``rf.oob_score_`` for INTERP-06's predictive reference metric,
    D-07: the SAME RF, no separate GBM), the SHAP values array, the feature
    matrix ``X`` (or its ``explain_sample_size`` sample -- see below) used to
    explain, and the ``shap.TreeExplainer`` instance itself (for downstream
    plotting, e.g. shap.summary_plot).

    Predictors per D-05: 6.4.2, 6.4.1, 8.2.1 (numeric) + is_ldc, is_lldc,
    is_sids, region (typology) -- 2.3.1 is deliberately excluded (D-06).

    ``check_additivity`` defaults to ``True`` -- shap.TreeExplainer's own
    default -- so every caller that does not pass it (the Phase-4 notebook,
    tests) gets the full additivity check. 04-RESEARCH.md Pitfall #4: this
    check takes ~355s at this project's real-data scale, so the Phase-5
    dashboard's demo-runtime wrapper (``dashboard.data.cached_shap``) passes
    ``check_additivity=False`` to stay inside the <5s cold-start budget
    (DASH-02) -- the SHAP values themselves are unaffected; only the
    post-hoc consistency re-check is skipped.

    ``rf`` defaults to ``None``, which fits a fresh RandomForest as described
    above (the Phase-4 notebook's path, and the only path that produces a
    trustworthy ``rf_shap_model.pkl`` to serialize -- D-08). If a caller
    passes an already-fitted ``rf`` (e.g. the archived
    ``data/modelos/rf_shap_model.pkl``), the fit step is skipped entirely and
    only ``X``'s construction + the SHAP explanation run -- this is what
    ``dashboard.data.cached_shap`` does, since live-refitting a 300-tree RF
    on every cold Streamlit session measured ~4.2s by itself (05-05
    rehearsal), on top of the SHAP computation -- together blowing the <5s
    budget (DASH-02) regardless of ``check_additivity``.

    ``explain_sample_size`` defaults to ``None`` (explain every complete-case
    row, the Phase-4 notebook's full-fidelity path). The Phase-5 dashboard
    passes a small integer (live-measured at ~0.1s/row for
    ``explainer.shap_values``) as a second demo-runtime knob alongside
    ``rf``/``check_additivity`` -- sampling which rows are *explained* does
    not touch the fitted RF (identical model either way) or the SHAP
    algorithm itself, only how many rows get plotted in the live summary
    plot; the archived Plan-B screenshots (figuras/plan_b/) carry the
    full-fidelity version for the record.
    """
    complete = df[feature_vars + [dep_var]].dropna()

    cat_cols = [c for c in ["region"] if c in feature_vars]
    if cat_cols:
        X = pd.get_dummies(complete[feature_vars], columns=cat_cols, drop_first=True)
    else:
        X = complete[feature_vars].copy()
    y = complete[dep_var]

    if rf is None:
        rf = RandomForestRegressor(
            n_estimators=300,
            random_state=seed,
            n_jobs=1,  # MUST be 1 -- REPRO-02, Pitfall #2
            oob_score=True,
        )
        rf.fit(X, y)

    if explain_sample_size is not None and explain_sample_size < len(X):
        X = X.sample(n=explain_sample_size, random_state=seed)

    explainer = shap.TreeExplainer(rf)
    shap_values = explainer.shap_values(X, check_additivity=check_additivity)

    return rf, shap_values, X, explainer


def partial_dependence_plots(
    rf: RandomForestRegressor,
    X: pd.DataFrame,
    features: list[str],
    ax=None,
):
    """Render partial-dependence plots (PDP) for ``features`` using
    ``sklearn.inspection.PartialDependenceDisplay`` -- the zero-new-
    dependency fallback for INTERP-05.

    Chosen deliberately over ``PyALE``: PyALE was flagged ``SUS`` in the
    Phase 4 legitimacy audit (04-RESEARCH.md Package Legitimacy Audit) and
    CLAUDE.md fixes project dependencies without justification. The RF's
    three numeric predictors are only weakly correlated globally (max
    |r|=0.09, VIF < 2.2 per Phase 2's real numbers, reproduced in
    04-RESEARCH.md Pitfall #5), which blunts PDP's documented
    correlated-feature bias concern for THIS specific dataset -- an honest,
    data-grounded rationale rather than a blanket claim that PDP is always
    safe.

    If true ALE is later desired, ``PyALE`` would require a
    ``checkpoint:human-verify`` gate before install per the package
    legitimacy protocol -- that path is NOT taken here: no new dependency is
    introduced, no checkpoint is required.

    Returns the ``PartialDependenceDisplay`` instance so the caller (the
    Phase-4 notebook) can embed/further customize the figure.
    """
    return PartialDependenceDisplay.from_estimator(rf, X, features, ax=ax)
