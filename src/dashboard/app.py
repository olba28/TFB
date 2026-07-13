"""Streamlit entry point for the Phase 5 dashboard (D-06, DASH-01, DASH-02,
DASH-03). This module is the ONLY place in the project that imports
``streamlit`` for rendering purposes -- it is deliberately kept to
layout/orchestration only, calling into the cached data layer
(:mod:`src.dashboard.data`), the pure Plotly figure builders
(:mod:`src.dashboard.plots`), and the active-model registry
(:mod:`src.dashboard.models`) rather than doing SQL/pickle I/O or figure
math itself (05-PATTERNS.md, D-06 controller-separation).

Single-page, four-tab layout (D-06): "Mapa e indicadores" (D-02's
side-by-side choropleth comparison, filled in a later task of this plan),
"Modelo 1", "Simulación", and "Interpretabilidad (SHAP)". ``st.tabs`` is
used instead of a multipage app so all four sections share Streamlit's
cache/session state without ``st.session_state`` bookkeeping (D-06).

DASH-01: this module reads ONLY local artifacts through
:mod:`src.dashboard.data` (``data/panel.db``, ``data/modelos/*.pkl``) --
never the UN SDG API. ``tests/dashboard/test_no_live_api.py`` statically
enforces the absence of ``requests``/``httpx``/``src.ingesta`` anywhere
under ``src/dashboard/``.

This is Task 1 of 05-04-PLAN.md: page config, title/caption, the 4 D-06 tab
labels, the top-level artifact-load error handling (UI-SPEC), and the
cold-start timing readout. Tab bodies are filled by Tasks 2-3.
"""

from __future__ import annotations

import time

import streamlit as st

from src.dashboard import data

st.set_page_config(layout="wide")

# Cold-start timing readout (Claude's Discretion, DASH-02) -- logs elapsed
# wall-clock time since the FIRST script execution to a sidebar caption, per
# 05-RESEARCH.md's Code Examples section. ``st.session_state`` survives
# reruns within the same browser session, so this only logs once.
if "app_start_time" not in st.session_state:
    st.session_state["app_start_time"] = time.perf_counter()
    st.session_state["cold_start_logged"] = False

st.title("Impacto Económico del Estrés Hídrico")
st.caption("TFB — Panel de resultados (2000–2022)")

ARTIFACT_ERROR_MSG = (
    "No se pudieron cargar los datos del panel. Verifica que 'data/panel.db' "
    "existe y contiene la tabla 'panel_clean'. Ejecuta primero el pipeline de "
    "ingesta (Fase 1) y de modelado (Fase 3/4) antes de abrir el dashboard."
)

# Top-level artifact load (D-06 shared across all 4 tabs): a broken/missing
# panel.db must show a clear next-step message instead of a raw traceback in
# front of the tribunal (UI-SPEC Copywriting Contract, Error state).
try:
    engine = data.get_engine()
    df = data.load_panel_clean(engine)
except Exception:
    st.error(ARTIFACT_ERROR_MSG)
    st.stop()

tab_mapa, tab_modelo1, tab_simulacion, tab_shap = st.tabs(
    ["Mapa e indicadores", "Modelo 1", "Simulación", "Interpretabilidad (SHAP)"]
)

# Placeholder bodies -- filled by Task 2 (Mapa e indicadores) and Task 3
# (Modelo 1 / Simulación / Interpretabilidad SHAP) of 05-04-PLAN.md.
with tab_mapa:
    st.write("Mapa e indicadores -- pendiente de implementación (Task 2).")

with tab_modelo1:
    st.write("Modelo 1 -- pendiente de implementación (Task 3).")

with tab_simulacion:
    st.write("Simulación -- pendiente de implementación (Task 3).")

with tab_shap:
    st.write("Interpretabilidad (SHAP) -- pendiente de implementación (Task 3).")

# Cold-start timing readout, logged once after the first full render.
if not st.session_state["cold_start_logged"]:
    elapsed = time.perf_counter() - st.session_state["app_start_time"]
    st.sidebar.caption(f"Carga en frío: {elapsed:.2f}s")
    st.session_state["cold_start_logged"] = True
