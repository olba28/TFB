from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor

from src import interpret

ACCENT_COLOR = "#1B6CA8"

_FIGURE_MARGIN = dict(l=4, r=4, b=8, t=32)


def build_choropleth(df: pd.DataFrame, indicator_col: str, title: str) -> go.Figure:
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
    return interpret.partial_dependence_plots(rf, X, features, ax=ax)
