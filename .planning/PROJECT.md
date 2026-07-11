# TFB — Impacto económico del estrés hídrico

## What This Is

Trabajo Final de Bàtxelor (TFB) en Ciencia de Datos que cuantifica y modela la relación entre el estrés hídrico de un país y sus resultados económicos —crecimiento del PIB per cápita y productividad agrícola— usando exclusivamente indicadores públicos ODS de la API de la ONU para más de 150 países (series 2000–2022). El sistema resultante permite simular escenarios contrafactuales: cuánto mejorarían el PIB y la productividad agrícola si el estrés hídrico se redujera en X puntos porcentuales, y visualizar los resultados en un dashboard geoespacial interactivo. Es un trabajo académico individual, entregado y defendido ante tribunal (UCMA).

## Core Value

Un pipeline reproducible de extremo a extremo (ingesta API → almacenamiento → modelado → simulación → visualización) que demuestre, con datos abiertos y trazables, la relación cuantitativa entre estrés hídrico y resultados económicos — y que sea defendible ante un tribunal académico.

## Business Context

<!-- Trabajo académico individual, no monetizado ni customer-facing. -->

- **Destinatario**: Tutor/a de TFB y tribunal de defensa (UCMA)
- **Criterio de éxito**: Memoria aprobada (60–80 páginas) + defensa oral 10–15 min; ponderación 70% memoria + 30% defensa
- **Fuente de estrategia**: `G:\Mi unidad\UCMA\tfb\TFB Pablo Martínez Entrega 2.docx` (propuesta oficial entregada)

## Requirements

### Validated

- [x] Ingesta automática de indicadores ODS vía API pública de la ONU (Python + requests) para 150+ países, series 2000–2022 — Validado en Fase 01: ingesta-y-almacenamiento-versionado (INGEST-01/02/03)
- [x] Almacenamiento del panel de datos en SQLite (dataset integrado país × año) — Validado en Fase 01 (INGEST-05)
- [x] Descarga y versionado de una copia local de los datos (mitigación ante cambios de la API) — Validado en Fase 01 (INGEST-04)
- [x] Reproducibilidad: `pip freeze > requirements.lock.txt` y versiones exactas fijadas — Validado en Fase 01 (REPRO-01)

### Active

- [ ] Limpieza, transformación y feature engineering del panel
- [ ] Análisis exploratorio (EDA) de la relación estrés hídrico ↔ resultados económicos (global, regional, por tipología de país)
- [ ] Modelo 1: regresión de panel con efectos fijos por país (PanelOLS) para predecir la tasa de crecimiento del PIB real per cápita en función del estrés hídrico + variables de control socioeconómicas
- [ ] Modelo 2: mismo enfoque metodológico para productividad agrícola (indicador 2.3.1) — tratado como extensión del Modelo 1; si la cobertura de datos es insuficiente, limitar a países con datos completos y documentarlo
- [ ] Simulación de escenarios contrafactuales: impacto en PIB/productividad agrícola ante reducciones hipotéticas del estrés hídrico, con intervalos de confianza (enmarcado como simulación de sensibilidad, no predicción causal)
- [ ] Análisis de interpretabilidad (SHAP) del peso relativo del estrés hídrico frente a otras variables
- [ ] Dashboard geoespacial interactivo local (Streamlit + Plotly choropleth) para explorar resultados por país/región, usado en la demo de la defensa oral
- [ ] Filtrado de países con cobertura mínima del 70% de años disponibles por indicador; exclusiones documentadas

### Out of Scope

- Viabilidad técnica o coste de despliegue de los MOFs (estructuras metalorgánicas) — el Nobel de Química 2025 es la motivación del estudio, no una variable del modelo
- Datos subnacionales o a nivel de cuenca hidrográfica — el análisis es a nivel país
- Sistemas en tiempo real o conexión a APIs en streaming — la ingesta es batch sobre copia local versionada
- Efectos de segunda derivada del agua (migraciones, conflictos, salud pública) en los modelos
- Predicciones a nivel de país individual — el modelo es global/panel y los resultados se interpretan en ese contexto
- Despliegue online del dashboard (Streamlit Community Cloud u otro) — decisión explícita del alumno: solo uso local para la demo de defensa

## Context

- Fase 01 completa (2026-07-11): cliente API SDG con paginación/reintentos, crosswalk M49→ISO3, `data/panel.db` poblado (18,086 `raw_observations`, 4,923 `panel`, 215 países), copia local versionada de los 5 indicadores con manifiesto de procedencia, `requirements.lock.txt` congelado. Ver `.planning/phases/01-ingesta-y-almacenamiento-versionado/01-VERIFICATION.md`.
- Repo ya inicializado en git con estructura mínima: `requirements.txt` (dependencias ya elegidas: requests, pandas, numpy, jupyter, matplotlib, seaborn, statsmodels, linearmodels, scikit-learn, shap, plotly, streamlit), carpetas `data/`, `figuras/`, `notebook/`, `src/ingesta/` — ver `.planning/codebase/` para el mapeo detallado (STACK, ARCHITECTURE, STRUCTURE, CONVENTIONS, TESTING, INTEGRATIONS, CONCERNS).
- Fuente de datos única: API pública de indicadores ODS de la ONU (`https://unstats.un.org/SDGAPI/v1/`), ya usada en trabajos previos del alumno.
- Indicadores clave identificados en la propuesta:
  1. Nivel de estrés hídrico (indicador ODS 6.4.2, extracción de agua dulce como % de recursos disponibles) — variable independiente principal, 2000–2022, 180 países
  2. Eficiencia en el uso del agua por sector económico — variable independiente complementaria
  3. Tasa de crecimiento anual del PIB real per cápita — variable objetivo del Modelo 1
  4. Crecimiento del PIB real por persona empleada (productividad laboral) — variable complementaria del Modelo 1
  5. Volumen de producción agrícola por unidad de trabajo (indicador ODS 2.3.1) — variable objetivo del Modelo 2
- Riesgos identificados en la propuesta oficial y su mitigación:
  - Cobertura incompleta de países → filtrar con mínimo 70% de años disponibles, documentar exclusiones
  - Causalidad inversa (países pobres → más estrés hídrico) → modelos de panel con efectos fijos por país; discutir la limitación explícitamente en la memoria
  - Escenario contrafactual difícil de validar empíricamente → enmarcarlo como simulación de sensibilidad, presentar intervalos de confianza
  - Indicador 2.3.1 con menor cobertura → Modelo 2 como extensión del Modelo 1, limitar si hace falta
  - Tiempo limitado para dos modelos completos → priorizar Modelo 1 (PIB); Modelo 2 si el avance lo permite
  - Cambios en la API de la ONU → copia local versionada desde la primera fase
- Cronograma oficial UCMA (referencia, no vinculante para el roadmap de GSD):
  - Entrega 2 (marco teórico + metodología, ~60%): 20–26 julio 2026 — ingesta API, limpieza, BD, EDA, primer entrenamiento del Modelo 1
  - Entrega 3 (100%): 31 agosto–6 septiembre 2026 — Modelo 2, simulación contrafactual, dashboard, discusión, conclusiones, referencias APA (60–80 páginas)
  - Entrega 4 (depósito final): 14–20 septiembre 2026
  - Defensa oral: 12–25 octubre 2026 (70% memoria + 30% defensa)
- Referencias metodológicas ya seleccionadas por el alumno: Baltagi (panel data), Wooldridge (econometría), James et al. / ISLR (aprendizaje estadístico), Molnar (interpretabilidad), FAO & UN-Water 2024, UNESCO 2024, Borja-Vega & Zhang / Banco Mundial.
- Competencias del Bachelor a demostrar (nivel esperado 1–5): CE2 (4), CE3 (3), CE4 (5), CE5 (4), CE8 (3), CE10 (2), CE11 (3).

## Constraints

- **Lenguaje/Stack**: Python, dependencias fijadas en `requirements.txt` (pandas, numpy, statsmodels, linearmodels, scikit-learn, shap, plotly, streamlit, jupyter) — no cambiar sin justificación
- **Fuente de datos**: Exclusivamente la API pública ODS de la ONU — ninguna otra fuente de datos, para garantizar trazabilidad y reproducibilidad total
- **Almacenamiento**: SQLite (decisión del alumno — cero configuración, un solo fichero, fácil de entregar/versionar)
- **Alcance geográfico/temporal**: Nivel país (no subnacional), 2000–2022, ~150–180 países según cobertura
- **Metodología**: Modelos de panel con efectos fijos (no solo regresión OLS simple) para controlar heterogeneidad no observada
- **Entregable académico**: Memoria de 60–80 páginas + defensa oral; debe seguir la estructura de índice ya propuesta (introducción, marco teórico, metodología, desarrollo, resultados, conclusiones, referencias APA, anexos)
- **Plazo**: Cronograma UCMA con hitos hasta octubre 2026 (ver Context) — sirve de referencia pero el roadmap de fases de GSD es independiente y puede tener más granularidad
- **Windows**: Entorno de desarrollo en Windows — se evitó GDAL/geopandas por fragilidad de instalación (ya reflejado en `requirements.txt`)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Roadmap de GSD cubre el TFB completo (no solo Entrega 2) | El alumno prefiere planificar todas las fases desde el inicio, ajustando sobre la marcha | — Pending |
| SQLite como motor de almacenamiento del panel | Cero configuración, un solo archivo, adecuado para un TFB individual y fácil de entregar/versionar | Implementado en Fase 01 (`src/db.py`) |
| Dashboard solo local (sin despliegue online) | Basta con demo en vivo durante la defensa oral; evita complejidad/coste de hosting | — Pending |
| Fuente de datos única: API SDG de la ONU | Exigencia explícita de la propuesta — garantiza trazabilidad y reproducibilidad total | Implementado en Fase 01 (`src/ingesta/`) |
| Modelos de panel con efectos fijos (no solo regresión simple) | Mitigación del riesgo de causalidad inversa señalado en el análisis de riesgos de la propuesta | — Pending |
| Modelo 2 (agricultura) como extensión del Modelo 1, priorizado tras Modelo 1 (PIB) | Mitigación del riesgo de tiempo limitado señalado en la propuesta | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-11 after Phase 01 completion*
