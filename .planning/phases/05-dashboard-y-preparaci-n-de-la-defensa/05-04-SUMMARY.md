---
phase: 05-dashboard-y-preparaci-n-de-la-defensa
plan: 04
subsystem: ui
tags: [streamlit, plotly, apptest, shap, dashboard-controller]

# Dependency graph
requires:
  - phase: 05-dashboard-y-preparaci-n-de-la-defensa
    provides: "05-01: src/dashboard/models.py (ACTIVE_MODELS/INDICATOR_LABELS), .streamlit/config.toml theme, tests/dashboard/conftest.py fixtures"
  - phase: 05-dashboard-y-preparaci-n-de-la-defensa
    provides: "05-02: src/dashboard/plots.py (build_choropleth, build_scenario_plot, build_pdp) -- pure Plotly builders consumed unmodified"
  - phase: 05-dashboard-y-preparaci-n-de-la-defensa
    provides: "05-03: src/dashboard/data.py cached loaders/wrappers (get_engine, load_panel_clean, load_model, cached_bootstrap, cached_shap) -- consumed unmodified"
provides:
  - "src/dashboard/app.py -- the Streamlit controller: wide layout, 4 D-06 tabs, side-by-side choropleth comparison (DASH-03/D-02), Modelo 1/Simulacion/SHAP tab wiring, cold-start timing, UI-SPEC artifact-error handling"
  - "tests/dashboard/test_app.py -- AppTest integration test (DASH-03) with monkeypatched loaders"
  - "tests/dashboard/test_no_live_api.py -- static no-live-API guard over src/dashboard/*.py (DASH-01)"
affects: ["05-05 (DASH-05 rehearsal/Plan B, formal manual smoke gate for this app.py)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Controller-only app.py: no pd.read_sql/pickle.load/px.*/go.* figure construction in the entry point -- all data access via data.py, all figure math via plots.py, all model config via models.py (05-PATTERNS.md D-06 controller separation)"
    - "Per-section try/except reusing a single ARTIFACT_ERROR_MSG constant (verbatim UI-SPEC copy) for CRITICAL artifact loads (top-level panel_clean, Modelo 1/Simulacion/SHAP tabs' pkl/compute loads); the Mapa tab's OPTIONAL Modelo-1-overlay pkl load uses a lighter inline st.caption fallback instead, since the tab's primary content (5 raw indicators) still renders fine without it"
    - "AppTest tests monkeypatch src.dashboard.data's module-level function objects (data.get_engine = ...) before .run() -- works because AppTest executes the script through the same sys.modules-cached data module the test imports, never re-fetching real panel.db/.pkl artifacts"

key-files:
  created:
    - src/dashboard/app.py
    - tests/dashboard/test_app.py
    - tests/dashboard/test_no_live_api.py
  modified: []

key-decisions:
  - "Model 1's fitted-values overlay in the Mapa tab is genuinely mappable (not a fallback-to-raw-series case): PanelEffectsResults.fitted_values is a DataFrame indexed by (country_code, year) with a single 'fitted_values' column -- confirmed live against the real model1_gdp.pkl -- so it merges directly onto panel_clean via a plain pandas merge in app.py (explicitly sanctioned by the plan's own action text: 'load via data.load_model + the fitted-values attribute ... joined back to country_code/year')"
  - "SHAP tab's VIF precedence caveat uses ALL 5 ODS indicator codes (models.INDICATOR_LABELS.keys()) as compute_vif_table's numeric_cols, not just the RF's 3 numeric predictor subset -- matches notebook/4_1_interpretabilidad_simulacion.ipynb cell 18's exact reproduction of Phase 2's committed global VIF numbers (INDICATOR_COLS = the 5 indicators), consistent with STATE.md's Phase-04-03 decision to match Phase 2 methodology exactly"
  - "st.metric's delta_color is set to 'off' for the Simulacion tab's per-scenario central estimates -- the delta shown is the bootstrap 95% CI range (not a directional increase/decrease vs. a prior value), so Streamlit's default red/green delta coloring would be misleading"
  - "Task 2's plan-specified verify command (pytest tests/dashboard/test_app.py -x -q) could not run as written because test_app.py is created in Task 3 -- substituted an ast-parse + full tests/dashboard -q run for Task 2's own verification, and ran the plan's literal command once test_app.py existed at the end of Task 3 (see Deviations)"

patterns-established:
  - "Pattern: any future dashboard tab that needs a critical (data-blocking) artifact reuses the module-level ARTIFACT_ERROR_MSG constant + the same try/except-then-st.error idiom, rather than composing a new error string per tab"

requirements-completed: [DASH-01, DASH-03]

coverage:
  - id: D14
    description: "app.py renders a wide-layout, single-page Streamlit app with the exact 4 D-06 tab labels (Mapa e indicadores, Modelo 1, Simulacion, Interpretabilidad (SHAP)), verified end-to-end via AppTest"
    requirement: "DASH-03"
    verification:
      - kind: integration
        ref: "tests/dashboard/test_app.py::test_side_by_side_comparison"
        status: pass
    human_judgment: false
  - id: D15
    description: "The Mapa e indicadores tab renders two independent choropleths in st.columns(2, gap='large') with distinct indicator_left/indicator_right selectbox keys and no DuplicateWidgetID (DASH-03/D-02)"
    requirement: "DASH-03"
    verification:
      - kind: integration
        ref: "tests/dashboard/test_app.py::test_side_by_side_comparison"
        status: pass
    human_judgment: false
  - id: D16
    description: "The app degrades gracefully with the verbatim UI-SPEC st.error copy (and st.stop()) when the top-level panel_clean load fails, instead of a raw traceback"
    verification:
      - kind: integration
        ref: "tests/dashboard/test_app.py::test_missing_panel_shows_ui_spec_error"
        status: pass
    human_judgment: false
  - id: D17
    description: "No source file under src/dashboard/ imports the UN SDG API client (src.ingesta), an HTTP client (requests/httpx/urllib.request), or references the UN SDG API host (unstats.un.org) -- static guard over every src/dashboard/*.py file"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "tests/dashboard/test_no_live_api.py::test_no_dashboard_module_imports_a_live_http_client_or_ingesta tests/dashboard/test_no_live_api.py::test_no_dashboard_module_references_the_un_sdg_api_host"
        status: pass
    human_judgment: false
  - id: D18
    description: "Modelo 1/Simulacion/Interpretabilidad(SHAP) tabs wire data.py's cached loaders and plots.py's pure builders (coefficient table, scenario plot + per-scenario st.metric, VIF caveat + SHAP summary plot) -- app.py itself contains no pd.read_sql/pickle.load/px.*/go.* construction"
    verification:
      - kind: unit
        ref: "grep -nE 'pd\\.read_sql|pickle\\.load|px\\.|go\\.Figure|go\\.Scatter|import requests|import httpx|src\\.ingesta' src/dashboard/app.py (no code match, only prose mention in module docstring, verified during execution)"
        status: pass
    human_judgment: false
  - id: D19
    description: "Manual DASH-05 rehearsal (streamlit run src/dashboard/app.py on real data, cold-cache timing, Plan B captures) -- explicitly deferred to Plan 05-05 per this plan's own <verification> note ('formal gate is 05-05')"
    human_judgment: true
    rationale: "Requires launching an interactive browser session against the real data/panel.db and production .pkl artifacts and visually confirming the render -- not automatable from this non-interactive executor context, and the plan itself defers this to 05-05"

# Metrics
duration: 25min
completed: 2026-07-13
status: complete
---

# Phase 05 Plan 04: Streamlit Dashboard Controller Summary

**`src/dashboard/app.py`, the single-page 4-tab Streamlit controller wiring `data.py`'s cached loaders + `plots.py`'s pure builders + `models.py`'s active-model registry into a wide-layout dashboard with side-by-side choropleth comparison (DASH-03/D-02), verified end-to-end via `AppTest` with no real `panel.db`/`.pkl` access.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-13T19:29:00Z (approx.)
- **Completed:** 2026-07-13T19:38:04Z
- **Tasks:** 3
- **Files modified:** 3 (all created)

## Accomplishments

- `src/dashboard/app.py`: `st.set_page_config(layout="wide")` once, verbatim UI-SPEC title/caption, the 4 D-06 tabs (`Mapa e indicadores`, `Modelo 1`, `Simulación`, `Interpretabilidad (SHAP)`), a top-level `data.get_engine()`/`data.load_panel_clean()` load wrapped in try/except emitting the verbatim UI-SPEC `st.error` + `st.stop()` on failure, and a `st.session_state`-gated cold-start timing readout in `st.sidebar.caption`.
- **Mapa e indicadores tab (DASH-03/D-02):** `st.columns(2, gap="large")` with two `st.selectbox`es (`key="indicator_left"`/`key="indicator_right"`) offering the 5 raw ODS indicators (`models.INDICATOR_LABELS`) plus a "Modelo 1: valores ajustados (8.1.1)" option built by merging `PanelEffectsResults.fitted_values` onto `panel_clean` on `(country_code, year)`; each column renders `plots.build_choropleth(...)` via `st.plotly_chart(..., use_container_width=True)` with the UI-SPEC no-data caption beneath.
- **Modelo 1 tab:** loads `model1_gdp.pkl` via `data.load_model` and renders a coefficient/diagnostic `st.dataframe` (coefficient, std error, 95% CI, p-value) plus an R²(within)/N caption.
- **Simulación tab:** `data.cached_bootstrap(dep_var="8.1.1", indep_var="6.4.2")` → `plots.build_scenario_plot` via `st.plotly_chart`, plus one `st.metric` per scenario (central estimate as value, bootstrap 95% CI range as `delta_color="off"` delta), framed explicitly as a sensitivity analysis, never a per-country prediction.
- **Interpretabilidad (SHAP) tab:** `interpret.compute_vif_table` over all 5 ODS indicators (reproducing Phase 2's exact global VIF, INTERP-04 precedence) shown as `st.dataframe`, followed by `data.cached_shap(...)` → `shap.summary_plot(..., show=False)` embedded via `st.pyplot` (SHAP's own palette, UI-SPEC exception) and the RF's OOB R² caption.
- `tests/dashboard/test_app.py`: `AppTest.from_file("src/dashboard/app.py")`-based `test_side_by_side_comparison` (DASH-03: monkeypatches `data.get_engine`/`load_panel_clean`/`load_model`/`cached_bootstrap`/`cached_shap`, asserts no exception, both selectbox keys present, exact 4 tab labels) and `test_missing_panel_shows_ui_spec_error` (asserts the verbatim UI-SPEC error text renders when the top-level load fails).
- `tests/dashboard/test_no_live_api.py`: two static-scan tests (DASH-01) asserting no `src/dashboard/*.py` file imports `requests`/`httpx`/`urllib.request`/`src.ingesta` or references the UN SDG API host (`unstats.un.org`).

## Task Commits

Each task was committed atomically:

1. **Task 1: App shell — page config, title, tabs, timing, error handling** - `1a57231` (feat)
2. **Task 2: Mapa e indicadores tab — side-by-side choropleths (DASH-03/D-02)** - `6df097b` (feat)
3. **Task 3: Modelo 1 / Simulación / SHAP tabs + AppTest + no-live-API guard** - `2b024a9` (feat)

## Files Created/Modified

- `src/dashboard/app.py` - Streamlit controller: layout/orchestration only, no data-access or figure math (delegated to `data.py`/`plots.py`/`models.py`).
- `tests/dashboard/test_app.py` - `AppTest` integration tests (DASH-03), monkeypatched loaders, never the real `data/panel.db`/production `.pkl`.
- `tests/dashboard/test_no_live_api.py` - static no-live-API guard (DASH-01) over every `src/dashboard/*.py` file.

## Decisions Made

- Model 1's fitted-values overlay for the Mapa tab is genuinely mappable — `PanelEffectsResults.fitted_values` (confirmed live against the real `model1_gdp.pkl`) is a DataFrame indexed by `(country_code, year)` with a single `fitted_values` column, so it merges directly onto `panel_clean`; no fallback-to-raw-series caveat was needed for this layer.
- The SHAP tab's VIF precedence check reproduces Phase 2's exact global VIF numbers by using all 5 ODS indicator codes as `compute_vif_table`'s `numeric_cols` (matching `notebook/4_1_interpretabilidad_simulacion.ipynb` cell 18's `INDICATOR_COLS`), not just the RF's own 3-predictor subset — consistent with the project's established "match Phase 2 methodology exactly" convention (STATE.md Phase-04-03 decision).
- `st.metric`'s `delta_color="off"` is used for the Simulación tab's scenario metrics because the "delta" shown is a bootstrap 95% CI range, not a directional change — Streamlit's default red/green coloring would misleadingly imply "better/worse."
- Critical artifact-load failures (top-level `panel_clean`, and each of the Modelo 1/Simulación/SHAP tabs' own `.pkl`/live-recompute loads) all reuse the single verbatim UI-SPEC `ARTIFACT_ERROR_MSG` constant via `st.error`. The Mapa tab's Modelo-1-fitted-values overlay is treated differently: it's an *optional* enhancement to a tab whose primary content (the 5 raw indicators) still renders correctly without it, so a failed overlay load falls back to a lighter inline `st.caption` rather than the full blocking error — showing the full UI-SPEC error there would misleadingly suggest the whole tab failed when only one selector option is unavailable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 2's plan-specified verify command referenced a test file created in Task 3**
- **Found during:** Task 2 (Mapa e indicadores tab)
- **Issue:** The plan's Task 2 `<verify>` block runs `pytest tests/dashboard/test_app.py -x -q`, but `tests/dashboard/test_app.py` is not created until Task 3 — running it as written at Task 2 would hard-fail with a file-not-found collection error, not a meaningful red/green signal.
- **Fix:** Substituted Task 2's own verification with `python -c "import ast; ast.parse(...)"` (confirms the file still parses) plus the existing `pytest tests/dashboard -q` suite (confirms no regression to Plans 05-01/05-02/05-03's tests), and additionally ran a throwaway (uncommitted) `AppTest` smoke script directly against the Mapa tab to confirm no exception and both selectbox keys present, before moving to Task 3. The plan's literal `pytest tests/dashboard/test_app.py -x -q` command was then run for real once Task 3 created that file, and passed.
- **Files modified:** None (verification-only adjustment, no source change).
- **Committed in:** N/A (verification step, not a code change) — confirmed again in `2b024a9`'s full-suite run.

---

**Total deviations:** 1 auto-fixed (1 blocking — verification-sequencing only, no code/behavior deviation).
**Impact on plan:** No scope creep; the plan's own Task 3 already anticipated and delivered exactly the test file Task 2's verify command was written against.

## Issues Encountered

None beyond the Task 2 verification-sequencing note documented above.

## User Setup Required

None — no external service configuration required. The plan's `<verification>` section explicitly defers the manual `streamlit run src/dashboard/app.py` smoke test and the DASH-05 rehearsal to Plan 05-05.

## Next Phase Readiness

- `src/dashboard/app.py` is feature-complete for DASH-01/DASH-02/DASH-03/DASH-04 (all consumed via the already-verified `data.py`/`plots.py` from 05-02/05-03) and ready for Plan 05-05's DASH-05 checkpoint: cold-cache rehearsal on the real `data/panel.db`/production `.pkl` artifacts and Plan B screenshot capture.
- Full test suite (`pytest tests/ -q`) passes at 109/109 after this plan (105 prior + 4 new: 2 in `test_app.py`, 2 in `test_no_live_api.py`), confirming no regression to Phases 1–4 or Plans 05-01/05-02/05-03.
- Model 2 (Phase 6) can add its `ACTIVE_MODELS` entry (`dep_var="2.3.1"`) and the Mapa/Modelo-1/Simulación/SHAP tabs will pick it up once a model selector is added — no `app.py` restructuring needed, per D-07's registry design (already validated end-to-end by this plan's tabs all reading `ACTIVE_MODEL` from the registry rather than hardcoded literals).

---
*Phase: 05-dashboard-y-preparaci-n-de-la-defensa*
*Completed: 2026-07-13*

## Self-Check: PASSED

All created files verified present on disk (src/dashboard/app.py, tests/dashboard/test_app.py, tests/dashboard/test_no_live_api.py, 05-04-SUMMARY.md). All 4 commits (1a57231, 6df097b, 2b024a9, b2a8b94) verified present in git log.
