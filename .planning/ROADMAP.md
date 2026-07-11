# Roadmap: TFB — Impacto económico del estrés hídrico

## Overview

El proyecto avanza como un pipeline de datos secuencial y en capas: primero se ingiere y versiona una copia local de los 5 indicadores ODS de la ONU, después se construye y explora un panel país×año limpio, luego se ajusta el Modelo 1 (PanelOLS de efectos fijos bidireccionales para el crecimiento del PIB per cápita) con el rigor diagnóstico que exige un tribunal econométrico, a continuación se añaden interpretabilidad (SHAP/ALE) y simulación contrafactual sobre ese modelo ya validado, después se construye y ensaya el dashboard local de defensa, y — si el tiempo lo permite — se extiende toda la metodología a un Modelo 2 de productividad agrícola. Cada fase depende de que la anterior entregue artefactos ya calculados y confiables; nada se reajusta ni se recalcula "en caliente" aguas abajo.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Ingesta y Almacenamiento Versionado** - Cliente API SDG de la ONU con paginación/reintentos, filtrado de dimensiones y agregados regionales, copia local versionada con manifiesto, panel base en SQLite
- [ ] **Phase 2: Construcción del Panel y EDA** - Limpieza/fusión/feature engineering idempotente, filtrado por cobertura del 70%, discusión de datos faltantes (MNAR), EDA global/regional/por tipología con correlación/VIF
- [ ] **Phase 3: Modelo 1 — Regresión de Panel (PIB per cápita)** - `panel_base.py` compartido, PanelOLS con efectos fijos bidireccionales, comparación pooled/RE + Hausman, SEs robustos, robustez, serialización, sección de limitaciones
- [ ] **Phase 4: Interpretabilidad, Simulación y Robustez** - Simulación contrafactual bootstrap multi-escenario, heterogeneidad regional/por ingresos, SHAP + ALE con semillas fijas
- [ ] **Phase 5: Dashboard y Preparación de la Defensa** - Dashboard Streamlit/Plotly cacheado, choropleth, comparación de indicadores, animación temporal, ensayo con caché fría y respaldo pre-renderizado
- [ ] **Phase 6: Modelo 2 — Productividad Agrícola (stretch)** - Reutilización de `panel_base.py` para el indicador 2.3.1, documentación de cobertura reducida, extensión de simulación/SHAP/dashboard

## Phase Details

### Phase 1: Ingesta y Almacenamiento Versionado

**Goal**: El sistema obtiene y almacena de forma trazable y reproducible los 5 indicadores ODS de la ONU para 150+ países (2000–2022), sin duplicados ni agregados regionales, antes de cualquier transformación.
**Depends on**: Nothing (first phase)
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, REPRO-01
**Success Criteria** (what must be TRUE):

  1. La tabla `raw_observations` en SQLite contiene una única fila por (país, año, indicador) tras el filtrado de dimensiones (p. ej. `Activity: TOTAL`) — verificable con un assert de unicidad.
  2. Ningún código M49 de región aparece en el panel de países; el crosswalk M49↔ISO3 (pycountry) y la lista canónica de países filtran los agregados regionales.
  3. Existe, por cada indicador, una copia local versionada del JSON crudo devuelto por la API junto con un manifiesto de procedencia (fecha de descarga, URL, parámetros de consulta).
  4. El cliente de la API pagina automáticamente y reintenta ante fallos transitorios (verificable simulando una respuesta fallida/paginada).
  5. `requirements.lock.txt` existe en el repo y refleja las versiones exactas instaladas vía `pip freeze`.

**Plans**: 4/5 plans executed
**Wave 1**

- [x] 01-01-PLAN.md — Fundación: higiene del repo (.gitignore), entorno .venv, requirements.lock.txt (REPRO-01) y scaffolding de tests

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Cliente HTTP con reintentos/paginación + manifiesto de procedencia (INGEST-01, INGEST-04)
- [x] 01-03-PLAN.md — Lista canónica de países M49 + crosswalk ISO3 + log de exclusiones (INGEST-03)
- [x] 01-04-PLAN.md — Esquema SQLite: raw_observations (UNIQUE + assert) y panel derivada (INGEST-05)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-05-PLAN.md — Orquestador de ingesta + carga real de los 5 indicadores + verificación (INGEST-01/02/04)

### Phase 2: Construcción del Panel y EDA

**Goal**: A partir de los datos crudos versionados, el sistema produce un panel país×año limpio, filtrado por cobertura y documentado, junto con un análisis exploratorio que informa la especificación del Modelo 1.
**Depends on**: Phase 1
**Requirements**: PANEL-01, PANEL-02, PANEL-03, PANEL-04
**Success Criteria** (what must be TRUE):

  1. Reconstruir la tabla `panel` desde cero a partir de `raw_observations` produce un resultado idéntico (idempotencia verificable por comparación/hash entre ejecuciones).
  2. Existe una tabla de exclusiones que documenta qué países fueron descartados por no alcanzar el 70% de cobertura de años disponibles por indicador, y por qué.
  3. El documento/notebook incluye una discusión explícita del patrón de datos faltantes (riesgo MNAR) y de su posible sesgo hacia países con mejor reporting estadístico.
  4. El EDA produce estadísticas descriptivas y una matriz de correlación/VIF entre variables a nivel global, regional y por tipología de país.

**Plans**: TBD

### Phase 3: Modelo 1 — Regresión de Panel (PIB per cápita)

**Goal**: El sistema ajusta y diagnostica un modelo de panel de efectos fijos bidireccionales para el crecimiento del PIB real per cápita, con la especificación, los errores estándar y las comprobaciones de robustez que un tribunal econométrico exige, y lo deja serializado para su reutilización.
**Depends on**: Phase 2
**Requirements**: MODEL1-01, MODEL1-02, MODEL1-03, MODEL1-04, MODEL1-05, MODEL1-06, REPRO-03
**Success Criteria** (what must be TRUE):

  1. `panel_base.py` expone una función de ajuste/diagnóstico de panel reutilizable, invocada por el Modelo 1 (y diseñada para ser reutilizada sin cambios por el Modelo 2).
  2. El Modelo 1 se ajusta con `PanelOLS` y efectos fijos de país Y de año (`entity_effects=True, time_effects=True`) como especificación base.
  3. La comparación pooled OLS vs. efectos aleatorios (RE) vs. efectos fijos, junto con el test de Hausman, está documentada y justifica explícitamente la elección de efectos fijos.
  4. El Modelo 1 reporta errores estándar clustered por país (o Driscoll-Kraay si el test de dependencia transversal de Pesaran lo indica), no errores estándar por defecto.
  5. Al menos una comprobación de robustez (especificación alternativa o submuestra) produce resultados cualitativamente consistentes con el modelo base y queda documentada.
  6. `model1_gdp.pkl` existe y puede cargarse para generar predicciones/diagnósticos sin necesidad de reajustar el modelo.
  7. La memoria incluye una sección "Limitaciones / Amenazas a la validez" que aborda explícitamente causalidad inversa y endogeneidad.

**Plans**: TBD

### Phase 4: Interpretabilidad, Simulación y Robustez

**Goal**: Sobre el Modelo 1 ya diagnosticado y serializado, el sistema produce una simulación contrafactual de sensibilidad y un análisis de interpretabilidad, ambos reproducibles y sin extrapolar más allá del rango de datos observado.
**Depends on**: Phase 3
**Requirements**: INTERP-01, INTERP-02, INTERP-03, INTERP-04, INTERP-05, INTERP-06, REPRO-02
**Success Criteria** (what must be TRUE):

  1. La simulación contrafactual produce intervalos de confianza por bootstrap para al menos tres escenarios de reducción del estrés hídrico (p. ej. -10%, -20%, -30%), enmarcada explícitamente como análisis de sensibilidad y con verificación de que ningún escenario extrapola más allá del rango empírico observado.
  2. Existe un gráfico multi-escenario que visualiza los tres (o más) niveles de reducción simulados con sus intervalos de confianza.
  3. El análisis de heterogeneidad regional/por nivel de ingresos (interacciones o subgrupos) está documentado y no genera predicciones por país individual.
  4. Los valores SHAP (TreeExplainer sobre un RandomForest auxiliar) están precedidos por la matriz de correlación/VIF de la Fase 2 y acompañados de un aviso explícito de posible sesgo por variables correlacionadas.
  5. Existen gráficos ALE/partial-dependence que complementan los SHAP para las variables correlacionadas identificadas.
  6. Ejecutar dos veces el pipeline estocástico (bootstrap, entrenamiento del RandomForest, cualquier split) produce resultados idénticos gracias a semillas aleatorias fijas.

**Plans**: TBD

### Phase 5: Dashboard y Preparación de la Defensa

**Goal**: Un dashboard local que consume exclusivamente artefactos ya calculados responde con fluidez y fiabilidad durante la demo en directo de la defensa oral.
**Depends on**: Phase 4
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):

  1. El dashboard muestra un choropleth interactivo por país sin realizar ninguna llamada en tiempo real a la API de la ONU (verificable inspeccionando el código y el tráfico de red durante el uso).
  2. Con caché fría en la máquina de presentación, la primera carga completa el render en un tiempo aceptable para una demo en directo (objetivo: menos de 5 segundos) y las interacciones posteriores son instantáneas gracias a `st.cache_data`/`st.cache_resource`.
  3. El usuario puede comparar al menos dos indicadores lado a lado y reproducir la animación temporal del choropleth a lo largo de 2000–2022.
  4. Existen capturas de pantalla y/o un vídeo de respaldo pre-renderizados, ensayados como plan B ante un fallo del dashboard en directo.

**Plans**: TBD
**UI hint**: yes

### Phase 6: Modelo 2 — Productividad Agrícola (stretch)

**Goal**: Si el avance del proyecto lo permite, la misma metodología del Modelo 1 se extiende al indicador de productividad agrícola (2.3.1), reutilizando la infraestructura compartida en lugar de reimplementarla.
**Depends on**: Phase 5
**Requirements**: MODEL2-01, MODEL2-02, MODEL2-03
**Success Criteria** (what must be TRUE):

  1. `model2_agri.py` reutiliza `panel_base.py` sin duplicar lógica y aplica la misma especificación metodológica (efectos fijos bidireccionales, SEs clustered, mismos diagnósticos) que el Modelo 1.
  2. Si la muestra de países se reduce por la cobertura del indicador 2.3.1, la limitación queda documentada explícitamente con una tabla de cobertura/exclusiones específica del Modelo 2.
  3. El dashboard, la simulación contrafactual y el análisis SHAP incluyen una vista o selector que permite explorar los resultados del Modelo 2 junto a los del Modelo 1.

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Ingesta y Almacenamiento Versionado | 4/5 | In Progress|  |
| 2. Construcción del Panel y EDA | 0/TBD | Not started | - |
| 3. Modelo 1 — Regresión de Panel (PIB per cápita) | 0/TBD | Not started | - |
| 4. Interpretabilidad, Simulación y Robustez | 0/TBD | Not started | - |
| 5. Dashboard y Preparación de la Defensa | 0/TBD | Not started | - |
| 6. Modelo 2 — Productividad Agrícola (stretch) | 0/TBD | Not started | - |
