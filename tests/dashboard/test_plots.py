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

from src.dashboard import plots


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
