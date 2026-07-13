---
phase: 05-dashboard-y-preparaci-n-de-la-defensa
plan: 03
subsystem: ui
tags: [streamlit, sqlalchemy, caching, pytest, dashboard-data-layer]

# Dependency graph
requires:
  - phase: 05-dashboard-y-preparaci-n-de-la-defensa
    provides: "05-01: src/dashboard/models.py (ACTIVE_MODELS registry), tests/dashboard/conftest.py (tiny_panel_engine, toy_model_pkl fixtures)"
  - phase: 04-interpretabilidad-simulaci-n-y-robustez
    provides: "src/simulate.py::bootstrap_counterfactual, src/interpret.py::shap_analysis -- called unmodified (D-03)"
  - phase: 01-ingesta-y-almacenamiento-versionado
    provides: "src/db.py::get_engine -- reused, not reimplemented"
provides:
  - "src/dashboard/data.py -- cached loaders (get_engine, load_panel_clean, load_panel_exclusions, load_model) and cached live-recompute wrappers (cached_bootstrap, cached_shap)"
  - "tests/dashboard/test_caching.py -- unit tests asserting the st.cache_resource/st.cache_data contract"
affects: ["05-04 (app.py tabs consume data.py's loaders/wrappers)", "05-05", "06-modelo-2 (cached_bootstrap/cached_shap already generic in dep_var/feature_vars)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "st.cache_resource for shared/non-copyable objects (Engine, fitted model); st.cache_data for copyable results (DataFrames, bootstrap/SHAP arrays) -- the central caching split from 05-RESEARCH.md Pattern 1"
    - "Cached live-recompute wrappers never receive a non-hashable Engine/model as an argument -- they call get_engine()/load_model() internally (05-RESEARCH.md Pattern 5)"
    - "Streamlit cache-decorator verification via CachedFunc._info.cache_type (streamlit.runtime.caching.cache_utils/cache_type) instead of wall-clock timing, per 05-VALIDATION.md's DASH-02 row"

key-files:
  created:
    - src/dashboard/data.py
    - tests/dashboard/test_caching.py
  modified: []

key-decisions:
  - "Tasks 1 and 2 (loaders, then live-recompute wrappers) were committed as a single atomic commit rather than two, since both build the same src/dashboard/data.py file and the plan's own verify command (pytest tests/dashboard/test_caching.py) only exists once both are present -- an intermediate loaders-only commit would not be independently testable against the plan's task-3 test file"
  - "cached_bootstrap's n_replicas defaults to 200 (not simulate.py's production default of 1000) purely as a demo-runtime knob documented in the docstring -- the underlying bootstrap methodology in simulate.py is unchanged (D-03 explicit requirement)"

patterns-established:
  - "Pattern: any future cached live-recompute wrapper (e.g. Phase 6's Model 2 equivalents) loads Engine/model internally via get_engine()/load_model(), never as a function argument"

requirements-completed: [DASH-01, DASH-02]

coverage:
  - id: D9
    description: "data.get_engine and data.load_model are st.cache_resource-wrapped; data.load_panel_clean, data.load_panel_exclusions, data.cached_bootstrap, data.cached_shap are st.cache_data-wrapped"
    requirement: "DASH-02"
    verification:
      - kind: unit
        ref: "pytest tests/dashboard/test_caching.py::test_get_engine_and_load_model_are_cache_resource tests/dashboard/test_caching.py::test_loaders_and_compute_wrappers_are_cache_data -x"
        status: pass
    human_judgment: false
  - id: D10
    description: "load_panel_clean/load_panel_exclusions take a leading-underscore _engine parameter so Streamlit excludes the non-hashable Engine from the cache key"
    verification:
      - kind: unit
        ref: "pytest tests/dashboard/test_caching.py::test_load_panel_clean_takes_underscore_prefixed_engine_param -x"
        status: pass
    human_judgment: false
  - id: D11
    description: "cached_bootstrap/cached_shap take no Engine/model/fitted parameter -- they load both internally via get_engine/load_model (D-03, RESEARCH Pattern 5)"
    verification:
      - kind: unit
        ref: "pytest tests/dashboard/test_caching.py::test_cached_bootstrap_and_cached_shap_take_no_engine_or_model_param -x"
        status: pass
    human_judgment: false
  - id: D12
    description: "load_panel_clean returns a non-empty DataFrame with the 5 indicator columns when loaded from the in-memory fixture engine (never real panel.db); load_panel_exclusions and load_model also functionally verified against fixtures"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "pytest tests/dashboard/test_caching.py::test_load_panel_clean_returns_indicator_columns tests/dashboard/test_caching.py::test_load_panel_exclusions_returns_dataframe tests/dashboard/test_caching.py::test_load_model_loads_toy_pickle -x"
        status: pass
    human_judgment: false
  - id: D13
    description: "src/dashboard/data.py imports neither requests/httpx nor src.ingesta anywhere -- static grep check, no live UN SDG API call in the data layer"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "grep -nE \"^import (requests|httpx)|^from (requests|httpx|src\\.ingesta)\" src/dashboard/data.py (no match, verified during execution)"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-13
status: complete
---

# Phase 05 Plan 03: Dashboard Cached Data-Access Layer Summary

**`src/dashboard/data.py` implements the full `st.cache_resource`/`st.cache_data` split (DASH-02) for Engine/model loaders and live-recomputed bootstrap/SHAP wrappers, reading only local `panel.db`/`.pkl` artifacts (DASH-01) — proven by `tests/dashboard/test_caching.py` inspecting Streamlit's own cache-decorator metadata rather than timing.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-13T19:16:00Z (approx.)
- **Completed:** 2026-07-13T19:21:04Z
- **Tasks:** 3 (loaders + wrappers committed together, tests committed separately — see Decisions)
- **Files modified:** 2 (both created)

## Accomplishments

- `src/dashboard/data.py::get_engine()` (`@st.cache_resource`) wraps `db.get_engine("data/panel.db")` unmodified — the single reused SQLAlchemy connection (DASH-01).
- `load_panel_clean(_engine)`/`load_panel_exclusions(_engine)` (`@st.cache_data`) read `panel_clean`/`panel_exclusions` via fixed-literal `SELECT * FROM ...` strings, with a leading-underscore `_engine` param excluding the non-hashable Engine from Streamlit's cache key (RESEARCH Pitfall 2). `load_panel_clean` warns (`UserWarning`) if the result is empty, matching the project's warn-don't-hide convention.
- `load_model(pkl_path)` (`@st.cache_resource`) deserializes a project-produced `.pkl` (T-5-02) — no `st.file_uploader` for `.pkl` anywhere in this phase.
- `cached_bootstrap(dep_var, indep_var, reduction_pcts=(-0.10,-0.20,-0.30), n_replicas=200, seed=42)` (`@st.cache_data`) loads Engine/Model 1's fitted results internally via `get_engine()`/`load_model()` and calls `simulate.bootstrap_counterfactual` unmodified (D-03) — `reduction_pcts` accepted as a hashable tuple, converted to a list before delegating. `n_replicas` defaults to 200 (a demo-runtime knob, not a methodology change — documented in the docstring) versus `simulate.py`'s own production default of 1000.
- `cached_shap(dep_var, feature_vars)` (`@st.cache_data`) loads Engine/panel data internally and calls `interpret.shap_analysis` unmodified (D-03) — `feature_vars` accepted as a hashable tuple.
- `tests/dashboard/test_caching.py` — 7 unit tests: cache-type assertions (via `CachedFunc._info.cache_type`) for all six loaders/wrappers, underscore-prefix signature checks, no-engine/model-param checks on the cached-compute wrappers, and three functional checks against the `tiny_panel_engine`/`toy_model_pkl` fixtures from 05-01's `conftest.py`.

## Task Commits

1. **Task 1 + Task 2: Cached loaders (Engine/panel tables/model) + cached live-recompute wrappers (bootstrap/SHAP)** — `d553737` (feat). Both tasks build the same `src/dashboard/data.py` file incrementally per the plan; committed together since an intermediate loaders-only state is not independently testable against the plan's own `test_caching.py` verify command (see Decisions).
2. **Task 3: test_caching.py — verify cache decorators + reuse (DASH-02)** — `bf28c6b` (test).

## Files Created/Modified

- `src/dashboard/data.py` — cached loaders (`get_engine`, `load_panel_clean`, `load_panel_exclusions`, `load_model`) + cached live-recompute wrappers (`cached_bootstrap`, `cached_shap`); no `requests`/`httpx`/`src.ingesta` import.
- `tests/dashboard/test_caching.py` — 7 unit tests using `tests/dashboard/conftest.py`'s `tiny_panel_engine`/`toy_model_pkl` fixtures, never the real `data/panel.db`/production `.pkl`.

## Decisions Made

- Discovered live that Streamlit's `st.cache_data`/`st.cache_resource` decorators wrap the function in a `streamlit.runtime.caching.cache_utils.CachedFunc` instance exposing `._info.cache_type` (a `CacheType.DATA`/`CacheType.RESOURCE` enum) — used this as the authoritative, non-timing-based verification mechanism the plan's `<action>` section asked for ("inspecting the wrapper attributes Streamlit's cache decorators attach").
- Tasks 1 and 2 were committed as a single atomic commit (`d553737`) rather than two separate commits, because both add code to the same `src/dashboard/data.py` file and the plan's own automated verify command (`pytest tests/dashboard/test_caching.py`) requires both the loaders and the wrappers to exist simultaneously — an intermediate "loaders only" commit would fail that same verify command the plan attaches to Task 1. Task 3 (the test file itself) was committed separately as planned.
- `cached_bootstrap` accepts `fitted_results` implicitly by loading it via `load_model` before calling `simulate.bootstrap_counterfactual(fitted, df, ...)` — matching `bootstrap_counterfactual`'s own documented API-symmetry note ("fitted_results ... accepted for API symmetry ... not itself refit here").

## Deviations from Plan

None — plan executed exactly as written. All three tasks' automated verify commands (`pytest tests/dashboard/test_caching.py -x -q`) passed on first run; no auto-fixes, no architectural questions, no auth gates. Confirmed via static grep that `data.py` imports neither `requests`/`httpx` nor `src.ingesta`, and via `git diff --stat`/`git status` that `src/simulate.py`/`src/interpret.py` were not modified.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `src/dashboard/data.py`'s six loaders/wrappers are ready for `05-04`'s `app.py` to call directly across all four tabs ("Mapa e indicadores" via `get_engine`/`load_panel_clean`; "Modelo 1" via `load_model`; "Simulación" via `cached_bootstrap`; "Interpretabilidad (SHAP)" via `cached_shap`).
- Full test suite (`pytest tests/ -q`) passes at 105/105 after this plan (98 prior + 7 new), confirming no regression to Phases 1–4 or Plans 05-01/05-02.
- `tests/dashboard/conftest.py`'s `tiny_panel_engine`/`toy_model_pkl` fixtures proved sufficient for all of this plan's tests without modification — no parallel fixture set was created.

---
*Phase: 05-dashboard-y-preparaci-n-de-la-defensa*
*Completed: 2026-07-13*

## Self-Check: PASSED

All created files verified present on disk (src/dashboard/data.py, tests/dashboard/test_caching.py, 05-03-SUMMARY.md). Both commits (d553737, bf28c6b) verified present in git log.
