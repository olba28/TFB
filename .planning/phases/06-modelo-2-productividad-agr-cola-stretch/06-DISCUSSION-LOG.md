# Phase 6: Modelo 2 — Productividad Agrícola (stretch) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-14
**Phase:** 6-Modelo 2 — Productividad Agrícola (stretch)
**Areas discussed:** Umbral de cobertura del Modelo 2, Alcance de la extensión (simulación/SHAP/dashboard), Paridad de robustez/heterogeneidad con el Modelo 1

---

## Umbral de cobertura del Modelo 2

| Option | Description | Selected |
|--------|-------------|----------|
| Mínimo 3 años observados (Recomendado) | Alineado con las oleadas reales del indicador (2010/2013/2016/2020) — deja 39 países | ✓ |
| Mínimo 2 años observados | Maximiza N a 44 países, a costa de más ruido | |
| Sin umbral mínimo (≥1 observación) | Incluye los 49 países; PanelOLS absorbe los singletons | |

**User's choice:** Mínimo 3 años observados (Recomendado)
**Notes:** Verificado en vivo contra `data/panel.db`: el umbral del 70% del Modelo 1 deja el panel de 2.3.1 en 0 países (cobertura máxima real: 26%, TZA/UGA/PRY). El indicador se reporta cada ~3 años (oleadas 2010/2013/2016/2020).

| Option | Description | Selected |
|--------|-------------|----------|
| Nuevo helper paramétrico en panel_base.py (Recomendado) | filter_by_min_years(...) calculado sobre panel_clean, no sobre panel_exclusions | ✓ |
| Extender la tabla panel_exclusions con un umbral distinto | Mezcla dos criterios de cobertura en la misma tabla | |
| Lógica ad hoc en el notebook/script del Modelo 2 | No reutilizable, rompe el patrón paramétrico | |

**User's choice:** Nuevo helper paramétrico en panel_base.py (Recomendado)

| Option | Description | Selected |
|--------|-------------|----------|
| Tabla dedicada, mismo estilo que panel_exclusions de la Fase 2 (Recomendado) | country_code, years_available, included/excluded, reason | ✓ |
| Solo párrafo descriptivo | Sin tabla estructurada | |

**User's choice:** Tabla dedicada, mismo estilo que panel_exclusions de la Fase 2 (Recomendado)

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, ejecutar igual y documentar si degeneran (Recomendado) | Consistente con la convención "warn, don't hide" ya en panel_base.py | ✓ |
| Omitir y documentar solo cualitativamente | Se desvía del Success Criterion del roadmap | |

**User's choice:** Sí, ejecutar igual y documentar si degeneran (Recomendado)
**Notes:** Panel disperso: ~3.5 observaciones/país en promedio.

---

## Alcance de la extensión (simulación/SHAP/dashboard)

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, mismo n_replicas=1000 (Recomendado) | Parámetro ya expuesto en bootstrap_counterfactual, sin tocar la función | ✓ |
| Reducir n_replicas para el Modelo 2 | No aporta nada estadísticamente con tan pocas entidades | |

**User's choice:** Sí, mismo n_replicas=1000 (Recomendado)
**Notes:** El bootstrap remuestreará ~39 entidades (vs. 171 del Modelo 1) — el IC resultante será más ancho, documentado como limitación.

| Option | Description | Selected |
|--------|-------------|----------|
| Mismos 3 predictores + tipología que el Modelo 1 (Recomendado) | 6.4.2, 6.4.1, 8.2.1 + is_ldc/is_lldc/is_sids/region | ✓ |
| Solo estrés hídrico (6.4.2) + tipología | SHAP no podría mostrar el peso relativo frente a otras variables | |

**User's choice:** Mismos 3 predictores + tipología que el Modelo 1 (Recomendado)
**Notes:** Verificado en vivo: pérdida de filas por missingness mínima (171/173 filas completas).

| Option | Description | Selected |
|--------|-------------|----------|
| Selector en la barra lateral (st.sidebar.selectbox) (Recomendado) | Cambia ACTIVE_MODEL globalmente; las 4 pestañas ya leen de ahí (D-07 Fase 5) | ✓ |
| Pestañas nuevas y separadas para el Modelo 2 | Duplicar las 4 pestañas | |

**User's choice:** Selector en la barra lateral (st.sidebar.selectbox) (Recomendado)

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, caption/aviso fijo en cada pestaña cuando Modelo 2 está activo (Recomendado) | Mismo patrón que ARTIFACT_ERROR_MSG de la Fase 5 | ✓ |
| No, solo queda documentado en la memoria | El dashboard no distingue visualmente | |

**User's choice:** Sí, caption/aviso fijo en cada pestaña cuando Modelo 2 está activo (Recomendado)

---

## Paridad de robustez/heterogeneidad con el Modelo 1

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, incluir ambas piezas (Recomendado) | Mismo rigor econométrico completo que el Modelo 1, refuerza la narrativa de extensión directa | ✓ |
| Solo especificación base + diagnósticos | Omitir robustez/heterogeneidad por tamaño muestral | |

**User's choice:** Sí, incluir ambas piezas (Recomendado)
**Notes:** El roadmap solo exige explícitamente efectos fijos + SEs clustered + mismos diagnósticos — robustez/heterogeneidad no son requisito literal, pero el usuario prefiere mantener paridad completa.

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, mismo criterio sin-COVID 2000-2019 (Recomendado) | Pérdida moderada (39→35 países) | ✓ |
| Comprobación distinta (p.ej. añadir controles 6.4.1+8.2.1) | Evita perder la oleada 2020 pero rompe la comparabilidad | |

**User's choice:** Sí, mismo criterio sin-COVID 2000-2019 (Recomendado)
**Notes:** Verificado en vivo: excluir 2020-2022 deja 35 de 39 países (2020 es la oleada individual más grande: 32/173 observaciones, pero no vacía el panel).

| Option | Description | Selected |
|--------|-------------|----------|
| Solo is_ldc (Recomendado) | Abandona la interacción por región (4 de 6 regiones con un solo país) | ✓ |
| Mantener ambas (región + is_ldc), igual que el Modelo 1 | Documentando que los coeficientes de región con un solo país no son interpretables | |

**User's choice:** Solo is_ldc (Recomendado)
**Notes:** Verificado en vivo: entre los 39 países del Modelo 2, región está muy desbalanceada (Europa=26, África subsahariana=9, 4 regiones con 1 país cada una). is_ldc balanceado (30 vs. 9).

---

## Claude's Discretion

- Nombre exacto del módulo/notebook del Modelo 2 (`src/model2_agri.py`, `notebook/6_1_modelo2_agricultura.ipynb`)
- Estructura interna exacta de `filter_by_min_years`
- Ubicación exacta de `model2_agri.pkl` y del RF auxiliar (ya anticipada como `data/modelos/model2_agri.pkl` en `src/dashboard/models.py`)
- Formato exacto del caption de aviso de cobertura reducida en el dashboard
- Redacción exacta de la sección de limitaciones del Modelo 2 en la memoria

## Deferred Ideas

None — la discusión se mantuvo dentro del alcance de la Fase 6.
