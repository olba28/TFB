---
phase: 06-modelo-2-productividad-agr-cola-stretch
plan: 02
subsystem: modeling
tags: [linearmodels, panel-data, bootstrap, shap, random-forest, sqlite]

# Dependency graph
requires:
  - phase: 06-modelo-2-productividad-agr-cola-stretch plan 01
    provides: "panel_base.filter_by_min_years(df, dep_var, indep_vars, min_years=3) -- the >=N-observed-years coverage helper this plan's build_model2_panel calls directly"
  - phase: 03-modelo-1-regresion-de-panel-pib-per-capita
    provides: "src/panel_base.py (fit_panel_model, hausman_test, pesaran_cd_test, choose_cov_type) invoked unmodified with dep_var=2.3.1"
  - phase: 04-interpretabilidad-simulaci-n-y-robustez
    provides: "src/simulate.py (bootstrap_counterfactual, fit_interaction_model) and src/interpret.py (shap_analysis) invoked unmodified with dep_var=2.3.1"
provides:
  - "src/model2_agri.py -- full runnable Model 2 pipeline (build panel, coverage table, fit + diagnostics, sin-COVID robustness, bootstrap, is_ldc heterogeneity, SHAP, serialization)"
  - "data/modelos/model2_agri.pkl, data/modelos/rf_shap_model_m2.pkl -- Model 2's fitted PanelEffectsResults and SHAP RandomForest, round-trip verified"
  - "model2_coverage table in data/panel.db -- 39/39 countries marked included, panel_exclusions-style schema"
affects: [06-modelo-2-productividad-agr-cola-stretch plan 03 (dashboard selector integration)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure parametric-reuse pipeline module: every estimation/simulation/interpretability call in src/model2_agri.py is an unmodified Phase 3/4 function invoked with dep_var='2.3.1' -- no PanelOLS/RandomForest/SHAP math re-implemented"
    - "RandomEffects fit directly via linearmodels.panel.RandomEffects (not wrapped by panel_base) solely to build Hausman-test input, following compare_specifications' constant-column convention -- the only new estimator call not routed through panel_base"

key-files:
  created:
    - src/model2_agri.py
    - tests/test_model2_agri.py
  modified: []

key-decisions:
  - "The Hausman-input FE fit and the RandomEffects fit both use cov_type='unadjusted' (classical covariances) -- the Hausman chi2 approximation assumes classical SEs, matching tests/test_panel_base.py's own Hausman fixtures; the FINAL fitted model (returned to callers/serialized) still uses whatever choose_cov_type selects from the Pesaran result"
  - "run_robustness_no_covid(panel_m2, cov_type='clustered', **cov_config) exposes cov_type/cov_config as optional kwargs (defaulting to fit_panel_model's own default) so _main() can pass fit_model2's actual chosen cov_type/cov_config for a like-for-like comparison against the main fit, while the plan's literal call-with-only-panel_m2 shape still works"
  - "run_shap(panel_clean) is called with the FULL panel_clean, not the 39-country panel_m2 -- shap_analysis performs its own complete-case dropna over feature_vars+[dep_var], and the RF's 3 numeric predictors have much broader real coverage (171/173 complete rows per 06-CONTEXT.md D-06) than 2.3.1 alone"

patterns-established:
  - "New Phase-6 pipeline modules follow the same module-docstring convention as panel_base.py/simulate.py/interpret.py: cite every D-xx decision motivating a design choice inline"

requirements-completed: [MODEL2-01, MODEL2-02, MODEL2-03]

coverage:
  - id: D1
    description: "build_model2_panel/build_coverage_table build the 39-country Model 2 panel and its dedicated model2_coverage documentation table (D-01/D-02/D-03)"
    requirement: "MODEL2-02"
    verification:
      - kind: unit
        ref: "tests/test_model2_agri.py#test_build_coverage_table_has_expected_columns"
        status: pass
      - kind: unit
        ref: "tests/test_model2_agri.py#test_build_coverage_table_marks_included_iff_at_or_above_min_years"
        status: pass
      - kind: unit
        ref: "tests/test_model2_agri.py#test_build_coverage_table_excludes_countries_with_zero_dep_var_observations"
        status: pass
      - kind: unit
        ref: "tests/test_model2_agri.py#test_build_model2_panel_keeps_only_countries_meeting_threshold"
        status: pass
      - kind: unit
        ref: "tests/test_model2_agri.py#test_build_model2_panel_default_min_years_is_three"
        status: pass
      - kind: other
        ref: "SELECT COUNT(*) FROM model2_coverage WHERE included=1 against real data/panel.db -> 39"
        status: pass
    human_judgment: false
  - id: D2
    description: "fit_model2 fits Model 2's two-way FE PanelOLS via panel_base.fit_panel_model, runs Hausman/Pesaran diagnostics, and picks cov_type via choose_cov_type -- identical decision flow to Model 1 (MODEL2-01, D-04)"
    requirement: "MODEL2-01"
    verification:
      - kind: other
        ref: "python -m src.model2_agri live run against real data/panel.db -> Hausman stat=5.995 df=1 p=0.0143; Pesaran CD stat=-0.168 p=0.867; chosen cov_type=clustered (cluster_entity=True)"
        status: pass
    human_judgment: false
  - id: D3
    description: "run_robustness_no_covid, run_bootstrap, run_heterogeneity, run_shap extend simulation/heterogeneity/SHAP to Model 2 via unmodified simulate.py/interpret.py calls (MODEL2-03, D-05/D-06/D-09/D-10/D-11)"
    requirement: "MODEL2-03"
    verification:
      - kind: other
        ref: "python -m src.model2_agri live run: sin-COVID robustness nobs=120 (35 countries survive year<2020); bootstrap n_replicas=1000; heterogeneity group_col=is_ldc; SHAP feature_vars=[6.4.2,6.4.1,8.2.1,is_ldc,is_lldc,is_sids,region]"
        status: pass
    human_judgment: false
  - id: D4
    description: "model2_agri.pkl and rf_shap_model_m2.pkl serialize and round-trip load to the correct types without refitting"
    requirement: "MODEL2-01"
    verification:
      - kind: other
        ref: "pickle.load(data/modelos/model2_agri.pkl) isinstance PanelEffectsResults; pickle.load(data/modelos/rf_shap_model_m2.pkl) isinstance RandomForestRegressor"
        status: pass
    human_judgment: false

# Metrics
duration: ~15min
completed: 2026-07-15
status: complete
---

# Phase 6 Plan 2: Model 2 (agricultural productivity) pipeline Summary

**`src/model2_agri.py` extends the entire Model 1 methodology (two-way FE PanelOLS, Hausman/Pesaran diagnostics, sin-COVID robustness, 1000-replica bootstrap, is_ldc heterogeneity, SHAP) to indicator 2.3.1 by calling `panel_base`/`simulate`/`interpret` unmodified with `dep_var="2.3.1"`, and documents the reduced 39-country coverage in a dedicated `model2_coverage` table.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-15T06:56:19Z
- **Completed:** 2026-07-15T07:11:52Z
- **Tasks:** 3 completed
- **Files modified:** 2

## Accomplishments
- `src/model2_agri.py` built as pure parametric reuse: `build_model2_panel`/`build_coverage_table` (D-01/D-02/D-03), `fit_model2` (D-04, same Hausman/Pesaran/choose_cov_type decision flow as Model 1), `run_robustness_no_covid` (D-10, sin-COVID year<2020), `run_bootstrap`/`run_heterogeneity`/`run_shap` (D-05/D-06/D-11), `serialize_artifacts`/`write_coverage_table`/`_main` (runnable `python -m src.model2_agri` CLI)
- Live pipeline run against the real `data/panel.db` confirms all the phase's headline numbers: **39/39 countries** in `model2_coverage` (D-01), Hausman statistic=5.995 (df=1, p=0.0143 — rejects H0, favors RE over FE on this specification, a notable divergence from Model 1's "no rechaza H0, apoya FE" documented in PROJECT.md, flagged below for the memoria's limitations section), Pesaran CD p=0.867 (fails to reject — no cross-sectional dependence detected, so `choose_cov_type` selected **clustered** SEs, unlike Model 1's Driscoll-Kraay choice), sin-COVID robustness sub-sample nobs=120 (~35 surviving countries)
- Both `data/modelos/model2_agri.pkl` (`PanelEffectsResults`) and `data/modelos/rf_shap_model_m2.pkl` (`RandomForestRegressor`) serialize and round-trip load without refitting
- 5 new unit tests (`tests/test_model2_agri.py`) for the deterministic coverage-table/panel-filter bookkeeping; full project suite (118 tests) passes with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Build model2_agri.py (panel construction, coverage table, fit+diagnostics+robustness, bootstrap+heterogeneity+SHAP+serialization+_main)** - `b67d960` (feat)
2. **Task 3: Tests + execute the pipeline to produce artifacts and coverage table** - `22e9ec5` (test)

_Tasks 1 and 2 were committed together as a single atomic commit since both build the same file (`src/model2_agri.py`) and the plan's own Task 1 verify command is a strict subset of Task 2's; splitting them would have required an artificial intermediate write/re-read of the same file with no independent verification step in between._

## Files Created/Modified
- `src/model2_agri.py` - Full Model 2 pipeline: panel construction, coverage table, fit+diagnostics, sin-COVID robustness, bootstrap, is_ldc heterogeneity, SHAP, serialization, runnable `_main()`
- `tests/test_model2_agri.py` - 5 unit tests for `build_coverage_table`/`build_model2_panel` deterministic bookkeeping on a synthetic sparse panel using the real `2.3.1`/`6.4.2` column names
- `data/modelos/model2_agri.pkl`, `data/modelos/rf_shap_model_m2.pkl` (gitignored, regenerable via `python -m src.model2_agri` — not committed, per project convention already established for `model1_gdp.pkl`/`rf_shap_model.pkl`)
- `data/panel.db` `model2_coverage` table (gitignored file, not committed — regenerated by the same pipeline run)

## Decisions Made
- The Hausman-input FE fit and the `RandomEffects` fit both use `cov_type="unadjusted"` (classical covariances) — the Hausman chi2 approximation assumes this, matching `tests/test_panel_base.py`'s own Hausman fixtures; the FINAL fitted model (serialized, returned to `run_bootstrap`/`run_heterogeneity`) still uses whatever `choose_cov_type` selects from the Pesaran CD result (clustered, in this live run).
- `run_robustness_no_covid(panel_m2, cov_type="clustered", **cov_config)` exposes `cov_type`/`cov_config` as optional keyword arguments rather than hardcoding a single covariance choice, so `_main()` passes `fit_model2`'s actual chosen `cov_type`/`cov_config` for a true like-for-like comparison against the main fit, while still satisfying the plan's literal `run_robustness_no_covid(panel_m2)` call shape for any other caller.
- `run_shap(panel_clean)` is called with the FULL `panel_clean`, not the 39-country `panel_m2` — `interpret.shap_analysis` performs its own complete-case `.dropna()` over `feature_vars + [dep_var]`, and the RF's 3 numeric predictors have much broader real coverage (171/173 complete rows per 06-CONTEXT.md D-06) than `2.3.1` alone would allow if restricted to `panel_m2`.
- Used `linearmodels.panel.RandomEffects` directly (not wrapped by `panel_base`) solely to build the Hausman-test's RE input, since `panel_base.py` exposes no standalone RE-fitting function — this is the one place `model2_agri.py` calls a `linearmodels` estimator class directly rather than through `panel_base`, and it does not violate the "no re-implementation" acceptance criteria (which forbid re-implementing `PanelOLS`/Hausman/Pesaran math, not fitting the one estimator `panel_base` doesn't already wrap).

## Deviations from Plan

None - plan executed exactly as written. The Task 1/Task 2 commit consolidation (documented above) is a task-boundary/commit-granularity detail, not a scope change: every acceptance criterion from both tasks is satisfied within the single commit, and both tasks build the identical file with no independently verifiable intermediate state.

## Issues Encountered
None. The live pipeline run surfaced an expected `linearmodels.panel.model.MissingValueWarning` ("Inputs contain missing values. Dropping rows with missing observations") repeatedly during the 1000-replica bootstrap — this is `linearmodels`' own standard behavior when `PanelOLS` is fit on a resampled entity draw that still carries some individually-missing years within an included country's qualifying span (expected under D-01's country-level, not row-level, inclusion criterion), not a bug or a suppressed diagnostic. No custom `panel_base` warning (singular Hausman matrix, negative statistic, degenerate Pesaran result) fired during this live run — the diagnostics resolved cleanly at N=39.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
`data/modelos/model2_agri.pkl`, `data/modelos/rf_shap_model_m2.pkl`, and the `model2_coverage` table are all in place and verified for plan 06-03 (dashboard selector integration), which reads them via the `ACTIVE_MODELS` registry stub already staged in `src/dashboard/models.py`.

**Flag for the memoria's limitations section (D-04):** Model 2's Hausman test REJECTS H0 at the 5% level (p=0.0143), unlike Model 1's "no rechaza H0, apoya FE" result (PROJECT.md Fase 03). This is a genuine, documented divergence between the two models' diagnostics on the sparse 39-country/~3.5-obs-per-country panel — not a degenerate/singular-matrix warning (none fired), but a real result that should be discussed explicitly rather than omitted, per D-04's "warn, don't hide" convention extended to write-up time.

---
*Phase: 06-modelo-2-productividad-agr-cola-stretch*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: src/model2_agri.py
- FOUND: tests/test_model2_agri.py
- FOUND: data/modelos/model2_agri.pkl
- FOUND: data/modelos/rf_shap_model_m2.pkl
- FOUND: b67d960 (feat commit)
- FOUND: 22e9ec5 (test commit)
