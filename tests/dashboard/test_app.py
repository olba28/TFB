"""AppTest integration test for src/dashboard/app.py (DASH-03, D-02, D-06).

Uses ``streamlit.testing.v1.AppTest.from_file`` to render the whole app
headlessly (no browser). Every heavy loader (``data.get_engine``,
``data.load_panel_clean``, ``data.load_model``, ``data.cached_bootstrap``,
``data.cached_shap``) is monkeypatched to a tiny fixture BEFORE ``.run()`` --
per this phase's Wave 0 requirement, this test NEVER reads the real
215-country ``data/panel.db`` or the real production ``.pkl`` artifacts
(``data/modelos/model1_gdp.pkl``, ``data/modelos/rf_shap_model.pkl``), so it
stays fast (~10-15s budget, 05-VALIDATION.md) and independent of the exact
pinned scikit-learn/linearmodels versions those real pickles require.

Reuses ``tests/dashboard/conftest.py``'s ``tiny_panel_df``/``tiny_panel_engine``
fixtures (05-01), matching every other dashboard test file's convention.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from streamlit.testing.v1 import AppTest

from src.dashboard import data, models


class _FakePanelEffectsResults:
    """Minimal stand-in for linearmodels.panel.results.PanelEffectsResults,
    exposing only the attributes app.py's "Modelo 1" tab and the "Mapa e
    indicadores" tab's fitted-values overlay read (params, std_errors,
    pvalues, conf_int(), rsquared_within, nobs, fitted_values) -- avoids
    loading the real, scikit-learn/linearmodels-version-pinned
    model1_gdp.pkl in this test (Wave 0 requirement).
    """

    def __init__(self, panel_df: pd.DataFrame, indep_var: str) -> None:
        self.params = pd.Series({indep_var: -0.05})
        self.std_errors = pd.Series({indep_var: 0.02})
        self.pvalues = pd.Series({indep_var: 0.01})
        self.rsquared_within = 0.12
        self.nobs = len(panel_df)

        fitted = panel_df[["country_code", "year"]].drop_duplicates().copy()
        fitted["fitted_values"] = 1.0
        self.fitted_values = fitted.set_index(["country_code", "year"])

    def conf_int(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"lower": [-0.09], "upper": [-0.01]},
            index=list(self.params.index),
        )


def _fake_cached_bootstrap(
    dep_var: str,
    indep_var: str,
    active_model_name: str,
    reduction_pcts: tuple[float, ...] = (-0.10, -0.20, -0.30),
    n_replicas: int = 200,
    seed: int = 42,
) -> dict:
    """Shaped exactly like simulate.bootstrap_counterfactual's return value
    (keyed by signed reduction pct; effect_draws/ci_2.5/ci_97.5 per
    scenario) -- deterministic, no dependency on simulate.py's own runtime.
    """
    rng = np.random.default_rng(0)
    results = {}
    for pct in reduction_pcts:
        effect_draws = rng.normal(loc=pct * 10, scale=1.0, size=(20, 3))
        results[pct] = {
            "effect_draws": effect_draws,
            "ci_2.5": np.percentile(effect_draws, 2.5, axis=0),
            "ci_97.5": np.percentile(effect_draws, 97.5, axis=0),
            "excluded_countries": [],
        }
    return results


def _fake_cached_shap(
    dep_var: str, feature_vars: tuple[str, ...], active_model_name: str
):
    """Trains a tiny real RandomForestRegressor (so rf.oob_score_ and
    shap.summary_plot both work against real, well-shaped objects) instead
    of loading the production rf_shap_model.pkl."""
    rng = np.random.default_rng(0)
    X = pd.DataFrame(
        {name: rng.normal(size=30) for name in feature_vars if name != "region"}
    )
    y = X.iloc[:, 0] * 2.0 + rng.normal(scale=0.1, size=30)

    rf = RandomForestRegressor(n_estimators=10, random_state=0, n_jobs=1, oob_score=True)
    rf.fit(X, y)

    shap_values = rng.normal(size=X.shape)
    return rf, shap_values, X, None


def test_side_by_side_comparison(monkeypatch, tiny_panel_engine, tiny_panel_df):
    """DASH-03/D-02: the "Mapa e indicadores" tab renders two independent
    choropleths with distinct indicator_left/indicator_right selectbox
    keys, and the whole 4-tab app runs without raising (no
    DuplicateWidgetID, no other exception)."""
    fake_results = _FakePanelEffectsResults(tiny_panel_df, "6.4.2")

    monkeypatch.setattr(data, "get_engine", lambda: tiny_panel_engine)
    monkeypatch.setattr(data, "load_panel_clean", lambda engine: tiny_panel_df)
    monkeypatch.setattr(data, "load_model", lambda pkl_path: fake_results)
    monkeypatch.setattr(data, "cached_bootstrap", _fake_cached_bootstrap)
    monkeypatch.setattr(data, "cached_shap", _fake_cached_shap)

    at = AppTest.from_file("src/dashboard/app.py", default_timeout=30)
    at.run()

    assert not at.exception, f"App raised on first run: {at.exception}"

    selectbox_keys = {sb.key for sb in at.selectbox}
    assert "indicator_left" in selectbox_keys
    assert "indicator_right" in selectbox_keys

    tab_labels = [t.label for t in at.tabs]
    assert tab_labels == [
        "Mapa e indicadores",
        "Modelo 1",
        "Simulación",
        "Interpretabilidad (SHAP)",
    ]


def test_active_model_selector_defaults_to_modelo_1(
    monkeypatch, tiny_panel_engine, tiny_panel_df
):
    """D-07: the sidebar exposes a ``st.sidebar.selectbox`` keyed
    ``active_model_name`` with options equal to ``models.ACTIVE_MODELS``'s
    keys (in dict order), defaulting to Modelo 1 (PIB per cápita)."""
    fake_results = _FakePanelEffectsResults(tiny_panel_df, "6.4.2")

    monkeypatch.setattr(data, "get_engine", lambda: tiny_panel_engine)
    monkeypatch.setattr(data, "load_panel_clean", lambda engine: tiny_panel_df)
    monkeypatch.setattr(data, "load_model", lambda pkl_path: fake_results)
    monkeypatch.setattr(data, "cached_bootstrap", _fake_cached_bootstrap)
    monkeypatch.setattr(data, "cached_shap", _fake_cached_shap)

    at = AppTest.from_file("src/dashboard/app.py", default_timeout=30)
    at.run()

    assert not at.exception, f"App raised on first run: {at.exception}"

    selector = at.sidebar.selectbox(key="active_model_name")
    assert list(selector.options) == list(models.ACTIVE_MODELS.keys())
    assert selector.value == "Modelo 1 (PIB per cápita)"


def test_modelo_2_selection_shows_reduced_coverage_caption(
    monkeypatch, tiny_panel_engine, tiny_panel_df
):
    """D-08: selecting Modelo 2 in the sidebar and rerunning must make
    ``MODEL2_COVERAGE_CAPTION``'s text appear somewhere in the rendered
    output (all 4 tabs render it at the top of their body)."""
    fake_results = _FakePanelEffectsResults(tiny_panel_df, "6.4.2")

    monkeypatch.setattr(data, "get_engine", lambda: tiny_panel_engine)
    monkeypatch.setattr(data, "load_panel_clean", lambda engine: tiny_panel_df)
    monkeypatch.setattr(data, "load_model", lambda pkl_path: fake_results)
    monkeypatch.setattr(data, "cached_bootstrap", _fake_cached_bootstrap)
    monkeypatch.setattr(data, "cached_shap", _fake_cached_shap)

    at = AppTest.from_file("src/dashboard/app.py", default_timeout=30)
    at.run()

    at.sidebar.selectbox(key="active_model_name").select(
        "Modelo 2 (Productividad agrícola)"
    ).run()

    assert not at.exception, f"App raised after selecting Modelo 2: {at.exception}"

    caption_texts = [c.value for c in at.caption]
    assert any(
        "muestra reducida a 39 países" in text for text in caption_texts
    ), "Expected the D-08 reduced-coverage caption text somewhere in the rendered captions"


def test_modelo_1_selection_never_shows_reduced_coverage_caption(
    monkeypatch, tiny_panel_engine, tiny_panel_df
):
    """D-08: the reduced-coverage caption must NEVER appear when Modelo 1
    (the default selection) is active."""
    fake_results = _FakePanelEffectsResults(tiny_panel_df, "6.4.2")

    monkeypatch.setattr(data, "get_engine", lambda: tiny_panel_engine)
    monkeypatch.setattr(data, "load_panel_clean", lambda engine: tiny_panel_df)
    monkeypatch.setattr(data, "load_model", lambda pkl_path: fake_results)
    monkeypatch.setattr(data, "cached_bootstrap", _fake_cached_bootstrap)
    monkeypatch.setattr(data, "cached_shap", _fake_cached_shap)

    at = AppTest.from_file("src/dashboard/app.py", default_timeout=30)
    at.run()

    assert not at.exception

    caption_texts = [c.value for c in at.caption]
    assert not any("muestra reducida a 39 países" in text for text in caption_texts)


def test_missing_panel_shows_ui_spec_error(monkeypatch):
    """The app must degrade gracefully with the verbatim UI-SPEC st.error
    copy (and stop) if the top-level panel.db/panel_clean load fails --
    never a raw traceback in front of the tribunal."""

    def _raise(*args, **kwargs):
        raise RuntimeError("simulated missing panel.db")

    monkeypatch.setattr(data, "get_engine", _raise)

    at = AppTest.from_file("src/dashboard/app.py", default_timeout=30)
    at.run()

    assert not at.exception
    error_texts = [e.value for e in at.error]
    assert any("No se pudieron cargar los datos del panel" in text for text in error_texts)
