# Phase 6: Modelo 2 — Productividad Agrícola (stretch) - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning

<domain>
## Phase Boundary

`model2_agri.py` (o módulo equivalente) reutiliza `panel_base.py` sin modificarlo (D-05, 03-CONTEXT.md) para ajustar un segundo `PanelOLS` de efectos fijos bidireccionales con `dep_var="2.3.1"` (productividad agrícola) e `indep_var="6.4.2"` (estrés hídrico) — misma especificación metodológica, mismos diagnósticos (Hausman, Pesaran CD) y misma elección de SEs (clustered/Driscoll-Kraay según Pesaran) que el Modelo 1. Cubre un nuevo criterio de cobertura de países (el umbral del 70% del Modelo 1 deja el panel de 2.3.1 en cero países), la extensión de `simulate.py`/`interpret.py`/dashboard al Modelo 2 sin modificarlos (D-12, 04-CONTEXT.md; D-07, 05-CONTEXT.md), y la documentación explícita de la cobertura reducida (MODEL2-02). Cubre MODEL2-01, MODEL2-02, MODEL2-03.

Esta fase NO introduce nuevos indicadores, nuevas fuentes de datos, ni cambia la metodología del Modelo 1 ya cerrado (Fases 3-5). Tampoco reestructura `panel_base.py`/`simulate.py`/`interpret.py` — solo los invoca con parámetros distintos, y añade lo estrictamente necesario (un nuevo helper de umbral de cobertura) siguiendo el mismo patrón paramétrico ya establecido.

</domain>

<decisions>
## Implementation Decisions

### Umbral de cobertura del Modelo 2 (MODEL2-01, MODEL2-02)
- **D-01:** El umbral del 70%-de-años del Modelo 1 (`panel_exclusions`, D-01/D-02 Fase 3) deja el panel de `2.3.1` en **CERO países** — la cobertura máxima real es 26% (TZA/UGA/PRY), porque el indicador se reporta cada ~3 años (oleadas 2010/2013/2016/2020, muy pocos años sueltos fuera de esas oleadas), no anualmente. El criterio de inclusión del Modelo 2 es **mínimo 3 años observados por país** (no un % sobre 2000–2022) — deja **39 países** con `6.4.2` y `2.3.1` no nulos simultáneamente, cada uno con variación temporal suficiente para efectos fijos de entidad sin ser un único punto ruidoso.
- **D-02:** La lógica del nuevo criterio vive en un **nuevo helper paramétrico en `panel_base.py`** (p. ej. `filter_by_min_years(df, dep_var, indep_vars, min_years)`), calculado directamente sobre `panel_clean` — **no** sobre la tabla `panel_exclusions` de la Fase 2 (que está fijada al criterio del 70%). No se toca `filter_by_exclusions` ni el comportamiento del Modelo 1; `panel_base.py` sigue siendo la única fuente reutilizable de lógica de filtrado, con dos criterios de cobertura coexistiendo como funciones separadas y explícitas.
- **D-03:** La cobertura/exclusiones del Modelo 2 se documentan en una **tabla dedicada**, mismo estilo que `panel_exclusions` de la Fase 2 (`country_code`, `years_available`, `included`/`excluded`, `reason`) — citable directamente en la memoria, no un párrafo descriptivo suelto.
- **D-04:** Los tests de Hausman y Pesaran CD (**"mismos diagnósticos"**, exigido explícitamente por el Success Criterion de la Fase 6) se ejecutan igual que en el Modelo 1 pese al panel disperso (~3.5 obs/país en promedio), siguiendo la convención ya establecida en `panel_base.py` de **"warn, don't hide"** (`hausman_test`/`pesaran_cd_test` ya avisan de matrices singulares o estadísticos negativos vía `warnings.warn` en vez de fallar silenciosamente). Si el test sale numéricamente degenerado con esta N pequeña, se documenta explícitamente como limitación — no se omite ni se sustituye por una discusión solo cualitativa.

### Alcance de la extensión — simulación, SHAP y dashboard (MODEL2-03)
- **D-05:** El bootstrap contrafactual del Modelo 2 usa el **mismo `n_replicas=1000`** que el Modelo 1 (parámetro ya expuesto en `bootstrap_counterfactual`, D-02 04-CONTEXT.md, sin tocar la función), aunque el "block bootstrap por país" remuestree solo ~39 entidades en vez de 171. El intervalo de confianza resultante será más ancho — se documenta como limitación real del Modelo 2, no se disimula reduciendo el número de réplicas.
- **D-06:** El RandomForest+SHAP del Modelo 2 usa los **mismos 3 predictores numéricos + tipología** que el Modelo 1: `6.4.2` (estrés hídrico), `6.4.1` (eficiencia del agua), `8.2.1` (productividad laboral), más `is_ldc`/`is_lldc`/`is_sids`/`region`. Verificado en vivo: la pérdida de filas por missingness es prácticamente nula (171/173 filas completas con los 3 predictores). Mantener el mismo conjunto permite comparar el peso relativo del estrés hídrico entre ambos modelos en la memoria — reducir a solo `6.4.2` rompería ese propósito explícito de INTERP-04/MODEL2-03.
- **D-07:** El dashboard añade el Modelo 2 vía un **selector en la barra lateral** (`st.sidebar.selectbox`, "Modelo activo: Modelo 1 / Modelo 2") que cambia `ACTIVE_MODEL` globalmente — no pestañas nuevas y duplicadas. Las 4 pestañas existentes (Mapa, Modelo, Simulación, SHAP) ya leen de `ACTIVE_MODEL` sin reestructurarse, cumpliendo exactamente el propósito de D-07 (05-CONTEXT.md): Fase 6 solo añade la entrada `"Modelo 2 (Productividad agrícola)"` al dict `ACTIVE_MODELS` (`src/dashboard/models.py`, ya tiene el stub comentado) y sustituye el `ACTIVE_MODEL_NAME` hardcoded por el valor del selector.
- **D-08:** Cuando el Modelo 2 está seleccionado, cada pestaña muestra un **caption/aviso visible** sobre su cobertura reducida (≤39 países vs. 171 del Modelo 1) — mismo patrón ya usado en la Fase 5 para errores de carga de artefactos (`ARTIFACT_ERROR_MSG`, `src/dashboard/app.py`). El tribunal ve inmediatamente que la N es distinta sin tener que preguntarlo en la defensa oral.

### Paridad de robustez y heterogeneidad con el Modelo 1
- **D-09:** El Success Criterion de la Fase 6 solo exige explícitamente "efectos fijos bidireccionales, SEs clustered, mismos diagnósticos" — no menciona robustez ni heterogeneidad. Aun así, el Modelo 2 **incluye ambas piezas**, igual que el Modelo 1: mantiene el mismo rigor econométrico completo, no solo el mínimo exigido por el roadmap, y refuerza la narrativa de "extensión directa y comparable" ante el tribunal — consistente con la preferencia ya mostrada por el usuario en las Fases 3-5 (dashboard como "vitrina completa", no un mínimo viable).
- **D-10:** La comprobación de robustez usa el **mismo criterio sin-COVID (submuestra 2000–2019)** que el Modelo 1 (D-04, 03-CONTEXT.md). Verificado en vivo: excluir 2020–2022 deja 35 de 39 países (pérdida moderada; 2020 es la oleada individual más grande, 32 de 173 observaciones totales, pero no vacía el panel). Se usa el mismo criterio exacto — no la alternativa de controles `6.4.1`+`8.2.1` que ya se consideró y no se eligió en la Fase 3 — para mantener la comparabilidad directa "misma comprobación" entre ambos modelos en la memoria.
- **D-11:** El análisis de heterogeneidad del Modelo 2 usa **solo la interacción por tipología ONU (`is_ldc`)** — se abandona la interacción por región. Verificado en vivo: entre los 39 países del Modelo 2, la región está muy desbalanceada (Europa=26, África subsahariana=9, y 4 regiones con un único país cada una) — el término de interacción por región no sería identificable de forma fiable con N=1 por grupo (colineal con los efectos fijos de entidad). `is_ldc` sí mantiene variación real dentro de cada grupo (30 vs. 9 países).

### Claude's Discretion
- Nombre exacto del módulo/notebook del Modelo 2 (p. ej. `src/model2_agri.py`, `notebook/6_1_modelo2_agricultura.ipynb`) — libre mientras siga el patrón de nombres ya establecido (`panel_base.py`, `3_1_modelo1_pib.ipynb`, `4_1_interpretabilidad_simulacion.ipynb`).
- Estructura interna exacta de `filter_by_min_years` (D-02) más allá de su firma pública genérica — libre mientras calcule años observados directamente sobre `panel_clean` y no dependa de `panel_exclusions`.
- Ubicación exacta de `model2_agri.pkl` y del RF auxiliar del Modelo 2 (ya anticipada en `src/dashboard/models.py` como `data/modelos/model2_agri.pkl`) — libre mientras sea cargable sin reajuste, igual que `model1_gdp.pkl`.
- Formato exacto del caption de aviso de cobertura reducida en el dashboard (D-08) — libre mientras sea visible en cada pestaña cuando el Modelo 2 está activo.
- Redacción exacta de la sección de limitaciones del Modelo 2 en la memoria (extensión de REPRO-03) — libre mientras aborde explícitamente la cobertura reducida y cualquier resultado degenerado de Hausman/Pesaran (D-04).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Documentos del proyecto
- `.planning/PROJECT.md` — contexto completo; riesgo ya identificado en la propuesta oficial ("Indicador 2.3.1 con menor cobertura → Modelo 2 como extensión del Modelo 1, limitar si hace falta") y decisión [Phase 01-05] sobre el indicador `PD_AGR_SSFP` con su caveat de cobertura (50 países, 173/900 no-nulos) ya anotado para esta fase.
- `.planning/REQUIREMENTS.md` §"Modelo 2 — Productividad Agrícola" — MODEL2-01, MODEL2-02, MODEL2-03, con su criterio de aceptación exacto.
- `.planning/ROADMAP.md` §"Phase 6" — Goal y 3 Success Criteria verificables que esta fase debe cumplir (especialmente el listado explícito de "mismos diagnósticos" en el Criterion 1, base de D-04/D-09).

### Artefactos de fases anteriores (entrada directa de esta fase)
- `.planning/phases/03-modelo-1-regresi-n-de-panel-pib-per-c-pita/03-CONTEXT.md` — D-01/D-02 (regla de exclusión país-completo del Modelo 1, base de contraste para D-01/D-02 de esta fase), D-04 (robustez sin-COVID, replicada en D-10), D-05 (diseño paramétrico de `panel_base.py`, base de D-02).
- `.planning/phases/04-interpretabilidad-simulaci-n-y-robustez/04-CONTEXT.md` — D-02 (n_replicas=1000, replicado en D-05), D-05/D-06 (predictores del RF, replicados en D-06), D-09/D-10/D-11 (heterogeneidad por interacción, base de contraste para D-11), D-12 (diseño paramétrico de `simulate.py`/`interpret.py`).
- `.planning/phases/05-dashboard-y-preparaci-n-de-la-defensa/05-CONTEXT.md` — D-07 (parámetro de "modelo activo" ya preparado para esta fase, base directa de D-07 de esta fase).
- `src/panel_base.py` — `fit_panel_model`, `filter_by_exclusions`, `hausman_test`, `pesaran_cd_test`, `choose_cov_type` ya implementados y sin modificar; esta fase añade `filter_by_min_years` (D-02) sin tocar el resto.
- `src/simulate.py` — `bootstrap_counterfactual`, `fit_interaction_model`, `check_non_extrapolation` — invocados sin modificar con `dep_var="2.3.1"`.
- `src/interpret.py` — `shap_analysis`, `compute_vif_table` — invocados sin modificar con `dep_var="2.3.1"`, `feature_vars` de D-06.
- `src/dashboard/models.py` — `ACTIVE_MODELS` dict con el stub comentado para Modelo 2 ya preparado; esta fase lo completa (D-07).
- `src/dashboard/app.py`, `src/dashboard/data.py` — patrón de lectura de `ACTIVE_MODEL` en las 4 pestañas; base directa de D-07/D-08.
- `data/panel.db` (tablas `panel_clean`, `panel_exclusions`) — fuente de datos verificada en vivo durante esta discusión: 49 países con algún dato de `2.3.1`, 0 sobreviven al umbral del 70%, 39 sobreviven al umbral de ≥3 años (D-01), 35 sobreviven además excluyendo 2020-2022 (D-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/panel_base.py::fit_panel_model` — invocado sin modificar con `dep_var="2.3.1", indep_vars=["6.4.2"]` (patrón ya usado por el Modelo 1).
- `src/panel_base.py::hausman_test`, `pesaran_cd_test`, `choose_cov_type` — mismos diagnósticos, invocados sin modificar (D-04).
- `src/simulate.py::bootstrap_counterfactual`, `fit_interaction_model` — genéricos en `dep_var`/`indep_var`/`group_col`, invocados con `group_col="is_ldc"` (D-11), sin modificar.
- `src/interpret.py::shap_analysis`, `compute_vif_table` — genéricos en `dep_var`/`feature_vars`, invocados sin modificar (D-06).
- `src/dashboard/models.py::ACTIVE_MODELS` — dict ya preparado con un stub comentado exacto para la entrada del Modelo 2 (`dep_var="2.3.1"`, `pkl_path="data/modelos/model2_agri.pkl"`).
- `src/dashboard/app.py` — patrón `ARTIFACT_ERROR_MSG`/captions ya usado para avisos visibles de estado; reutilizable para D-08.

### Established Patterns
- Diseño paramétrico desde el principio (`panel_base.py` D-05 Fase 3, `simulate.py`/`interpret.py` D-12 Fase 4, `models.py` D-07 Fase 5) — esta fase es la primera que efectivamente ejercita esa reutilización, sin modificar ninguno de los módulos existentes.
- Patrón "warn, don't hide" (`hausman_test`/`pesaran_cd_test`/`compute_vif_table` ya usan `warnings.warn` con `stacklevel=2` ante resultados numéricamente degenerados) — replicado en D-04 para los diagnósticos del Modelo 2.
- Patrón "nunca hand-editar, siempre regenerar desde origen" — el nuevo `filter_by_min_years` (D-02) se calcula desde `panel_clean`, no desde un artefacto intermedio.

### Integration Points
- El dashboard (`src/dashboard/app.py`) es el punto de integración final — el selector de sidebar (D-07) conecta el nuevo `model2_agri.pkl`/RF con las 4 pestañas existentes sin reestructurarlas.
- `data/modelos/model2_agri.pkl` y el RF auxiliar del Modelo 2 siguen el mismo patrón de serialización round-trip-verificada que `model1_gdp.pkl` (Fase 3) y `rf_shap_model.pkl` (Fase 4).

</code_context>

<specifics>
## Specific Ideas

- El usuario seleccionó consistentemente la opción "Recomendado" en las 12 preguntas de esta discusión (umbral de cobertura, ubicación del helper, formato de documentación, ejecución de diagnósticos, n_replicas, predictores del RF, selector del dashboard, aviso de cobertura, alcance robustez+heterogeneidad, criterio sin-COVID, agrupación de heterogeneidad) — confirma, por quinta fase consecutiva, la preferencia ya establecida por especificaciones rigurosas y defendibles ante tribunal, diseño paramétrico/reutilizable, y transparencia explícita ("warn, don't hide") sobre atajos ocultos, incluso cuando eso significa documentar limitaciones de tamaño muestral en vez de disimularlas.
- Verificación en vivo durante la discusión (no solo prosa) reveló un hallazgo crítico no documentado en fases anteriores: el umbral de cobertura del 70% del Modelo 1 deja el Modelo 2 en **cero países** (cobertura máxima real 26%). Este hallazgo cambia sustancialmente el enfoque de MODEL2-02 de "documentar una reducción moderada de cobertura" (como anticipaba PROJECT.md) a "diseñar un criterio de inclusión completamente nuevo" — reflejado en D-01/D-02.

</specifics>

<deferred>
## Deferred Ideas

None — la discusión se mantuvo dentro del alcance de la Fase 6.

</deferred>

---

*Phase: 6-Modelo 2 — Productividad Agrícola (stretch)*
*Context gathered: 2026-07-14*
