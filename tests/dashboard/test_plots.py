"""Tests for src/dashboard/plots.py: the pure Plotly/Matplotlib figure
builders (DASH-04, 05-CONTEXT.md D-05). Covers the animated choropleth's
fixed 23-year, fixed-color-range contract (Pitfall 4), the scenario CI plot's
accent-colored central estimate, and build_pdp's pure delegation to
interpret.partial_dependence_plots (INTERP-05).

Mirrors tests/test_interpret.py's house style: one def test_<behavior>() per
behavior, docstring-per-test. Uses the tiny_panel_df fixture from
tests/dashboard/conftest.py -- never the real 215-country data/panel.db.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src import interpret
from src.dashboard import plots


def _make_synthetic_scenario_results() -> dict:
    """A synthetic dict shaped exactly like
    simulate.bootstrap_counterfactual's return value: keyed by signed
    reduction pct, each value carrying effect_draws (n_replicas x
    n_surviving_countries), ci_2.5, and ci_97.5 -- deterministic via a fixed
    rng, no dependency on simulate.py itself (keeps plots.py's tests fast
    and isolated from the bootstrap's own runtime)."""
    rng = np.random.default_rng(0)
    results = {}
    for pct in (-0.10, -0.20, -0.30):
        effect_draws = rng.normal(loc=pct * 10, scale=1.0, size=(50, 4))
        results[pct] = {
            "effect_draws": effect_draws,
            "ci_2.5": np.percentile(effect_draws, 2.5, axis=0),
            "ci_97.5": np.percentile(effect_draws, 97.5, axis=0),
            "excluded_countries": [],
        }
    return results


# --- build_choropleth() (DASH-04) ------------------------------------------


def test_choropleth_has_all_years(tiny_panel_df):
    """DASH-04, 05-RESEARCH.md Pitfall 4: build_choropleth's animation must
    cover exactly the 23 years 2000-2022 (one frame per year present in
    tiny_panel_df), and the coloraxis range must be FIXED to the indicator's
    global min/max across all years -- not auto-scaled per frame.
    """
    fig = plots.build_choropleth(tiny_panel_df, "6.4.2", "Estrés hídrico")

    years_in_frames = sorted(int(frame.name) for frame in fig.frames)
    assert years_in_frames == list(range(2000, 2023))
    assert len(fig.frames) == 23

    assert fig.layout.coloraxis.cmin == tiny_panel_df["6.4.2"].min()
    assert fig.layout.coloraxis.cmax == tiny_panel_df["6.4.2"].max()


def test_choropleth_uses_iso3_locationmode(tiny_panel_df):
    """build_choropleth must bind locations to the country_code column with
    locationmode="ISO-3" -- panel_clean.country_code is already ISO3, no
    transform needed."""
    fig = plots.build_choropleth(tiny_panel_df, "6.4.2", "Estrés hídrico")

    assert fig.data[0].locationmode == "ISO-3"
    assert set(fig.data[0].locations).issubset(set(tiny_panel_df["country_code"].unique()))


# --- build_scenario_plot() / build_pdp() -----------------------------------


def test_scenario_plot_has_ci_error_bars():
    """build_scenario_plot must render one point per scenario key, with
    asymmetric error bars derived from each scenario's ci_2.5/ci_97.5
    bounds."""
    results = _make_synthetic_scenario_results()

    fig = plots.build_scenario_plot(results, "Simulación de escenarios")

    trace = fig.data[0]
    assert len(trace.x) == len(results)
    assert len(trace.y) == len(results)
    assert trace.error_y is not None
    assert trace.error_y.array is not None
    assert trace.error_y.arrayminus is not None
    assert len(trace.error_y.array) == len(results)
    assert len(trace.error_y.arrayminus) == len(results)


def test_scenario_plot_uses_accent_color():
    """The central-estimate marker must use the UI-SPEC accent color
    (#1B6CA8), never the choropleth's Viridis data-color scale."""
    results = _make_synthetic_scenario_results()

    fig = plots.build_scenario_plot(results, "Simulación de escenarios")

    assert fig.data[0].marker.color == "#1B6CA8"


def test_build_pdp_delegates(monkeypatch):
    """build_pdp must delegate to interpret.partial_dependence_plots with
    the same arguments and return exactly what it returns (INTERP-05 -- no
    reimplementation of PDP math)."""
    sentinel = object()
    captured = {}

    def fake_partial_dependence_plots(rf, X, features, ax=None):
        captured["args"] = (rf, X, features, ax)
        return sentinel

    monkeypatch.setattr(interpret, "partial_dependence_plots", fake_partial_dependence_plots)

    rf_stub = object()
    X_df = pd.DataFrame({"a": [1, 2, 3]})
    features_list = ["a"]

    result = plots.build_pdp(rf_stub, X_df, features_list)

    assert result is sentinel
    assert captured["args"] == (rf_stub, X_df, features_list, None)


# --- static purity guard ----------------------------------------------------


def test_plots_module_has_no_streamlit_import():
    """plots.py must stay pure -- no Streamlit import anywhere in the
    module's source text -- so every builder is testable under plain pytest
    without launching Streamlit. Checks for the actual import statement
    (not the word "streamlit", which legitimately appears in prose within
    the module's own docstring)."""
    source_path = Path(__file__).resolve().parents[2] / "src" / "dashboard" / "plots.py"
    source = source_path.read_text(encoding="utf-8")

    assert "import streamlit" not in source
    assert "from streamlit" not in source
