"""Pure Plotly/Matplotlib figure builders for the Streamlit dashboard
(DASH-04, 05-CONTEXT.md D-05). Every function here is a pure transform --
DataFrame/result-dict in, a ``plotly.graph_objects.Figure`` (or a delegated
matplotlib display) out -- with NO ``st.*`` calls and NO I/O, mirroring the
pure-vs-IO separation already established by ``src/panel_base.py`` (pure) vs
``src/db.py`` (IO). This keeps every builder unit-testable under plain
pytest, without launching Streamlit.

``build_choropleth`` (DASH-04): an animated choropleth over the full
2000-2022 year range using Plotly's native ``animation_frame="year"``
mechanism (D-05 -- no custom Streamlit slider). ``range_color`` is fixed to
the indicator's GLOBAL min/max computed once across ALL years before
building the figure -- Plotly Express does NOT compute the union of
per-frame color ranges automatically, so without an explicit fixed range the
color scale would jump between animation frames (05-RESEARCH.md Pitfall 4).
``locationmode="ISO-3"`` matches ``panel_clean.country_code``, which is
already ISO3 (no transform needed).

``build_scenario_plot``: consumes the dict returned by
``simulate.bootstrap_counterfactual`` (keyed by the signed reduction pct,
e.g. -0.10/-0.20/-0.30; each value carrying ``effect_draws``/``ci_2.5``/
``ci_97.5``). Framed explicitly as a sensitivity analysis over scenarios
(matches Phase 4's INTERP-03 "coefficient table, never a per-country
prediction" framing) -- the central estimate and CI bounds plotted are
aggregated ACROSS surviving countries (mean), giving one overall sensitivity
number per scenario rather than a per-country figure. Uses the UI-SPEC
accent color (``#1B6CA8``) for the central-estimate marker.

``build_pdp`` is a thin delegating wrapper over
``interpret.partial_dependence_plots`` -- it does NOT reimplement PDP math
(INTERP-05 already owns it). The SHAP summary plot is deliberately NOT
wrapped here: it uses SHAP's own default palette and is rendered directly in
the app tab (UI-SPEC SHAP exception), so no SHAP-recoloring builder exists in
this module.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor

from src import interpret

# UI-SPEC accent color (#1B6CA8) -- reserved for the central-estimate marker
# in the scenario plot; never used as the choropleth's data-color scale.
ACCENT_COLOR = "#1B6CA8"

# UI-SPEC spacing scale: xs=4px, sm=8px, xl=32px (figure has its own title).
_FIGURE_MARGIN = dict(l=4, r=4, b=8, t=32)


def build_choropleth(df: pd.DataFrame, indicator_col: str, title: str) -> go.Figure:
    """Animated choropleth (DASH-04) over every year present in ``df`` for
    ``indicator_col``, using Plotly's native ``animation_frame="year"``
    (D-05) so play/pause/slider controls are generated automatically -- no
    custom Streamlit slider.

    ``range_color`` is computed from ``df[indicator_col].min()/.max()``
    across the FULL year range passed in (2000-2022 in production), NOT
    per-frame -- Plotly Express does not compute the union of per-frame
    color ranges automatically, so without an explicit fixed range the color
    scale would jump between animation frames (05-RESEARCH.md Pitfall 4).

    ``locationmode="ISO-3"`` binds to the ``country_code`` column, which is
    already ISO3 in ``panel_clean`` -- no transformation needed.

    Pure function: no ``st.*`` call, no I/O. ``df`` must already be loaded
    by the caller (e.g. via ``dashboard.data``).
    """
    fig = px.choropleth(
        df,
        locations="country_code",
        locationmode="ISO-3",
        color=indicator_col,
        animation_frame="year",
        range_color=(df[indicator_col].min(), df[indicator_col].max()),
        color_continuous_scale="Viridis",
        title=title,
    )
    fig.update_layout(margin=_FIGURE_MARGIN)
    return fig


def build_scenario_plot(results: dict, title: str) -> go.Figure:
    """Multi-scenario central estimate + bootstrap CI plot (INTERP-03
    framing) from ``simulate.bootstrap_counterfactual``'s output dict (keyed
    by signed reduction pct, e.g. -0.10/-0.20/-0.30; each value carrying
    ``effect_draws`` (n_replicas x n_surviving_countries), ``ci_2.5``, and
    ``ci_97.5``).

    Aggregation choice (documented explicitly, Claude's Discretion): each
    scenario's central estimate is the mean of ``effect_draws`` across BOTH
    bootstrap replicas AND surviving countries -- a single overall
    sensitivity number per scenario, consistent with this project's
    "simulación de sensibilidad, no predicción por país" framing (never a
    per-country predicted value). The asymmetric error-bar bounds are the
    across-country mean of the per-country ``ci_2.5``/``ci_97.5`` percentile
    bounds.

    The central-estimate marker uses the UI-SPEC accent color (``#1B6CA8``).
    Pure function: no ``st.*`` call, no I/O.
    """
    pcts = sorted(results.keys())
    centrals: list[float] = []
    err_plus: list[float] = []
    err_minus: list[float] = []
    for pct in pcts:
        scenario = results[pct]
        central = float(np.mean(scenario["effect_draws"]))
        ci_low = float(np.mean(scenario["ci_2.5"]))
        ci_high = float(np.mean(scenario["ci_97.5"]))
        centrals.append(central)
        err_plus.append(max(ci_high - central, 0.0))
        err_minus.append(max(central - ci_low, 0.0))

    labels = [f"{pct:+.0%}" for pct in pcts]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=centrals,
            mode="markers",
            marker=dict(color=ACCENT_COLOR, size=10),
            error_y=dict(
                type="data",
                symmetric=False,
                array=err_plus,
                arrayminus=err_minus,
            ),
            name="Estimación central",
        )
    )
    fig.update_layout(
        title=title,
        xaxis=dict(
            title="Escenario (reducción del estrés hídrico)",
            type="category",
        ),
        yaxis_title="Efecto simulado sobre la variable dependiente",
        margin=_FIGURE_MARGIN,
    )
    return fig


def build_pdp(
    rf: RandomForestRegressor,
    X: pd.DataFrame,
    features: list[str],
    ax: Any | None = None,
):
    """Thin wrapper (INTERP-05) delegating to
    ``interpret.partial_dependence_plots`` -- does NOT reimplement PDP math,
    which ``interpret.py`` already owns. Returns exactly what
    ``interpret.partial_dependence_plots`` returns, for embedding by the
    caller (the SHAP/Interpretabilidad tab).

    Pure function: no ``st.*`` call, no I/O.
    """
    return interpret.partial_dependence_plots(rf, X, features, ax=ax)
