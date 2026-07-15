"""Streamlit entry point for the Phase 5 dashboard (D-06, DASH-01, DASH-02,
DASH-03). This module is the ONLY place in the project that imports
``streamlit`` for rendering purposes -- it is deliberately kept to
layout/orchestration only, calling into the cached data layer
(:mod:`src.dashboard.data`), the pure Plotly figure builders
(:mod:`src.dashboard.plots`), and the active-model registry
(:mod:`src.dashboard.models`) rather than doing SQL/pickle I/O or figure
math itself (05-PATTERNS.md, D-06 controller-separation).

Single-page, four-tab layout (D-06): "Mapa e indicadores" (D-02's
side-by-side choropleth comparison), "Modelo 1", "Simulación", and
"Interpretabilidad (SHAP)". ``st.tabs`` is used instead of a multipage app
so all four sections share Streamlit's cache/session state without
``st.session_state`` bookkeeping (D-06).

DASH-01: this module reads ONLY local artifacts through
:mod:`src.dashboard.data` (``data/panel.db``, ``data/modelos/*.pkl``) --
never the UN SDG API. ``tests/dashboard/test_no_live_api.py`` statically
enforces the absence of ``requests``/``httpx``/``src.ingesta`` anywhere
under ``src/dashboard/``.

"Modelo 1" reads the coefficient/diagnostic table straight from the
deserialized ``PanelEffectsResults`` (``model1_gdp.pkl``, no reajuste).
"Simulación" and "Interpretabilidad (SHAP)" call D-03's cached live-recompute
wrappers (``data.cached_bootstrap``/``data.cached_shap``) -- the bootstrap
counterfactual and SHAP analysis are recomputed inside the dashboard, never
precomputed to a dedicated artifact, but always through
:mod:`src.dashboard.data`'s ``st.cache_data``/``st.cache_resource`` split so
repeat interactions never re-read ``panel.db``/re-run the computation
(DASH-02). The SHAP tab computes the Phase-2 VIF/correlation caveat via
``interpret.compute_vif_table`` BEFORE the SHAP summary plot, matching
INTERP-04's precedence requirement.
"""

from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import streamlit as st

from src import interpret, panel_base
from src.dashboard import data, models, plots

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

ACTIVE_MODEL_NAME = st.sidebar.selectbox(
    "Modelo activo",
    list(models.ACTIVE_MODELS.keys()),
    key="active_model_name",
)
ACTIVE_MODEL = models.ACTIVE_MODELS[ACTIVE_MODEL_NAME]


def _model2_coverage_caption() -> str:
    """Build the reduced-coverage caption with country counts computed at
    runtime (06-REVIEW.md WR-03) rather than hardcoded literals that could
    silently drift out of sync with the actual data (e.g. after a UN SDG API
    refresh regenerates ``panel_clean``). Model 1's count reuses
    ``panel_base.filter_by_exclusions`` (the same function Model 1's own
    exclusion pipeline calls); Model 2's count reuses
    ``panel_base.filter_by_min_years`` (the same function
    ``model2_agri.build_model2_panel`` calls) -- both against ``df``/
    ``panel_exclusions``, already loaded/cached, so no extra DB query is
    introduced beyond the existing ``st.cache_data`` loaders.
    """
    model1_cfg = models.ACTIVE_MODELS["Modelo 1 (PIB per cápita)"]
    model2_cfg = models.ACTIVE_MODELS["Modelo 2 (Productividad agrícola)"]

    exclusions = data.load_panel_exclusions(engine)
    model1_panel = panel_base.filter_by_exclusions(
        df, exclusions, model1_cfg["dep_var"], [model1_cfg["indep_var"]]
    )
    n_model1 = model1_panel["country_code"].nunique()

    model2_panel = panel_base.filter_by_min_years(
        df, model2_cfg["dep_var"], [model2_cfg["indep_var"]]
    )
    n_model2 = model2_panel["country_code"].nunique()

    return (
        f"Modelo 2 (productividad agrícola, indicador {model2_cfg['dep_var']}): muestra "
        f"reducida a {n_model2} países con >=3 años observados (vs. {n_model1} del Modelo "
        "1), por la baja frecuencia de reporte del indicador (oleadas "
        "~2010/2013/2016/2020). Ver tabla de cobertura/exclusiones del Modelo 2, Fase 6."
    )


# Gated off the registry's "reduced_coverage" flag (06-REVIEW.md WR-02), not
# brittle display-name string matching
# (ACTIVE_MODEL_NAME.startswith("Modelo 2")) -- computed once here, referenced
# identically across all 4 tabs below. If the display name in models.py is
# ever edited/translated, this caption keeps appearing correctly because it
# no longer depends on the human-readable string at all.
MODEL2_COVERAGE_CAPTION: str | None = None
if ACTIVE_MODEL["reduced_coverage"]:
    try:
        MODEL2_COVERAGE_CAPTION = _model2_coverage_caption()
    except Exception:
        # Fall back to a count-free caption rather than crashing the whole
        # app if the runtime count computation itself fails for some reason
        # (e.g. an unexpected panel_exclusions schema) -- still communicates
        # the reduced-coverage caveat to the tribunal (D-08).
        MODEL2_COVERAGE_CAPTION = (
            "Modelo 2 (productividad agrícola, indicador 2.3.1): muestra reducida "
            "frente al Modelo 1 -- ver tabla de cobertura/exclusiones del Modelo 2, "
            "Fase 6."
        )

NO_DATA_CAPTION = (
    "Los países en gris no disponen de datos suficientes para este indicador "
    "o fueron excluidos por cobertura mínima (ver Fase 2)."
)

tab_mapa, tab_modelo1, tab_simulacion, tab_shap = st.tabs(
    ["Mapa e indicadores", "Modelo 1", "Simulación", "Interpretabilidad (SHAP)"]
)

# --- Tab 1: Mapa e indicadores (DASH-03/D-02) -------------------------------
with tab_mapa:
    if MODEL2_COVERAGE_CAPTION:
        st.caption(MODEL2_COVERAGE_CAPTION)
    st.subheader("Comparación de indicadores")

    # D-01: the mappable layers are the 5 raw ODS indicators plus the active
    # model's fitted values (a country-year scalar, joinable onto the panel
    # like any other indicator column). The simulation/SHAP layers (D-01
    # layers 3-4) are not a single scalar per country-year and are surfaced
    # in their own tabs below instead of on this map.
    map_options: dict[str, str] = dict(models.INDICATOR_LABELS)
    map_df = df
    fitted_col = "_modelo1_valores_ajustados"
    fitted_label = f"{ACTIVE_MODEL_NAME}: valores ajustados ({ACTIVE_MODEL['dep_var']})"
    try:
        fitted_results = data.load_model(ACTIVE_MODEL["pkl_path"])
        fitted_long = fitted_results.fitted_values.reset_index().rename(
            columns={"fitted_values": fitted_col}
        )
        map_df = df.merge(fitted_long, on=["country_code", "year"], how="left")
        map_options[fitted_col] = fitted_label
    except Exception:
        st.caption(
            "No se pudieron cargar los valores ajustados del Modelo 1 -- se "
            "muestran solo los indicadores crudos del panel."
        )

    option_keys = list(map_options.keys())

    col_left, col_right = st.columns(2, gap="large")
    with col_left:
        indicator_left = st.selectbox(
            "Indicador (izquierda)",
            option_keys,
            format_func=lambda k: map_options[k],
            key="indicator_left",
        )
        st.plotly_chart(
            plots.build_choropleth(map_df, indicator_left, map_options[indicator_left]),
            use_container_width=True,
            key="choropleth_left",
        )
        st.caption(NO_DATA_CAPTION)

    with col_right:
        default_right_index = 1 if len(option_keys) > 1 else 0
        indicator_right = st.selectbox(
            "Indicador (derecha)",
            option_keys,
            index=default_right_index,
            format_func=lambda k: map_options[k],
            key="indicator_right",
        )
        st.plotly_chart(
            plots.build_choropleth(map_df, indicator_right, map_options[indicator_right]),
            use_container_width=True,
            key="choropleth_right",
        )
        st.caption(NO_DATA_CAPTION)

# --- Tab 2: Modelo 1 ---------------------------------------------------------
with tab_modelo1:
    if MODEL2_COVERAGE_CAPTION:
        st.caption(MODEL2_COVERAGE_CAPTION)
    st.subheader(f"{ACTIVE_MODEL_NAME}: coeficientes y diagnósticos")
    try:
        res = data.load_model(ACTIVE_MODEL["pkl_path"])
        ci = res.conf_int()
        coef_table = pd.DataFrame(
            {
                "coeficiente": res.params,
                "error_std": res.std_errors,
                "IC 2.5%": ci["lower"],
                "IC 97.5%": ci["upper"],
                "p-valor": res.pvalues,
            }
        )
        st.dataframe(coef_table, use_container_width=True)
        st.caption(
            f"R² (within): {res.rsquared_within:.4f} · N observaciones: {res.nobs} "
            "(efectos fijos bidireccionales, panel_base.fit_panel_model)."
        )
    except Exception:
        st.error(ARTIFACT_ERROR_MSG)

# --- Tab 3: Simulación (D-03) -------------------------------------------------
with tab_simulacion:
    if MODEL2_COVERAGE_CAPTION:
        st.caption(MODEL2_COVERAGE_CAPTION)
    st.subheader("Simulación contrafactual (análisis de sensibilidad)")
    st.caption(
        "Escenarios de reducción del estrés hídrico sobre el valor de 2022 de "
        "cada país, con intervalos de confianza bootstrap (block bootstrap por "
        "país). No es una predicción individual por país -- ver limitaciones "
        "metodológicas, Fase 4."
    )
    try:
        results = data.cached_bootstrap(
            dep_var=ACTIVE_MODEL["dep_var"],
            indep_var=ACTIVE_MODEL["indep_var"],
            active_model_name=ACTIVE_MODEL_NAME,
        )
        fig_scenario = plots.build_scenario_plot(
            results,
            f"Efecto simulado del estrés hídrico sobre {models.INDICATOR_LABELS[ACTIVE_MODEL['dep_var']]}",
        )
        st.plotly_chart(fig_scenario, use_container_width=True)

        pcts = sorted(results.keys())
        metric_cols = st.columns(len(pcts))
        for metric_col, pct in zip(metric_cols, pcts):
            scenario = results[pct]
            central = float(np.mean(scenario["effect_draws"]))
            ci_low = float(np.mean(scenario["ci_2.5"]))
            ci_high = float(np.mean(scenario["ci_97.5"]))
            with metric_col:
                st.metric(
                    label=f"Escenario {pct:+.0%}",
                    value=f"{central:.4f}",
                    delta=f"IC95%: [{ci_low:.4f}, {ci_high:.4f}]",
                    delta_color="off",
                )
    except Exception:
        st.error(ARTIFACT_ERROR_MSG)

# --- Tab 4: Interpretabilidad (SHAP) (D-03, INTERP-04) ------------------------
with tab_shap:
    if MODEL2_COVERAGE_CAPTION:
        st.caption(MODEL2_COVERAGE_CAPTION)
    st.subheader("Interpretabilidad (SHAP)")
    try:
        indicator_cols = list(models.INDICATOR_LABELS.keys())
        vif_table = interpret.compute_vif_table(df, indicator_cols)
        st.caption(
            "Antes de interpretar los valores SHAP, se revisa la "
            "multicolinealidad (VIF) entre los 5 indicadores ODS -- reproduce "
            "la comprobación de precedencia de la Fase 2 (INTERP-04)."
        )
        st.dataframe(vif_table, use_container_width=True)

        feature_vars = tuple(ACTIVE_MODEL["feature_vars"])
        rf, shap_values, X_shap, _explainer = data.cached_shap(
            dep_var=ACTIVE_MODEL["dep_var"],
            feature_vars=feature_vars,
            active_model_name=ACTIVE_MODEL_NAME,
        )
        st.caption(f"R² OOB del RandomForest de referencia: {rf.oob_score_:.4f}")

        shap.summary_plot(
            shap_values,
            X_shap,
            show=False,
            plot_size=(10, 0.4 * X_shap.shape[1] + 2),
        )
        fig_shap = plt.gcf()
        fig_shap.tight_layout()
        st.pyplot(fig_shap)
        plt.close(fig_shap)
    except Exception:
        st.error(ARTIFACT_ERROR_MSG)

# Cold-start timing readout, logged once after the first full render.
if not st.session_state["cold_start_logged"]:
    elapsed = time.perf_counter() - st.session_state["app_start_time"]
    st.sidebar.caption(f"Carga en frío: {elapsed:.2f}s")
    st.session_state["cold_start_logged"] = True
