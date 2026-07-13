---
phase: 05-dashboard-y-preparaci-n-de-la-defensa
plan: 01
subsystem: ui
tags: [streamlit, plotly, sqlite, pytest, dashboard-foundation]

# Dependency graph
requires:
  - phase: 04-interpretabilidad-simulaci-n-y-robustez
    provides: "src/simulate.py, src/interpret.py, data/modelos/rf_shap_model.pkl -- parametric modules the dashboard will call in vivo (D-03) in later plans of this phase"
  - phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita
    provides: "src/panel_base.py, data/modelos/model1_gdp.pkl -- Model 1 artifacts the registry (models.py) points to"
provides:
  - "src/dashboard/ package skeleton (__init__.py)"
  - "src/dashboard/models.py -- ACTIVE_MODELS registry (D-07) and INDICATOR_LABELS"
  - ".streamlit/config.toml -- UI-SPEC theme (no [server] override, T-5-03)"
  - "tests/dashboard/conftest.py -- Wave 0 shared fixtures (tiny_panel_df, tiny_panel_engine, toy_model_pkl) for all subsequent dashboard plans"
affects: [05-02, 05-03, 05-04, 05-05, "06-modelo-2 (extends ACTIVE_MODELS)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Active-model registry: a single dict (ACTIVE_MODELS) keyed by display name, holding dep_var/indep_var/feature_vars/pkl_path -- every dashboard tab looks up its model here instead of hardcoding literals (D-07)"
    - "Streamlit theme declared exclusively via .streamlit/config.toml [theme] block -- no injected CSS/unsafe_allow_html anywhere in this phase"
    - "Dashboard test fixtures use real ISO3 country codes (not synthetic C00/C01 entity IDs) because Plotly's locationmode=\"ISO-3\" requires real codes to resolve on the choropleth"

key-files:
  created:
    - src/dashboard/__init__.py
    - src/dashboard/models.py
    - .streamlit/config.toml
    - tests/dashboard/__init__.py
    - tests/dashboard/conftest.py
  modified: []

key-decisions:
  - "ACTIVE_MODELS['Modelo 1 (PIB per cápita)']['feature_vars'] excludes indicator 2.3.1 (D-06, Phase 4) -- it is Model 2's own dependent variable, not a Model 1 predictor"
  - "tiny_panel_df fixture uses 4 real ISO3 codes (ESP/FRA/DEU/ITA) instead of synthetic entity IDs, departing from tests/test_simulate.py's f\"C{i:02d}\" convention, because Plotly locationmode=\"ISO-3\" needs real codes"
  - "One (country, year, indicator) cell (FRA, 2000, 2.3.1) is deliberately NaN in the fixture so no-data/gray-fill handling is exercised by every consumer, not just the all-finite case"

patterns-established:
  - "Pattern: Dashboard modules are pure Python (no st.* import) wherever they don't render UI -- models.py imports cleanly under plain pytest, verified by the Task 1 automated check"
  - "Pattern: tests/dashboard/conftest.py is the single source of synthetic panel/model fixtures for the whole phase -- later plans (05-02..05-04) must reuse these fixtures, not create parallel ones"

requirements-completed: [DASH-01]

coverage:
  - id: D1
    description: "src/dashboard/models.py exposes ACTIVE_MODELS with Model 1's dep_var/indep_var/feature_vars/pkl_path and INDICATOR_LABELS for all 5 ODS codes, importable without Streamlit"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "python -c import-and-assert check (05-01-PLAN.md Task 1 automated verify)"
        status: pass
    human_judgment: false
  - id: D2
    description: ".streamlit/config.toml declares the UI-SPEC theme palette with no [server] override (T-5-03 mitigation, localhost-only binding preserved)"
    verification:
      - kind: unit
        ref: "python -c tomllib parse-and-assert check (05-01-PLAN.md Task 2 automated verify)"
        status: pass
    human_judgment: false
  - id: D3
    description: "tests/dashboard/conftest.py provides tiny_panel_df/tiny_panel_engine/toy_model_pkl fixtures that never touch the real 215-country panel.db or production .pkl artifacts"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "pytest tests/dashboard -q (collection + throwaway fixture-exercise test, removed before commit per plan's Wave 0 intent)"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-13
status: complete
---

# Phase 05 Plan 01: Dashboard Foundation Summary

**Active-model registry (D-07), UI-SPEC Streamlit theme config, and Wave 0 pytest fixtures establishing `src/dashboard/` ahead of app/data/plots implementation.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-13T18:51:00Z (approx.)
- **Completed:** 2026-07-13T18:54:53Z
- **Tasks:** 3
- **Files modified:** 5 (all created, none modified)

## Accomplishments
- `src/dashboard/models.py`: single-source-of-truth `ACTIVE_MODELS` dict (Model 1: `dep_var="8.1.1"`, `indep_var="6.4.2"`, feature set excluding 2.3.1 per D-06, `pkl_path="data/modelos/model1_gdp.pkl"`) plus `INDICATOR_LABELS` for the 5 ODS codes — Phase 6 appends Model 2 as one dict entry without touching `app.py` (D-07).
- `.streamlit/config.toml`: UI-SPEC palette (`primaryColor #1B6CA8`, `backgroundColor #FFFFFF`, `secondaryBackgroundColor #EFF3F7`, `textColor #1A1A1A`) — the only theming mechanism for this phase, no `[server]` override (T-5-03).
- `tests/dashboard/conftest.py`: `tiny_panel_df` (4 ISO3 countries x 23 years x 5 indicators, one deliberate NaN cell), `tiny_panel_engine` (in-memory SQLite `panel_clean` + `panel_exclusions`), `toy_model_pkl` (tiny fitted `RandomForestRegressor` pickled to `tmp_path`) — shared Wave 0 infrastructure for every later dashboard test file.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/dashboard package + active-model registry (D-07)** - `4942a25` (feat)
2. **Task 2: Declare Streamlit theme in .streamlit/config.toml (UI-SPEC)** - `2b625a2` (feat)
3. **Task 3: Create shared dashboard test fixtures (Wave 0 infrastructure)** - `30e32c4` (test)

## Files Created/Modified
- `src/dashboard/__init__.py` - empty package marker for `src/dashboard/`
- `src/dashboard/models.py` - `ACTIVE_MODELS` registry (D-07) + `INDICATOR_LABELS`, pure config (no `streamlit` import)
- `.streamlit/config.toml` - `[theme]` block matching UI-SPEC, no `[server]` table
- `tests/dashboard/__init__.py` - empty test package marker
- `tests/dashboard/conftest.py` - `tiny_panel_df`/`tiny_panel_engine`/`toy_model_pkl` fixtures

## Decisions Made
- `feature_vars` for Model 1 in `ACTIVE_MODELS` mirrors `interpret.shap_analysis`'s D-05 predictor set exactly (`6.4.2, 6.4.1, 8.2.1, is_ldc, is_lldc, is_sids, region`), deliberately excluding `2.3.1` per D-06 (it is Model 2's dependent variable, not a Model 1 predictor).
- `tiny_panel_df` uses real ISO3 country codes (`ESP, FRA, DEU, ITA`) rather than the synthetic `f"C{i:02d}"` entity-naming convention used by `tests/test_simulate.py`/`tests/test_panel_base.py`, because Plotly's `locationmode="ISO-3"` (used by `plots.build_choropleth` in a later plan) requires real ISO3 codes to resolve on the map — a deliberate, necessary departure from the otherwise-mirrored fixture style.
- One cell (`FRA`, `2000`, `"2.3.1"`) is deliberately set to `NaN` in the fixture so downstream no-data/gray-fill handling is exercised by every fixture consumer by default, not left to each test to construct separately.

## Deviations from Plan

None - plan executed exactly as written. All three tasks' automated verify commands passed on first run; no auto-fixes, no architectural questions, no auth gates.

## Issues Encountered
A throwaway `tests/dashboard/test_zzz_fixture_check.py` file was created locally to exercise all three fixtures end-to-end (asserting exact row counts, year coverage, NaN presence, and pickle loadability) beyond what the plan's `pytest tests/dashboard -q` collection-only check covers. It passed (3/3) and was deleted before the Task 3 commit — not part of the plan's deliverables, purely a local correctness check during execution.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `src/dashboard/` package, `models.py` registry, and `.streamlit/config.toml` theme are in place for Plan 02 (`data.py` cached loaders, `plots.py` figure builders) to build on.
- `tests/dashboard/conftest.py` fixtures are ready for Plans 02-04's test files (`test_plots.py`, `test_caching.py`, `test_app.py`) to import directly — no parallel fixture set should be created.
- Full test suite (`pytest tests/ -q`) passes at 92/92 after this plan, confirming no regression to Phases 1-4's existing tests.

---
*Phase: 05-dashboard-y-preparaci-n-de-la-defensa*
*Completed: 2026-07-13*
