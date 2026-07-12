# Phase 4: Interpretabilidad, Simulación y Robustez - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-12
**Phase:** 4-Interpretabilidad, Simulación y Robustez
**Areas discussed:** Bootstrap contrafactual, Modelo auxiliar SHAP, Heterogeneidad, Reutilización Fase 6

---

## Bootstrap contrafactual

| Option | Description | Selected |
|--------|-------------|----------|
| Bootstrap por país (block) | Remuestrea entidades completas con reemplazo, reajustando fit_panel_model en cada réplica | ✓ |
| Bootstrap paramétrico (SEs) | Muestrea coeficientes de una normal multivariante usando la Cov Driscoll-Kraay ya estimada | |
| Tú decides | Método a discreción de Claude | |

**User's choice:** Bootstrap por país (block)

| Option | Description | Selected |
|--------|-------------|----------|
| 1000 réplicas | Estándar académico para CI estables | ✓ |
| 200 réplicas | Más rápido de iterar pero colas menos estables | |
| Tú decides | Número a discreción de Claude | |

**User's choice:** 1000 réplicas

| Option | Description | Selected |
|--------|-------------|----------|
| Último año observado (2022) | Valor más reciente de cada país como base de la reducción | ✓ |
| Media del país 2000-2022 | Promedio histórico como base | |
| Tú decides | Valor base a discreción de Claude | |

**User's choice:** Último año observado (2022)

| Option | Description | Selected |
|--------|-------------|----------|
| Excluir ese país del escenario | El país se omite solo en los escenarios donde extrapola | ✓ |
| Cap al mínimo observado | Trunca el valor simulado al mínimo empírico global | |
| Tú decides | Criterio a discreción de Claude | |

**User's choice:** Excluir ese país del escenario
**Notes:** El usuario priorizó explícitamente la honestidad estadística (excluir) sobre mantener el N constante entre escenarios (cap).

---

## Modelo auxiliar SHAP

| Option | Description | Selected |
|--------|-------------|----------|
| Multivariante (5 indicadores) | Incluye varios indicadores como predictores del RF | ✓ |
| Solo estrés hídrico | Igual que la especificación base del Modelo 1 | |
| Tú decides | Conjunto a discreción de Claude | |

**User's choice:** Multivariante (5 indicadores)
**Notes:** Refinado en la siguiente pregunta — el conjunto final excluye 2.3.1 (ver abajo), quedando en 6.4.2, 6.4.1, 8.2.1 + tipología.

| Option | Description | Selected |
|--------|-------------|----------|
| Excluir 2.3.1 | Es la variable objetivo del Modelo 2 (Fase 6) y tiene cobertura reducida (50 países) | ✓ |
| Incluir 2.3.1 | La incluye como predictor pero fuerza al RF a reducirse a ~50 países | |
| Tú decides | Decisión a discreción de Claude | |

**User's choice:** Excluir 2.3.1

| Option | Description | Selected |
|--------|-------------|----------|
| Mismo RF para ambos | Un único RandomForest sirve para SHAP y para el modelo de referencia predictivo | ✓ |
| RF para SHAP + GBM separado | Dos modelos ML distintos, uno por requisito | |
| Tú decides | Decisión a discreción de Claude | |

**User's choice:** Mismo RF para ambos

---

## Heterogeneidad

| Option | Description | Selected |
|--------|-------------|----------|
| Términos de interacción | estrés_hídrico × grupo dentro del mismo PanelOLS | ✓ |
| Submodelos por subgrupo | Reajusta fit_panel_model por separado para cada subgrupo | |
| Tú decides | Enfoque a discreción de Claude | |

**User's choice:** Términos de interacción

| Option | Description | Selected |
|--------|-------------|----------|
| Región + tipología ONU | Dos interacciones: estrés_hídrico × region y estrés_hídrico × is_ldc | ✓ |
| Solo región | Una única interacción con región | |
| Tú decides | Variable(s) a discreción de Claude | |

**User's choice:** Región + tipología ONU

| Option | Description | Selected |
|--------|-------------|----------|
| Coeficientes de interacción por grupo | Se reporta únicamente la tabla de coeficientes, nunca un valor predicho por país | ✓ |
| Tú decides | Formato a discreción de Claude | |

**User's choice:** Coeficientes de interacción por grupo

---

## Reutilización Fase 6

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, paramétricos desde ahora | simulate.py/interpret.py genéricos en dep_var, invocables por Fase 6 sin modificar | ✓ |
| Notebook-only por ahora | Todo el código vive en el notebook, se extrae solo si Fase 6 se implementa | |
| Tú decides | Decisión a discreción de Claude | |

**User's choice:** Sí, paramétricos desde ahora

| Option | Description | Selected |
|--------|-------------|----------|
| Uno solo (4_1) | Un único notebook 4_1_interpretabilidad_simulacion.ipynb | ✓ |
| Dos notebooks separados | 4_1 (simulación/heterogeneidad) + 4_2 (SHAP/ALE) | |
| Tú decides | Organización a discreción de Claude | |

**User's choice:** Uno solo (4_1)

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, a data/modelos/ | El RF auxiliar se serializa igual que model1_gdp.pkl | ✓ |
| No, solo en notebook | El RF vive solo dentro de la ejecución del notebook | |
| Tú decides | Decisión a discreción de Claude | |

**User's choice:** Sí, a data/modelos/

---

## Claude's Discretion

- Formato exacto del gráfico multi-escenario de sensibilidad (INTERP-02)
- Estructura interna exacta de `simulate.py`/`interpret.py` más allá de las firmas públicas
- Umbral/criterio de significancia de los coeficientes de interacción de heterogeneidad
- Qué variables reciben gráficos ALE/partial-dependence (INTERP-05)
- Mecanismo exacto de fijación de semillas (REPRO-02)
- Hiperparámetros del RandomForest

## Deferred Ideas

None — la discusión se mantuvo dentro del alcance de la Fase 4.
