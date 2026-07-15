"""Unit tests for ``src/dashboard/data.py`` (DASH-02): verify the correct
``st.cache_resource`` vs. ``st.cache_data`` decorator split and that the
loaders/cached-compute wrappers work against the in-memory fixture engine
(``tests/dashboard/conftest.py``), never the real ``data/panel.db`` or the
production ``.pkl`` artifacts.

Per 05-VALIDATION.md's DASH-02 row, correctness is asserted by inspecting
the wrapper's cache-type attribute (Streamlit's own
``streamlit.runtime.caching.cache_utils.CachedFunc._info.cache_type``), not
by wall-clock timing.
"""

from __future__ import annotations

import inspect

import pandas as pd
from streamlit.runtime.caching.cache_type import CacheType
from streamlit.runtime.caching.cache_utils import CachedFunc

from src.dashboard import data


def _cache_type(func: CachedFunc) -> CacheType:
    """Return the ``CacheType`` (DATA or RESOURCE) a Streamlit cache
    decorator attached to ``func``."""
    assert isinstance(func, CachedFunc), f"{func} is not Streamlit-cache-wrapped"
    return func._info.cache_type


def test_get_engine_and_load_model_are_cache_resource() -> None:
    """``get_engine``/``load_model`` return shared, non-copyable objects
    (Engine, fitted model) -- must be ``st.cache_resource`` (Pitfall 1)."""
    assert _cache_type(data.get_engine) == CacheType.RESOURCE
    assert _cache_type(data.load_model) == CacheType.RESOURCE


def test_loaders_and_compute_wrappers_are_cache_data() -> None:
    """``load_panel_clean``/``load_panel_exclusions``/``cached_bootstrap``/
    ``cached_shap`` return copyable results (DataFrames/dicts/tuples) --
    must be ``st.cache_data``."""
    assert _cache_type(data.load_panel_clean) == CacheType.DATA
    assert _cache_type(data.load_panel_exclusions) == CacheType.DATA
    assert _cache_type(data.cached_bootstrap) == CacheType.DATA
    assert _cache_type(data.cached_shap) == CacheType.DATA


def test_load_panel_clean_takes_underscore_prefixed_engine_param() -> None:
    """The Engine parameter must be prefixed with ``_`` so Streamlit excludes
    it from cache-key hashing (05-RESEARCH.md Pitfall 2)."""
    params = list(inspect.signature(data.load_panel_clean.__wrapped__).parameters)
    assert params == ["_engine"]

    params = list(inspect.signature(data.load_panel_exclusions.__wrapped__).parameters)
    assert params == ["_engine"]


def test_cached_bootstrap_and_cached_shap_take_no_engine_or_model_param() -> None:
    """``cached_bootstrap``/``cached_shap`` must load the Engine/fitted model
    internally (via the ``st.cache_resource`` loaders) rather than receiving
    them as parameters -- RESEARCH Pattern 5."""
    bootstrap_params = set(inspect.signature(data.cached_bootstrap.__wrapped__).parameters)
    shap_params = set(inspect.signature(data.cached_shap.__wrapped__).parameters)

    forbidden = {"engine", "model", "fitted", "_engine", "_model", "_fitted"}
    assert not (bootstrap_params & forbidden)
    assert not (shap_params & forbidden)


def test_load_panel_clean_returns_indicator_columns(tiny_panel_engine) -> None:
    """Functional check via the in-memory fixture engine (never the real
    215-country ``data/panel.db``): proves ``panel_clean`` loads with the 5
    indicator columns present."""
    frame = data.load_panel_clean(tiny_panel_engine)

    assert isinstance(frame, pd.DataFrame)
    assert not frame.empty
    for indicator in ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"]:
        assert indicator in frame.columns


def test_load_panel_exclusions_returns_dataframe(tiny_panel_engine) -> None:
    """Functional check that ``panel_exclusions`` loads from the fixture
    engine with the expected schema columns."""
    frame = data.load_panel_exclusions(tiny_panel_engine)

    assert isinstance(frame, pd.DataFrame)
    assert "country_code" in frame.columns
    assert "excluded" in frame.columns


def test_cached_bootstrap_honors_active_model_name(monkeypatch, tiny_panel_engine) -> None:
    """Phase 6 (D-07/06-PATTERNS.md): calling cached_bootstrap with
    active_model_name="Modelo 2 (Productividad agrícola)" must result in
    data.load_model being invoked with Model 2's pkl_path -- proving the
    parameter actually changes which artifact gets requested, not just that
    the registry entry exists."""
    recorded_paths: list[str] = []

    def _fake_load_model(pkl_path: str):
        recorded_paths.append(pkl_path)

        class _Fitted:
            pass

        return _Fitted()

    def _fake_bootstrap_counterfactual(fitted, df, dep_var, indep_var, **kwargs):
        return {}

    monkeypatch.setattr(data, "get_engine", lambda: tiny_panel_engine)
    monkeypatch.setattr(data, "load_panel_clean", lambda engine: pd.DataFrame())
    monkeypatch.setattr(data, "load_model", _fake_load_model)
    monkeypatch.setattr(data.simulate, "bootstrap_counterfactual", _fake_bootstrap_counterfactual)

    data.cached_bootstrap.clear()
    data.cached_bootstrap(
        dep_var="2.3.1",
        indep_var="6.4.2",
        active_model_name="Modelo 2 (Productividad agrícola)",
    )

    assert recorded_paths == ["data/modelos/model2_agri.pkl"]


def test_load_model_loads_toy_pickle(toy_model_pkl) -> None:
    """``load_model`` successfully deserializes the toy fitted
    RandomForestRegressor fixture without depending on the production
    ``data/modelos/*.pkl`` artifacts."""
    model = data.load_model(str(toy_model_pkl))

    assert hasattr(model, "predict")
