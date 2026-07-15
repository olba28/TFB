# Phase 7: Mapa de Calor de Cobertura - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-15
**Phase:** 7-Mapa de Calor de Cobertura
**Areas discussed:** Layout heatmap, Orden de países, Definición missing, Entry point, Otros detalles

---

## Layout heatmap

| Option | Description | Selected |
|--------|-------------|----------|
| 5 sub-heatmaps (uno por indicador) | Grid de 5 paneles país×año (uno por cada uno de los 5 indicadores ODS), cada celda coloreada por presencia/ausencia. Más fiel a COVER-01, pero cada panel tiene 215 filas. | ✓ |
| 1 heatmap país×año, color = nº indicadores presentes (0-5) | Un solo panel país×año con intensidad de color = cuántos de los 5 indicadores tienen dato. Más compacto pero no distingue qué indicador falta. | |
| 1 heatmap país×indicador, color = % años con dato | País×indicador (215×5), cada celda = % de 23 años con dato. Colapsa el eje temporal. | |

**User's choice:** 5 sub-heatmaps (uno por indicador)
**Notes:** Combinados en un único fichero PNG (per COVER-02), no 5 PNGs separados.

---

## Orden de países

| Option | Description | Selected |
|--------|-------------|----------|
| Agrupados por región SDG | Usa el campo `region` calculado en Fase 2, con separadores visuales. | ✓ |
| Ordenados por cobertura | De mayor a menor cobertura total, sin agrupación geográfica. | |
| Alfabético por ISO3 | Orden simple, sin agrupación temática. | |

**User's choice:** Agrupados por región SDG
**Notes:** Requiere join de `raw_observations` con el mapa de región (no con `panel_clean`, para no contaminar la fuente de cobertura con el filtro del 70%).

---

## Definición missing

| Option | Description | Selected |
|--------|-------------|----------|
| Ambos casos igual: sin dato = sin fila O value NULL | Trata fila-ausente y value=NULL como el mismo estado "sin dato". | ✓ |
| Solo fila ausente cuenta como missing; value NULL se trata aparte | Distingue "nunca reportado" de "reportado pero NULL" — tercera categoría de color. | |

**User's choice:** Ambos casos igual
**Notes:** Definición más simple y la esperada por un lector del tribunal para "cobertura de datos".

---

## Entry point

| Option | Description | Selected |
|--------|-------------|----------|
| Nuevo notebook | notebook/7_1_mapa_calor_cobertura.ipynb, siguiendo la convención numérica ya usada (2_1, 3_1, 4_1). | ✓ |
| Script en scripts/ | scripts/generar_heatmap_cobertura.py, siguiendo el precedente de scripts/verify_repro02.py. | |

**User's choice:** Nuevo notebook
**Notes:** Consistente con el resto del pipeline (notebooks de fase como orquestador único).

---

## Otros detalles

| Option | Description | Selected |
|--------|-------------|----------|
| No, estoy listo para continuar | Deja nombre de fichero, DPI, colores a discreción de Claude. | ✓ |
| Sí, quiero especificar algo más | Describir un detalle adicional antes de cerrar. | |

**User's choice:** No, estoy listo para continuar

---

## Claude's Discretion

- Nombre exacto del fichero PNG dentro de `figuras/`
- DPI/tamaño de figura para impresión en la memoria
- Paleta de colores exacta para el estado binario missing/presente
- Orientación de etiquetas de eje (rotación de años en eje X)

## Deferred Ideas

None — discussion stayed within phase scope.
