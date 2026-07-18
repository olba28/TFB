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
            n_jobs=1,
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
    return PartialDependenceDisplay.from_estimator(rf, X, features, ax=ax)
