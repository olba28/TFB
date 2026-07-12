# Phase 3: Modelo 1 — Regresión de Panel (PIB per cápita) - Context

**Gathered:** 2026-07-12
**Status:** Ready for planning

<domain>
## Phase Boundary

`panel_base.py` (función compartida de ajuste/diagnóstico de panel, reutilizable por Modelo 1 y Modelo 2) + Modelo 1: PanelOLS con efectos fijos bidireccionales (país y año) que predice el crecimiento del PIB real per cápita (`8.1.1`) en función del estrés hídrico (`6.4.2`), con comparación pooled OLS vs. efectos aleatorios (RE) + test de Hausman, errores estándar robustos (clustered por país, o Driscoll-Kraay si el test de Pesaran lo indica), una comprobación de robustez, serialización del modelo (`.pkl`), y una sección de limitaciones sobre causalidad inversa/endogeneidad. Cubre MODEL1-01 a MODEL1-06 y REPRO-03.

Esta fase NO incluye simulación contrafactual, SHAP/ALE, ni el dashboard (eso es Fase 4/5). Tampoco incluye el Modelo 2 (productividad agrícola) en sí — solo deja `panel_base.py` preparado para que la Fase 6 lo reutilice.

</domain>

<decisions>
## Implementation Decisions

### Cobertura/exclusiones en el ajuste
- **D-01:** `panel_base.py` filtra las observaciones usando `panel_exclusions` (tabla de la Fase 2, 529 pares país-indicador por debajo del 70% de cobertura) antes de ajustar PanelOLS — no usa `panel_clean` sin filtrar. Honra PANEL-02 explícitamente en el modelo, no solo en la documentación.
- **D-02:** Regla de exclusión cuando un país pasa el 70% en una variable del modelo pero no en otra: se excluye el país del ajuste si **cualquiera** de las variables usadas en esa especificación (dependiente o independiente) falla el umbral del 70% — panel balanceado respecto a las variables del modelo, no fila a fila.

### Variables de control del modelo base
- **D-03:** La especificación base (MODEL1-02) usa **solo** estrés hídrico (`6.4.2`) como variable independiente principal, más `entity_effects=True, time_effects=True` — sin controles adicionales (ni eficiencia hídrica `6.4.1` ni productividad laboral `8.2.1`) en el modelo base. Los efectos fijos absorben heterogeneidad no observada por país y shocks globales por año.

### Comprobación de robustez (MODEL1-05)
- **D-04:** La comprobación de robustez reajusta el modelo base sobre la submuestra 2000–2019, excluyendo los años COVID (2020–2022) — prueba que el resultado no depende de los shocks atípicos globales de ese período. (Nota: durante la discusión también se consideró "añadir controles 6.4.1+8.2.1" como alternativa; el usuario eligió la submuestra sin-COVID como la comprobación de robustez de esta fase — añadir controles no fue seleccionado y no debe asumirse como una segunda comprobación implícita.)

### Reutilización de panel_base.py para Modelo 2
- **D-05:** `panel_base.py` se diseña **paramétrico desde ya**: expone una función tipo `fit_panel_model(df, dep_var, indep_vars, entity_effects=True, time_effects=True, ...)` genérica en variable dependiente e independientes. El Modelo 1 la invoca con `dep_var="8.1.1", indep_vars=["6.4.2"]`; la Fase 6 (Modelo 2) la invocará con `dep_var="2.3.1"` sin modificar `panel_base.py`. Esto satisface MODEL2-01 ("reutiliza panel_base.py sin duplicar lógica") por construcción desde esta fase, evitando tener que tocar/re-validar el código del Modelo 1 más adelante.

### Claude's Discretion
- Método exacto para decidir clustered SEs vs. Driscoll-Kraay (criterio del test de dependencia transversal de Pesaran y su umbral) — MODEL1-04 solo exige que se use el apropiado según ese test, no fija el umbral de decisión.
- Estructura interna exacta de `panel_base.py` (nombres de funciones auxiliares, cómo se organiza el pooled/RE/Hausman internamente) más allá de la firma pública `fit_panel_model(...)` fijada en D-05.
- Ubicación exacta de `model1_gdp.pkl` (p. ej. `data/modelos/`) — MODEL1-06 solo exige que exista y sea cargable sin reajuste.
- Formato exacto de la sección de límites/Hausman en el output (tabla vs. texto) — libre mientras documente la comparación pooled/RE/FE y justifique la elección de efectos fijos.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Documentos del proyecto
- `.planning/PROJECT.md` — contexto completo, referencias metodológicas ya elegidas (Baltagi, Wooldridge) relevantes para el diseño de `panel_base.py`.
- `.planning/REQUIREMENTS.md` §"Modelo 1 — PIB per cápita" — MODEL1-01 a MODEL1-06 y REPRO-03, con su criterio de aceptación exacto.
- `.planning/ROADMAP.md` §"Phase 3" — Goal y 7 Success Criteria verificables que esta fase debe cumplir.
- `.planning/phases/02-construcci-n-del-panel-y-eda/02-VERIFICATION.md` §"Known Limitations Carried Forward" — documenta explícitamente que esta fase debe decidir cómo `panel_base.py` maneja `panel_exclusions` (resuelto en D-01/D-02 arriba).

### Artefactos de la Fase 2 (entrada directa de esta fase)
- `.planning/phases/02-construcci-n-del-panel-y-eda/02-01-SUMMARY.md` — esquema exacto de `panel_clean`/`panel_exclusions`/`country_reference` en `data/panel.db`.
- `.planning/phases/02-construcci-n-del-panel-y-eda/02-02-SUMMARY.md` — hallazgos EDA (VIF/correlación) que informan la interpretación de los resultados del Modelo 1.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/panel_build.py` — `rebuild_clean_panel(engine)` ya produce `panel_clean` (país×año, columnas de indicador `2.3.1, 6.4.1, 6.4.2, 8.1.1, 8.2.1` + `region, subregion, is_ldc, is_lldc, is_sids`) y `panel_exclusions` (529 filas, columnas `country_code, indicator_code, years_available, years_required, coverage_pct, excluded, reason`) en `data/panel.db` — insumo directo de `panel_base.py`.
- `src/db.py` — `get_engine()` ya establece el patrón de conexión SQLAlchemy que `panel_base.py` debe reutilizar (mismo engine, no una conexión nueva).

### Established Patterns
- Patrón "nunca hand-editar, siempre regenerar desde origen" (`db.rebuild_panel`, `panel_build.rebuild_clean_panel`) — `panel_base.py` debería seguir el mismo principio: el modelo se reajusta desde `panel_clean`/`panel_exclusions`, no desde un artefacto intermedio hand-tuned.
- Nombres de tabla fijos, nunca construidos desde input externo (Security V5, ya establecido en `src/db.py` y `src/panel_build.py`) — `panel_base.py` debe mantener el mismo patrón.

### Integration Points
- La Fase 4 (Interpretabilidad/Simulación) consumirá `model1_gdp.pkl` directamente, sin reajustar.
- La Fase 6 (Modelo 2) invocará `panel_base.py`'s `fit_panel_model(...)` con `dep_var="2.3.1"` — la firma paramétrica de D-05 es lo que hace esa reutilización posible sin tocar el módulo.

</code_context>

<specifics>
## Specific Ideas

- El usuario prefirió consistentemente las opciones "Recomendado" en las 4 áreas discutidas (filtrado por cobertura, especificación base parsimoniosa, robustez, diseño paramétrico) — indica preferencia por especificaciones simples/defendibles ante tribunal sobre alternativas más complejas, y por diseñar para reutilización futura desde el principio en vez de posponer refactors.

</specifics>

<deferred>
## Deferred Ideas

None — la discusión se mantuvo dentro del alcance de la Fase 3.

</deferred>

---

*Phase: 3-Modelo 1 — Regresión de Panel (PIB per cápita)*
*Context gathered: 2026-07-12*
