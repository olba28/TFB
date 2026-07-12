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
from statsmodels.stats.outliers_influence import variance_inflation_factor


def compute_vif_table(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    """VIF per numeric predictor, reusing
    ``statsmodels.stats.outliers_influence.variance_inflation_factor`` -- do
    NOT hand-roll VIF math (04-RESEARCH.md "Don't Hand-Roll" table). Mirrors
    the helper pattern already validated in Phase 2's
    ``notebook/2_1_construccion_panel_eda.ipynb`` (cells 13-15), promoted
    here so interpret.py can call it programmatically (INTERP-04 precedence:
    this table must be computed and reportable BEFORE SHAP output).

    Rows with missing values in ``numeric_cols`` are dropped complete-case
    before computing VIF -- ``variance_inflation_factor`` requires a
    complete numeric matrix.

    Emits a UserWarning (stacklevel=2) if any VIF is undefined (perfect
    collinearity, e.g. a zero-variance or exactly-collinear column) --
    matches this project's "warn, don't hide" convention
    (src/panel_base.py's hausman_test/pesaran_cd_test).
    """
    complete = df[numeric_cols].dropna()
    matrix = complete.to_numpy(dtype=float)

    vifs = []
    for i in range(matrix.shape[1]):
        vif = variance_inflation_factor(matrix, i)
        vifs.append(vif)
        if not np.isfinite(vif):
            warnings.warn(
                f"compute_vif_table: VIF for '{numeric_cols[i]}' is not finite "
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
    matrix ``X`` used to fit/explain, and the ``shap.TreeExplainer``
    instance itself (for downstream plotting, e.g. shap.summary_plot).

    Predictors per D-05: 6.4.2, 6.4.1, 8.2.1 (numeric) + is_ldc, is_lldc,
    is_sids, region (typology) -- 2.3.1 is deliberately excluded (D-06).

    During iterative development, ``explainer.shap_values(X,
    check_additivity=False)`` can be called separately by the caller to
    speed up the SHAP computation (04-RESEARCH.md Pitfall #4: the default
    additivity check takes ~355s at this project's real-data scale) -- the
    committed default here keeps the full additivity check
    (check_additivity defaults to True in shap.TreeExplainer.shap_values).
    """
    complete = df[feature_vars + [dep_var]].dropna()

    cat_cols = [c for c in ["region"] if c in feature_vars]
    if cat_cols:
        X = pd.get_dummies(complete[feature_vars], columns=cat_cols, drop_first=True)
    else:
        X = complete[feature_vars].copy()
    y = complete[dep_var]

    rf = RandomForestRegressor(
        n_estimators=300,
        random_state=seed,
        n_jobs=1,  # MUST be 1 -- REPRO-02, Pitfall #2
        oob_score=True,
    )
    rf.fit(X, y)

    explainer = shap.TreeExplainer(rf)
    shap_values = explainer.shap_values(X)

    return rf, shap_values, X, explainer
