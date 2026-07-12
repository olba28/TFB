# Phase 4: Interpretabilidad, Simulación y Robustez - Context

**Gathered:** 2026-07-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Sobre `model1_gdp.pkl` ya ajustado y diagnosticado (Fase 3: PanelOLS efectos fijos bidireccionales, `dep_var="8.1.1"`, `indep_vars=["6.4.2"]`, SEs Driscoll-Kraay), esta fase añade: (1) simulación contrafactual con bootstrap por país para al menos tres escenarios de reducción del estrés hídrico (-10/-20/-30%), con verificación explícita de no-extrapolación; (2) gráfico multi-escenario de sensibilidad; (3) análisis de heterogeneidad regional/por tipología de país vía términos de interacción, sin predicciones por país individual; (4) interpretabilidad SHAP (TreeExplainer sobre un RandomForest auxiliar multivariante), precedida por la matriz VIF/correlación de la Fase 2; (5) gráficos ALE/partial-dependence complementarios; (6) el mismo RandomForest sirve como modelo de referencia predictivo (INTERP-06); (7) semillas aleatorias fijas en todo paso estocástico (REPRO-02, bootstrap + entrenamiento RF). Cubre INTERP-01 a INTERP-06 y REPRO-02.

Esta fase NO incluye el dashboard (Fase 5) ni el ajuste del Modelo 2 en sí (Fase 6) — pero sí deja `simulate.py`/`interpret.py` diseñados para que Fase 6 los reutilice sin modificarlos, siguiendo el patrón ya establecido por `panel_base.py` (D-05, Fase 3).

</domain>

<decisions>
## Implementation Decisions

### Bootstrap de la simulación contrafactual (INTERP-01)
- **D-01:** El bootstrap remuestrea **entidades completas (países) con reemplazo** ("block bootstrap" por país) y reajusta `fit_panel_model` en cada réplica — no bootstrap paramétrico sobre la matriz de covarianzas Driscoll-Kraay. Respeta la dependencia temporal dentro de cada país y la dependencia transversal que el test de Pesaran CD detectó en la Fase 3 (p=0.0014), que un bootstrap i.i.d. por fila violaría.
- **D-02:** Objetivo de **1000 réplicas** por escenario — estándar académico para CI estables en los percentiles 2.5/97.5, asumible en tiempo de ejecución dado el tamaño del panel (171 países, ~3879 obs.) y la velocidad de `PanelOLS`.
- **D-03:** La reducción de estrés hídrico de cada escenario (-10/-20/-30%) se aplica sobre el **valor de estrés hídrico del último año observado por país (2022)**, no sobre la media histórica — más intuitivo de comunicar en la defensa oral ("si el estrés hídrico actual bajara X%") y más simple de verificar contra el rango empírico 2000–2022.
- **D-04:** Verificación de no-extrapolación (INTERP-01): si el valor simulado de un país para un escenario cae por debajo del mínimo de estrés hídrico observado globalmente en el panel 2000–2022, **ese país se excluye únicamente de ese escenario** (puede seguir presente en escenarios menos agresivos) — no se trunca ("cap") el valor. El número/lista de países excluidos por escenario debe documentarse explícitamente.

### Modelo auxiliar ML para SHAP e INTERP-06
- **D-05:** El RandomForest auxiliar (INTERP-04) es **multivariante**: predictores `6.4.2` (estrés hídrico), `6.4.1` (eficiencia agua), `8.2.1` (productividad laboral), más tipología de país (`is_ldc`/`is_lldc`/`is_sids`, `region`) — no solo estrés hídrico. Necesario para que SHAP pueda mostrar el "peso relativo del estrés hídrico frente a otras variables" (propósito explícito de INTERP-04), que la especificación parsimoniosa del Modelo 1 (D-03, Fase 3) no puede responder por diseño.
- **D-06:** `2.3.1` (productividad agrícola) se **excluye** de los predictores del RF de esta fase — es la variable objetivo del Modelo 2 (Fase 6), no un predictor de PIB per cápita, y su cobertura reducida (50 países vs. 171 del Modelo 1) recortaría drásticamente la muestra disponible si se incluyera.
- **D-07:** El **mismo RandomForest** entrenado para SHAP (INTERP-04) se reutiliza como modelo de referencia predictivo de INTERP-06 — no se entrena un Gradient Boosting separado. Evita duplicar entrenamiento/validación/documentación de dos modelos ML distintos para un requisito que no lo exige explícitamente; consistente con la preferencia del usuario por especificaciones simples y defendibles ante tribunal.
- **D-08:** El RandomForest auxiliar se **serializa** (p. ej. `data/modelos/rf_shap_model.pkl`), igual que `model1_gdp.pkl` (MODEL1-06) — la Fase 5 (dashboard, DASH-01) necesita consumir artefactos ya calculados sin llamadas/reajustes en tiempo real, y la Fase 6 podrá reutilizarlo o reajustarlo desde el mismo patrón.

### Heterogeneidad regional/por tipología (INTERP-03)
- **D-09:** Se implementa con **términos de interacción** dentro del mismo `PanelOLS` de efectos fijos (`estrés_hídrico × grupo` como regresor adicional) — no submodelos separados por subgrupo. Un solo modelo, coeficiente de interacción testable directamente, reutiliza `fit_panel_model` sin modificarlo (solo cambia `indep_vars`).
- **D-10:** Las variables de agrupación son **`region` y la tipología ONU (`is_ldc`)** (dos interacciones separadas) — la tipología ONU es el proxy ya validado en Fase 2 (D-01, 02-CONTEXT.md) para "nivel de desarrollo/ingresos", dado que no hay grupos de ingresos del Banco Mundial disponibles en la API SDG.
- **D-11:** Los resultados se presentan **únicamente como tabla de coeficientes de interacción por grupo** (estrés hídrico dentro de cada región/tipología, con SE e IC) — nunca un valor predicho para un país individual. Cumple la restricción de INTERP-03 por diseño del output, no por un filtro posterior.

### Reutilización de código para Fase 6 (Modelo 2)
- **D-12:** Se diseñan módulos paramétricos en `src/` (`simulate.py`, `interpret.py`) desde esta fase, siguiendo el mismo patrón que `panel_base.py` (D-05, 03-CONTEXT.md): genéricos en variable dependiente/independientes (p. ej. `bootstrap_counterfactual(fitted_results, df, dep_var, indep_var, ...)`, `shap_analysis(df, dep_var, feature_vars, ...)`), invocables por la Fase 6 con `dep_var="2.3.1"` sin modificar el módulo. Consistente con la preferencia del usuario, ya expresada en Fase 3, de diseñar para reutilización desde el principio en vez de posponer refactors.
- **D-13:** Un único notebook `4_1_interpretabilidad_simulacion.ipynb` cubre simulación contrafactual, heterogeneidad, SHAP y ALE en orden — consistente con el patrón de un notebook por fase ya usado en Fases 2 y 3 (`3_1_modelo1_pib.ipynb`).

### Claude's Discretion
- Formato exacto del gráfico multi-escenario de sensibilidad (INTERP-02) — libre mientras visualice los ≥3 escenarios con sus intervalos de confianza.
- Estructura interna exacta de `simulate.py`/`interpret.py` (nombres de funciones auxiliares) más allá de las firmas públicas genéricas fijadas en D-12.
- Umbral/criterio de significancia de los coeficientes de interacción de heterogeneidad (D-09/D-10) — libre mientras se reporte SE e IC.
- Qué variables concretas de las Fase-2-VIF-correlacionadas reciben gráficos ALE/partial-dependence (INTERP-05) — libre mientras se complementen los predictores del RF con correlación relevante identificada en la Fase 2.
- Mecanismo exacto de fijación de semillas (REPRO-02) — una semilla global vs. semillas por paso — libre mientras sea determinista y documentado, y garantice resultados idénticos entre ejecuciones.
- Hiperparámetros del RandomForest (n_estimators, max_depth, etc.) — libre mientras sea reproducible con semilla fija.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Documentos del proyecto
- `.planning/PROJECT.md` — contexto completo, riesgo "escenario contrafactual difícil de validar empíricamente" y su mitigación (enmarcar como simulación de sensibilidad, presentar intervalos de confianza) — directamente relevante para D-01 a D-04.
- `.planning/REQUIREMENTS.md` §"Interpretabilidad, Simulación y Robustez" — INTERP-01 a INTERP-06 y REPRO-02, con su criterio de aceptación exacto.
- `.planning/ROADMAP.md` §"Phase 4" — Goal y 6 Success Criteria verificables que esta fase debe cumplir.

### Artefactos de fases anteriores (entrada directa de esta fase)
- `.planning/phases/03-modelo-1-regresi-n-de-panel-pib-per-c-pita/03-CONTEXT.md` — D-05 (diseño paramétrico de `panel_base.py`), patrón que `simulate.py`/`interpret.py` deben replicar (D-12 arriba).
- `.planning/phases/03-modelo-1-regresi-n-de-panel-pib-per-c-pita/03-VERIFICATION.md` — resultados live del Modelo 1 (Pesaran CD p=0.0014, Driscoll-Kraay SEs elegidas) que justifican D-01 (block bootstrap, no i.i.d.).
- `.planning/phases/02-construcci-n-del-panel-y-eda/02-CONTEXT.md` (si existe) / `.planning/PROJECT.md` — decisión de tipología ONU (`is_ldc`/`is_lldc`/`is_sids`) como proxy de nivel de desarrollo en ausencia de grupos de ingresos del Banco Mundial — base directa de D-10.
- `src/panel_base.py` — `fit_panel_model`, `filter_by_exclusions`, `choose_cov_type` ya implementados; `simulate.py`/`interpret.py` los invocan, no los duplican.
- `data/modelos/model1_gdp.pkl` — modelo ya serializado que esta fase carga y NO reajusta (excepto dentro de las réplicas bootstrap de D-01, que sí reajustan expresamente).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/panel_base.py` — `fit_panel_model(df, dep_var, indep_vars, entity_effects, time_effects, cov_type, **cov_config)`, `filter_by_exclusions(df, exclusions, dep_var, indep_vars)`, `choose_cov_type(pesaran_result, alpha)` — el bootstrap de D-01 reajusta el modelo llamando a `fit_panel_model` en cada réplica sobre un remuestreo de países, reutilizando la misma función sin modificarla.
- `src/db.py` — `get_engine()`, patrón de conexión SQLAlchemy a `data/panel.db` que `simulate.py`/`interpret.py` deben reutilizar para cargar `panel_clean`/`panel_exclusions`.
- `data/modelos/model1_gdp.pkl` — modelo base ya ajustado (Fase 3); la simulación contrafactual arranca desde sus coeficientes/especificación, no reajusta desde cero salvo en las réplicas bootstrap.

### Established Patterns
- Diseño paramétrico desde el principio (`panel_base.py`, D-05 Fase 3) — replicado aquí en D-12 para `simulate.py`/`interpret.py`.
- Patrón "nunca hand-editar, siempre regenerar desde origen" — el bootstrap y el RF se reajustan/regeneran desde `panel_clean`/`panel_exclusions`, no desde artefactos intermedios hand-tuned.
- Naming de notebooks `{fase}_{n}_{nombre}.ipynb` (`3_1_modelo1_pib.ipynb`) — esta fase continúa con `4_1_interpretabilidad_simulacion.ipynb` (D-13).
- Serialización de modelos a `data/modelos/*.pkl` (MODEL1-06) — replicado en D-08 para el RF auxiliar.

### Integration Points
- La Fase 5 (Dashboard) consumirá los artefactos serializados de esta fase (resultados de simulación, `rf_shap_model.pkl`, valores SHAP) sin llamadas en tiempo real (DASH-01).
- La Fase 6 (Modelo 2) invocará `simulate.py`/`interpret.py` con `dep_var="2.3.1"` — la firma paramétrica de D-12 es lo que hace esa reutilización posible sin tocar los módulos, igual que D-05 lo hizo para `panel_base.py`.

</code_context>

<specifics>
## Specific Ideas

- El usuario ha mantenido, por tercera fase consecutiva, la preferencia por especificaciones simples/defendibles ante tribunal (un solo RF en vez de RF+GBM, interacciones en vez de submodelos) y por diseñar módulos reutilizables desde el principio en vez de posponer refactors (D-12, igual que D-05 en Fase 3).
- Insistencia explícita en que el chequeo de no-extrapolación (D-04) excluya países por escenario en vez de aplicar un "cap" — el usuario prioriza la honestidad estadística del método (excluir cuando el supuesto no se sostiene) sobre mantener el N constante entre escenarios.

</specifics>

<deferred>
## Deferred Ideas

None — la discusión se mantuvo dentro del alcance de la Fase 4.

</deferred>

---

*Phase: 4-Interpretabilidad, Simulación y Robustez*
*Context gathered: 2026-07-12*
