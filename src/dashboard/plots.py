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
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
