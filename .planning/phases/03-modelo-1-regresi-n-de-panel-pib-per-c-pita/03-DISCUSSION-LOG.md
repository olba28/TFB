# Phase 3: Modelo 1 — Regresión de Panel (PIB per cápita) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-12
**Phase:** 3-Modelo 1 — Regresión de Panel (PIB per cápita)
**Areas discussed:** Cobertura/exclusiones en el ajuste, Variables de control del modelo base, Comprobación de robustez (MODEL1-05), Reutilización de panel_base.py para Modelo 2

---

## Cobertura/exclusiones en el ajuste

| Option | Description | Selected |
|--------|-------------|----------|
| Filtrar con panel_exclusions | Honra PANEL-02 explícitamente en el modelo, no solo en la documentación | ✓ |
| Usar panel_clean completo, sin filtrar | Maximiza tamaño muestral; PanelOLS descarta NaN automáticamente | |
| Ambos: base filtrada + robustez sin filtrar | Base filtrada, robustez reajusta sin filtro como sensibilidad | |

**User's choice:** Filtrar con panel_exclusions (Recomendado)

**Follow-up question:** Si un país pasa el 70% en una variable del modelo pero no en otra, ¿cómo se resuelve?

| Option | Description | Selected |
|--------|-------------|----------|
| Excluir el país si CUALQUIER variable usada en el modelo falla | Panel balanceado respecto a las variables del modelo | ✓ |
| Excluir solo las filas año-país con valor faltante en esa variable | Deja que PanelOLS maneje el desbalance fila a fila | |

**User's choice:** Excluir el país si CUALQUIER variable usada en el modelo falla (Recomendado)
**Notes:** Ninguna aclaración adicional — el usuario confirmó "Siguiente tema" tras estas dos preguntas.

---

## Variables de control del modelo base

| Option | Description | Selected |
|--------|-------------|----------|
| Solo estrés hídrico + efectos fijos | entity_effects + time_effects absorben heterogeneidad no observada | ✓ |
| Añadir eficiencia hídrica (6.4.1) como control | Otra variable de agua identificada en la propuesta oficial | |
| Añadir eficiencia hídrica (6.4.1) Y productividad laboral (8.2.1) | Especificación más completa, converge con Wooldridge/Baltagi | |

**User's choice:** Solo estrés hídrico + efectos fijos (Recomendado)
**Notes:** Ninguna aclaración adicional.

---

## Comprobación de robustez (MODEL1-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Añadir controles (6.4.1 + 8.2.1) | Reajustar con controles ya que la base es parsimoniosa | |
| Excluir años COVID (2020-2022) | Submuestra 2000-2019, prueba que el resultado no depende de shocks atípicos | ✓ |
| Submuestra por tipología (excluir SIDS) | Prueba que el resultado no está impulsado por ese subgrupo | |

**User's choice:** Excluir años COVID (2020-2022)
**Notes:** El usuario NO eligió "añadir controles" como robustez, pese a que la base carece de ellos — se documentó explícitamente en CONTEXT.md para evitar que un agente downstream asuma esa opción como implícita.

---

## Reutilización de panel_base.py para Modelo 2

| Option | Description | Selected |
|--------|-------------|----------|
| Paramétrica desde ya: dep_var + indep_vars como argumentos | Modelo 2 la reutiliza sin tocar panel_base.py; cumple MODEL2-01 por construcción | ✓ |
| Específica a PIB ahora, refactorizar en Fase 6 | Menos trabajo de diseño ahora, riesgo de romper Modelo 1 al refactorizar después | |

**User's choice:** Paramétrica desde ya: variable dependiente + independiente como argumentos (Recomendado)
**Notes:** Ninguna aclaración adicional.

---

## Claude's Discretion

- Criterio/umbral exacto del test de Pesaran para decidir clustered SEs vs. Driscoll-Kraay (MODEL1-04)
- Estructura interna de panel_base.py más allá de la firma pública fit_panel_model(...)
- Ubicación exacta de model1_gdp.pkl (p. ej. data/modelos/)
- Formato de la sección de comparación pooled/RE/Hausman en el output

## Deferred Ideas

None — la discusión se mantuvo dentro del alcance de la Fase 3.
