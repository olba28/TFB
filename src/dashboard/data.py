"""Cached data-access layer for the Phase 5 Streamlit dashboard (DASH-01,
DASH-02, D-03, D-04).

Streamlit re-executes the WHOLE script top-to-bottom on every widget
interaction (05-RESEARCH.md architecture diagram) -- without correctly
wrapping every heavy load/compute in ``st.cache_resource``/``st.cache_data``,
each click would reopen the SQLite engine, re-deserialize a pickled model, or
re-run the bootstrap/SHAP computation, freezing the live demo (DASH-02). The
split follows Streamlit's own distinction: ``st.cache_resource`` for objects
that are shared/non-copyable (the SQLAlchemy ``Engine``, a fitted
``PanelEffectsResults``/``RandomForestRegressor``) and ``st.cache_data`` for
results that can be safely copied (DataFrames, bootstrap effect arrays, SHAP
values) -- 05-RESEARCH.md Pattern 1, Pitfall 1.

This module also enforces DASH-01: it reads ONLY local artifacts --
``data/panel.db`` (via ``src.db.get_engine``, reused unmodified) and local
``.pkl`` files under ``data/modelos/`` -- and imports neither
``requests``/``httpx`` nor ``src.ingesta``. There is no live call to the UN
SDG API anywhere in this module.

``cached_bootstrap``/``cached_shap`` implement D-03: the bootstrap
counterfactual and SHAP analysis are recomputed live inside the dashboard
(never precomputed to a dedicated artifact) but their heavy inputs (Engine,
fitted model) are always loaded internally via the ``st.cache_resource``
loaders above -- never accepted as a hashed function argument
(05-RESEARCH.md Pattern 5 / Pitfall 2).

No cache here uses a ``ttl`` (D-04) -- caches are permanent for the lifetime
of the demo session; there is no manual reload button.
"""

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
    """Return the shared SQLAlchemy Engine bound to ``data/panel.db``.

    Wrapped in ``st.cache_resource`` (not ``st.cache_data``) because an
    Engine is a shared, non-copyable resource (05-RESEARCH.md Pitfall 1).
    Calls ``src.db.get_engine`` directly rather than reimplementing the
    connection (05-PATTERNS.md).
    """
    return db.get_engine("data/panel.db")


@st.cache_data
def load_panel_clean(_engine: Engine) -> pd.DataFrame:
    """Load the full ``panel_clean`` table.

    The table name is a fixed string literal -- never built from a widget
    value (mirrors ``src/db.py``'s parameterized-SQL discipline, T-5-01).
    ``_engine`` is prefixed with an underscore so Streamlit excludes the
    non-hashable Engine from the cache key (05-RESEARCH.md Pitfall 2).
    """
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
    """Load the full ``panel_exclusions`` table.

    Same fixed-literal-table-name and underscore-prefix rationale as
    ``load_panel_clean`` (T-5-01, 05-RESEARCH.md Pitfall 2).
    """
    return pd.read_sql("SELECT * FROM panel_exclusions", _engine)


@st.cache_resource
def load_model(pkl_path: str) -> Any:
    """Deserialize a project-produced ``.pkl`` model artifact.

    Loads ONLY local, project-produced artifacts under ``data/modelos/``
    (T-5-02) -- no ``st.file_uploader`` for ``.pkl`` exists anywhere in this
    phase. MUST be run from the project's ``.venv`` interpreter so
    ``linearmodels``/``scikit-learn`` classes deserialize correctly
    (05-RESEARCH.md Pitfall 6).
    """
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


@st.cache_data
def cached_bootstrap(
    dep_var: str,
    indep_var: str,
    reduction_pcts: tuple[float, ...] = (-0.10, -0.20, -0.30),
    n_replicas: int = 200,
    seed: int = 42,
) -> dict:
    """Cached live recompute of the bootstrap counterfactual (D-03).

    Loads its heavy inputs (Engine, fitted Model 1 results) internally via
    ``get_engine``/``load_model`` -- both ``st.cache_resource`` -- rather
    than receiving them as arguments, so no non-hashable object ever enters
    this function's cache key (05-RESEARCH.md Pattern 5 / Pitfall 2).
    ``reduction_pcts`` is a ``tuple`` (hashable) and is converted to a
    ``list`` before delegating to ``simulate.bootstrap_counterfactual``,
    which is called unmodified (D-03).

    ``n_replicas`` defaults to 200 here -- smaller than ``simulate.py``'s own
    production default of 1000 -- purely as a demo-runtime knob to keep the
    first cold compute inside the <5s demo budget (DASH-02); the underlying
    bootstrap methodology in ``simulate.py`` is unchanged.
    """
    engine = get_engine()
    df = load_panel_clean(engine)
    fitted = load_model(models.ACTIVE_MODELS["Modelo 1 (PIB per cápita)"]["pkl_path"])
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
) -> tuple[Any, Any, pd.DataFrame, Any]:
    """Cached live recompute of the SHAP analysis (D-03).

    Loads the Engine/panel data internally via ``get_engine``/
    ``load_panel_clean`` rather than receiving them as arguments (same
    rationale as ``cached_bootstrap``). ``feature_vars`` is a ``tuple``
    (hashable), converted to a ``list`` before delegating to
    ``interpret.shap_analysis``, which is called unmodified (D-03).

    ``interpret.shap_analysis`` already fixes its random seed (REPRO-02), so
    the cached result is deterministic within a session -- no ``ttl`` is
    needed here (D-04).
    """
    engine = get_engine()
    df = load_panel_clean(engine)
    return interpret.shap_analysis(df, dep_var, list(feature_vars))
