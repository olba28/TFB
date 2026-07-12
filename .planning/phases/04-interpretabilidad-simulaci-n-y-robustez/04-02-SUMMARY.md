---
phase: 04-interpretabilidad-simulaci-n-y-robustez
plan: 02
subsystem: modeling
tags: [scikit-learn, shap, randomforest, statsmodels, vif, interpretability, partial-dependence]

# Dependency graph
requires:
  - phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita
    provides: "src/panel_base.py conventions (module docstring citing decisions, warnings.warn(stacklevel=2), pd.to_numeric coercion) replicated here for src/interpret.py"
provides:
  - "src/interpret.py: compute_vif_table, shap_analysis, partial_dependence_plots"
  - "tests/test_interpret.py: fixture-based unit tests proving SHAP output shape, oob_score_ presence, RF determinism under n_jobs=1, and finite VIFs on a non-collinear fixture"
affects: [04-03, "06-modelo-2 (Phase 6 reuses interpret.py unmodified with dep_var='2.3.1')"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "n_jobs=1 mandatory on RandomForestRegressor for REPRO-02 (n_jobs=-1 breaks reproducibility even with fixed random_state)"
    - "shap.TreeExplainer wraps a standalone RandomForestRegressor, never PanelOLS.predict (Phase 3's decoupled-SHAP resolution)"
    - "compute_vif_table reuses statsmodels.stats.outliers_influence.variance_inflation_factor (no hand-rolled VIF math)"
    - "sklearn.inspection.PartialDependenceDisplay as the zero-new-dependency PDP fallback for INTERP-05 (PyALE deliberately not installed)"

key-files:
  created:
    - src/interpret.py
    - tests/test_interpret.py
  modified: []

key-decisions:
  - "partial_dependence_plots implemented via sklearn.inspection.PartialDependenceDisplay.from_estimator only -- PyALE (SUS-flagged in 04-RESEARCH.md's Package Legitimacy Audit) was never installed, no checkpoint:human-verify task was needed, requirements.txt/requirements.lock.txt unchanged"
  - "shap_analysis one-hot encodes only the 'region' categorical column (via pd.get_dummies(..., columns=['region'], drop_first=True)) -- is_ldc/is_lldc/is_sids are already binary 0/1 flags in panel_clean, no encoding needed"

patterns-established:
  - "Parametric, dependent-variable-agnostic module design (D-12): shap_analysis(df, dep_var, feature_vars, seed=42) takes dep_var/feature_vars as parameters, never hardcodes '8.1.1' or the D-05 predictor list, so Phase 6 can call with dep_var='2.3.1' unmodified"

requirements-completed: [INTERP-04, INTERP-05, INTERP-06, REPRO-02]

coverage:
  - id: D1
    description: "shap_analysis trains a RandomForestRegressor with n_jobs=1 and random_state=SEED and returns SHAP values of shape (n_samples, n_features) via shap.TreeExplainer"
    requirement: "INTERP-04"
    verification:
      - kind: unit
        ref: "tests/test_interpret.py#test_shap_values_shape"
        status: pass
    human_judgment: false
  - id: D2
    description: "The trained RF exposes a real-float oob_score_ as the INTERP-06 predictive reference metric (D-07: same RF, no separate GBM)"
    requirement: "INTERP-06"
    verification:
      - kind: unit
        ref: "tests/test_interpret.py#test_oob_score_present"
        status: pass
    human_judgment: false
  - id: D3
    description: "compute_vif_table returns a VIF table (statsmodels variance_inflation_factor) computed and reportable before SHAP output, all finite for a non-collinear fixture"
    requirement: "INTERP-04"
    verification:
      - kind: unit
        ref: "tests/test_interpret.py#test_vif_table"
        status: pass
    human_judgment: false
  - id: D4
    description: "Two RF trainings with the same seed and n_jobs=1 give identical feature_importances_/oob_score_ (REPRO-02, guards Pitfall #2's n_jobs=-1 non-determinism bug)"
    requirement: "REPRO-02"
    verification:
      - kind: unit
        ref: "tests/test_interpret.py#test_rf_determinism"
        status: pass
    human_judgment: false
  - id: D5
    description: "partial_dependence_plots produces PDP figures for the correlated predictors without any new dependency (INTERP-05, sklearn fallback, PyALE not installed)"
    requirement: "INTERP-05"
    verification:
      - kind: manual_procedural
        ref: "Manual smoke test run during Task 3 execution: interpret.partial_dependence_plots(rf, X, ['6.4.2', '6.4.1']) returns a PartialDependenceDisplay instance; no unit test in tests/test_interpret.py per plan's <behavior> spec"
        status: pass
    human_judgment: true
    rationale: "The plan's Task 1 <behavior> spec (RED phase) enumerates exactly four tests (shap_values_shape, oob_score_present, rf_determinism, vif_table) and does not include a dedicated unit test for partial_dependence_plots -- coverage for this deliverable is a manual smoke-test run plus full-suite pass, not an automated assertion, so verifier judgment is needed to confirm the plan's own test scope was followed."

# Metrics
duration: 5min
completed: 2026-07-12
status: complete
---

# Phase 4 Plan 2: RF + SHAP + VIF + PDP Interpretability Module Summary

**`src/interpret.py`: multivariate RandomForest (n_jobs=1, oob_score=True) feeding shap.TreeExplainer and sklearn PartialDependenceDisplay, preceded by a statsmodels VIF table -- zero new dependencies**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-07-12T18:48:44Z
- **Completed:** 2026-07-12T18:53:15Z
- **Tasks:** 3
- **Files modified:** 2 (both created: `src/interpret.py`, `tests/test_interpret.py`)

## Accomplishments
- `compute_vif_table()` reuses `statsmodels.stats.outliers_influence.variance_inflation_factor` (no hand-rolled VIF math) so INTERP-04's correlation-bias precedence check can run before SHAP output
- `shap_analysis()` trains one multivariate `RandomForestRegressor(n_estimators=300, random_state=seed, n_jobs=1, oob_score=True)` on complete-case rows (predictors: `6.4.2`, `6.4.1`, `8.2.1`, `is_ldc`, `is_lldc`, `is_sids`, one-hot `region` per D-05; `2.3.1` excluded per D-06), computes SHAP values via `shap.TreeExplainer`, and returns `(rf, shap_values, X, explainer)` so the Phase-4 notebook (Plan 03) can serialize the RF (D-08) and read `rf.oob_score_` for INTERP-06 (D-07 -- the SAME RF, no separate GBM)
- `n_jobs=1` enforced on the RF -- guards REPRO-02 against 04-RESEARCH.md's live-verified Pitfall #2 (`n_jobs=-1` breaks determinism even with a fixed `random_state`)
- `partial_dependence_plots()` renders PDP figures via `sklearn.inspection.PartialDependenceDisplay.from_estimator` -- the zero-new-dependency fallback for INTERP-05; `PyALE` (SUS-flagged in the Phase 4 legitimacy audit) was never installed, so no `checkpoint:human-verify` task was needed
- Four fixture-based unit tests (no real 171-country panel used, per Wave 0 requirement) prove SHAP output shape, `oob_score_` presence, RF determinism, and finite non-collinear VIFs; full test suite remains green at 92 tests with zero change to `requirements.txt`/`requirements.lock.txt`

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing unit tests for src/interpret.py** - `91ca5c6` (test)
2. **Task 2: Implement RF + SHAP + VIF in src/interpret.py** - `ad20892` (feat)
3. **Task 3: Implement partial-dependence plots in src/interpret.py** - `4d8bfba` (feat)

_Note: no deviations occurred, so no fix commits were needed beyond the three planned task commits._

## Files Created/Modified
- `src/interpret.py` - `compute_vif_table`, `shap_analysis`, `partial_dependence_plots` (all dependent-variable-agnostic, D-12)
- `tests/test_interpret.py` - fixture-based unit tests for `shap_analysis`/`compute_vif_table`, mirroring `tests/test_panel_base.py`'s conventions

## Decisions Made
- `partial_dependence_plots` implemented solely via `sklearn.inspection.PartialDependenceDisplay.from_estimator` -- `PyALE` (flagged `SUS` in 04-RESEARCH.md's Package Legitimacy Audit) was never installed; the RF's three numeric predictors are only weakly correlated globally (max |r|=0.09, VIF<2.2 per Phase 2's real numbers), which blunts PDP's documented correlated-feature bias concern for this specific dataset -- an honest, data-grounded rationale documented in the function's docstring rather than a blanket "PDP is always fine" claim.
- `shap_analysis` one-hot encodes only the `region` categorical column via `pd.get_dummies(..., columns=["region"], drop_first=True)` -- `is_ldc`/`is_lldc`/`is_sids` arrive as binary 0/1 flags already, requiring no encoding.

## Deviations from Plan

None - plan executed exactly as written. All four RED tests were written first and confirmed to fail only on `ImportError: cannot import name 'interpret' from 'src'` (collection error, not a partial/wrong-behavior failure), then made to pass incrementally across Tasks 2 and 3 with no auto-fixes needed.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. No new dependency was installed (INTERP-05 resolved with the already-pinned `scikit-learn` fallback).

## Next Phase Readiness
- `src/interpret.py` is ready for Plan 03's notebook (`4_1_interpretabilidad_simulacion.ipynb`) to orchestrate against the real `data/panel.db` panel_clean (complete-case ~3473 rows per 04-RESEARCH.md's live-verified estimate) and serialize `rf` to `data/modelos/rf_shap_model.pkl` (D-08)
- Phase 6 (Modelo 2) can call `shap_analysis`/`compute_vif_table`/`partial_dependence_plots` unmodified with `dep_var="2.3.1"` per D-12 -- no changes needed to this module
- `src/panel_base.py` remains untouched, and `requirements.txt`/`requirements.lock.txt` are unchanged, confirming both the parametric-reuse contract and the zero-new-dependency constraint held

---
*Phase: 04-interpretabilidad-simulaci-n-y-robustez*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: src/interpret.py
- FOUND: tests/test_interpret.py
- FOUND: .planning/phases/04-interpretabilidad-simulaci-n-y-robustez/04-02-SUMMARY.md
- FOUND commit: 91ca5c6 (test)
- FOUND commit: ad20892 (feat)
- FOUND commit: 4d8bfba (feat)
