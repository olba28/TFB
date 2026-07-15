# Requirements: TFB — Impacto económico del estrés hídrico

**Defined:** 2026-07-15
**Core Value:** Un pipeline reproducible de extremo a extremo (ingesta API → almacenamiento → modelado → simulación → visualización) que demuestre, con datos abiertos y trazables, la relación cuantitativa entre estrés hídrico y resultados económicos — y que sea defendible ante un tribunal académico.

## v1 Requirements

Requisitos para el milestone v1.1 (Coverage Heatmap), cierre de EXTRA-01 diferido en v1.0.

### Visualización de Cobertura

- [x] **COVER-01**: El sistema genera un mapa de calor país × indicador × año que visualiza la cobertura de datos (presencia/ausencia) para los 5 indicadores ODS ya ingeridos, calculado sobre los datos crudos (antes del filtro de cobertura del 70% de Fase 2)
- [ ] **COVER-02**: La figura se exporta en formato estático (PNG) al directorio `figuras/` para su inclusión directa en el anexo de la memoria, sin cambios al dashboard Streamlit

## v2 Requirements

Ninguno diferido en este momento.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Integración en el dashboard Streamlit (nueva pestaña) | Decisión explícita del alumno: el heatmap es una figura estática para la memoria, no una vista interactiva |
| Nueva sección de discusión escrita sobre missingness | La discusión MNAR ya existe en la Fase 2 (PANEL-03); esta figura es un complemento visual, no un análisis nuevo |
| Extensión del heatmap a variables derivadas (residuos de modelos, SHAP, etc.) | Fuera del alcance de EXTRA-01, que se limita a los 5 indicadores ODS crudos |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COVER-01 | Phase 7 | Complete |
| COVER-02 | Phase 7 | Pending |

**Coverage:**

- v1 requirements: 2 total
- Mapped to phases: 2
- Unmapped: 0 ✅

---
*Requirements defined: 2026-07-15*
*Last updated: 2026-07-15 after roadmap creation (Phase 7 mapping)*
