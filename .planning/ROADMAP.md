# Roadmap: TFB — Impacto económico del estrés hídrico

## Milestones

- ✅ **v1.0 MVP** — Phases 1-6 (shipped 2026-07-15)
- 🚧 **v1.1 Coverage Heatmap** — Phase 7 (in planning)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-6) — SHIPPED 2026-07-15</summary>

- [x] Phase 1: Ingesta y Almacenamiento Versionado (6/6 plans) — completed 2026-07-11
- [x] Phase 2: Construcción del Panel y EDA (2/2 plans) — completed 2026-07-11
- [x] Phase 3: Modelo 1 — Regresión de Panel (PIB per cápita) (2/2 plans) — completed 2026-07-12
- [x] Phase 4: Interpretabilidad, Simulación y Robustez (3/3 plans) — completed 2026-07-13
- [x] Phase 5: Dashboard y Preparación de la Defensa (5/5 plans) — completed 2026-07-14
- [x] Phase 6: Modelo 2 — Productividad Agrícola (stretch) (3/3 plans) — completed 2026-07-15

Full phase details archived at `.planning/milestones/v1.0-ROADMAP.md`.

</details>

### v1.1 Coverage Heatmap

- [ ] **Phase 7: Mapa de Calor de Cobertura** - Figura estática PNG de cobertura/missingness (país × indicador × año) sobre datos crudos para el anexo de la memoria

## Phase Details

### Phase 7: Mapa de Calor de Cobertura
**Goal**: Producir una figura estática (PNG) de cobertura/missingness que visualiza la presencia/ausencia de datos país × indicador × año para los 5 indicadores ODS ya ingeridos, calculada sobre los datos crudos (`raw_observations`, antes del filtro del 70% de la Fase 2), lista para el anexo de la memoria.
**Depends on**: Phase 1 (tabla `raw_observations` poblada en `data/panel.db`) — todas las fases v1.0 completas
**Requirements**: COVER-01, COVER-02
**Success Criteria** (what must be TRUE):
  1. Existe un fichero PNG en `figuras/` que muestra un mapa de calor de cobertura (presencia/ausencia de datos) con ejes país × año y los 5 indicadores ODS representados.
  2. La cobertura mostrada se calcula desde `raw_observations` (datos crudos, sin aplicar la exclusión del 70% de la Fase 2), verificable porque incluye países/pares que `panel_clean` excluye.
  3. Los 5 indicadores ODS ingeridos (6.4.2, eficiencia de uso del agua, 8.1.1 PIB, productividad laboral, 2.3.1 agrícola) aparecen identificados en la figura.
  4. La figura se regenera de forma reproducible desde un script/notebook re-ejecutable, sin modificar ningún fichero del dashboard Streamlit (`src/dashboard/`).
**Plans**: 2 plans
- [ ] 07-01-PLAN.md — src/coverage.py (build_presence_matrix + ordered_countries_with_boundaries) + tests/test_coverage.py (COVER-01)
- [ ] 07-02-PLAN.md — notebook/7_1_mapa_calor_cobertura.ipynb + figuras/07_mapa_calor_cobertura.png (COVER-02)

## Progress

| Phase                                                | Milestone | Plans Complete | Status      | Completed  |
| ----------------------------------------------------- | --------- | --------------- | ----------- | ---------- |
| 1. Ingesta y Almacenamiento Versionado                 | v1.0      | 6/6             | Complete    | 2026-07-11 |
| 2. Construcción del Panel y EDA                       | v1.0      | 2/2             | Complete    | 2026-07-11 |
| 3. Modelo 1 — Regresión de Panel (PIB per cápita)      | v1.0      | 2/2             | Complete    | 2026-07-12 |
| 4. Interpretabilidad, Simulación y Robustez            | v1.0      | 3/3             | Complete    | 2026-07-13 |
| 5. Dashboard y Preparación de la Defensa                | v1.0      | 5/5             | Complete    | 2026-07-14 |
| 6. Modelo 2 — Productividad Agrícola (stretch)          | v1.0      | 3/3             | Complete    | 2026-07-15 |
| 7. Mapa de Calor de Cobertura                          | v1.1      | 0/2             | Planned     | -          |
