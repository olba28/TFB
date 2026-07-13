# Phase 5: Dashboard y Preparación de la Defensa - Research

**Researched:** 2026-07-13
**Domain:** Streamlit + Plotly local dashboard consuming pre-computed artifacts (SQLite, pickled models), with cached live recomputation and a pre-rendered offline backup
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** El dashboard cubre las **cuatro capas** discutidas, no solo los indicadores crudos: (1) los 5 indicadores ODS (`6.4.2`, `6.4.1`, `8.1.1`, `8.2.1`, `2.3.1`) tal cual del panel; (2) salidas del Modelo 1 (valores ajustados/coeficientes de `model1_gdp.pkl`); (3) resultados de la simulación contrafactual (escenarios -10/-20/-30% con CIs bootstrap de `simulate.py`); (4) interpretabilidad SHAP (`rf_shap_model.pkl` vía `interpret.py`). El usuario quiere el dashboard como vitrina completa de todo el trabajo de Fases 3–4, no solo un visor de datos.
- **D-02:** "Comparar dos indicadores lado a lado" (DASH-03) significa **dos choropleths del mismo año, uno junto al otro**, cada uno con su propio selector de indicador/serie (puede ser cualquier combinación de las 4 capas de D-01) — no un scatter de correlación.
- **D-03:** La simulación bootstrap y el análisis SHAP se **recalculan en vivo dentro del dashboard**, envueltos en `@st.cache_data`/`@st.cache_resource`, invocando directamente `simulate.bootstrap_counterfactual`/`interpret.shap_analysis` — no se crea un artefacto de precómputo dedicado ni se reutiliza `data/modelos/_repro_snapshot.pkl` (exclusivo de `scripts/verify_repro02.py`/REPRO-02, gitignored y sobrescrito en cada ejecución de verificación). El cálculo en vivo cumple DASH-01 porque solo lee `panel.db` local y modelos ya ajustados, nunca llama a la API de la ONU.
- **D-04:** El cache no usa TTL — es permanente durante la sesión de demo (`@st.cache_data`/`@st.cache_resource` sin parámetro `ttl`). No hace falta botón de recarga manual.
- **D-05:** La animación usa el mecanismo **nativo de Plotly** (`px.choropleth(..., animation_frame="year")`), con los controles de play/pause/slider generados automáticamente — no un slider manual de Streamlit.
- **D-06:** Una **sola app Streamlit** (`src/dashboard/app.py`) organizada con `st.tabs()`: pestañas "Mapa e indicadores", "Modelo 1", "Simulación", "Interpretabilidad (SHAP)". No multipágina.
- **D-07:** El dashboard se diseña con un **parámetro de "modelo activo"** desde esta fase (qué `dep_var`/`.pkl` cargar), aunque el selector visible solo muestre "Modelo 1" por ahora. Fase 6 solo añade la opción "Modelo 2" al selector existente, sin reestructurar `app.py`.
- **D-08:** El respaldo son **capturas de pantalla** (PNG/PDF) de cada pestaña con datos reales — no un vídeo grabado.

### Claude's Discretion

- Estructura interna exacta de `src/dashboard/` (un solo `app.py` vs. `app.py` + `plots.py`/`data.py` auxiliares) — libre mientras sea una sola app Streamlit con pestañas (D-06).
- Paleta de colores y estilo visual exacto del choropleth — libre mientras sea legible y consistente entre pestañas.
- Mecanismo exacto del parámetro "modelo activo" (dict de configuración, función factory, clase) — libre mientras permita que Fase 6 añada Modelo 2 sin tocar la estructura de `app.py` (D-07).
- Momento exacto de generación de las capturas de plan B (script dedicado vs. manual) — libre mientras se generen antes de la defensa con datos reales (D-08).
- Medición concreta del tiempo de carga en frío (<5s, DASH-02) — libre el método de medición (manual con cronómetro, `time.perf_counter` logueado) mientras se documente el resultado.

### Deferred Ideas (OUT OF SCOPE)

None — la discusión se mantuvo dentro del alcance de la Fase 5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| DASH-01 | Choropleth por país consumiendo únicamente artefactos ya calculados, sin llamadas en tiempo real a la API | Architecture Patterns (data access via `src/db.py::get_engine()` + pickled models); Security Domain (no network calls); Don't Hand-Roll; Validation Architecture (static/AppTest check for absence of live API calls) |
| DASH-02 | Caché de datos (`st.cache_data`) y de modelo (`st.cache_resource`) para evitar congelaciones en demo | Standard Stack; Architecture Patterns (Pattern 1); Common Pitfalls (1, 2, 8); Code Examples (cached loaders); Environment Availability (cold-start budget) |
| DASH-03 | Comparar múltiples indicadores lado a lado | Architecture Patterns (Pattern 2, `st.columns` with independent keys); Common Pitfalls (3); Code Examples (side-by-side comparison) |
| DASH-04 | Animación temporal del choropleth 2000–2022 | Architecture Patterns (Pattern 4, `animation_frame`); Common Pitfalls (4); Code Examples (choropleth builder) |
| DASH-05 | Ensayo con caché fría en la máquina de presentación + capturas/vídeo de respaldo pre-renderizados | Don't Hand-Roll (kaleido vs. manual capture); Package Legitimacy Audit (kaleido); Common Pitfalls (5); Environment Availability (Chrome dependency) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Stack fijo:** Python 3.12, dependencias en `requirements.txt`/`requirements.lock.txt` (streamlit, plotly ya pinned) — no añadir librerías sin justificación explícita en el plan.
- **Windows sin GDAL:** el proyecto evitó deliberadamente geopandas/folium; Plotly `px.choropleth` no requiere GDAL — confirmado en esta investigación (ver State of the Art / Environment Availability).
- **Solo API ODS de la ONU como fuente de datos** — el dashboard NUNCA debe llamar a la API en tiempo real (coincide con DASH-01 y con "Out of Scope: Ingesta en tiempo real" de REQUIREMENTS.md).
- **PEP8 vía Ruff** (formato automático al guardar); **type hints** esperados en todas las firmas públicas; **docstrings estilo Google** documentando el *porqué*, no el *qué* (patrón ya seguido en `src/db.py`, `src/panel_base.py`, `src/simulate.py`, `src/interpret.py` — mantener la misma voz).
- **GSD Workflow Enforcement:** cualquier edición de archivos debe pasar por `/gsd-execute-phase` (o `/gsd-quick`/`/gsd-debug`), no ediciones directas fuera del flujo GSD.
- **Despliegue:** explícitamente solo local — nunca `server.address=0.0.0.0` ni Streamlit Cloud para esta fase (PROJECT.md, "Out of Scope: Despliegue online del dashboard").

## Summary

Esta fase construye un único proceso Streamlit local (`src/dashboard/app.py`) que es, a la vez, su propio frontend y backend: no hay una API separada. La app lee `data/panel.db` (tablas `panel_clean`/`panel_exclusions` vía `src/db.py::get_engine()`) y dos modelos serializados (`data/modelos/model1_gdp.pkl`, `data/modelos/rf_shap_model.pkl`), y recalcula en vivo — pero cacheado — la simulación bootstrap (`src/simulate.py::bootstrap_counterfactual`) y el análisis SHAP (`src/interpret.py::shap_analysis`), tal como fija D-03. El patrón de caché correcto es: `st.cache_resource` para objetos no serializables/reutilizables (Engine de SQLAlchemy, modelo `RandomForestRegressor` ya ajustado, `PanelEffectsResults`), `st.cache_data` para resultados tabulares/array (DataFrames de `panel_clean`, arrays de efectos bootstrap, valores SHAP). El error más común y mejor documentado en la comunidad Streamlit es pasar un objeto no-hasheable (Engine, modelo) como parámetro directo de una función `@st.cache_data` sin prefijo `_`; la investigación confirma el patrón correcto — o bien prefijar el parámetro con `_` para excluirlo del hashing, o (más limpio para este proyecto) cargar el recurso pesado con una llamada interna a una función `@st.cache_resource` en vez de recibirlo como argumento.

Para el choropleth animado (D-05), `px.choropleth(..., locations="country_code", locationmode="ISO-3", animation_frame="year", range_color=(min, max))` es el patrón verificado en la documentación oficial de Plotly — `locationmode="ISO-3"` es, además, la opción que Plotly recomienda explícitamente frente a `"country names"` (cuya librería subyacente está cambiando). `range_color` debe fijarse explícitamente con el mínimo/máximo global del indicador a través de todos los años — Plotly Express NO calcula automáticamente la unión de rangos de color entre frames de una animación, así que sin este parámetro la escala de color "salta" entre años.

Para el respaldo Plan B (D-08, DASH-05), la investigación descarta explícitamente introducir Playwright u otra automatización de navegador — es una sobrecarga innecesaria para una demo local de una sola persona. La combinación recomendada es `kaleido` (motor oficial de Plotly para exportar figuras a PNG/PDF, `fig.write_image(...)`) para las figuras Plotly individuales, más una captura manual del navegador (recorte de pantalla o "Imprimir a PDF") para las pestañas completas con sus widgets — sin nueva dependencia pesada. Un hallazgo importante: `kaleido>=1.0` ya NO empaqueta Chromium — requiere Chrome/Chromium instalado por separado en el sistema (o `plotly.io.get_chrome()` para descargarlo), lo cual es directamente relevante para DASH-05's mandato de ensayar en la máquina de presentación real.

**Primary recommendation:** Estructurar `src/dashboard/` en `app.py` (solo layout/tabs) + `data.py` (loaders cacheados) + `plots.py` (constructores de figuras Plotly, funciones puras testables) + `models.py` (registro del "modelo activo", D-07); usar `st.cache_resource` para Engine/modelos/Explainer y `st.cache_data` para DataFrames/arrays de resultados; fijar `range_color` explícito en cada choropleth animado; generar el respaldo Plan B con `kaleido` + captura manual del navegador, verificando Chrome disponible en la máquina de presentación como parte del ensayo ya exigido por DASH-05.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Lectura de `panel.db` / carga de modelos `.pkl` | Backend/proceso local (`src/db.py`, `data/modelos/*.pkl`) | — | Streamlit es un único proceso Python local; no existe una API/backend separado — la propia app es el backend |
| Cómputo en vivo cacheado (bootstrap, SHAP) | Backend/proceso local, envuelto en `@st.cache_data`/`@st.cache_resource` | — | D-03: invoca `simulate.py`/`interpret.py` directamente, cacheado por sesión, nunca contra la API |
| Construcción de figuras Plotly (choropleth, comparación, SHAP) | Backend/proceso local (funciones puras en `plots.py`) | — | La figura se construye en Python antes de enviarse al cliente; debe ser testable sin `st.*` |
| Renderizado de tabs/columnas/widgets | Cliente Streamlit (React, vía WebSocket desde el servidor local) | Backend (el script Python se re-ejecuta completo en cada interacción) | Modelo de ejecución de Streamlit: cada interacción de usuario reejecuta el script de arriba a abajo; el cliente solo pinta el árbol de widgets que el script produce |
| Generación de capturas Plan B | Herramienta offline separada (script/manual, fuera de `app.py`) | — | D-08: no debe vivir en el runtime de la app en vivo; se genera antes de la defensa, con datos reales |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| streamlit | 1.59.1 (pinned, `requirements.lock.txt`) | App/UI framework, `st.tabs`, `st.columns`, `st.cache_data`/`st.cache_resource` | Ya elegido en PROJECT.md/requirements.txt; API estable desde 1.18+ |
| plotly | 6.9.0 (pinned) | `px.choropleth` con `animation_frame` nativo | Sin dependencia de GDAL, estable en Windows (ya justificado en `requirements.txt`) |
| sqlalchemy | ≥2.0 (pinned) | `Engine` para leer `panel_clean`/`panel_exclusions` | Ya usado por `src/db.py::get_engine()` — reutilizar, no reimplementar |
| scikit-learn | 1.9.0 (pinned) | Deserializar `rf_shap_model.pkl` (`RandomForestRegressor`) | El pkl fue serializado con esta versión exacta — un entorno con otra versión emite `InconsistentVersionWarning` (verificado en vivo en esta sesión) |
| linearmodels | 7.0 (pinned) | Deserializar `model1_gdp.pkl` (`PanelEffectsResults`) | Verificado en vivo: `pickle.load` sin `linearmodels` importable falla con `ModuleNotFoundError` |
| shap | 0.52.0 (pinned) | `TreeExplainer` para el análisis SHAP en vivo (D-03) | Ya usado por `src/interpret.py::shap_analysis` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| kaleido | 1.3.0 (última en PyPI; no instalada aún) | Exportar figuras Plotly individuales a PNG/PDF para el respaldo Plan B | Solo si se automatiza la exportación de las figuras Plotly del Plan B (D-08); requiere Chrome/Chromium instalado por separado desde v1 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Captura manual de pantalla/navegador | `kaleido` (solo figuras Plotly) o Playwright (página completa) | `kaleido` no captura el layout completo de Streamlit (tabs, sidebar, widgets) — solo las figuras Plotly; Playwright automatiza la página completa pero añade una dependencia pesada (navegador + driver) injustificada para un artefacto de un solo uso en un proyecto académico individual |
| `st.tabs()` (D-06 ya fija esto) | App multipágina (`pages/`) | Descartado por D-06: comparte cache/estado sin `st.session_state` explícito, un solo proceso más simple de ensayar |
| Registro dict del "modelo activo" | Clase/factory más elaborada | Un dict simple `{nombre: {dep_var, pkl_path, indep_var}}` es suficiente para que Fase 6 añada una entrada sin tocar `app.py` (D-07) — no sobre-diseñar para un único caso de uso adicional conocido |

**Installation:**
```bash
# Solo si se decide automatizar la exportación de figuras Plotly para el Plan B (D-08):
pip install kaleido
python -c "import plotly.io as pio; pio.get_chrome()"   # descarga Chrome for Testing si no hay Chrome/Chromium en el sistema
```

**Version verification:** `streamlit==1.59.1`, `plotly==6.9.0`, `scikit-learn==1.9.0`, `shap==0.52.0`, `linearmodels==7.0` confirmados directamente en `requirements.lock.txt` del repo (ya instalados en `.venv`). `kaleido` no está en `requirements.txt`/`requirements.lock.txt` — verificado vía `pip index versions kaleido` → última versión `1.3.0` en PyPI.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|--------------|---------|-------------|
| kaleido | PyPI | Publicado 2026-05-04 (release 1.3.0) | Desconocido (señal `unknown-downloads`, no es que las descargas sean bajas — el checker no pudo obtener el dato) | `github.com/plotly/kaleido` | `[SUS]` (única razón: `unknown-downloads`) | Flagged — mantenido, planner debe añadir `checkpoint:human-verify` antes de instalar |

**Packages removed due to [SLOP] verdict:** ninguno.
**Packages flagged as suspicious [SUS]:** `kaleido` — el único motivo automático es la falta de dato de descargas, no una señal de paquete malicioso/inexistente. `kaleido` es el motor oficial de exportación estática de Plotly (organización `plotly` en GitHub, mismo mantenedor que la librería `plotly` ya usada en este proyecto, documentado en `plotly.com/python/static-image-export/`). Mismo patrón de falso positivo ya observado en Fase 1 con `pytest` (heurística de recencia de release). Aun así, el planner debe insertar un `checkpoint:human-verify` antes de `pip install kaleido`, siguiendo el protocolo — y solo si se decide automatizar el Plan B en vez de capturas manuales.

*`kaleido` fue descubierto vía documentación oficial de Plotly (`[CITED: plotly.com/python/static-image-export]`), no solo vía WebSearch — pero mantiene el flag `[SUS]` del checker automático y requiere el mismo gate humano.*

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  streamlit run src/dashboard/app.py   (proceso único, localhost)         │
│                                                                            │
│  app.py  ──▶  st.tabs(["Mapa e indicadores","Modelo 1",                  │
│                          "Simulación","Interpretabilidad (SHAP)"])       │
│                                                                            │
│   ┌─ Tab "Mapa e indicadores" ───────────────────────────────────────┐   │
│   │  data.get_engine()  [st.cache_resource]                         │   │
│   │      │                                                           │   │
│   │      ▼                                                           │   │
│   │  data.load_panel_clean(_engine)  [st.cache_data]                │   │
│   │      │  (SELECT * FROM panel_clean — nunca API ONU, DASH-01)    │   │
│   │      ▼                                                           │   │
│   │  st.columns(2)                                                   │   │
│   │   ├─ col izq: selectbox(key="ind_left")  ─▶ plots.build_choropleth ─▶ st.plotly_chart │
│   │   └─ col der: selectbox(key="ind_right") ─▶ plots.build_choropleth ─▶ st.plotly_chart │
│   │      (D-02: dos choropleths independientes, mismo año,           │   │
│   │       animation_frame="year", D-05)                              │   │
│   └───────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│   ┌─ Tab "Modelo 1" ─────────────────────────────────────────────────┐   │
│   │  models.ACTIVE_MODELS["Modelo 1..."]  (registro D-07)            │   │
│   │      │                                                           │   │
│   │      ▼                                                           │   │
│   │  data.load_model(pkl_path)  [st.cache_resource]                 │   │
│   │      │  (pickle.load — model1_gdp.pkl, sin reajuste)             │   │
│   │      ▼                                                           │   │
│   │  Tabla de coeficientes / diagnósticos  ─▶  st.dataframe/st.write │   │
│   └───────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│   ┌─ Tab "Simulación" ───────────────────────────────────────────────┐   │
│   │  data.cached_bootstrap(dep_var, indep_var, reduction_pcts, ...)  │   │
│   │      [st.cache_data]                                             │   │
│   │      │  internamente llama panel_base.fit_panel_model +          │   │
│   │      │  simulate.bootstrap_counterfactual (D-03, sin API)        │   │
│   │      ▼                                                           │   │
│   │  plots.build_scenario_plot(results)  ─▶  st.plotly_chart         │   │
│   └───────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│   ┌─ Tab "Interpretabilidad (SHAP)" ────────────────────────────────┐   │
│   │  data.cached_shap(dep_var, feature_vars)  [st.cache_data]        │   │
│   │      │  internamente llama interpret.shap_analysis (D-03)        │   │
│   │      ▼                                                           │   │
│   │  shap.summary_plot / plots.build_pdp  ─▶  st.pyplot/st.plotly    │   │
│   └───────────────────────────────────────────────────────────────────┘   │
│                                                                            │
└─────────────────────────────────────────────────────────────────────────┘
                     ▲                                    │
                     │ NUNCA llamadas en runtime           │ (offline, antes de la defensa)
                     │                                     ▼
              API SDG de la ONU               scripts/capture_plan_b.py (o manual)
              (solo Fase 1, ingesta)          kaleido.write_image() + captura navegador
                                               ──▶ figuras/plan_b/*.png, *.pdf
```

### Recommended Project Structure

```
src/dashboard/
├── __init__.py
├── app.py       # Entry point: st.set_page_config, st.tabs(), layout/orquestación únicamente
├── data.py      # Loaders cacheados: get_engine (cache_resource), load_panel_clean (cache_data),
│                #  load_model (cache_resource), cached_bootstrap/cached_shap (cache_data) -- D-03/D-04
├── plots.py     # Constructores de figuras Plotly puros (sin llamadas st.*, testables con pytest normal)
└── models.py    # ACTIVE_MODELS: registro dict del "modelo activo" (D-07) -- Fase 6 añade una entrada aquí
```

### Pattern 1: `st.cache_resource` para recursos, `st.cache_data` para datos

**What:** `st.cache_resource` para objetos no serializables/compartidos (Engine SQLAlchemy, modelo ya ajustado, `shap.TreeExplainer`); `st.cache_data` para lo que se puede copiar/serializar (DataFrames, arrays de resultados bootstrap, valores SHAP).
**When to use:** Siempre — es la distinción central que Streamlit documenta explícitamente. `st.cache_resource` devuelve el objeto en sí (compartido, mutaciones visibles globalmente); `st.cache_data` devuelve una copia nueva en cada llamada (seguro contra mutación accidental).
**Example:**
```python
# Source: https://docs.streamlit.io/develop/concepts/architecture/caching
import streamlit as st
import pandas as pd
from src import db

@st.cache_resource
def get_engine():
    return db.get_engine("data/panel.db")

@st.cache_data
def load_panel_clean(_engine) -> pd.DataFrame:
    # el prefijo "_" excluye _engine del hashing -- es un objeto no hasheable
    return pd.read_sql("SELECT * FROM panel_clean", _engine)
```

### Pattern 2: Comparación lado a lado con `st.columns` y claves únicas (D-02)

**What:** Dos choropleths independientes en columnas, cada una con su propio selector, con `key=` explícito y único por columna para evitar `DuplicateWidgetID`.
**When to use:** Pestaña "Mapa e indicadores" para DASH-03.
**Example:**
```python
# Source: https://docs.streamlit.io/develop/api-reference/layout/st.columns
import streamlit as st

col1, col2 = st.columns(2)
options = list(indicator_labels.keys())

with col1:
    indicator_a = st.selectbox("Indicador (izquierda)", options, key="indicator_left")
    st.plotly_chart(plots.build_choropleth(df, indicator_a), use_container_width=True)

with col2:
    indicator_b = st.selectbox("Indicador (derecha)", options, key="indicator_right")
    st.plotly_chart(plots.build_choropleth(df, indicator_b), use_container_width=True)
```

### Pattern 3: Choropleth animado con rango de color fijo (D-05)

**What:** `px.choropleth` con `locationmode="ISO-3"` (recomendado explícitamente por Plotly frente a `"country names"`), `animation_frame="year"`, y `range_color` fijado manualmente al rango global del indicador.
**When to use:** Cualquier choropleth de las 4 capas (D-01) que se anime sobre 2000–2022.
**Example:**
```python
# Source: https://plotly.com/python/choropleth-maps/, https://plotly.com/python/colorscales/
import plotly.express as px

def build_choropleth(df, indicator_col, title):
    return px.choropleth(
        df,
        locations="country_code",
        locationmode="ISO-3",           # ISO3 ya es la clave de country_code en panel_clean
        color=indicator_col,
        animation_frame="year",
        range_color=(df[indicator_col].min(), df[indicator_col].max()),  # evita "saltos" de escala entre años
        color_continuous_scale="Viridis",
        title=title,
    )
```

### Pattern 4: Registro del "modelo activo" (D-07)

**What:** Un dict simple, único punto de verdad, con la configuración de cada modelo disponible en el selector.
**When to use:** Cualquier pestaña que necesite saber qué `.pkl`/`dep_var` cargar.
**Example:**
```python
# src/dashboard/models.py
ACTIVE_MODELS = {
    "Modelo 1 (PIB per cápita)": {
        "dep_var": "8.1.1",
        "indep_var": "6.4.2",
        "pkl_path": "data/modelos/model1_gdp.pkl",
    },
    # Fase 6 añade aquí "Modelo 2 (Productividad agrícola)":
    # {"dep_var": "2.3.1", "indep_var": "6.4.2", "pkl_path": "data/modelos/model2_agri.pkl"}
    # -- sin tocar app.py, solo esta lista.
}
```

### Pattern 5: Evitar pasar objetos pesados como parámetro de una función cacheada

**What:** En vez de recibir el modelo ya ajustado como argumento de una función `@st.cache_data`, la función cacheada llama internamente a la función `@st.cache_resource` que lo carga — así el modelo nunca entra en el hashing de argumentos.
**When to use:** `cached_bootstrap`/`cached_shap` (D-03), donde `bootstrap_counterfactual`/`shap_analysis` normalmente reciben un modelo/resultado ya ajustado.
**Example:**
```python
# Source: patrón derivado de https://docs.streamlit.io/develop/concepts/architecture/caching
# (hash_funcs / underscore-prefix section) aplicado a este proyecto
import streamlit as st
from src import simulate

@st.cache_data
def cached_bootstrap(dep_var: str, indep_var: str, reduction_pcts: tuple[float, ...]):
    engine = get_engine()                    # st.cache_resource, no pasado como argumento
    df = load_panel_clean(engine)
    fitted = load_model(ACTIVE_MODELS["Modelo 1 (PIB per cápita)"]["pkl_path"])  # st.cache_resource
    return simulate.bootstrap_counterfactual(
        fitted, df, dep_var, indep_var, reduction_pcts=list(reduction_pcts)
    )
```

### Anti-Patterns to Avoid

- **Cargar `panel.db`/pkl dentro de la función que renderiza una pestaña, sin cache:** Streamlit re-ejecuta TODO el script en cada interacción de widget — sin `st.cache_data`/`st.cache_resource`, cada clic recarga el modelo o vuelve a leer SQLite completo, violando DASH-02 directamente.
- **Cachear el Engine de SQLAlchemy con `st.cache_data`:** un Engine no es serializable de forma segura y no debe copiarse; usar `st.cache_resource`.
- **Pasar un `PanelEffectsResults`/`RandomForestRegressor` como parámetro normal (sin `_`) de una función `@st.cache_data`:** provoca error de hashing en tiempo de ejecución; usar el patrón 5 (cargar internamente vía recurso cacheado) o el prefijo `_`.
- **Dos `st.selectbox` con el mismo `label` y sin `key=` explícito en columnas distintas:** Streamlit lanza `DuplicateWidgetID`; cada selector de la comparación lado a lado (D-02) necesita `key` único.
- **No fijar `range_color` en un choropleth animado:** la escala de color se recalcula por frame, causando parpadeo/salto de leyenda entre años — rompe la fluidez esperada por DASH-04.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Exportar figuras Plotly individuales a PNG/PDF | Captura manual recortada figura por figura, o script de renderizado headless casero | `kaleido` (`fig.write_image(...)`) | Motor oficial de exportación estática de Plotly, una línea de API, ya es el estándar de facto del ecosistema |
| Capturar el layout completo de Streamlit (tabs + widgets) para el Plan B | Pipeline de automatización de navegador (Selenium/Playwright) | Captura manual de pantalla / "Imprimir a PDF" del navegador durante el ensayo | D-08 + discreción explícita del usuario ("mantenerlo simple"); Playwright añade una dependencia pesada (navegador + driver) para un artefacto generado una sola vez en un proyecto académico individual |
| Verificar comportamiento de la app (estado de widgets, que el cache funcione) | Solo clics manuales en el navegador | `streamlit.testing.v1.AppTest` + `pytest` | Framework de testing headless nativo de Streamlit (sin Selenium/Playwright), mismo patrón `pytest` ya usado en `tests/test_*.py` del proyecto |
| Normalizar la escala de color entre frames de una animación | Bucle manual sobre los años normalizando colores antes de construir la figura | `range_color=(min, max)` de `px.choropleth` | Parámetro nativo documentado de Plotly Express; evita reimplementar la unión de rangos que Plotly Express no calcula automáticamente |

**Key insight:** Todo lo que este dashboard necesita (caché, animación, exportación de imágenes, testing headless) ya tiene una solución de primera clase en el propio ecosistema Streamlit/Plotly ya pinned en el proyecto — no hay justificación para añadir Selenium/Playwright/frameworks de captura de pantalla de terceros a un proyecto académico de una sola persona con demo local.

## Common Pitfalls

### Pitfall 1: Cachear un recurso pesado con `st.cache_data` en vez de `st.cache_resource`
**What goes wrong:** Streamlit intenta copiar/serializar (vía pickle) un objeto no diseñado para ello (Engine, modelo), fallando o degradando el rendimiento.
**Why it happens:** Confusión entre "dato" (copiable) y "recurso" (compartido, no copiable) — la distinción no es obvia para quien no ha leído la documentación de caché.
**How to avoid:** Regla simple usada en este proyecto: si la función devuelve un DataFrame/array/dict de resultados → `st.cache_data`; si devuelve un Engine, un modelo ajustado, o un `TreeExplainer` → `st.cache_resource`.
**Warning signs:** Errores de pickling en la consola de Streamlit al primer render, o lentitud inesperada en cada interacción.

### Pitfall 2: Pasar un objeto no-hasheable como argumento normal de una función cacheada
**What goes wrong:** `UnhashableParamError` en tiempo de ejecución cuando Streamlit intenta hashear el argumento para la clave de caché.
**Why it happens:** Los modelos/Engine no tienen un hash estable por defecto.
**How to avoid:** Prefijo `_` en el nombre del parámetro (excluido del hashing) o, mejor para este proyecto, cargar el recurso internamente vía una función `@st.cache_resource` separada (Pattern 5) en vez de recibirlo como argumento.
**Warning signs:** Traceback mencionando "cannot be hashed" al invocar una función `@st.cache_data` con un modelo como argumento.

### Pitfall 3: Widgets duplicados sin `key` único en `st.columns`
**What goes wrong:** `DuplicateWidgetID`, la app se rompe al renderizar la comparación lado a lado.
**Why it happens:** Dos `st.selectbox` con el mismo texto de `label` generan la misma clave implícita si no se especifica `key=`.
**How to avoid:** `key=f"indicator_{'left' if col_idx == 0 else 'right'}"` explícito en cada selector de la comparación (D-02).
**Warning signs:** Error visible inmediatamente al cargar la pestaña "Mapa e indicadores" con dos selectores.

### Pitfall 4: Escala de color inconsistente en la animación temporal
**What goes wrong:** El mapa de color "salta" o cambia de intensidad entre años al reproducir la animación, dando una impresión visual poco profesional durante la demo.
**Why it happens:** Plotly Express NO calcula automáticamente la unión de rangos de color entre frames — sin `range_color` explícito, cada frame se autoescala con su propio min/max.
**How to avoid:** Calcular `(df[indicator_col].min(), df[indicator_col].max())` sobre TODO el rango 2000–2022 antes de construir la figura, y pasarlo como `range_color`.
**Warning signs:** La leyenda de color cambia de rango visiblemente al mover el slider de años.

### Pitfall 5: `kaleido>=1.0` requiere Chrome/Chromium instalado por separado
**What goes wrong:** `fig.write_image(...)` falla silenciosamente o con error si no hay Chrome/Chromium disponible en el sistema — versiones anteriores a kaleido v1 empaquetaban su propio Chromium, la v1+ ya no.
**Why it happens:** Cambio de arquitectura de kaleido en su versión 1.0 (2024–2025), documentado oficialmente.
**How to avoid:** Verificar `plotly.io.get_chrome()` (descarga Chrome for Testing) o confirmar que Chrome/Edge ya está instalado — especialmente en la máquina de presentación real, no solo en el entorno de desarrollo. Ya se confirmó Chrome y Edge instalados en la máquina de desarrollo actual; **debe verificarse también en la máquina de presentación** como parte del ensayo que DASH-05 ya exige.
**Warning signs:** Excepción al ejecutar el script de generación de capturas Plan B; funciona en desarrollo pero falla en la máquina de la defensa.

### Pitfall 6 (específico del proyecto): deserializar los `.pkl` requiere el entorno exacto del proyecto
**What goes wrong:** `pickle.load(model1_gdp.pkl)` falla con `ModuleNotFoundError: No module named 'linearmodels'` si se ejecuta fuera del `.venv` del proyecto — verificado en vivo en esta sesión de investigación al intentar inspeccionar el pkl con un intérprete Python global sin `linearmodels` instalado.
**Why it happens:** Los objetos `PanelEffectsResults`/`RandomForestRegressor` serializados dependen de que las clases originales (y, para scikit-learn, la MISMA versión) estén disponibles al deserializar.
**How to avoid:** El dashboard debe ejecutarse siempre con `streamlit run` invocado desde el intérprete de `.venv/Scripts/python.exe` del proyecto (o `python -m streamlit run ...`), nunca con un Python global — esto ya es una convención del proyecto (`requirements.lock.txt` congelado "estrictamente desde el intérprete .venv").
**Warning signs:** `InconsistentVersionWarning` de scikit-learn al cargar `rf_shap_model.pkl` (confirmado en vivo: se disparó al deserializar con scikit-learn 1.5.1 en vez de la 1.9.0 con la que fue entrenado) o `ModuleNotFoundError` directo para `linearmodels`.

## Code Examples

Verified patterns from official sources:

### Carga cacheada de Engine + panel_clean
```python
# Source: https://docs.streamlit.io/develop/concepts/architecture/caching
import streamlit as st
import pandas as pd
from src import db

@st.cache_resource
def get_engine():
    return db.get_engine("data/panel.db")

@st.cache_data
def load_panel_clean(_engine) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM panel_clean", _engine)
```

### Carga cacheada de modelo serializado
```python
# Source: patrón st.cache_resource, https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource
import pickle
import streamlit as st

@st.cache_resource
def load_model(pkl_path: str):
    with open(pkl_path, "rb") as f:
        return pickle.load(f)
```

### Choropleth animado con rango de color fijo
```python
# Source: https://plotly.com/python/choropleth-maps/, https://plotly.com/python/colorscales/
import plotly.express as px

def build_choropleth(df, indicator_col: str, title: str):
    return px.choropleth(
        df,
        locations="country_code",
        locationmode="ISO-3",
        color=indicator_col,
        animation_frame="year",
        range_color=(df[indicator_col].min(), df[indicator_col].max()),
        color_continuous_scale="Viridis",
        title=title,
    )
```

### Exportación estática para el Plan B (si se automatiza)
```python
# Source: https://plotly.com/python/static-image-export/
import plotly.io as pio

pio.get_chrome()  # solo la primera vez, si no hay Chrome/Chromium instalado

fig = build_choropleth(df, "6.4.2", "Estrés hídrico 2022")
fig.write_image("figuras/plan_b/mapa_estres_2022.png", width=1200, height=700, scale=2)
```

### Timing de carga en frío (Claude's Discretion, DASH-02)
```python
import time
import streamlit as st

if "app_start_time" not in st.session_state:
    st.session_state["app_start_time"] = time.perf_counter()
    st.session_state["cold_start_logged"] = False

# al final del primer render completo de la app:
if not st.session_state["cold_start_logged"]:
    elapsed = time.perf_counter() - st.session_state["app_start_time"]
    st.sidebar.caption(f"Carga en frío: {elapsed:.2f}s")
    st.session_state["cold_start_logged"] = True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|----------------|--------|
| `kaleido` empaquetaba Chromium propio | `kaleido>=1.0` requiere Chrome/Chromium del sistema (o `pio.get_chrome()`) | Kaleido v1 (2024–2025) | El script de generación del Plan B debe verificar Chrome disponible, especialmente en la máquina de presentación |
| `st.experimental_memo`/`st.experimental_singleton` | `st.cache_data`/`st.cache_resource` (API estable) | Streamlit 1.18+ (2023) | Ya son los únicos nombres usados en esta investigación — sin riesgo de API legacy en el 1.59.1 pinned |
| Automatización con Selenium/Playwright para testing de UI | `streamlit.testing.v1.AppTest` nativo, sin navegador | Streamlit 1.28+ | Disponible para los tests de Wave 0 de esta fase sin nueva dependencia |

**Deprecated/outdated:**
- `plotly.io.kaleido.scope` (interfaz de configuración antigua): sigue funcionando pero la documentación oficial recomienda `plotly.io.defaults` en su lugar.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|-----------------|
| A1 | Chrome/Chromium estará disponible en la máquina de presentación real de la defensa (confirmado solo en la máquina de desarrollo actual) | Common Pitfalls #5, Environment Availability | Si no está disponible y se depende de `kaleido` para el Plan B, la generación de capturas fallaría — mitigado porque DASH-05 ya exige un ensayo completo en esa máquina antes de la defensa, y el fallback (captura manual de navegador) no depende de Chrome/kaleido en absoluto |
| A2 | `kaleido` es la herramienta recomendada pese al flag `[SUS]` automático (basado únicamente en falta de dato de descargas, no en señales de paquete malicioso) | Package Legitimacy Audit, Standard Stack | Bajo — es el paquete oficial de la organización `plotly` en GitHub y PyPI, mismo patrón de falso positivo ya validado en Fase 1 con `pytest`; aun así requiere `checkpoint:human-verify` antes de instalar, según protocolo |

**Si esta tabla está vacía:** No aplica — hay 2 asunciones de bajo riesgo, ambas con mitigación ya incorporada en el diseño (D-08 fallback manual, checkpoint humano de instalación).

## Open Questions

1. **¿Automatizar la generación del Plan B con `kaleido`, o hacerlo enteramente manual?**
   - What we know: `kaleido` solo exporta figuras Plotly individuales, no el layout completo de Streamlit (tabs, sidebar, selectores). Para capturar la experiencia completa de cada pestaña se necesita de todos modos una captura de pantalla/impresión a PDF del navegador.
   - What's unclear: Si vale la pena instalar `kaleido` (con su gate `checkpoint:human-verify`) solo para las figuras individuales, cuando la captura manual del navegador ya cubre tabs completas incluyendo esas mismas figuras.
   - Recommendation: El planner puede optar por la vía puramente manual (captura de pantalla completa de cada tab durante el ensayo, D-08 no exige automatización) y omitir `kaleido` por completo — es la opción más simple y ya cumple D-08 al pie de la letra. Si se prefiere automatizar, añadir el `checkpoint:human-verify` para `kaleido` antes de instalarlo.

2. **¿Dónde se rehearsa exactamente DASH-05 (caché fría en la máquina de presentación)?**
   - What we know: DASH-05 exige explícitamente el ensayo en la máquina de presentación, no solo en desarrollo.
   - What's unclear: Si la máquina de presentación es la misma máquina de desarrollo (Windows 11, con Chrome/Edge ya confirmados) o un equipo distinto de la universidad/tribunal.
   - Recommendation: Tratar esto como un `checkpoint:human-verify`/tarea manual explícita en el plan de ejecución, no como algo resoluble en fase de investigación — coincide con la discreción ya otorgada por el usuario sobre "el momento exacto de generación de las capturas".

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Python `.venv` del proyecto | Ejecutar `streamlit run src/dashboard/app.py` con las versiones pinned | ✓ | 3.12.4 | — |
| streamlit | Framework de la app | ✓ (pinned) | 1.59.1 | — |
| plotly | Choropleth animado | ✓ (pinned) | 6.9.0 | — |
| `data/panel.db` (`panel_clean`, `panel_exclusions`) | Pestaña "Mapa e indicadores" | ✓ | — | — |
| `data/modelos/model1_gdp.pkl` | Pestaña "Modelo 1", simulación | ✓ (round-trip verificado, Fase 3) | — | — |
| `data/modelos/rf_shap_model.pkl` | Pestaña SHAP | ✓ (round-trip verificado, Fase 4) | — | — |
| Google Chrome / Chromium | `kaleido` (solo si se automatiza el Plan B) | ✓ en máquina de desarrollo (`C:\Program Files\Google\Chrome\Application\chrome.exe`); Edge también presente | — | Captura manual de pantalla/navegador (no requiere Chrome ni kaleido en absoluto) |
| `kaleido` | Exportación PNG/PDF de figuras Plotly individuales para el Plan B | ✗ (no instalado, no está en `requirements.txt`/`requirements.lock.txt`) | — | Captura manual (recomendada, ver Open Question 1) |

**Missing dependencies with no fallback:** ninguna.
**Missing dependencies with fallback:** `kaleido` — fallback: captura manual de pantalla/navegador durante el ensayo de DASH-05, que de todos modos ya es obligatorio.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (pinned, `requirements.lock.txt`), `pytest-cov` 7.1.0 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options] testpaths = ["tests"]`) |
| Quick run command | `pytest tests/dashboard -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|----------------|
| DASH-01 | El dashboard nunca llama a la API de la ONU en tiempo real | unit (estático) | `pytest tests/dashboard/test_no_live_api.py -x` | ❌ Wave 0 |
| DASH-02 | Loaders envueltos en `st.cache_data`/`st.cache_resource`; sin freezes en interacciones repetidas | unit | `pytest tests/dashboard/test_caching.py -x` | ❌ Wave 0 |
| DASH-03 | Dos choropleths independientes con selectores propios se renderizan sin error | integration (`AppTest`) | `pytest tests/dashboard/test_app.py::test_side_by_side_comparison -x` | ❌ Wave 0 |
| DASH-04 | El choropleth incluye `animation_frame` con los 23 años (2000–2022) | unit | `pytest tests/dashboard/test_plots.py::test_choropleth_has_all_years -x` | ❌ Wave 0 |
| DASH-05 | Ensayo con caché fría en la máquina de presentación + capturas de respaldo generadas con datos reales | manual-only (justificado: requiere hardware físico de la defensa, no automatizable) | `checkpoint:human-verify` — rehearsal en máquina real + inspección visual de las capturas | ❌ Wave 0 (checklist, no test) |

### Sampling Rate

- **Per task commit:** `pytest tests/dashboard -x`
- **Per wave merge:** `pytest tests/`
- **Phase gate:** Suite completa en verde antes de `/gsd-verify-work`, más el `checkpoint:human-verify` de DASH-05 completado con evidencia (capturas generadas + notas del ensayo).

### Wave 0 Gaps

- [ ] `tests/dashboard/__init__.py`
- [ ] `tests/dashboard/conftest.py` — fixture de `panel.db` en memoria con datos mínimos (pocos países/años) + fixtures de modelos `.pkl` de juguete, para no depender de los artefactos completos de producción en cada test
- [ ] `tests/dashboard/test_no_live_api.py` — cubre DASH-01
- [ ] `tests/dashboard/test_caching.py` — cubre DASH-02 (verifica que los loaders llevan `st.cache_data`/`st.cache_resource`, p. ej. inspeccionando `__wrapped__`/atributos del decorador)
- [ ] `tests/dashboard/test_app.py` — cubre DASH-03 vía `streamlit.testing.v1.AppTest`
- [ ] `tests/dashboard/test_plots.py` — cubre DASH-04, funciones puras de `plots.py` testeables sin levantar Streamlit
- [ ] Framework install: ninguno — `pytest` ya está en `requirements.lock.txt`; `streamlit.testing.v1.AppTest` viene incluido dentro del propio paquete `streamlit` ya pinned, no es una dependencia nueva

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|-----------------|---------|---------------------|
| V2 Authentication | No | App local de un solo usuario para una demo, sin login — fuera de alcance (PROJECT.md ya excluye despliegue online) |
| V3 Session Management | No (parcial) | `st.session_state` de Streamlit gestiona el estado de la sesión del navegador local; no hay autenticación ni sesiones multiusuario que proteger |
| V4 Access Control | No | Un solo usuario, sin roles |
| V5 Input Validation | Sí | Los widgets de Streamlit (`selectbox`, `slider`) son de elección cerrada — no aceptan texto libre para indicadores/años, lo que ya mitiga la mayoría de vectores de inyección por diseño; cualquier consulta SQL debe seguir el patrón parametrizado ya establecido en `src/db.py` (`pd.read_sql`/`to_sql`, nunca interpolación de f-strings en SQL) |
| V6 Cryptography | No | No se manejan secretos ni credenciales en esta fase |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Inyección SQL si el valor de un selector se interpola directamente en una consulta SQL en vez de usarse como clave de un diccionario/whitelist | Tampering | Reutilizar el patrón ya establecido en `src/db.py` (SQL parametrizado o `pd.read_sql` con nombre de tabla fijo); nunca construir SQL con f-strings a partir de la selección del usuario — restringir los valores de indicador/año a un conjunto fijo conocido en `panel_clean` |
| Deserialización de pickle no confiable (`st.cache_data` usa pickle implícitamente para copiar datos; los `.pkl` de modelos también se deserializan con `pickle.load`) | Tampering / Information Disclosure | Los únicos `.pkl` cargados son artefactos producidos por el propio pipeline del proyecto (`model1_gdp.pkl`, `rf_shap_model.pkl`), nunca subidos por un usuario ni descargados de la red — no añadir ningún widget de carga de archivos (`st.file_uploader`) para `.pkl` en esta fase |
| Exposición accidental de la app fuera de `localhost` | Elevation of Privilege (exposición de red no intencionada) | Ejecutar `streamlit run` con el binding por defecto (`localhost`); no establecer `server.address=0.0.0.0` — coincide con la decisión explícita de PROJECT.md de mantener el dashboard exclusivamente local |

## Sources

### Primary (HIGH confidence)
- [Caching overview - Streamlit Docs](https://docs.streamlit.io/develop/concepts/architecture/caching) - `st.cache_data` vs `st.cache_resource`, prefijo `_`, `hash_funcs`, `ttl`
- [Choropleth maps in Python - Plotly](https://plotly.com/python/choropleth-maps/) - `locations`, `locationmode`, `range_color`
- [Continuous color scales and color bars in Python - Plotly](https://plotly.com/python/colorscales/) - `range_color` para consistencia entre frames
- [Static image export in Python - Plotly](https://plotly.com/python/static-image-export/) - `kaleido`, `fig.write_image`, requisito de Chrome en kaleido v1+
- [App testing - Streamlit Docs](https://docs.streamlit.io/develop/api-reference/app-testing) - `streamlit.testing.v1.AppTest`
- Código fuente del proyecto: `src/db.py`, `src/panel_base.py`, `src/simulate.py`, `src/interpret.py`, `requirements.lock.txt` (versiones pinned confirmadas por lectura directa)
- `data/panel.db` (esquema de tablas inspeccionado en vivo: `panel_clean` con `country_code` en formato ISO3), `data/modelos/*.pkl` (deserialización probada en vivo)

### Secondary (MEDIUM confidence)
- [st.columns - Streamlit Docs / WebSearch cross-check](https://docs.streamlit.io/develop/api-reference/layout/st.columns) - patrón de columnas, necesidad de `key` único
- WebSearch: hilos de `discuss.streamlit.io` y GitHub issues sobre performance de arranque en frío y hashing de parámetros no-hasheables

### Tertiary (LOW confidence)
- Ninguno — todos los hallazgos clave fueron cruzados con al menos una fuente oficial (docs.streamlit.io o plotly.com) o verificados en vivo contra el repositorio del proyecto.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versiones pinned confirmadas por lectura directa de `requirements.lock.txt`, sin necesidad de inferencia
- Architecture: HIGH - patrones de caché y choropleth confirmados contra documentación oficial de Streamlit/Plotly
- Pitfalls: HIGH - varios pitfalls (deserialización de `.pkl`, formato ISO3 de `country_code`) verificados en vivo directamente contra los artefactos reales del proyecto en esta sesión

**Research date:** 2026-07-13
**Valid until:** 2026-08-12 (30 días — stack estable y ya pinned, pero recheck si `requirements.lock.txt` cambia o si se decide instalar `kaleido`)
