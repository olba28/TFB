# Phase 5: Dashboard y Preparación de la Defensa - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-13
**Phase:** 5-Dashboard y Preparación de la Defensa
**Areas discussed:** Alcance choropleth, Precómputo vs. vivo, Animación temporal, Preparación Modelo 2, Navegación, Comparación lado a lado, Plan B, Cache

---

## Alcance choropleth (DASH-01/DASH-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Solo los 5 indicadores ODS crudos | Valores del panel tal cual, sin salidas de modelo | ✓ |
| Indicadores + resultados del Modelo 1 | Valores ajustados/coeficientes de PanelOLS | ✓ |
| Indicadores + simulación contrafactual | Escenarios -10/-20/-30% con CIs bootstrap | ✓ |
| Indicadores + SHAP/interpretabilidad | Importancia SHAP por país/variable | ✓ |

**User's choice:** Las cuatro opciones (multiSelect) — dashboard como vitrina completa.
**Notes:** El usuario quiere cubrir todo el trabajo de Fases 3–4 en el dashboard, no solo un visor de datos crudos.

---

## Precómputo vs. vivo (DASH-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Recalcular en vivo con cache | `@st.cache_data`/`@st.cache_resource` sobre `simulate.py`/`interpret.py` | ✓ |
| Artefacto propio pre-serializado | Nuevo `.pkl` generado de antemano, dashboard solo lee | |

**User's choice:** Recalcular en vivo con cache (Recomendado).
**Notes:** Se descartó reutilizar `_repro_snapshot.pkl` — es un artefacto exclusivo de `verify_repro02.py`/REPRO-02, gitignored y sobrescrito en cada ejecución.

---

## Animación temporal (DASH-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Animación nativa de Plotly | `animation_frame="year"`, controles play/pause/slider automáticos | ✓ |
| Slider manual controlado por Streamlit | `st.slider` + re-render en cada cambio | |

**User's choice:** Animación nativa de Plotly (Recomendado).

---

## Preparación para Modelo 2 (ROADMAP Fase 6)

| Option | Description | Selected |
|--------|-------------|----------|
| Diseño parametrizado por modelo | Parámetro "modelo activo" desde ahora; Fase 6 solo añade la opción al selector | ✓ |
| Solo Modelo 1 ahora, extensión en Fase 6 | Dashboard simple ahora, generalización pospuesta | |

**User's choice:** Diseño parametrizado por modelo (Recomendado).
**Notes:** Consistente con el patrón ya usado en `panel_base.py` (Fase 3) y `simulate.py`/`interpret.py` (Fase 4).

---

## Navegación

| Option | Description | Selected |
|--------|-------------|----------|
| Pestañas/secciones en una sola app | `st.tabs()` en un único `app.py`, cache compartido | ✓ |
| App multipágina de Streamlit | Carpeta `pages/`, navegación nativa en sidebar | |

**User's choice:** Pestañas/secciones en una sola app (Recomendado).

---

## Comparación lado a lado (DASH-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Dos choropleths lado a lado, mismo año | Dos selectores independientes, dos mapas del mismo año | ✓ |
| Un mapa + gráfico de dispersión/correlación | Choropleth + scatter indicador A vs. B | |

**User's choice:** Dos choropleths lado a lado, mismo año (Recomendado).

---

## Plan B (DASH-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Capturas de pantalla de cada sección | PNG/PDF de cada pestaña con datos reales | ✓ |
| Vídeo corto de la demo completa | Screen recording 1-2 min | |

**User's choice:** Capturas de pantalla de cada sección (Recomendado).

---

## Cache

| Option | Description | Selected |
|--------|-------------|----------|
| Cache permanente, sin TTL | Sin parámetro `ttl`, datos estáticos durante la demo | ✓ |
| Botón manual de "Recargar datos" | `st.cache_data.clear()` desde el sidebar | |

**User's choice:** Cache permanente, sin TTL (Recomendado).

---

## Claude's Discretion

- Estructura interna exacta de `src/dashboard/` (un solo `app.py` vs. módulos auxiliares).
- Paleta de colores y estilo visual del choropleth.
- Mecanismo exacto del parámetro "modelo activo".
- Momento/script exacto de generación de las capturas de plan B.
- Método de medición del tiempo de carga en frío (<5s).

## Deferred Ideas

None — la discusión se mantuvo dentro del alcance de la Fase 5.
