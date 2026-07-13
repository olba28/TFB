# Phase 5: Dashboard y Preparación de la Defensa - Context

**Gathered:** 2026-07-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Un dashboard local Streamlit + Plotly que consume exclusivamente artefactos ya calculados (panel.db, `model1_gdp.pkl`, `rf_shap_model.pkl`, resultados de `simulate.py`/`interpret.py` recalculados en vivo con cache, nunca la API de la ONU en tiempo real): choropleth interactivo de los 5 indicadores ODS + salidas del Modelo 1 + simulación contrafactual + interpretabilidad SHAP, con animación temporal 2000–2022, comparación lado a lado de dos indicadores/series, caché para carga fluida en demo (<5s en frío), y un respaldo pre-renderizado (capturas) ensayado como plan B. Cubre DASH-01 a DASH-05.

Esta fase NO incluye el ajuste ni la implementación del Modelo 2 en sí (eso es Fase 6) — pero el dashboard se diseña ya parametrizado por modelo para que Fase 6 solo tenga que añadir la opción al selector, no reestructurar la app.

</domain>

<decisions>
## Implementation Decisions

### Alcance del choropleth y vistas (DASH-01, DASH-03)
- **D-01:** El dashboard cubre las **cuatro capas** discutidas, no solo los indicadores crudos: (1) los 5 indicadores ODS (`6.4.2`, `6.4.1`, `8.1.1`, `8.2.1`, `2.3.1`) tal cual del panel; (2) salidas del Modelo 1 (valores ajustados/coeficientes de `model1_gdp.pkl`); (3) resultados de la simulación contrafactual (escenarios -10/-20/-30% con CIs bootstrap de `simulate.py`); (4) interpretabilidad SHAP (`rf_shap_model.pkl` vía `interpret.py`). El usuario quiere el dashboard como vitrina completa de todo el trabajo de Fases 3–4, no solo un visor de datos.
- **D-02:** "Comparar dos indicadores lado a lado" (DASH-03) significa **dos choropleths del mismo año, uno junto al otro**, cada uno con su propio selector de indicador/serie (puede ser cualquier combinación de las 4 capas de D-01) — no un scatter de correlación.

### Precómputo vs. cálculo en vivo (DASH-01, DASH-02)
- **D-03:** La simulación bootstrap y el análisis SHAP se **recalculan en vivo dentro del dashboard**, envueltos en `@st.cache_data`/`@st.cache_resource`, invocando directamente `simulate.bootstrap_counterfactual`/`interpret.shap_analysis` — no se crea un artefacto de precómputo dedicado ni se reutiliza `data/modelos/_repro_snapshot.pkl` (ese fichero es exclusivo de `scripts/verify_repro02.py`/REPRO-02, gitignored y sobrescrito en cada ejecución de verificación — no es una fuente de datos estable para el dashboard). El cálculo en vivo cumple DASH-01 porque solo lee `panel.db` local y modelos ya ajustados, nunca llama a la API de la ONU; el cache de Streamlit asegura que cada combinación de parámetros solo se computa una vez por sesión.
- **D-04:** El cache no usa TTL — es permanente durante la sesión de demo (`@st.cache_data`/`@st.cache_resource` sin parámetro `ttl`). Los datos son estáticos para la defensa; no hace falta botón de recarga manual (no exigido por DASH-01..05).

### Animación temporal (DASH-04)
- **D-05:** La animación usa el mecanismo **nativo de Plotly** (`px.choropleth(..., animation_frame="year")`), con los controles de play/pause/slider que Plotly genera automáticamente — no un slider manual de Streamlit con re-render por cambio de año.

### Navegación y estructura de la app
- **D-06:** Una **sola app Streamlit** (`src/dashboard/app.py`) organizada con `st.tabs()` en vez de una app multipágina: pestañas "Mapa e indicadores", "Modelo 1", "Simulación", "Interpretabilidad (SHAP)". Esto comparte cache/estado entre secciones sin necesitar `st.session_state` explícito y simplifica el ensayo de la demo (un solo proceso).

### Preparación para Modelo 2 (Fase 6, stretch)
- **D-07:** El dashboard se diseña con un **parámetro de "modelo activo"** desde esta fase (qué `dep_var`/`.pkl` cargar, qué columnas de predictores usar), aunque el selector visible de esta fase solo muestre "Modelo 1". Sigue el mismo patrón de reutilización-sin-retrabajo ya usado en `panel_base.py` (D-05, Fase 3), `simulate.py`/`interpret.py` (D-12, Fase 4): Fase 6 solo añade la opción "Modelo 2" al selector existente, sin reestructurar `app.py`.

### Plan B / respaldo pre-renderizado (DASH-05)
- **D-08:** El respaldo son **capturas de pantalla** (PNG/PDF) de cada pestaña con datos reales ya cargados — no un vídeo grabado. Más rápido de generar y suficiente como plan B estático si el dashboard en vivo falla durante la defensa.

### Claude's Discretion
- Estructura interna exacta de `src/dashboard/` (un solo `app.py` vs. `app.py` + `plots.py`/`data.py` auxiliares) — libre mientras sea una sola app Streamlit con pestañas (D-06).
- Paleta de colores y estilo visual exacto del choropleth — libre mientras sea legible y consistente entre pestañas.
- Mecanismo exacto del parámetro "modelo activo" (dict de configuración, función factory, clase) — libre mientras permita que Fase 6 añada Modelo 2 sin tocar la estructura de `app.py` (D-07).
- Momento exacto de generación de las capturas de plan B (script dedicado vs. manual) — libre mientras se generen antes de la defensa con datos reales (D-08).
- Medición concreta del tiempo de carga en frío (<5s, DASH-02) — libre el método de medición (manual con cronómetro, `time.perf_counter` logueado) mientras se documente el resultado.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Documentos del proyecto
- `.planning/PROJECT.md` — contexto completo; decisión explícita de dashboard solo local (sin despliegue online) y stack Plotly/Streamlit elegido por estabilidad en Windows sin GDAL.
- `.planning/REQUIREMENTS.md` §"Dashboard" — DASH-01 a DASH-05, con su criterio de aceptación exacto.
- `.planning/ROADMAP.md` §"Phase 5" — Goal y 4 Success Criteria verificables que esta fase debe cumplir; también §"Phase 6" Success Criterion #3 (selector Modelo 1/Modelo 2), motivo directo de D-07.

### Artefactos de fases anteriores (entrada directa de esta fase)
- `.planning/phases/04-interpretabilidad-simulaci-n-y-robustez/04-CONTEXT.md` — D-12/D-13 (diseño paramétrico reutilizable), patrón que D-07 replica para el dashboard.
- `.planning/phases/04-interpretabilidad-simulaci-n-y-robustez/04-VERIFICATION.md` — confirma que `data/modelos/_repro_snapshot.pkl` es un artefacto de trabajo de REPRO-02 (gitignored, sobrescrito cada ejecución), base de D-03 (no reutilizarlo como fuente del dashboard).
- `.planning/phases/03-modelo-1-regresi-n-de-panel-pib-per-c-pita/03-CONTEXT.md` — D-05 (diseño paramétrico de `panel_base.py`), mismo patrón de reutilización que D-07 extiende al dashboard.
- `src/simulate.py` — `bootstrap_counterfactual`, `fit_interaction_model`, `check_non_extrapolation` — invocadas en vivo por el dashboard (D-03).
- `src/interpret.py` — `shap_analysis`, `compute_vif_table`, `partial_dependence_plots` — invocadas en vivo por el dashboard (D-03).
- `src/panel_base.py` — `fit_panel_model` — reutilizada para mostrar salidas del Modelo 1 (D-01).
- `src/db.py` — `get_engine()` — patrón de conexión SQLAlchemy que el dashboard debe reutilizar para leer `panel_clean`/`panel_exclusions`.
- `data/modelos/model1_gdp.pkl`, `data/modelos/rf_shap_model.pkl` — modelos ya serializados que el dashboard carga sin reajustar (excepto las réplicas bootstrap internas de D-03).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/db.py::get_engine()` — conexión SQLAlchemy ya establecida a `data/panel.db`; el dashboard debe reutilizarla, no crear una nueva.
- `src/panel_base.py::fit_panel_model` — usada para mostrar diagnósticos/valores ajustados del Modelo 1 en la pestaña correspondiente.
- `src/simulate.py`, `src/interpret.py` — funciones paramétricas (genéricas en `dep_var`) ya diseñadas en Fase 4 pensando en reutilización; el dashboard las invoca directamente envueltas en cache (D-03), sin modificarlas.
- `data/modelos/model1_gdp.pkl`, `data/modelos/rf_shap_model.pkl` — modelos serializados y round-trip-verificados, listos para cargar.

### Established Patterns
- Diseño paramétrico desde el principio (`panel_base.py` D-05 Fase 3, `simulate.py`/`interpret.py` D-12 Fase 4) — replicado aquí en D-07 para el "modelo activo" del dashboard.
- Serialización de modelos a `data/modelos/*.pkl` — el dashboard es el primer consumidor real (no de verificación) de estos artefactos.
- `src/dashboard/` existe como carpeta esqueleto planificada en STRUCTURE.md (no implementada aún) — ubicación ya designada para `app.py`.

### Integration Points
- El dashboard es el punto de integración final de Fases 1–4: lee `panel.db` (Fase 1/2), `model1_gdp.pkl` (Fase 3), `simulate.py`/`interpret.py`/`rf_shap_model.pkl` (Fase 4).
- Fase 6 (Modelo 2) extenderá el selector de "modelo activo" (D-07) añadiendo `dep_var="2.3.1"` sin reestructurar `app.py`.

</code_context>

<specifics>
## Specific Ideas

- El usuario quiere el dashboard como una vitrina completa de todo el pipeline (indicadores + Modelo 1 + simulación + SHAP), no un visor mínimo de datos — eligió expresamente las 4 capas en vez de limitarse a los indicadores crudos.
- Mantiene, por cuarta fase consecutiva, la preferencia por diseño paramétrico/reutilizable desde el principio (D-07, mismo patrón que D-05 Fase 3 y D-12 Fase 4) en vez de posponer la generalización a la Fase 6.
- Prefirió sistemáticamente las opciones "Recomendado" en las 8 preguntas de esta discusión — indica confianza en las recomendaciones estándar de Streamlit/Plotly para este caso de uso (demo local, datos estáticos).

</specifics>

<deferred>
## Deferred Ideas

None — la discusión se mantuvo dentro del alcance de la Fase 5.

</deferred>

---

*Phase: 5-Dashboard y Preparación de la Defensa*
*Context gathered: 2026-07-13*
