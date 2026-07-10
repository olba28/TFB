# Requirements: TFB — Impacto económico del estrés hídrico

**Defined:** 2026-07-10
**Core Value:** Un pipeline reproducible de extremo a extremo (ingesta API → almacenamiento → modelado → simulación → visualización) que demuestre, con datos abiertos y trazables, la relación cuantitativa entre estrés hídrico y resultados económicos — y que sea defendible ante un tribunal académico.

## v1 Requirements

### Ingesta y Almacenamiento

- [ ] **INGEST-01**: El sistema obtiene, vía la API SDG de la ONU, los 5 indicadores definidos (estrés hídrico 6.4.2, eficiencia de uso del agua, crecimiento PIB per cápita, productividad laboral, productividad agrícola 2.3.1) para 150+ países, series 2000–2022, con paginación y reintentos
- [ ] **INGEST-02**: El sistema filtra las respuestas de la API por dimensión (p. ej. `Activity: TOTAL`) para evitar filas duplicadas por país-año
- [ ] **INGEST-03**: El sistema excluye agregados regionales (códigos M49 de región) del panel de países, usando un crosswalk M49↔ISO3 (pycountry) y una lista canónica de países
- [ ] **INGEST-04**: El sistema guarda una copia local versionada de los datos crudos (JSON) junto con un manifiesto de procedencia, antes de cualquier transformación
- [ ] **INGEST-05**: El sistema almacena el panel en SQLite (tabla `raw_observations` larga e inmutable + tabla `panel` ancha derivada)

### Construcción del Panel y EDA

- [ ] **PANEL-01**: El pipeline de limpieza, fusión y feature engineering es idempotente y reconstruible desde los datos crudos
- [ ] **PANEL-02**: El sistema filtra países con cobertura mínima del 70% de años disponibles por indicador, documentando las exclusiones en una tabla
- [ ] **PANEL-03**: La memoria documenta explícitamente el patrón de datos faltantes (riesgo MNAR) y su posible sesgo hacia países con mejor reporting
- [ ] **PANEL-04**: El sistema produce un análisis exploratorio (EDA) global, regional y por tipología de país, con matriz de correlación/VIF entre variables

### Modelo 1 — PIB per cápita

- [ ] **MODEL1-01**: Existe una función compartida de ajuste/diagnóstico de panel (`panel_base.py`) reutilizable por Modelo 1 y Modelo 2
- [ ] **MODEL1-02**: El Modelo 1 usa PanelOLS con efectos fijos de país Y de año (two-way fixed effects) como especificación base
- [ ] **MODEL1-03**: El sistema compara el Modelo 1 con especificaciones pooled OLS y de efectos aleatorios (RE), incluyendo el test de Hausman que justifica la elección de efectos fijos
- [ ] **MODEL1-04**: El Modelo 1 usa errores estándar robustos apropiados (clustered por país, o Driscoll-Kraay si el test de dependencia transversal de Pesaran lo indica)
- [ ] **MODEL1-05**: El sistema incluye al menos una comprobación de robustez del Modelo 1 (especificación alternativa o submuestra)
- [ ] **MODEL1-06**: El Modelo 1 ajustado se serializa (pickle) para su uso posterior por simulación e interpretabilidad, sin necesidad de reajuste

### Interpretabilidad, Simulación y Robustez

- [ ] **INTERP-01**: El sistema ejecuta una simulación contrafactual con intervalos de confianza por bootstrap, enmarcada explícitamente como análisis de sensibilidad (no predicción causal), verificando que los escenarios no extrapolan más allá del rango empírico observado
- [ ] **INTERP-02**: El sistema produce un gráfico multi-escenario de sensibilidad (p. ej. -10%, -20%, -30% de reducción del estrés hídrico)
- [ ] **INTERP-03**: El sistema incluye un análisis de heterogeneidad regional/por nivel de ingresos (términos de interacción o subgrupos), sin generar predicciones por país individual
- [ ] **INTERP-04**: El sistema calcula interpretabilidad SHAP vía un modelo auxiliar de scikit-learn (RandomForest) con TreeExplainer, precedido de una matriz de correlación/VIF como aviso de posible sesgo por variables correlacionadas
- [ ] **INTERP-05**: El sistema produce gráficos ALE/partial-dependence como complemento a SHAP para las variables correlacionadas
- [ ] **INTERP-06**: El sistema incluye un modelo de referencia (Random Forest/Gradient Boosting) como comparación predictiva complementaria al modelo econométrico, sin sustituir su interpretación causal

### Dashboard

- [ ] **DASH-01**: El dashboard local (Streamlit + Plotly) muestra un choropleth por país y consume únicamente artefactos ya calculados, sin llamadas en tiempo real a la API
- [ ] **DASH-02**: El dashboard usa caché de datos (`st.cache_data`) y de modelo (`st.cache_resource`) para evitar congelaciones durante la demo en directo
- [ ] **DASH-03**: El dashboard permite comparar múltiples indicadores lado a lado
- [ ] **DASH-04**: El dashboard incluye una animación temporal del choropleth a lo largo de 2000–2022
- [ ] **DASH-05**: El dashboard se ensaya con caché fría en la máquina de presentación antes de la defensa, con capturas/vídeo de respaldo pre-renderizados

### Reproducibilidad

- [ ] **REPRO-01**: El proyecto genera un fichero de dependencias fijas (`requirements.lock.txt`) vía `pip freeze`
- [ ] **REPRO-02**: Todos los pasos estocásticos (bootstrap, modelo ML, cualquier split) usan semillas aleatorias fijas
- [ ] **REPRO-03**: La memoria incluye una sección explícita de "Limitaciones / Amenazas a la validez" que aborda causalidad inversa y endogeneidad

### Modelo 2 — Productividad Agrícola

- [ ] **MODEL2-01**: El Modelo 2 (productividad agrícola, indicador 2.3.1) reutiliza `panel_base.py` con la misma metodología que el Modelo 1
- [ ] **MODEL2-02**: El sistema documenta las limitaciones de cobertura de países si la muestra se reduce para el indicador 2.3.1
- [ ] **MODEL2-03**: La simulación, SHAP y el dashboard se extienden para cubrir los resultados del Modelo 2

## v2 Requirements

Reconocidos pero no comprometidos en el roadmap actual.

### Diferenciadores adicionales

- **EXTRA-01**: Informe automatizado y visual de cobertura/missingness (mapa de calor país × indicador × año)

## Out of Scope

Excluidos explícitamente por la propuesta oficial del TFB (`PROJECT.md`).

| Feature | Reason |
|---------|--------|
| Viabilidad técnica o coste de despliegue de los MOFs | El Nobel de Química 2025 es la motivación del estudio, no una variable del modelo |
| Datos subnacionales / a nivel de cuenca hidrográfica | Alcance a nivel país únicamente, según la fuente de datos (API SDG) |
| Ingesta en tiempo real o conexión a APIs en streaming | Contradice el objetivo de reproducibilidad con una copia local versionada y congelada |
| Efectos de segunda derivada del agua (migraciones, conflictos, salud pública) | Fuera del alcance económico definido (PIB y productividad agrícola) |
| Predicciones a nivel de país individual | El modelo es global/panel; los resultados se interpretan en ese contexto, no como pronóstico por país |
| Despliegue online del dashboard | Decisión explícita del alumno: solo uso local para la demo de defensa |
| Métodos formales de identificación causal (IV, DiD, synthetic control) | No hay instrumento válido identificado; contradice el enfoque elegido de "simulación de sensibilidad, no predicción causal" |
| AutoML / búsqueda extensiva de hiperparámetros | Coste de tiempo alto frente al plazo académico fijo, sin beneficio claro para el objetivo causal/interpretativo |
| Plataforma de ingesta ODS/SDG genérica y reutilizable | El alcance es un conjunto fijo y pequeño de indicadores para un TFB, no una plataforma |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 1 | Pending |
| INGEST-02 | Phase 1 | Pending |
| INGEST-03 | Phase 1 | Pending |
| INGEST-04 | Phase 1 | Pending |
| INGEST-05 | Phase 1 | Pending |
| REPRO-01 | Phase 1 | Pending |
| PANEL-01 | Phase 2 | Pending |
| PANEL-02 | Phase 2 | Pending |
| PANEL-03 | Phase 2 | Pending |
| PANEL-04 | Phase 2 | Pending |
| MODEL1-01 | Phase 3 | Pending |
| MODEL1-02 | Phase 3 | Pending |
| MODEL1-03 | Phase 3 | Pending |
| MODEL1-04 | Phase 3 | Pending |
| MODEL1-05 | Phase 3 | Pending |
| MODEL1-06 | Phase 3 | Pending |
| REPRO-03 | Phase 3 | Pending |
| INTERP-01 | Phase 4 | Pending |
| INTERP-02 | Phase 4 | Pending |
| INTERP-03 | Phase 4 | Pending |
| INTERP-04 | Phase 4 | Pending |
| INTERP-05 | Phase 4 | Pending |
| INTERP-06 | Phase 4 | Pending |
| REPRO-02 | Phase 4 | Pending |
| DASH-01 | Phase 5 | Pending |
| DASH-02 | Phase 5 | Pending |
| DASH-03 | Phase 5 | Pending |
| DASH-04 | Phase 5 | Pending |
| DASH-05 | Phase 5 | Pending |
| MODEL2-01 | Phase 6 | Pending |
| MODEL2-02 | Phase 6 | Pending |
| MODEL2-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-10*
*Last updated: 2026-07-10 after roadmap creation (6 phases, 100% coverage)*
