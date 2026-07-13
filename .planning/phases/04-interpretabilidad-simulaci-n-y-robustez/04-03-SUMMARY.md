---
phase: 04-interpretabilidad-simulaci-n-y-robustez
plan: 03
subsystem: modeling
tags: [jupyter, nbconvert, shap, randomforest, bootstrap, reproducibility]

# Dependency graph
requires:
  - phase: 04-interpretabilidad-simulaci-n-y-robustez
    provides: "src/simulate.py (Plan 01: bootstrap_counterfactual, fit_interaction_model, check_non_extrapolation) and src/interpret.py (Plan 02: compute_vif_table, shap_analysis, partial_dependence_plots), consumed unmodified"
provides:
  - "notebook/4_1_interpretabilidad_simulacion.ipynb: single Phase-4 orchestration notebook run against the real 171-country/3933-obs panel"
  - "data/modelos/rf_shap_model.pkl: serialized RandomForestRegressor (gitignored, round-trip verified), consumed by Phase 5 dashboard and reusable by Phase 6"
  - "scripts/verify_repro02.py: standalone reproducibility-proof script (two independent full notebook executions, bit-identical comparison)"
affects: ["05-dashboard (consumes rf_shap_model.pkl and notebook outputs without live recomputation)", "06-modelo-2 (interpret.py reuse with dep_var=2.3.1)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Notebook-local SEED=42 threaded through every stochastic step (bootstrap SeedSequence + RF random_state), proven bit-identical via np.array_equal across two independent full top-to-bottom executions"
    - "Reproducibility snapshot cell (data/modelos/_repro_snapshot.pkl, gitignored working artifact) captures bootstrap CIs/excluded countries/RF feature_importances_/oob_score_/SHAP values for external diffing by scripts/verify_repro02.py"
    - "verify_repro02.py runs as a standalone script (not pytest) because a full run costs ~25-30 min, far outside the pytest suite's 10s feedback-latency budget"

key-files:
  created:
    - notebook/4_1_interpretabilidad_simulacion.ipynb
    - scripts/verify_repro02.py
  modified:
    - src/interpret.py

key-decisions:
  - "compute_vif_table (Plan 02) was fixed (commit 8857120) to add a constant column to the design matrix before computing VIF -- without it, the function silently produced inflated VIF numbers that did not match Phase 2's committed EDA output. Root cause found while building the notebook's VIF/SHAP precedence section, which required reproducing Phase 2's real numbers exactly."
  - "The reproducibility snapshot is written to a fixed gitignored path (data/modelos/_repro_snapshot.pkl), deliberately separate from rf_shap_model.pkl, so scripts/verify_repro02.py can overwrite it on each of the two independent executions without touching the committed model artifact."

patterns-established:
  - "Blocking checkpoint:human-verify (Task 2b) gates notebook narrative/output review before the expensive reproducibility proof (Task 3) runs -- avoids spending ~50-60 min re-verifying reproducibility on a notebook a human might still ask to change."

requirements-completed: [INTERP-01, INTERP-02, INTERP-03, INTERP-04, INTERP-05, INTERP-06, REPRO-02]

coverage:
  - id: D1
    description: "Multi-scenario sensitivity plot (-10%/-20%/-30%) with bootstrap percentile CI bands, explicitly framed as sensitivity analysis, not causal prediction (INTERP-01/02)"
    requirement: "INTERP-02"
    verification:
      - kind: manual_procedural
        ref: "User checkpoint (Task 2b) approved 2026-07-12: confirmed 3 visibly distinct CI bands with axis/legend labels and explicit sensitivity-framing markdown cell"
        status: pass
    human_judgment: true
    rationale: "Visual plot legibility and narrative framing require human review; this is exactly what Task 2b's blocking checkpoint gated, and the user approved it."
  - id: D2
    description: "Non-extrapolation exclusions documented explicitly per scenario (D-04) -- Congo (COG) excluded from all three scenarios"
    requirement: "INTERP-01"
    verification:
      - kind: manual_procedural
        ref: "User checkpoint (Task 2b) approved 2026-07-12"
        status: pass
    human_judgment: true
    rationale: "Part of the same approved checkpoint review."
  - id: D3
    description: "Heterogeneity section renders only grouped region/is_ldc interaction-coefficient tables with SE/CI, no per-country prediction anywhere (INTERP-03/D-11)"
    requirement: "INTERP-03"
    verification:
      - kind: manual_procedural
        ref: "User checkpoint (Task 2b) approved 2026-07-12"
        status: pass
    human_judgment: true
    rationale: "Part of the same approved checkpoint review."
  - id: D4
    description: "VIF/correlation table (real Phase-2 numbers) precedes SHAP output with an explicit correlation-bias caveat (INTERP-04); PDP plots complement SHAP for correlated predictors (INTERP-05); oob_score_ reported as predictive reference (INTERP-06)"
    requirement: "INTERP-04"
    verification:
      - kind: manual_procedural
        ref: "User checkpoint (Task 2b) approved 2026-07-12"
        status: pass
    human_judgment: true
    rationale: "Part of the same approved checkpoint review."
  - id: D5
    description: "data/modelos/rf_shap_model.pkl is serialized and round-trip-verified (np.allclose on feature_importances_)"
    requirement: "INTERP-06"
    verification:
      - kind: automated_ui
        ref: "Notebook cell assertion (in-notebook np.allclose check) + plan's standalone verify command, both executed during Task 2"
        status: pass
    human_judgment: false
  - id: D6
    description: "Two full top-to-bottom executions of the notebook produce bit-identical bootstrap CIs, excluded-country lists, RF feature importances/oob_score_, and SHAP values (REPRO-02)"
    requirement: "REPRO-02"
    verification:
      - kind: other
        ref: "scripts/verify_repro02.py (exit 0, PASS printed)"
        status: pass
    human_judgment: false

# Metrics
duration: ~50min active work (spread across 2026-07-12 21:03 - 2026-07-13 15:33 wall-clock; see Issues Encountered for an overnight stall gap excluded from this figure)
completed: 2026-07-13
status: complete
---

# Phase 4 Plan 3: Phase-4 Orchestration Notebook Summary

**`notebook/4_1_interpretabilidad_simulacion.ipynb`: real-panel counterfactual simulation, heterogeneity analysis, and RF/SHAP/VIF/PDP interpretability stack, with `rf_shap_model.pkl` serialized and REPRO-02 proven bit-identical across two independent full executions**

## Performance

- **Duration:** ~50 min active work (Tasks 1-2: 2026-07-12T21:03:31+02:00 → 21:28:09+02:00, ~25 min; Task 3: resumed 2026-07-13, reproducibility script ran ~50-60 min wall-clock, final commit 15:33:44+02:00). See Issues Encountered for the overnight gap between these two windows, which was orchestrator-detected idle time, not active execution.
- **Started:** 2026-07-12T21:03:31+02:00
- **Completed:** 2026-07-13T15:33:44+02:00
- **Tasks:** 4 (3 planned auto tasks + 1 blocking checkpoint)
- **Files modified:** 3 (`notebook/4_1_interpretabilidad_simulacion.ipynb` created, `scripts/verify_repro02.py` created, `src/interpret.py` fixed)

## Accomplishments
- Built the single Phase-4 orchestration notebook (D-13) that runs, in order, the bootstrap counterfactual simulation (INTERP-01/02), region/is_ldc heterogeneity analysis (INTERP-03), and the VIF→SHAP→PDP interpretability stack (INTERP-04/05/06) against the real 171-country/3933-observation panel (1.4% drift, within tolerance)
- Found and fixed a real bug in `src/interpret.py::compute_vif_table` (Plan 02 code): it was missing a constant column in the design matrix, silently producing inflated VIF numbers that didn't match Phase 2's committed EDA output — caught while trying to honestly reproduce those real numbers in the notebook
- Serialized `data/modelos/rf_shap_model.pkl` (D-08, gitignored) and round-trip-verified it via `np.allclose` on `feature_importances_`
- User-approved blocking checkpoint (Task 2b) confirmed the sensitivity plot, non-extrapolation exclusions, heterogeneity tables, VIF/SHAP precedence, and PDP plots all meet the Phase-4 success criteria
- Built `scripts/verify_repro02.py`, which independently executes the committed notebook twice and asserts `np.array_equal` (exact, not approximate) between bootstrap CIs, excluded-country lists, RF feature importances/`oob_score_`, and SHAP values — confirmed **PASS**, proving REPRO-02 end-to-end
- Full test suite remains green (92 tests) after all changes

## Task Commits

Each task was committed atomically:

1. **Fix: `compute_vif_table` design matrix** - `8857120` (fix)
2. **Task 1: Simulation + heterogeneity notebook sections** - `af4b453` (feat)
3. **Task 2: Interpretability section + serialize `rf_shap_model.pkl`** - `cb16142` (feat)
4. **Checkpoint pause (Task 2b, user-approved)** - `0513e92` (docs)
5. **Task 3: Prove full-notebook reproducibility (REPRO-02)** - `e97b8c4` (feat)

## Files Created/Modified
- `notebook/4_1_interpretabilidad_simulacion.ipynb` - Phase-4 orchestration notebook (32 cells): simulation, heterogeneity, interpretability, and reproducibility-snapshot sections
- `scripts/verify_repro02.py` - standalone reproducibility-proof script (two independent full executions, bit-identical comparison via `np.array_equal`)
- `src/interpret.py` - `compute_vif_table` fixed to add a constant column to the design matrix

## Decisions Made
- `compute_vif_table`'s missing-constant bug was fixed in `src/interpret.py` rather than worked around in the notebook, since the root cause was in Plan 02's shared module code and any future caller (Phase 6) would hit the same silent-inflation bug otherwise.
- The reproducibility snapshot is written to a fixed gitignored path (`data/modelos/_repro_snapshot.pkl`) deliberately separate from `rf_shap_model.pkl`, so `verify_repro02.py` can overwrite it twice without touching the committed model artifact.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed `compute_vif_table` design matrix**
- **Found during:** Task 2 (Interpretability section, reproducing Phase 2's real VIF numbers)
- **Issue:** `compute_vif_table` (from Plan 02) did not add a constant column before computing VIF, silently producing inflated VIF numbers that contradicted Phase 2's own committed EDA output
- **Fix:** Added the constant-column step per the standard `variance_inflation_factor` methodology
- **Files modified:** `src/interpret.py`
- **Verification:** Notebook's VIF table now matches `notebook/2_1_construccion_panel_eda.ipynb`'s committed numbers (VIF 6.4.2=1.127, 6.4.1=1.195, 8.2.1=1.981)
- **Committed in:** `8857120`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Necessary correctness fix in shared Plan-02 code; no scope creep — Plan 02's own test suite still passes unchanged.

## Issues Encountered
**Overnight executor stall (orchestrator-recovered, not a plan defect):** After the user approved the Task 2b checkpoint, the continuation executor agent launched Task 3's reproducibility check but its own background-task self-monitoring never resolved — its last recorded action was an `echo` placeholder awaiting a notification that was never coming, leaving it idle for roughly 9 hours with no further progress (no new commits, no running processes). The orchestrator detected this via direct repo inspection (unchanged file timestamps, no active Python processes), presented the stall to the user with three recovery options, and per the user's choice ("I run it directly") ran the already-authored `scripts/verify_repro02.py` itself via a backgrounded shell command with reliable completion notification. The script passed on the first direct run — no code defect was involved, only the executor's flawed self-monitoring assumption.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `data/modelos/rf_shap_model.pkl` is serialized, round-trip-verified, and ready for Phase 5 (dashboard) to consume without live recomputation (DASH-01) and for Phase 6 (Modelo 2) to reuse with `dep_var="2.3.1"`
- All seven Phase-4 requirement IDs (INTERP-01 through INTERP-06, REPRO-02) are now marked complete in REQUIREMENTS.md
- Phase 4's three plans (04-01, 04-02, 04-03) are all complete; ready for phase-level goal verification

---
*Phase: 04-interpretabilidad-simulaci-n-y-robustez*
*Completed: 2026-07-13*

## Self-Check: PASSED

- FOUND: notebook/4_1_interpretabilidad_simulacion.ipynb
- FOUND: scripts/verify_repro02.py
- FOUND: data/modelos/rf_shap_model.pkl
- FOUND: .planning/phases/04-interpretabilidad-simulaci-n-y-robustez/04-03-SUMMARY.md
- FOUND commit: 8857120 (fix)
- FOUND commit: af4b453 (feat)
- FOUND commit: cb16142 (feat)
- FOUND commit: 0513e92 (docs)
- FOUND commit: e97b8c4 (feat)
