---
phase: 04-interpretabilidad-simulaci-n-y-robustez
plan: 01
subsystem: modeling
tags: [linearmodels, panelols, bootstrap, numpy, pandas, econometrics, panel-data]

# Dependency graph
requires:
  - phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita
    provides: "src/panel_base.py (fit_panel_model, filter_by_exclusions) -- fit_panel_model called unmodified once per bootstrap replica"
provides:
  - "src/simulate.py: resample_entities, bootstrap_counterfactual, check_non_extrapolation, fit_interaction_model"
  - "tests/test_simulate.py: fixture-based unit tests proving entity-relabeling correctness, non-extrapolation exclusion, bootstrap determinism, and interaction-formula correctness"
affects: [04-02, 04-03, "06-modelo-2 (Phase 6 reuses simulate.py unmodified with dep_var='2.3.1')"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Block bootstrap by entity with synthetic relabeling (f\"{entity}__b{i}\") to avoid PanelOLS silently collapsing duplicate-drawn countries into one fixed-effect bucket"
    - "numpy.random.SeedSequence(seed).spawn(n_replicas) for independent, reproducible per-replica RNGs (REPRO-02)"
    - "Interaction-only PanelOLS.from_formula syntax (indep_var : C(group_col), colon not *) to avoid AbsorbingEffectError from a time-invariant main effect under EntityEffects"
    - "Exclude-never-cap non-extrapolation rule (D-04) via a pure check_non_extrapolation(baseline, simulated_level, historical_min) function"

key-files:
  created:
    - src/simulate.py
    - tests/test_simulate.py
  modified: []

key-decisions:
  - "reduction_pcts default to signed fractions ([-0.10, -0.20, -0.30]) with delta = pct * baseline, not the unsigned-magnitude convention shown in 04-RESEARCH.md's illustrative code -- matches the plan's own explicit function-signature default"
  - "baseline/historical_min coerced via pd.to_numeric(errors='coerce') (not .astype(float)) to satisfy threat register T-04-05's numeric-coercion mitigation, consistent with panel_base.py's established convention (Rule 2 fix, see Deviations)"
  - "test_interaction_formula asserts on interaction-term parameter names (via 'C(group)' substring match) rather than a fixed total param count, since PanelOLS.from_formula's '1 +' term also returns an Intercept row alongside the two per-group interaction coefficients"

patterns-established:
  - "Parametric, dependent-variable-agnostic module design (D-12): every public function takes dep_var/indep_var/group_col as parameters, never hardcodes '8.1.1' or '6.4.2', so Phase 6 can call with dep_var='2.3.1' unmodified"

requirements-completed: [INTERP-01, INTERP-03, REPRO-02]

coverage:
  - id: D1
    description: "resample_entities relabels every drawn country to a unique synthetic entity id so N draws yield exactly N recognized entities (no silent collision)"
    requirement: "INTERP-01"
    verification:
      - kind: unit
        ref: "tests/test_simulate.py#test_resample_entities_unique_index"
        status: pass
    human_judgment: false
  - id: D2
    description: "bootstrap_counterfactual returns per-scenario coefficient/effect distributions with 2.5/97.5 percentile CIs for at least three reduction scenarios (-10/-20/-30%)"
    requirement: "INTERP-01"
    verification:
      - kind: unit
        ref: "tests/test_simulate.py#test_bootstrap_determinism"
        status: pass
    human_judgment: false
  - id: D3
    description: "check_non_extrapolation excludes a country from a scenario (never caps) when its simulated water-stress value falls below the global historical minimum, per scenario"
    requirement: "INTERP-01"
    verification:
      - kind: unit
        ref: "tests/test_simulate.py#test_non_extrapolation_exclusion"
        status: pass
    human_judgment: false
  - id: D4
    description: "Two calls to bootstrap_counterfactual with the same seed produce bit-identical coefficient draws (REPRO-02)"
    requirement: "REPRO-02"
    verification:
      - kind: unit
        ref: "tests/test_simulate.py#test_bootstrap_determinism"
        status: pass
    human_judgment: false
  - id: D5
    description: "fit_interaction_model returns one water-stress coefficient per group (region, is_ldc proxy) with SE/CI and never raises AbsorbingEffectError"
    requirement: "INTERP-03"
    verification:
      - kind: unit
        ref: "tests/test_simulate.py#test_interaction_formula"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-12
status: complete
---

# Phase 4 Plan 1: Bootstrap Counterfactual + Interaction Heterogeneity Summary

**`src/simulate.py`: block-bootstrap counterfactual simulation (entity-relabeled, `SeedSequence`-seeded, non-extrapolation exclusion) plus interaction-term regional/typology heterogeneity, both dependent-variable-agnostic for Phase 6 reuse**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-12T18:36:10Z (approx, per STATE.md session start)
- **Completed:** 2026-07-12T18:57:00Z (approx)
- **Tasks:** 3
- **Files modified:** 2 (both created: `src/simulate.py`, `tests/test_simulate.py`)

## Accomplishments
- `resample_entities()` fixes the silent entity-collision bug (04-RESEARCH.md Pitfall #1) by relabeling every bootstrap draw to a unique synthetic entity id before concatenation
- `bootstrap_counterfactual()` refits `panel_base.fit_panel_model` unmodified once per replica, using `numpy.random.SeedSequence(seed).spawn(n_replicas)` for bit-identical reproducibility (REPRO-02) across three default reduction scenarios (-10/-20/-30%)
- `check_non_extrapolation()` is a pure function excluding (never capping) a country from a scenario when its simulated water-stress level drops below the panel's global historical minimum (D-04)
- `fit_interaction_model()` fits the interaction-only `PanelOLS.from_formula` specification (`indep_var : C(group_col)`, colon not `*`), avoiding `AbsorbingEffectError` and returning a per-group coefficient table with SE/CI (D-11)
- Four fixture-based unit tests (no real 171-country panel used, per Wave 0 requirement) prove all of the above; full test suite remains green at 88 tests with zero modification to `src/panel_base.py`

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing unit tests for src/simulate.py** - `2214dcc` (test)
2. **Task 2: Implement bootstrap counterfactual + non-extrapolation in src/simulate.py** - `dc8b44b` (feat)
3. **Task 3: Implement interaction-term heterogeneity in src/simulate.py** - `28d7411` (feat)

**Deviation fix:** `11d38ba` (fix - numeric coercion consistency, see Deviations below)

_Note: Task 3's commit also includes a test-assertion refinement to `tests/test_simulate.py` (interaction-term param-name matching instead of a fixed total-param-count assertion), made necessary by observing the real `PanelOLS.from_formula` output during GREEN._

## Files Created/Modified
- `src/simulate.py` - `resample_entities`, `bootstrap_counterfactual`, `check_non_extrapolation`, `fit_interaction_model` (all dependent-variable-agnostic, D-12)
- `tests/test_simulate.py` - fixture-based unit tests for all four functions, mirroring `tests/test_panel_base.py`'s conventions

## Decisions Made
- Adopted the plan's explicit `reduction_pcts=[-0.10, -0.20, -0.30]` signed-fraction convention (`delta = pct * baseline`) rather than 04-RESEARCH.md's illustrative unsigned-magnitude convention (`delta = -pct * baseline`) -- the plan's own function signature is the authoritative source, and using signed fractions directly as dict keys (`results[-0.30]`) is more intuitive to read in the notebook (Plan 03) than a magnitude/sign split would be.
- `test_interaction_formula` asserts on interaction-term parameter names (substring match on `"C(group)"`) rather than a fixed total parameter count, since `PanelOLS.from_formula`'s `1 +` term also returns an `Intercept` row alongside the two per-group interaction coefficients -- confirmed by running the actual fit rather than assuming the exact param count from the research excerpt.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Numeric coercion consistency for baseline/historical_min**
- **Found during:** Post-implementation self-review against the plan's `<threat_model>` register (T-04-05)
- **Issue:** `bootstrap_counterfactual`'s `baseline`/`historical_min` construction initially used a bare `.astype(float)` instead of the `pd.to_numeric(..., errors="coerce")` pattern that `src/panel_base.py` already establishes and that the plan's threat register explicitly requires ("Reuse `pd.to_numeric(..., errors='coerce')` for any new numeric column touched")
- **Fix:** Replaced both call sites with `pd.to_numeric(..., errors="coerce")`
- **Files modified:** `src/simulate.py`
- **Verification:** Full test suite re-run green (88 tests) after the change
- **Committed in:** `11d38ba`

---

**Total deviations:** 1 auto-fixed (1 missing-critical / threat-mitigation completeness)
**Impact on plan:** Defensive consistency fix only, no behavior change on well-formed numeric input; no scope creep.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `src/simulate.py` is ready for Plan 03's notebook (`4_1_interpretabilidad_simulacion.ipynb`) to orchestrate against the real `data/panel.db` panel (bootstrap with `n_replicas=1000`, interaction models for `region` and `is_ldc`)
- Phase 6 (Modelo 2) can call every function in `src/simulate.py` unmodified with `dep_var="2.3.1"` per D-12 -- no changes needed to this module
- `src/panel_base.py` remains untouched, confirming the parametric-reuse contract from Phase 3 held

---
*Phase: 04-interpretabilidad-simulaci-n-y-robustez*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: src/simulate.py
- FOUND: tests/test_simulate.py
- FOUND: .planning/phases/04-interpretabilidad-simulaci-n-y-robustez/04-01-SUMMARY.md
- FOUND commit: 2214dcc (test)
- FOUND commit: dc8b44b (feat)
- FOUND commit: 28d7411 (feat)
- FOUND commit: 11d38ba (fix)
