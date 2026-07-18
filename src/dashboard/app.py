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


MODEL2_COVERAGE_CAPTION: str | None = None
if ACTIVE_MODEL["reduced_coverage"]:
    try:
        MODEL2_COVERAGE_CAPTION = _model2_coverage_caption()
    except Exception:
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

with tab_mapa:
    if MODEL2_COVERAGE_CAPTION:
        st.caption(MODEL2_COVERAGE_CAPTION)
    st.subheader("Comparación de indicadores")

    map_options: dict[str, str] = dict(models.INDICATOR_LABELS)
    map_df = df
    fitted_col = "_modelo_valores_ajustados"
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

if not st.session_state["cold_start_logged"]:
    elapsed = time.perf_counter() - st.session_state["app_start_time"]
    st.sidebar.caption(f"Carga en frío: {elapsed:.2f}s")
    st.session_state["cold_start_logged"] = True
