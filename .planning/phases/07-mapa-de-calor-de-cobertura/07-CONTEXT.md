# Phase 7: Mapa de Calor de Cobertura - Context

**Gathered:** 2026-07-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Producir una figura estática (PNG) de cobertura/missingness que visualiza la presencia/ausencia de datos país × indicador × año para los 5 indicadores ODS ya ingeridos (6.4.2, 6.4.1, 8.1.1, 8.2.1, 2.3.1), calculada sobre `raw_observations` (datos crudos, antes del filtro del 70% de la Fase 2), lista para el anexo de la memoria. Sin cambios al dashboard Streamlit. Sin nueva sección de discusión escrita (la discusión MNAR ya existe en la Fase 2).

</domain>

<decisions>
## Implementation Decisions

### Layout de la figura
- **D-01:** Grid de 5 sub-heatmaps (uno por cada uno de los 5 indicadores ODS), cada uno país × año, en lugar de colapsar a un único panel agregado. Justificación del usuario: más fiel a COVER-01 ("los 5 indicadores ODS... aparecen identificados en la figura") que un heatmap único con color agregado.
- **D-02:** El resultado final es UN solo fichero PNG (per COVER-02, "un fichero PNG") — los 5 sub-heatmaps se combinan en una sola figura (p.ej. matplotlib subplots grid), no 5 PNGs separados.

### Orden de países (eje Y de cada sub-heatmap)
- **D-03:** Países agrupados por región SDG (con separadores visuales entre grupos), no alfabético ni ordenado por cobertura. Usa el campo `region` ya calculado en Fase 2 (`src/ingesta/typology.py::build_region_map`, expuesto en la tabla `panel`/`panel_clean` vía `panel_build.py::REFERENCE_COLUMNS`). Nota: `raw_observations` no tiene columna `region` — requiere join con la tabla `panel` (o con el mapa de región derivado directamente de `GeoArea/Tree`) para obtener el agrupamiento, sin usar `panel_clean` como fuente de la cobertura en sí (eso violaría COVER-01: debe calcularse sobre datos crudos).

### Definición de "dato ausente"
- **D-04:** Una celda país-año-indicador cuenta como "sin dato" (missing) si NO existe fila en `raw_observations` para esa combinación, O si existe la fila pero `value IS NULL`. Ambos casos se tratan como el mismo estado visual (missing), sin distinguir en la leyenda entre "nunca reportado" y "reportado como NULL".

### Entry point / reproducibilidad
- **D-05:** Nuevo notebook `notebook/7_1_mapa_calor_cobertura.ipynb`, siguiendo la convención numérica ya establecida (`2_1_construccion_panel_eda.ipynb`, `3_1_modelo1_pib.ipynb`, `4_1_interpretabilidad_simulacion.ipynb`) — no un script standalone en `scripts/`. Debe ser re-ejecutable de principio a fin (Kernel → Restart & Run All) para cumplir con "figura reproducible" (Success Criteria #4 del roadmap).

### Claude's Discretion
- Nombre exacto del fichero PNG dentro de `figuras/` (p.ej. `figuras/07_mapa_calor_cobertura.png`), DPI/tamaño para impresión en la memoria, paleta de colores exacta para el estado binario missing/presente (puede reutilizar el estilo `cmap="Reds"` ya usado en la Fase 2 para el heatmap de missingness por región, o un esquema binario de 2 colores más apropiado para presencia/ausencia — a discreción), orientación de etiquetas de eje (rotación de años en el eje X), tamaño de figura exacto dado que cada sub-panel tiene ~40-45 países (215 países / 5-7 regiones SDG).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos y roadmap
- `.planning/REQUIREMENTS.md` — COVER-01, COVER-02 (única fuente de requisitos v1.1)
- `.planning/ROADMAP.md` §"Phase 7" — Success Criteria (4 condiciones verificables) y Depends on (Phase 1)

### Esquema de datos
- `src/db.py` — schema de `raw_observations` (UNIQUE(country_code, year, indicator_code), `value` nullable, sin columna `dimension` en el índice único)
- `src/ingesta/typology.py::build_region_map` — fuente del agrupamiento por región SDG
- `src/panel_build.py::REFERENCE_COLUMNS` — cómo se unen actualmente region/subregion/is_ldc/is_lldc/is_sids a la tabla `panel` (patrón de referencia, no reutilizar `panel_clean` como fuente de cobertura)

### Precedente de estilo visual
- `notebook/2_1_construccion_panel_eda.ipynb` celda 9 — heatmap de missingness existente (seaborn, `cmap="Reds"`, `annot=True`), calculado sobre `panel_clean` agregado por región — precedente de estilo pero NO de fuente de datos (Fase 7 usa `raw_observations`, no `panel_clean`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/db.py::get_engine` — conexión a `data/panel.db`, reutilizable directamente para leer `raw_observations`
- `src/ingesta/typology.py::build_region_map` — mapa m49_code → {region, subregion}, reutilizable para el agrupamiento del eje Y sin pasar por `panel_clean`
- matplotlib/seaborn ya en `requirements.txt`/`requirements.lock.txt` — sin nuevas dependencias necesarias

### Established Patterns
- Notebooks de fase (`N_M_nombre.ipynb`) como orquestador único que carga desde `data/panel.db`, transforma con pandas, y genera figuras con matplotlib/seaborn — mismo patrón que Fases 2-4
- Los 5 indicadores ODS confirmados por código: `6.4.2` (estrés hídrico), `6.4.1` (eficiencia uso de agua), `8.1.1` (PIB per cápita), `8.2.1` (productividad laboral), `2.3.1` (productividad agrícola)
- `figuras/` es el directorio de salida establecido para figuras estáticas de la memoria (ya contiene `figuras/plan_b/` con capturas del dashboard)

### Integration Points
- Ninguno con `src/dashboard/` — explícitamente fuera de alcance (Out of Scope en REQUIREMENTS.md)
- Ninguna modificación a `src/db.py`, `src/panel_build.py`, ni a ningún módulo de Fases 1-6 — Fase 7 es puramente lectura + visualización

</code_context>

<specifics>
## Specific Ideas

No hay referencias visuales externas específicas — el precedente de estilo es el heatmap existente de la Fase 2 (notebook 2_1, celda 9), pero adaptado a un grid de 5 sub-paneles con datos crudos en vez de un panel único agregado sobre datos filtrados.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 7-Mapa de Calor de Cobertura*
*Context gathered: 2026-07-15*
