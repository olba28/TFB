# Phase 4: Interpretabilidad, Simulación y Robustez - Research

**Researched:** 2026-07-12
**Domain:** Panel-data bootstrap inference (linearmodels/PanelOLS), interaction-term heterogeneity analysis, and post-hoc ML interpretability (scikit-learn RandomForest + SHAP + ALE/PDP)
**Confidence:** HIGH — the two riskiest technical questions (entity-resampling correctness and RF/SHAP reproducibility) were verified by running live code against this project's actual `data/panel.db` and pinned `.venv`, not just documentation lookup.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Bootstrap de la simulación contrafactual (INTERP-01)**
- D-01: El bootstrap remuestrea **entidades completas (países) con reemplazo** ("block bootstrap" por país) y reajusta `fit_panel_model` en cada réplica — no bootstrap paramétrico sobre la matriz de covarianzas Driscoll-Kraay. Respeta la dependencia temporal dentro de cada país y la dependencia transversal que el test de Pesaran CD detectó en la Fase 3 (p=0.0014), que un bootstrap i.i.d. por fila violaría.
- D-02: Objetivo de **1000 réplicas** por escenario.
- D-03: La reducción de estrés hídrico de cada escenario (-10/-20/-30%) se aplica sobre el **valor de estrés hídrico del último año observado por país (2022)**, no sobre la media histórica.
- D-04: Verificación de no-extrapolación (INTERP-01): si el valor simulado de un país para un escenario cae por debajo del mínimo de estrés hídrico observado globalmente en el panel 2000–2022, **ese país se excluye únicamente de ese escenario** — no se trunca ("cap") el valor. El número/lista de países excluidos por escenario debe documentarse explícitamente.

**Modelo auxiliar ML para SHAP e INTERP-06**
- D-05: El RandomForest auxiliar (INTERP-04) es **multivariante**: predictores `6.4.2` (estrés hídrico), `6.4.1` (eficiencia agua), `8.2.1` (productividad laboral), más tipología de país (`is_ldc`/`is_lldc`/`is_sids`, `region`).
- D-06: `2.3.1` (productividad agrícola) se **excluye** de los predictores del RF de esta fase.
- D-07: El **mismo RandomForest** entrenado para SHAP (INTERP-04) se reutiliza como modelo de referencia predictivo de INTERP-06 — no se entrena un Gradient Boosting separado.
- D-08: El RandomForest auxiliar se **serializa** (p. ej. `data/modelos/rf_shap_model.pkl`).

**Heterogeneidad regional/por tipología (INTERP-03)**
- D-09: Se implementa con **términos de interacción** dentro del mismo `PanelOLS` de efectos fijos (`estrés_hídrico × grupo` como regresor adicional) — no submodelos separados por subgrupo.
- D-10: Las variables de agrupación son **`region` y la tipología ONU (`is_ldc`)** (dos interacciones separadas).
- D-11: Los resultados se presentan **únicamente como tabla de coeficientes de interacción por grupo** — nunca un valor predicho para un país individual.

**Reutilización de código para Fase 6 (Modelo 2)**
- D-12: Se diseñan módulos paramétricos en `src/` (`simulate.py`, `interpret.py`) desde esta fase, siguiendo el mismo patrón que `panel_base.py` (D-05, 03-CONTEXT.md): genéricos en variable dependiente/independientes (p. ej. `bootstrap_counterfactual(fitted_results, df, dep_var, indep_var, ...)`, `shap_analysis(df, dep_var, feature_vars, ...)`), invocables por la Fase 6 con `dep_var="2.3.1"` sin modificar el módulo.
- D-13: Un único notebook `4_1_interpretabilidad_simulacion.ipynb` cubre simulación contrafactual, heterogeneidad, SHAP y ALE en orden.

### Claude's Discretion
- Formato exacto del gráfico multi-escenario de sensibilidad (INTERP-02) — libre mientras visualice los ≥3 escenarios con sus intervalos de confianza.
- Estructura interna exacta de `simulate.py`/`interpret.py` (nombres de funciones auxiliares) más allá de las firmas públicas genéricas fijadas en D-12.
- Umbral/criterio de significancia de los coeficientes de interacción de heterogeneidad (D-09/D-10) — libre mientras se reporte SE e IC.
- Qué variables concretas de las Fase-2-VIF-correlacionadas reciben gráficos ALE/partial-dependence (INTERP-05) — libre mientras se complementen los predictores del RF con correlación relevante identificada en la Fase 2.
- Mecanismo exacto de fijación de semillas (REPRO-02) — una semilla global vs. semillas por paso — libre mientras sea determinista y documentado.
- Hiperparámetros del RandomForest (n_estimators, max_depth, etc.) — libre mientras sea reproducible con semilla fija.

### Deferred Ideas (OUT OF SCOPE)
None — la discusión se mantuvo dentro del alcance de la Fase 4.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| INTERP-01 | Simulación contrafactual con IC por bootstrap, enmarcada como análisis de sensibilidad, con verificación de no-extrapolación | §Architecture Patterns Pattern 1 (block bootstrap by entity, live-verified entity-relabeling fix), §Common Pitfalls #1, §Code Examples "Bootstrap by entity" |
| INTERP-02 | Gráfico multi-escenario de sensibilidad | §Architecture Patterns Pattern 1, §Code Examples "Multi-scenario plot" |
| INTERP-03 | Heterogeneidad regional/por tipología vía interacciones, sin predicción por país | §Architecture Patterns Pattern 2 (interaction terms, live-verified formula syntax), §Code Examples "Interaction terms" |
| INTERP-04 | SHAP vía RandomForest + TreeExplainer, precedido de VIF/correlación, con aviso de sesgo por correlación | §Architecture Patterns Pattern 3, §Common Pitfalls #3/#5, §Code Examples "RF + TreeExplainer", real Phase-2 VIF numbers reproduced below |
| INTERP-05 | Gráficos ALE/partial-dependence complementarios | §Standard Stack (PyALE vs sklearn PDP), §Package Legitimacy Audit |
| INTERP-06 | Modelo de referencia predictivo (RF/GBM) complementario, no sustituye interpretación causal | §Architecture Patterns Pattern 3 (same RF instance, `oob_score=True` recommendation), §Open Questions Q1 |
| REPRO-02 | Semillas fijas en todos los pasos estocásticos (bootstrap, RF, splits) | §Common Pitfalls #2 (live-verified `n_jobs` non-determinism bug), §Code Examples "Seeding pattern" |
</phase_requirements>

## Summary

Phase 4 has three technically independent sub-problems that must all compose inside one notebook: (1) a **block bootstrap by country** that refits the existing `panel_base.fit_panel_model` 1000×3 times, (2) **interaction terms** inside the same `PanelOLS` two-way fixed-effects specification, and (3) a **RandomForest + SHAP + ALE/PDP** interpretability stack that is deliberately decoupled from the econometric model (per Phase 3's open blocker, now resolved: SHAP wraps a standalone `RandomForestRegressor`, never `PanelOLS.predict`).

Two live-verified findings materially change how this phase must be planned, and both are more important than anything found via web search:

1. **The naive implementation of D-01's block bootstrap is silently wrong.** Concatenating a resampled country's rows under its *original* `country_code` causes duplicate `(entity, year)` MultiIndex keys. `PanelOLS` does not raise an error — it silently collapses duplicate-drawn countries into a single fixed-effect bucket (verified live: 171 draws with 43 repeats produced only **109** recognized entities, not 171). The correct, mandatory pattern is to relabel every drawn country to a **unique synthetic entity id** (e.g. `f"{country}__b{i}"`) before calling `fit_panel_model`. This is not optional — it is the difference between a statistically valid cluster bootstrap and a silently-corrupted one, and it is exactly the kind of subtle bug a tribunal-facing thesis cannot afford.

2. **`RandomForestRegressor(random_state=42, n_jobs=-1)` is NOT reproducible across runs**, even with a fixed `random_state` — this was verified live with the project's pinned `scikit-learn==1.9.0`: `n_jobs=1` gave bit-identical predictions across two runs, `n_jobs=-1` did not. REPRO-02 therefore requires `n_jobs=1` for the RF training step (a known upstream scikit-learn issue, not a version-specific quirk). This directly conflicts with the intuitive urge to parallelize for speed and must be called out explicitly in the plan.

Performance is a real but manageable constraint: a single `fit_panel_model` refit on the real 171-country/3933-row filtered panel takes ~360ms regardless of `cov_type` (clustered vs. unadjusted), so 1000 replicas × 3 scenarios = 3000 refits is ≈18 minutes serial. This is tractable for a one-time notebook run but should be parallelized across replicas with `joblib.Parallel` + `numpy.random.SeedSequence.spawn()` (independent, order-independent, reproducible per-replica seeds) if faster iteration is desired during development. `shap.TreeExplainer` on the RF (300 trees, 3473 complete-case rows, 13 one-hot-encoded features) took ~355s with the default `check_additivity=True` — acceptable for a one-time notebook cell but worth knowing before planning a "run it 5 times while debugging" workflow.

The Phase-2 VIF/correlation matrix (read directly from the committed `notebook/2_1_construccion_panel_eda.ipynb`) shows the RF's three numeric predictors (`6.4.2`, `6.4.1`, `8.2.1`) are only weakly correlated globally (max |r| = 0.09 among them; global VIF all < 2.2) — the strongest correlation in the whole matrix (r=0.70) is between `8.2.1` and the *dependent* variable `8.1.1`, not between predictors. This is an honest, useful finding for INTERP-04's "aviso de sesgo por correlación": the notebook should report the real (modest) VIF numbers rather than assume high multicollinearity, while still noting SHAP's correlation-bias caveat applies in principle and that regional-subgroup VIF (also computed in Phase 2) is much higher in some regions, which the pooled global RF does not capture.

**Primary recommendation:** Reuse `panel_base.fit_panel_model` unmodified inside the bootstrap loop (per D-12), but wrap country resampling in a dedicated `resample_entities()` helper that performs the synthetic-relabel fix before calling it. Compute the counterfactual effect as `coef_replica × Δwater_stress_country` (a marginal-effect simulation), never as an absolute-level `.predict()` call — `linearmodels` does not support out-of-sample prediction with entity effects, which matches this project's "sensitivity analysis, not causal prediction" framing (03-VERIFICATION cell 14). Use `PanelOLS.from_formula(... : C(group) + EntityEffects + TimeEffects)` (colon, not `*`) for interactions — the standalone categorical main effect is absorbed by entity effects and must be omitted, live-verified. Train one `RandomForestRegressor(random_state=SEED, n_jobs=1, oob_score=True)` shared by SHAP and INTERP-06 (`oob_score` gives the "predictive comparison" metric for free, without a separate train/test split and its own seeding surface).

## Architectural Responsibility Map

*(This project is a single-process Python data-science pipeline, not a multi-tier web app — tiers below are the project's own established layers per `CLAUDE.md`/PROJECT.md, not the browser/API/CDN tiers of a web application.)*

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Block bootstrap resampling + refit | Modeling Layer (`src/simulate.py`) | Storage Layer (`data/panel.db` read-only) | Pure statistical computation over the already-cleaned panel; no I/O beyond loading `panel_clean`/`panel_exclusions` once |
| Non-extrapolation check (D-04) | Modeling Layer (`src/simulate.py`) | — | Pure function of simulated values vs. historical min; no external dependency |
| Interaction-term heterogeneity model | Modeling Layer (`src/panel_base.py`, reused via `fit_panel_model`) | — | Same `PanelOLS` machinery as Model 1, only `indep_vars` changes |
| RandomForest training + SHAP | Interpretation Layer (`src/interpret.py`) | Storage Layer (`data/modelos/rf_shap_model.pkl`) | Deliberately decoupled from the econometric model (Phase 3 blocker resolution); serialized for Phase 5 dashboard reuse |
| ALE / partial-dependence plots | Interpretation Layer (`src/interpret.py`) | — | Consumes the same trained RF, no new model |
| Orchestration / narrative | Notebook Layer (`notebook/4_1_interpretabilidad_simulacion.ipynb`) | — | D-13: single notebook calling into `src/simulate.py` + `src/interpret.py`, mirroring `3_1_modelo1_pib.ipynb`'s pattern of calling `panel_base.py` |
| Serialized artifacts for Phase 5 | Storage Layer (`data/modelos/*.pkl`) | — | DASH-01 requires the dashboard to consume pre-computed artifacts, no live recomputation |

## Standard Stack

### Core

| Library | Version (pinned, `requirements.lock.txt`) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `linearmodels` | 7.0 `[VERIFIED: requirements.lock.txt]` | `PanelOLS` refits inside the bootstrap loop, interaction-term formula API | Already the project's panel-regression library since Phase 3; no alternative needed |
| `scikit-learn` | 1.9.0 `[VERIFIED: requirements.lock.txt]` | `RandomForestRegressor` auxiliary model (D-05/D-07), `sklearn.inspection.partial_dependence`/`PartialDependenceDisplay` fallback for INTERP-05 | Already pinned; native NaN support in `RandomForestRegressor` since ~1.4 `[CITED: scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html]` is available but not required if complete-case rows are used (see Pitfall #5) |
| `shap` | 0.52.0 `[VERIFIED: requirements.lock.txt]` | `shap.TreeExplainer` for INTERP-04 | Already pinned; live-verified working against `RandomForestRegressor` with this exact version |
| `numpy` | 2.4.6 `[VERIFIED: requirements.lock.txt]` | `SeedSequence`/`default_rng` for all stochastic steps (REPRO-02) | Already pinned |
| `pandas` | 3.0.3 `[VERIFIED: requirements.lock.txt]` | DataFrame manipulation throughout | Already pinned |
| `matplotlib` / `seaborn` | 3.11.0 / 0.13.2 `[VERIFIED: requirements.lock.txt]` | Multi-scenario sensitivity plot (INTERP-02), VIF/correlation heatmap, SHAP summary/dependence plots | Already pinned; `shap` ships its own matplotlib-based plotting (`shap.summary_plot`, `shap.plots.*`) that needs no extra dependency |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `joblib` | 1.5.3 `[VERIFIED: requirements.lock.txt, transitive via scikit-learn]` | `joblib.Parallel` to parallelize the 3000-replica bootstrap loop across CPU cores | If the ~18-minute serial runtime is a friction point during iterative notebook development; NOT for `RandomForestRegressor`'s own `n_jobs` (must stay 1 — see Pitfall #2) |
| `PyALE` | 1.2.0 (candidate, NOT currently pinned) `[ASSUMED — see Package Legitimacy Audit]` | True Accumulated Local Effects plots for INTERP-05 | Only if the planner/user wants ALE specifically (statistically the correct complement to SHAP under correlated features) rather than sklearn's PDP |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `PyALE` for INTERP-05 | `sklearn.inspection.PartialDependenceDisplay` / `partial_dependence` | Zero new dependency (already-pinned `scikit-learn`), simpler to defend as "no unjustified dependency change" per `CLAUDE.md`. **Tradeoff:** PDP is documented to be biased/untrustworthy exactly under the correlated-feature scenario INTERP-05 exists to address `[CITED: christophm.github.io/interpretable-ml-book/ale.html]`, whereas the RF's actual predictors are only weakly correlated (see Summary), which somewhat blunts this concern for this specific dataset. |
| Refitting `PanelOLS` per bootstrap replica (D-01, locked) | Parametric bootstrap over the Driscoll-Kraay covariance matrix | Explicitly rejected by the user (D-01) — respects Pesaran-CD-detected cross-sectional dependence that an i.i.d./parametric approach would violate. Not re-researched — locked decision. |
| Separate GBM for INTERP-06 | Reuse the same RF (D-07, locked) | Explicitly rejected by the user — avoids duplicating training/validation/documentation for a requirement that doesn't demand two models. Not re-researched — locked decision. |

**Installation (only if PyALE is approved via the checkpoint below):**
```bash
pip install PyALE==1.2.0
pip freeze > requirements.lock.txt
```

**Version verification:** All core-stack versions above were read directly from this project's own `requirements.lock.txt` (already installed in `.venv`, already used in Phases 1–3) — not re-fetched from the registry, since they are pre-existing pinned dependencies, not new installs for this phase.

## Package Legitimacy Audit

> Required because this phase's INTERP-05 discretion point (ALE library choice) may introduce one new dependency (`PyALE`). All other libraries used in this phase (`linearmodels`, `scikit-learn`, `shap`, `numpy`, `pandas`, `matplotlib`, `seaborn`, `joblib`) are pre-existing, already-pinned dependencies from Phases 1–3 (confirmed present and working via live execution against this project's own `.venv` and `data/panel.db` during this research session) and are excluded from this table on that basis — they are not new installs.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `PyALE` | PyPI | First release 2019, latest 1.2.0 released 2024-03-27 `[VERIFIED: pip index versions PyALE — 7 versions listed, 1.0.0 through 1.2.0]` | Not confirmed via authoritative download-count source this session | `github.com/DanaJomar/PyALE` `[CITED: WebSearch result, also mirrored as a `conda-forge/pyale-feedstock` package]` | `gsd-tools package-legitimacy` returned **SUS** (reasons: `unknown-age`, `unknown-downloads`, `no-repository` — the tool's own registry signal was incomplete, not a red flag about the package itself) | **Flagged — planner must add a `checkpoint:human-verify` task before `pip install PyALE`**, per the Package Legitimacy Gate protocol (a SUS verdict requires this regardless of independent manual verification) |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `PyALE` — tool's registry-lookup signal was incomplete (no downloads/age data returned), but independent verification this session (`pip index versions`, GitHub repo search, conda-forge feedstock) found no red flags: single, long-tenured, single-maintainer package with a real (if slow) release cadence, last released 2024-03-27, no anomalous behavior. Planner must still gate the install behind `checkpoint:human-verify` per protocol — this is a process requirement, not a statement that the package is actually dangerous.

*If the human-verify checkpoint is not approved, or the planner prefers zero new dependencies, use `sklearn.inspection.PartialDependenceDisplay` instead (see Alternatives Considered) — no legitimacy audit needed, already pinned.*

## Architecture Patterns

### System Architecture Diagram

```
data/panel.db (panel_clean, panel_exclusions)
        │
        ▼
┌─────────────────────────┐        ┌──────────────────────────┐
│ src/panel_base.py        │        │ data/modelos/             │
│ (Phase 3, UNMODIFIED)    │◄───────┤ model1_gdp.pkl (loaded,   │
│ fit_panel_model()        │  reads │ NOT refit except inside   │
│ filter_by_exclusions()   │        │ bootstrap replicas)       │
└─────────────┬────────────┘        └──────────────────────────┘
              │ called once per bootstrap replica (1000×3)
              ▼
┌─────────────────────────────────────────────────────────────┐
│ src/simulate.py (NEW, D-12 parametric design)                 │
│                                                                 │
│  resample_entities(df, entity_col, rng) ──► relabeled df       │
│         │ (fixes silent entity-collision bug — see Pitfall #1) │
│         ▼                                                      │
│  bootstrap_counterfactual(fitted_results, df, dep_var,          │
│     indep_var, reduction_pcts=[-.10,-.20,-.30], n_replicas=1000,│
│     seed=SEED) ──► per-scenario coef distributions              │
│         │                                                        │
│         ▼                                                        │
│  check_non_extrapolation(...) ──► per-scenario excluded-country  │
│         list + filtered effect distribution                      │
│         │                                                        │
│         ▼                                                        │
│  percentile CI (2.5/97.5) per scenario ──► multi-scenario plot   │
│  (INTERP-01, INTERP-02)                                          │
└─────────────────────────────────────────────────────────────────┘
              │
              │ (separately) PanelOLS.from_formula(water_stress:C(group)
              │  + EntityEffects + TimeEffects) via panel_base machinery
              ▼
     interaction coefficient table (INTERP-03) — region, is_ldc

┌─────────────────────────────────────────────────────────────┐
│ src/interpret.py (NEW, D-12 parametric design)                │
│                                                                 │
│  panel_clean (complete-case on 6.4.2,6.4.1,8.2.1 + typology)   │
│         │                                                       │
│         ▼                                                       │
│  shap_analysis(df, dep_var, feature_vars, seed=SEED) ──►         │
│     RandomForestRegressor(random_state=SEED, n_jobs=1,           │
│        oob_score=True)  ──► serialize rf_shap_model.pkl (D-08)   │
│         │                                                        │
│         ├──► shap.TreeExplainer(rf).shap_values(X) (INTERP-04)   │
│         │      preceded by VIF/correlation table (Phase 2 reuse) │
│         │                                                        │
│         └──► ale_plots(rf, X, correlated_features) (INTERP-05)   │
│                                                                    │
│  rf.oob_score_ ──► "predictive comparison" metric (INTERP-06)     │
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
notebook/4_1_interpretabilidad_simulacion.ipynb (D-13, orchestrates
   simulate.py + interpret.py in order: simulation → heterogeneity →
   SHAP → ALE)
              │
              ▼
data/modelos/rf_shap_model.pkl  ──► consumed later by Phase 5 dashboard
   (no live recomputation, DASH-01) and reusable unmodified by Phase 6
   (dep_var="2.3.1")
```

### Recommended Project Structure
```
src/
├── panel_base.py     # Phase 3, UNCHANGED — fit_panel_model, filter_by_exclusions
├── simulate.py        # NEW — bootstrap_counterfactual, resample_entities,
│                       #   check_non_extrapolation
├── interpret.py        # NEW — shap_analysis, ale_plots (or partial_dependence_plots),
│                        #   compute_vif_table (small helper, mirrors Phase 2's
│                        #   notebook-local one — promote to src/ since interpret.py
│                        #   needs it programmatically, not just in a notebook cell)
notebook/
└── 4_1_interpretabilidad_simulacion.ipynb   # D-13, orchestrates the above
data/modelos/
├── model1_gdp.pkl      # Phase 3, read-only input to this phase
└── rf_shap_model.pkl   # NEW (D-08)
tests/
└── test_simulate.py, test_interpret.py  # unit tests mirroring test_panel_base.py's pattern
```

### Pattern 1: Block Bootstrap by Entity (INTERP-01/02)

**What:** Resample whole countries with replacement, relabel each draw to a unique synthetic entity id, refit `fit_panel_model`, extract the coefficient on the water-stress regressor, compute the scenario effect as `coef × Δwater_stress`, take percentile CIs across 1000 replicas.

**When to use:** Any panel bootstrap where the resampling unit (country) can legitimately be drawn more than once — always relabel before building the `(entity, time)` index.

**Example (live-verified against this project's `data/panel.db`):**
```python
# Source: live-verified in this research session against src/panel_base.py
import numpy as np
import pandas as pd

def resample_entities(df: pd.DataFrame, entity_col: str, rng: np.random.Generator) -> pd.DataFrame:
    """Draw countries with replacement and relabel each draw to a UNIQUE
    synthetic entity id -- without this, PanelOLS silently collapses
    duplicate-drawn countries into one fixed-effect bucket (verified live:
    171 draws with 43 repeats -> only 109 recognized entities without
    relabeling; 171 with relabeling, matching the draw count exactly).
    """
    entities = df[entity_col].unique()
    draws = rng.choice(entities, size=len(entities), replace=True)
    parts = []
    for i, entity in enumerate(draws):
        sub = df[df[entity_col] == entity].copy()
        sub[entity_col] = f"{entity}__b{i}"
        parts.append(sub)
    return pd.concat(parts, ignore_index=True)

def bootstrap_counterfactual(
    fitted_results,       # panel_base.fit_panel_model(...) result on the REAL data
    df: pd.DataFrame,
    dep_var: str,
    indep_var: str,
    reduction_pcts: list[float],
    baseline_year: int,
    n_replicas: int = 1000,
    seed: int = 42,
    entity_col: str = "country_code",
) -> dict:
    ss = np.random.SeedSequence(seed)
    child_seeds = ss.spawn(n_replicas)  # independent, reproducible, order-independent
    coefs = []
    for child in child_seeds:
        rng = np.random.default_rng(child)
        boot_df = resample_entities(df, entity_col, rng)
        # cov_type is irrelevant to the point estimate used per-replica --
        # percentile CI comes from replica-to-replica variance, not from any
        # single replica's own SE -- "unadjusted" is fastest.
        res = panel_base.fit_panel_model(
            boot_df, dep_var, [indep_var],
            entity_effects=True, time_effects=True, cov_type="unadjusted",
        )
        coefs.append(res.params[indep_var])
    coefs = np.array(coefs)

    baseline = (
        df[df["year"] == baseline_year]
        .set_index(entity_col)[indep_var]
    )
    historical_min = df[indep_var].min()

    results = {}
    for pct in reduction_pcts:
        delta = -pct * baseline           # e.g. pct=0.10 -> Delta = -10% of 2022 level
        simulated_level = baseline + delta
        survives = simulated_level >= historical_min       # D-04
        excluded = baseline.index[~survives].tolist()
        effect_draws = np.outer(coefs, delta[survives])    # (n_replicas, n_surviving_countries)
        results[pct] = {
            "effect_draws": effect_draws,
            "ci_2.5": np.percentile(effect_draws, 2.5, axis=0),
            "ci_97.5": np.percentile(effect_draws, 97.5, axis=0),
            "excluded_countries": excluded,
        }
    return results
```

### Pattern 2: Interaction Terms for Heterogeneity (INTERP-03)

**What:** Add `water_stress : C(group)` (colon, NOT `*`) to the `PanelOLS` formula. The standalone `C(group)` main effect must be OMITTED — it is a time-invariant, entity-level variable that gets fully absorbed by `entity_effects=True` and raises `AbsorbingEffectError` if included as a separate term. Only the interaction (which varies over time because `water_stress` does) is separately identified.

**When to use:** Whenever testing whether a regressor's slope differs by a time-invariant grouping variable inside a fixed-effects model.

**Example (live-verified — the `*` form fails with `AbsorbingEffectError`, the `:` form succeeds and returns exactly the per-group coefficient table D-11 requires):**
```python
# Source: live-verified against real panel_clean/panel_exclusions data, linearmodels 7.0
from linearmodels.panel import PanelOLS

indexed = filtered.set_index(["country_code", "year"])
for c in ["6.4.2", "8.1.1"]:
    indexed[c] = pd.to_numeric(indexed[c], errors="coerce")

# WRONG -- raises AbsorbingEffectError (C(region) main effect absorbed by EntityEffects):
# 'Q("8.1.1") ~ 1 + Q("6.4.2") * C(region) + EntityEffects + TimeEffects'

# CORRECT -- interaction only:
mod = PanelOLS.from_formula(
    'Q("8.1.1") ~ 1 + Q("6.4.2") : C(region) + EntityEffects + TimeEffects',
    data=indexed,
)
res = mod.fit(cov_type="clustered", cluster_entity=True)
# res.params -> one water-stress coefficient PER region (D-11's coefficient table)
# res.std_errors, res.conf_int() -> SE and CI per group, directly reportable

# Same pattern for the binary is_ldc typology flag:
mod2 = PanelOLS.from_formula(
    'Q("8.1.1") ~ 1 + Q("6.4.2") : C(is_ldc) + EntityEffects + TimeEffects',
    data=indexed,
)
res2 = mod2.fit(cov_type="clustered", cluster_entity=True)
```

### Pattern 3: Decoupled RF + SHAP + ALE (INTERP-04/05/06)

**What:** Train ONE `RandomForestRegressor` on complete-case rows for `[6.4.2, 6.4.1, 8.2.1, is_ldc, is_lldc, is_sids, region-one-hot]`, predicting `8.1.1`. Feed it to `shap.TreeExplainer` for INTERP-04, `PyALE`/`PartialDependenceDisplay` for INTERP-05, and read `oob_score_` for INTERP-06.

**When to use:** Whenever SHAP interpretability is needed for a model class (`PanelOLS`) that TreeExplainer cannot wrap directly — this project already resolved this exact open question (see STATE.md blocker) by training a standalone auxiliary sklearn model instead of trying to wrap `PanelOLS.predict`.

**Example (live-verified against real `panel_clean` data, shap 0.52.0 / scikit-learn 1.9.0):**
```python
# Source: live-verified in this research session
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import shap

predictors_num = ["6.4.2", "6.4.1", "8.2.1"]
cat = ["is_ldc", "is_lldc", "is_sids", "region"]
dep_var = "8.1.1"

sub = panel_clean[predictors_num + cat + [dep_var]].dropna()  # complete-case: N=3473 of 4923
X = pd.get_dummies(sub[predictors_num + cat], columns=["region"], drop_first=True)
y = sub[dep_var]

rf = RandomForestRegressor(
    n_estimators=300, random_state=SEED, n_jobs=1,  # n_jobs MUST be 1 -- see Pitfall #2
    oob_score=True,                                   # gives INTERP-06's predictive metric for free
)
rf.fit(X, y)
print("OOB R^2 (predictive reference metric, INTERP-06):", rf.oob_score_)

explainer = shap.TreeExplainer(rf)          # tree_path_dependent by default (no background needed)
shap_values = explainer.shap_values(X)      # shape (3473, 13) -- verified live, ~355s for 300 trees
```

### Anti-Patterns to Avoid
- **Resampling countries without relabeling entity ids:** silently collapses the bootstrap's effective entity count (live-verified: 171→109) — corrupts the two-way FE demeaning and understates any per-entity statistic. Always relabel.
- **Calling `.predict()` on a bootstrap-refit `PanelOLS` for an "absolute counterfactual GDP level":** `linearmodels` does not support out-of-sample prediction with entity/time effects `[CITED: bashtage.github.io/linearmodels/panel/panel/linearmodels.panel.results.PanelResults.predict.html]` — "idiosyncratic errors and effects are not available for out-of-sample predictions." Compute the scenario effect as `coefficient × Δregressor` (marginal effect), matching this project's "sensitivity analysis, not causal prediction" framing (03-VERIFICATION.md cell 14).
- **`RandomForestRegressor(..., n_jobs=-1)` for a reproducibility-critical fit:** breaks REPRO-02 even with `random_state` fixed (live-verified). Use `n_jobs=1` for the interpretability RF; parallelize the *bootstrap loop* instead (each replica is independent and can use `joblib.Parallel`, since determinism there comes from per-replica `SeedSequence` children, not from thread/process scheduling).
- **Including a standalone `C(region)`/`C(is_ldc)` main effect alongside `EntityEffects=True`:** raises `AbsorbingEffectError` (live-verified) — the variable is time-invariant per entity and fully collinear with the entity dummies.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile bootstrap CI | Custom sorting/indexing logic | `numpy.percentile(draws, [2.5, 97.5], axis=...)` | Battle-tested, vectorized, handles the 2D `(replicas × countries)` effect-draw array from Pattern 1 directly |
| Independent-but-reproducible parallel RNG streams | Manually offsetting a single global seed per replica (e.g. `seed + i`) — a documented anti-pattern that can produce correlated streams for some algorithms | `numpy.random.SeedSequence(seed).spawn(n)` | `[CITED: numpy.org/doc/stable/reference/random/parallel.html]` — designed specifically for this use case: reproducible AND statistically independent child streams |
| SHAP value computation | Custom Shapley-value approximation over tree paths | `shap.TreeExplainer` | Exact, fast, polynomial-time algorithm specific to tree ensembles (Lundberg et al.) — already pinned in this project |
| ALE computation | Custom binning + first-difference accumulation | `PyALE` (if approved) or accept PDP's documented correlated-feature bias and use `sklearn.inspection.partial_dependence` | ALE's binning/accumulation logic has known edge cases (empty bins, boundary effects) that a from-scratch implementation would need to re-derive and validate against the reference algorithm (Apley & Zhu 2020) |
| VIF computation | Custom matrix-inversion-based VIF | `statsmodels.stats.outliers_influence.variance_inflation_factor` (already used in Phase 2's `compute_vif_table` pattern) | Reuse the exact helper pattern already validated and committed in `notebook/2_1_construccion_panel_eda.ipynb` — don't reinvent it for Phase 4 |

**Key insight:** Every "don't hand-roll" item above is a place where hand-rolling wouldn't just be slower to write — it would introduce a *second*, unvalidated implementation of a statistical method this project already has a validated one for (VIF) or that has well-known numerical edge cases (ALE binning, parallel RNG streams). For a tribunal-facing thesis, using the standard, citable implementation is also a defensibility argument in itself.

## Common Pitfalls

### Pitfall 1: Silent entity-collision bug in the block bootstrap
**What goes wrong:** Concatenating a resampled country's rows under its original `country_code` produces a non-unique `(entity, year)` MultiIndex. `PanelOLS` does not raise an error.
**Why it happens:** `pandas.MultiIndex` does not require uniqueness by default, and `PanelOLS`'s internal grouping by the first index level silently treats all rows sharing a `country_code` — including the 2nd, 3rd, ... duplicate draw of the same country — as belonging to ONE entity.
**How to avoid:** Always relabel each draw to a synthetic unique id (`f"{country}__b{i}"}`) before calling `fit_panel_model`, as in Pattern 1's `resample_entities()`.
**Warning signs:** `res.entity_info["total"]` (number of entities `PanelOLS` recognizes) is smaller than the number of draws — live-verified concretely: 171 draws → 109 recognized entities without the fix, 171 with it.

### Pitfall 2: `RandomForestRegressor(n_jobs=-1)` breaks REPRO-02 even with `random_state` fixed
**What goes wrong:** Two runs of the exact same script produce different RF predictions/SHAP values.
**Why it happens:** Multi-threaded splitting in scikit-learn's RF introduces nondeterministic ordering of operations that a fixed `random_state` alone does not control — a known, long-standing upstream issue `[CITED: github.com/scikit-learn/scikit-learn/issues/11137]`, reproduced live in this session with the project's pinned `scikit-learn==1.9.0`.
**How to avoid:** Train the interpretability/reference RF with `n_jobs=1`. If speed matters, parallelize elsewhere (the bootstrap loop) where each unit of work has its own independent seed.
**Warning signs:** Re-running the notebook top-to-bottom twice produces different `rf.feature_importances_`, `shap_values`, or `oob_score_`.

### Pitfall 3: Attempting `.predict()` on a refit `PanelOLS` for an absolute counterfactual level
**What goes wrong:** Trying to get a country's simulated absolute GDP-growth level (not just the change) from a two-way fixed-effects model.
**Why it happens:** `PanelOLS`'s entity/time fixed effects are estimated via demeaning; they are not directly retrievable as reusable intercepts for new/counterfactual covariate values `[CITED: linearmodels docs — "idiosyncratic errors and effects are not available for out-of-sample predictions"]`.
**How to avoid:** Simulate the *change* in the outcome (`coefficient × Δregressor`), consistent with this phase's "sensitivity analysis, not causal prediction" framing already established in Phase 3's limitations section.
**Warning signs:** Needing to manually reconstruct or approximate an entity fixed-effect value for a scenario that doesn't correspond to an observed row.

### Pitfall 4: `shap.TreeExplainer`'s default `check_additivity=True` is slow at this scale
**What goes wrong:** A SHAP cell that "hangs" for several minutes during interactive notebook development.
**Why it happens:** The additivity check verifies `sum(shap_values) + expected_value == model_output` for every sample — live-verified at ~355s for 300 trees × 3473 rows × 13 features.
**How to avoid:** This is acceptable for a one-time "final" notebook run, but during iterative development, pass `check_additivity=False` or reduce `n_estimators`/sample size temporarily, then restore the full run for the committed notebook.
**Warning signs:** Notebook execution wall-clock time balloons during the SHAP cell specifically (isolate with `%%time` per cell).

### Pitfall 5: Assuming the RF predictors are highly correlated without checking
**What goes wrong:** Writing INTERP-04's "aviso de sesgo por correlación" as if `6.4.2` (water stress) and `6.4.1` (water efficiency) must be strongly correlated because they're both water-related.
**Why it happens:** Intuitive assumption, not verified against data.
**How to avoid:** The real global VIF for the RF's three numeric predictors (`6.4.2`=1.13, `6.4.1`=1.20, `8.2.1`=1.98) and their pairwise correlations (max |r|=0.09 among the three) — both pulled directly from `notebook/2_1_construccion_panel_eda.ipynb`'s cell 13 output — show only MODEST multicollinearity globally. The strongest correlation in the whole Phase-2 matrix (r=0.70) is between `8.2.1` and the *dependent* variable `8.1.1`, not between predictors. Report the honest numbers; note that regional-subgroup VIF (also in Phase 2's notebook, cells 14-15) is much higher for some regions (one region shows VIF > 300 for `2.3.1`), which the pooled global RF does not capture — a legitimate caveat to mention even though it doesn't affect the 3 predictors actually used here.
**Warning signs:** An interpretability section that asserts high correlation without a number backing it, or force-fits the a-priori "these must be correlated" narrative — this project's Phase 2 EDA already established a pattern of reporting the honest, sometimes-nuanced numbers (see 02-02-SUMMARY.md's MNAR discussion).

## Code Examples

Verified patterns from live execution against this project's own data and pinned `.venv` (see Patterns 1–3 above for the full versions):

### Reproducible seeding pattern (REPRO-02)
```python
# Source: live-verified + numpy.org/doc/stable/reference/random/parallel.html
import numpy as np

SEED = 42  # single project-wide constant, threaded through every stochastic step

# 1. Bootstrap replicas -- independent, reproducible, order-independent per replica
ss = np.random.SeedSequence(SEED)
child_seeds = ss.spawn(1000)
replica_rngs = [np.random.default_rng(c) for c in child_seeds]

# 2. RandomForest -- MUST use n_jobs=1 (see Pitfall #2)
from sklearn.ensemble import RandomForestRegressor
rf = RandomForestRegressor(random_state=SEED, n_jobs=1, oob_score=True)

# 3. If any train/test split is later added (see Open Questions Q1), also seed it:
# from sklearn.model_selection import train_test_split
# X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=SEED)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| PDP as the default "what does this variable do" plot | ALE preferred whenever features are correlated (Apley & Zhu 2020, popularized via Molnar's *Interpretable ML* book) | Established practice by ~2020, stable since | INTERP-05's explicit "complement SHAP for correlated variables" requirement is itself evidence the phase author is aware of this shift — PDP alone would not satisfy the intent |
| Global `np.random.seed()` | `np.random.default_rng(seed)` / `SeedSequence` local generators | numpy ≥1.17 (2019), now the documented best practice | Avoids the classic bug where an unrelated library call (e.g. inside `sklearn` or `pandas`) silently consumes/mutates the global RNG state between your own calls, breaking reproducibility in ways that are hard to trace |

**Deprecated/outdated:**
- Global `numpy.random.seed(...)` for anything beyond quick scripts: fragile under any library that also touches the global RNG state; `SeedSequence`-derived local generators are the current recommended pattern and directly needed here anyway for the parallel-safe bootstrap loop.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `PyALE` (v1.2.0, PyPI) is a legitimate, safe-to-install package despite the automated legitimacy checker returning `SUS` due to incomplete registry signals | Package Legitimacy Audit | Low — protocol already mandates a `checkpoint:human-verify` task before install regardless of this research's own manual verification; worst case is a rejected checkpoint, not a silent bad install |
| A2 | `oob_score_` is an adequate "comparación predictiva complementaria" for INTERP-06 without a separate train/test split | Summary, Pattern 3, Open Questions Q1 | Medium — if the planner/tribunal expects a conventional held-out test-set R²/MAE instead of OOB score, an extra seeded `train_test_split` step would need to be added; this is flagged explicitly in Open Questions for the planner to resolve, not silently assumed away |
| A3 | 300 trees / complete-case (N=3473) rows is a reasonable `RandomForestRegressor` configuration for this phase — exact hyperparameters left to Claude's Discretion per CONTEXT.md | Standard Stack, Pattern 3 | Low — CONTEXT.md explicitly leaves hyperparameters to discretion; 300/complete-case was only used for live timing/correctness verification, not asserted as the final tuned choice |

**If this table is empty:** N/A — see entries above.

## Open Questions (RESOLVED)

1. **Does INTERP-06 require a conventional held-out train/test split, or is the RF's `oob_score_` sufficient as the "predictive comparison" metric?** — `RESOLVED`
   - What we know: REPRO-02's wording explicitly anticipates "cualquier split" as a possible stochastic step needing a fixed seed, suggesting the phase's author considered a split might exist. `oob_score=True` gives an R² estimate "for free" from the same bootstrap-sampled trees already being fit, with no additional seeding surface.
   - What's unclear: Whether a tribunal/thesis-advisor would consider OOB score an adequate substitute for a conventional test-set metric, or whether a `train_test_split(random_state=SEED)` + `.score()` on the held-out set is expected as the more familiar, more easily explained "predictive comparison."
   - Recommendation: Default to `oob_score=True` (simpler, no extra seeding surface, already demonstrated deterministic under `n_jobs=1`) and let the planner add an explicit train/test split only if the phase's discuss-phase output or the thesis advisor specifically expects one. If added, it must be seeded (`random_state=SEED`) per REPRO-02.
   - **Resolution:** `04-02-PLAN.md` (Task 2) adopted `oob_score_` as the sole INTERP-06 metric — no separate train/test split.

2. **Exact runtime budget for the full notebook (3000 bootstrap refits + SHAP + ALE) — should the plan include a "reduce replicas for dev, restore to 1000 for final run" step?** — `RESOLVED`
   - What we know: ≈18 min (bootstrap, serial) + ≈6 min (SHAP on 300 trees) + ALE/PDP (fast, seconds) ≈ 25-30 min total for one full top-to-bottom execution, live-measured on this machine.
   - What's unclear: Whether this is acceptable as a single `nbconvert --execute` run (matching Phase 2/3's verification pattern of re-executing the whole notebook) or whether it needs `joblib.Parallel` to be part of the plan's Wave 0 rather than a "nice to have."
   - Recommendation: Plan for the serial version first (simpler to reason about and debug); add `joblib.Parallel` + `SeedSequence.spawn()` (Pattern 1) only if the ~25-30 min full-notebook re-execution becomes a practical blocker during the plan's own verification loop.
   - **Resolution:** `04-03-PLAN.md` adopted the serial version (no Wave 0 `joblib.Parallel` requirement); the plan's own Task 3 accepts the ~25-30 min-per-run cost since it re-executes the notebook twice for REPRO-02 proof.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| `linearmodels` | Bootstrap refits, interaction terms | ✓ (live-verified) | 7.0 | — |
| `scikit-learn` | RandomForest, PDP fallback | ✓ (live-verified) | 1.9.0 | — |
| `shap` | TreeExplainer | ✓ (live-verified) | 0.52.0 | — |
| `numpy` | SeedSequence, percentile CI | ✓ (live-verified) | 2.4.6 | — |
| `PyALE` | True ALE plots (INTERP-05, if chosen) | ✗ (not installed, not in `requirements.txt`) | — | `sklearn.inspection.PartialDependenceDisplay` (already available) — see Alternatives Considered |
| `joblib` | Optional bootstrap-loop parallelization | ✓ (already a transitive dependency of `scikit-learn`) | 1.5.3 | Serial loop (≈18 min, acceptable, see Open Questions Q2) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `PyALE` — fallback is `sklearn.inspection.PartialDependenceDisplay`, already pinned, zero new install.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` (already used: `tests/test_panel_base.py`, `tests/test_panel_build.py`, `tests/ingesta/`) |
| Config file | none found (no `pytest.ini`/`pyproject.toml` `[tool.pytest]` section) — defaults apply, consistent with Phase 3's setup |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_simulate.py tests/test_interpret.py -q` |
| Full suite command | `.venv/Scripts/python.exe -m pytest tests/ -q` (currently 84 tests passing per 03-VERIFICATION.md) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| INTERP-01 | `resample_entities()` produces a unique-index DataFrame with exactly N draws as recognized entities | unit | `pytest tests/test_simulate.py::test_resample_entities_unique_index -x` | ❌ Wave 0 |
| INTERP-01 | `check_non_extrapolation`-style logic excludes countries below historical min, per scenario | unit | `pytest tests/test_simulate.py::test_non_extrapolation_exclusion -x` | ❌ Wave 0 |
| INTERP-02 | Multi-scenario plot renders ≥3 scenarios with CI bands | manual/notebook | `nbconvert --execute` + visual check (no automated pixel test) | ❌ Wave 0 |
| INTERP-03 | Interaction formula (`:` not `*`) fits without `AbsorbingEffectError` and returns one coefficient per group | unit | `pytest tests/test_panel_base.py::test_interaction_formula -x` (or a small new test module) | ❌ Wave 0 |
| INTERP-04 | `shap_analysis()` returns SHAP values array of shape `(n_samples, n_features)` for a small fixture RF | unit | `pytest tests/test_interpret.py::test_shap_values_shape -x` | ❌ Wave 0 |
| INTERP-06 | `rf.oob_score_` (or equivalent) is computed and is a real float, not NaN/None | unit | `pytest tests/test_interpret.py::test_oob_score_present -x` | ❌ Wave 0 |
| REPRO-02 | Two calls to `bootstrap_counterfactual`/`shap_analysis` with the same seed produce identical results | unit (determinism) | `pytest tests/test_simulate.py::test_bootstrap_determinism -x`, `pytest tests/test_interpret.py::test_rf_determinism -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** quick run command above (small-fixture unit tests only — NOT the full 1000-replica bootstrap, which belongs only in the notebook's own execution)
- **Per wave merge:** full suite command
- **Phase gate:** full suite green before `/gsd-verify-work`, plus one full top-to-bottom notebook re-execution (matching Phase 2/3's verification pattern)

### Wave 0 Gaps
- [ ] `tests/test_simulate.py` — covers INTERP-01/02, REPRO-02 (bootstrap determinism)
- [ ] `tests/test_interpret.py` — covers INTERP-04/05/06, REPRO-02 (RF determinism)
- [ ] A small pytest fixture RF (tiny synthetic data, not the full 3473-row real panel) for fast unit tests of `shap_analysis`/`ale_plots` — the real-data run belongs only in the notebook, not the fast per-commit test loop
- Framework install: none needed — `pytest` already installed and used by Phases 1–3

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|-----------------|---------|--------------------|
| V2 Authentication | no | Local, single-user academic notebook/script pipeline — no auth surface |
| V3 Session Management | no | No web session in this phase |
| V4 Access Control | no | No multi-user access boundary |
| V5 Input Validation | partial | Predictor/typology columns come from this project's own `panel_clean` table (already validated/typed in Phase 1/2), not external user input — low risk, but `pd.to_numeric(..., errors="coerce")` (already the pattern in `panel_base.py`) should be reused for any new numeric columns touched by `simulate.py`/`interpret.py` |
| V6 Cryptography | no | No secrets/crypto surface in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Insecure deserialization via `pickle.load` on `rf_shap_model.pkl` | Tampering | This project's `.pkl` artifacts are only ever produced and consumed by its own code (never loaded from an untrusted/external source) — matches the existing pattern already established for `model1_gdp.pkl` in Phase 3 (round-trip verified in the same notebook run, not loaded from an external location). No additional mitigation needed beyond keeping this invariant; do not add any code path that loads a `.pkl` from a user-supplied path or network location. |
| SQL injection via table/column names | Tampering | Not a new risk in this phase — `src/db.py`'s existing pattern (fixed table names, parameterized `pandas.read_sql`) is reused unchanged; `simulate.py`/`interpret.py` only read `panel_clean`/`panel_exclusions` via the existing `get_engine()`/`read_sql` pattern, never constructing SQL from external input. |

## Sources

### Primary (HIGH confidence — live-verified against this project's own code/data/pinned `.venv`)
- Live execution of `src/panel_base.py::fit_panel_model` against real `data/panel.db` — timing (≈360ms/fit), entity-collision bug reproduction and fix, interaction-formula `AbsorbingEffectError`/fix
- Live execution of `RandomForestRegressor` + `shap.TreeExplainer` against real `panel_clean` data with pinned `scikit-learn==1.9.0`/`shap==0.52.0` — timing, `n_jobs` non-determinism reproduction
- `requirements.lock.txt` — exact pinned versions of all core-stack libraries
- `notebook/2_1_construccion_panel_eda.ipynb` cells 13-15 — real VIF/correlation numbers (read directly from the committed notebook's own output, not re-derived)
- `src/panel_base.py`, `src/db.py` — existing reusable code read directly

### Secondary (MEDIUM confidence — official docs, WebSearch/WebFetch)
- linearmodels docs (`bashtage.github.io/linearmodels`) — formula API, `EntityEffects`/`TimeEffects`, out-of-sample prediction limitations
- shap docs (`shap.readthedocs.io`) — `TreeExplainer` constructor, `feature_perturbation` options
- scikit-learn docs (`scikit-learn.org`) — `RandomForestRegressor` native NaN support, `random_state` behavior
- numpy docs (`numpy.org/doc/stable/reference/random/parallel.html`) — `SeedSequence.spawn()` pattern
- `github.com/scikit-learn/scikit-learn/issues/11137` — `n_jobs=-1` non-determinism, corroborating the live-reproduced finding
- PyPI (`pypi.org/project/PyALE`) + `pip index versions PyALE` — package age/version history
- `christophm.github.io/interpretable-ml-book/ale.html` — ALE vs. PDP under correlated features

### Tertiary (LOW confidence — WebSearch only, not independently verified this session)
- General academic literature on moving-block bootstrap for dynamic panel models (arxiv results) — theoretical background only, not directly implementable Python guidance; the block-bootstrap-by-entity pattern actually used here (D-01, live-verified) is simpler than the dynamic-panel literature discusses and does not rely on it
- `PyALE`'s exact weekly download count / GitHub star count — not confirmed via an authoritative source this session (flagged in Package Legitimacy Audit)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all core libraries are pre-existing pinned dependencies, versions read directly from `requirements.lock.txt`
- Architecture (bootstrap, interactions, RF/SHAP): HIGH — the two highest-risk patterns were live-verified end-to-end against this project's real data and pinned environment, not just documentation
- Pitfalls: HIGH — all 5 pitfalls are either live-reproduced bugs (1, 2, 3-related prediction limitation cited directly from official docs) or grounded in real Phase-2 numbers (5)
- ALE library choice (PyALE vs. PDP): MEDIUM — legitimacy-tool signal was incomplete; independent manual verification found no red flags, but protocol still requires a human-verify checkpoint

**Research date:** 2026-07-12
**Valid until:** ~30 days for the pinned-library findings (stable, already-installed versions won't drift); the live-verified bug reproductions (entity-collision, `n_jobs` non-determinism) are structural to `linearmodels`/`scikit-learn`'s current major versions and unlikely to change before this phase is executed.
