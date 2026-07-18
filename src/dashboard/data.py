from __future__ import annotations

import pickle
import warnings
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from src import db, interpret, simulate
from src.dashboard import models


@st.cache_resource
def get_engine() -> Engine:
    return db.get_engine("data/panel.db")


@st.cache_data
def load_panel_clean(_engine: Engine) -> pd.DataFrame:
    frame = pd.read_sql("SELECT * FROM panel_clean", _engine)
    if frame.empty:
        warnings.warn(
            "load_panel_clean: panel_clean returned an empty DataFrame",
            UserWarning,
            stacklevel=2,
        )
    return frame


@st.cache_data
def load_panel_exclusions(_engine: Engine) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM panel_exclusions", _engine)


@st.cache_resource
def load_model(pkl_path: str) -> Any:
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


@st.cache_data
def cached_bootstrap(
    dep_var: str,
    indep_var: str,
    active_model_name: str,
    reduction_pcts: tuple[float, ...] = (-0.10, -0.20, -0.30),
    n_replicas: int = 8,
    seed: int = 42,
) -> dict:
    engine = get_engine()
    df = load_panel_clean(engine)
    fitted = load_model(models.ACTIVE_MODELS[active_model_name]["pkl_path"])

    fitted_entities = fitted.fitted_values.index.get_level_values("country_code").unique()
    df = df[df["country_code"].isin(fitted_entities)]

    return simulate.bootstrap_counterfactual(
        fitted,
        df,
        dep_var,
        indep_var,
        reduction_pcts=list(reduction_pcts),
        n_replicas=n_replicas,
        seed=seed,
    )


@st.cache_data
def cached_shap(
    dep_var: str,
    feature_vars: tuple[str, ...],
    active_model_name: str,
    explain_sample_size: int = 20,
) -> tuple[Any, Any, pd.DataFrame, Any]:
    engine = get_engine()
    df = load_panel_clean(engine)
    rf = load_model(models.ACTIVE_MODELS[active_model_name]["rf_shap_pkl_path"])
    return interpret.shap_analysis(
        df,
        dep_var,
        list(feature_vars),
        check_additivity=False,
        rf=rf,
        explain_sample_size=explain_sample_size,
    )
