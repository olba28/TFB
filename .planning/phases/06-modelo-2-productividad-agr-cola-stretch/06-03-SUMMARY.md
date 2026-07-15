---
phase: 06-modelo-2-productividad-agr-cola-stretch
plan: 03
subsystem: ui
tags: [streamlit, dashboard, model-registry, caching]

# Dependency graph
requires:
  - phase: 06-modelo-2-productividad-agr-cola-stretch plan 02
    provides: "data/modelos/model2_agri.pkl, data/modelos/rf_shap_model_m2.pkl -- Model 2's fitted PanelEffectsResults and SHAP RandomForest, referenced (not created) here"
  - phase: 05-dashboard-y-preparaci-n-de-la-defensa
    provides: "src/dashboard/{models,data,app}.py -- the ACTIVE_MODELS registry stub, cached loaders, and 4-tab app.py this plan completes/wires"
provides:
  - "models.ACTIVE_MODELS['Modelo 2 (Productividad agrícola)'] -- completed D-07 registry entry"
  - "data.cached_bootstrap/data.cached_shap active_model_name parameter -- makes the sidebar selection actually change which artifact loads"
  - "app.py sidebar st.sidebar.selectbox('Modelo activo', key='active_model_name') -- global model switch across all 4 tabs"
  - "D-08 reduced-coverage caption on all 4 tabs when Modelo 2 is active"
affects: [memoria write-up (dashboard screenshots for both models), any future phase touching src/dashboard/]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Registry-driven dashboard component extension: adding a second model required zero tab-body restructuring, only completing a dict entry + parameterizing two cached loaders (D-07's original design intent, now exercised end-to-end)"

key-files:
  created: []
  modified:
    - src/dashboard/models.py
    - src/dashboard/data.py
    - src/dashboard/app.py
    - tests/dashboard/test_app.py
    - tests/dashboard/test_caching.py

key-decisions:
  - "cached_bootstrap/cached_shap's new active_model_name parameter is placed after dep_var/indep_var (or dep_var/feature_vars) and before the existing tunable knobs (reduction_pcts/n_replicas/seed, explain_sample_size) -- matches the plan's specified signature order exactly"
  - "Both fake stand-ins in tests/dashboard/test_app.py (_fake_cached_bootstrap, _fake_cached_shap) were updated to accept active_model_name -- without this, app.py's new call sites would raise a TypeError silently swallowed by each tab's existing try/except -> st.error(ARTIFACT_ERROR_MSG), which would have hidden a real signature mismatch behind a passing at.exception assertion"

patterns-established:
  - "Sidebar selectbox key convention: key='active_model_name' matches the parameter name app.py passes downstream (data.cached_bootstrap/cached_shap), keeping the widget key and the propagated parameter name identical for easy tracing"

requirements-completed: [MODEL2-03]

coverage:
  - id: D1
    description: "models.ACTIVE_MODELS gains a complete Model 2 entry (dep_var=2.3.1, indep_var=6.4.2, feature_vars matching Model 1, pkl_path/rf_shap_pkl_path pointing at 06-02's artifacts) without touching the Model 1 entry"
    requirement: "MODEL2-03"
    verification:
      - kind: unit
        ref: "tests/dashboard/test_caching.py::test_cached_bootstrap_honors_active_model_name"
        status: pass
      - kind: other
        ref: "grep -n 'Modelo 2 (Productividad agrícola)' src/dashboard/models.py -> present with dep_var=2.3.1, pkl_path=data/modelos/model2_agri.pkl, rf_shap_pkl_path=data/modelos/rf_shap_model_m2.pkl, feature_vars identical 7-element list to Model 1"
        status: pass
    human_judgment: false
  - id: D2
    description: "data.cached_bootstrap/data.cached_shap require active_model_name: str and use it to index models.ACTIVE_MODELS instead of the hardcoded Modelo 1 literal (06-PATTERNS.md-flagged gap)"
    requirement: "MODEL2-03"
    verification:
      - kind: other
        ref: "grep -n 'ACTIVE_MODELS\\[\"Modelo 1' src/dashboard/data.py -> zero matches"
        status: pass
      - kind: unit
        ref: "tests/dashboard/test_caching.py::test_cached_bootstrap_honors_active_model_name"
        status: pass
    human_judgment: false
  - id: D3
    description: "app.py replaces the hardcoded ACTIVE_MODEL_NAME literal with st.sidebar.selectbox('Modelo activo', key='active_model_name'), placed before the 4 tabs; selection propagates globally without restructuring any tab"
    requirement: "MODEL2-03"
    verification:
      - kind: automated_ui
        ref: "tests/dashboard/test_app.py::test_active_model_selector_defaults_to_modelo_1"
        status: pass
      - kind: automated_ui
        ref: "tests/dashboard/test_app.py::test_side_by_side_comparison"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-08 reduced-coverage caption renders on all 4 tabs only when Modelo 2 is active, and never when Modelo 1 is active"
    requirement: "MODEL2-03"
    verification:
      - kind: automated_ui
        ref: "tests/dashboard/test_app.py::test_modelo_2_selection_shows_reduced_coverage_caption"
        status: pass
      - kind: automated_ui
        ref: "tests/dashboard/test_app.py::test_modelo_1_selection_never_shows_reduced_coverage_caption"
        status: pass
    human_judgment: false
  - id: D5
    description: "Mapa tab's fitted-values label and Simulación tab's chart title are dynamic (via ACTIVE_MODEL_NAME/models.INDICATOR_LABELS) instead of Model-1-hardcoded strings"
    requirement: "MODEL2-03"
    verification:
      - kind: other
        ref: "grep -n '\"Modelo 1: valores ajustados (8.1.1)\"' src/dashboard/app.py -> zero matches; grep -n '\"Efecto simulado del estrés hídrico sobre el crecimiento del PIB per cápita\"' src/dashboard/app.py -> zero matches"
        status: pass
    human_judgment: false

# Metrics
duration: ~9min
completed: 2026-07-15
status: complete
---

# Phase 6 Plan 3: Dashboard Model 2 selector wiring Summary

**Streamlit sidebar `st.sidebar.selectbox("Modelo activo", key="active_model_name")` switches all 4 dashboard tabs between Model 1 and Model 2, with `cached_bootstrap`/`cached_shap` now parameterized on `active_model_name` and a D-08 reduced-coverage caption rendered only for Model 2.**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-07-15T07:20:44Z
- **Completed:** 2026-07-15T07:29:16Z
- **Tasks:** 3 completed
- **Files modified:** 5

## Accomplishments
- `src/dashboard/models.py`'s `ACTIVE_MODELS` registry stub completed for Model 2 (dep_var=2.3.1, indep_var=6.4.2, same 7-element `feature_vars` as Model 1, `pkl_path="data/modelos/model2_agri.pkl"`, `rf_shap_pkl_path="data/modelos/rf_shap_model_m2.pkl"`) without touching the Model 1 entry (D-07)
- `src/dashboard/data.py`'s `cached_bootstrap`/`cached_shap` gained a required `active_model_name: str` parameter, replacing the hardcoded `models.ACTIVE_MODELS["Modelo 1 (PIB per cápita)"]` literal that 06-PATTERNS.md flagged as a silent no-op risk for the sidebar selector
- `src/dashboard/app.py`'s hardcoded `ACTIVE_MODEL_NAME = "Modelo 1 (PIB per cápita)"` replaced with `st.sidebar.selectbox("Modelo activo", list(models.ACTIVE_MODELS.keys()), key="active_model_name")`, placed before the 4 tabs; all 4 tabs (Mapa, Modelo, Simulación, SHAP) render the new `MODEL2_COVERAGE_CAPTION` at the top of their body only when Modelo 2 is active (D-08)
- Mapa tab's fitted-values overlay label and Simulación tab's chart title made dynamic via `ACTIVE_MODEL_NAME`/`models.INDICATOR_LABELS[ACTIVE_MODEL['dep_var']]`, closing the stale-Model-1-wording gap 06-PATTERNS.md flagged
- 5 new/updated tests: sidebar selector default + options assertion, D-08 caption present-for-Model-2/absent-for-Model-1 (both via `streamlit.testing.v1.AppTest`), and a `test_caching.py` unit test proving `cached_bootstrap`'s `active_model_name` parameter actually changes which `pkl_path` `data.load_model` is called with (not just that the registry entry exists) -- full project suite (122 tests) passes with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Complete the ACTIVE_MODELS registry stub and parameterize data.py's cached loaders** - `6eb4e5b` (feat)
2. **Task 2: Sidebar selector, reduced-coverage caption, and dynamic labels in app.py** - `8d09cf9` (feat)
3. **Task 3: AppTest coverage for the selector, caption, and cache-propagation across both models** - `a791e88` (test)

## Files Created/Modified
- `src/dashboard/models.py` - Completed the D-07 Model 2 registry entry (dep_var, indep_var, feature_vars, pkl_path, rf_shap_pkl_path)
- `src/dashboard/data.py` - `cached_bootstrap`/`cached_shap` now require `active_model_name: str`, indexing `models.ACTIVE_MODELS` with it instead of a hardcoded Model 1 literal
- `src/dashboard/app.py` - Sidebar `st.sidebar.selectbox` replaces the hardcoded `ACTIVE_MODEL_NAME`; `MODEL2_COVERAGE_CAPTION` constant added and rendered on all 4 tabs when Modelo 2 is active; Mapa/Simulación labels made dynamic; both `cached_bootstrap`/`cached_shap` call sites pass `active_model_name=ACTIVE_MODEL_NAME`
- `tests/dashboard/test_app.py` - Updated fake `cached_bootstrap`/`cached_shap` signatures to accept `active_model_name`; added 3 new AppTest-based tests for the selector and the D-08 caption
- `tests/dashboard/test_caching.py` - Added a unit test proving cache-propagation of `active_model_name` into `data.load_model`'s requested `pkl_path`

## Decisions Made
- `active_model_name` placed after `dep_var`/`indep_var` (or `dep_var`/`feature_vars`) and before the existing tunable knobs in both cached functions' signatures, matching the plan's specified parameter order exactly.
- Updated the pre-existing `_fake_cached_bootstrap`/`_fake_cached_shap` test stand-ins in `test_app.py` to accept `active_model_name` as part of Task 3 -- without this fix, Task 2's new call sites in `app.py` would raise a `TypeError` that each tab's existing `try/except -> st.error(ARTIFACT_ERROR_MSG)` would silently swallow, letting `test_side_by_side_comparison`'s `not at.exception` assertion pass while actually hiding a broken Simulación/SHAP tab behind an error caption. Verified this was the actual failure mode by inspection of the exception-handling structure before fixing it in Task 3, exactly as the plan intended (Task 3's `read_first` explicitly calls out that the fakes need `active_model_name`).

## Deviations from Plan

None - plan executed exactly as written. All 5 truths, all key_links, and all acceptance criteria across the 3 tasks were satisfied without needing any Rule 1-4 deviation.

## Issues Encountered

None. The full `tests/dashboard/` suite (21 tests) and the full project suite (122 tests) both pass with zero regressions after all 3 tasks.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

ROADMAP Phase 6 Success Criterion 3 is met: the dashboard, counterfactual simulation, and SHAP analysis all expose a working sidebar selector to explore Model 2 alongside Model 1, with Model 1's existing behavior fully preserved (verified by the passing suite) and Model 2's reduced coverage (39 vs. 171 countries) disclosed transparently on every tab per D-08. This completes Phase 6's final plan -- MODEL2-01, MODEL2-02, and MODEL2-03 are all closed across plans 06-01/06-02/06-03. No blockers for the memoria write-up (dashboard screenshots for both models can now be captured live via `streamlit run src/dashboard/app.py`).

---
*Phase: 06-modelo-2-productividad-agr-cola-stretch*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: src/dashboard/models.py
- FOUND: src/dashboard/data.py
- FOUND: src/dashboard/app.py
- FOUND: tests/dashboard/test_app.py
- FOUND: tests/dashboard/test_caching.py
- FOUND: 6eb4e5b (feat commit)
- FOUND: 8d09cf9 (feat commit)
- FOUND: a791e88 (test commit)
