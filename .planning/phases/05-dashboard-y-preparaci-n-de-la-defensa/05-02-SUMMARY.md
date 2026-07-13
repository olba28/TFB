---
phase: 05-dashboard-y-preparaci-n-de-la-defensa
plan: 02
subsystem: ui
tags: [plotly, streamlit-free, pytest, dashboard-plots, tdd]

# Dependency graph
requires:
  - phase: 05-dashboard-y-preparaci-n-de-la-defensa
    provides: "05-01: src/dashboard/ package skeleton, tests/dashboard/conftest.py (tiny_panel_df fixture) -- foundation this plan builds figure builders on"
  - phase: 04-interpretabilidad-simulaci-n-y-robustez
    provides: "src/simulate.py (bootstrap_counterfactual output shape), src/interpret.py (partial_dependence_plots) -- consumed/delegated to by this plan's builders"
provides:
  - "src/dashboard/plots.py -- build_choropleth, build_scenario_plot, build_pdp: pure Plotly/Matplotlib figure builders, no st.* import"
  - "tests/dashboard/test_plots.py -- unit tests covering DASH-04 (animation + fixed color range) and the scenario/PDP builders"
affects: ["05-04 (Mapa tab consumes build_choropleth; Simulación tab consumes build_scenario_plot; SHAP tab consumes build_pdp)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure figure-builder pattern: DataFrame/result-dict in, plotly.graph_objects.Figure (or delegated display) out, no st.* call, no I/O -- mirrors src/panel_base.py's pure-vs-IO separation, extended to the dashboard layer"
    - "Fixed range_color computed once over the FULL year range before building an animated choropleth, to avoid Plotly Express's per-frame auto-scale (05-RESEARCH.md Pitfall 4)"
    - "Scenario-plot aggregation: central estimate = mean(effect_draws) across BOTH bootstrap replicas and surviving countries, giving one scalar per scenario; asymmetric error bars from the across-country mean of ci_2.5/ci_97.5"

key-files:
  created:
    - src/dashboard/plots.py
    - tests/dashboard/test_plots.py
  modified: []

key-decisions:
  - "build_scenario_plot's central estimate aggregates effect_draws across BOTH bootstrap replicas AND surviving countries into a single scalar per scenario (not per-country) -- consistent with the project's 'simulación de sensibilidad, no predicción por país' framing (matches Phase 4's INTERP-03 precedent); documented explicitly in the function's docstring as Claude's Discretion since the plan left the exact aggregation unspecified"
  - "test_plots_module_has_no_streamlit_import checks for the literal 'import streamlit'/'from streamlit' substrings, not the bare word 'streamlit' -- the bare-word check produced a false positive against plots.py's own module docstring, which legitimately says 'the Streamlit dashboard' in prose"

patterns-established:
  - "Pattern: dashboard figure builders never call st.* and never do I/O -- fully testable under plain pytest via tests/dashboard/conftest.py's tiny_panel_df fixture, extending the Phase 5 Wave 0 fixture convention to plots.py's test suite"

requirements-completed: [DASH-04]

coverage:
  - id: D4
    description: "build_choropleth returns an animated go.Figure covering 23 year-frames (2000-2022) with a coloraxis range fixed to the indicator's global min/max (not per-frame auto-scale) -- DASH-04, Pitfall 4"
    requirement: "DASH-04"
    verification:
      - kind: unit
        ref: "pytest tests/dashboard/test_plots.py::test_choropleth_has_all_years -x"
        status: pass
    human_judgment: false
  - id: D5
    description: "build_choropleth binds locations to country_code with locationmode=\"ISO-3\""
    verification:
      - kind: unit
        ref: "pytest tests/dashboard/test_plots.py::test_choropleth_uses_iso3_locationmode -x"
        status: pass
    human_judgment: false
  - id: D6
    description: "build_scenario_plot renders one point per scenario with asymmetric error bars from ci_2.5/ci_97.5, using the UI-SPEC accent color (#1B6CA8) for the central-estimate marker"
    verification:
      - kind: unit
        ref: "pytest tests/dashboard/test_plots.py::test_scenario_plot_has_ci_error_bars tests/dashboard/test_plots.py::test_scenario_plot_uses_accent_color -x"
        status: pass
    human_judgment: false
  - id: D7
    description: "build_pdp delegates to interpret.partial_dependence_plots without reimplementing PDP math"
    verification:
      - kind: unit
        ref: "pytest tests/dashboard/test_plots.py::test_build_pdp_delegates -x"
        status: pass
    human_judgment: false
  - id: D8
    description: "plots.py contains no Streamlit import (static guard)"
    verification:
      - kind: unit
        ref: "pytest tests/dashboard/test_plots.py::test_plots_module_has_no_streamlit_import -x"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-13
status: complete
---

# Phase 05 Plan 02: Dashboard Figure Builders Summary

**Pure, Streamlit-free Plotly builders (`build_choropleth`, `build_scenario_plot`, `build_pdp`) in `src/dashboard/plots.py`, isolating all figure construction — including DASH-04's animated, fixed-color-range choropleth — from Streamlit rendering.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-13T18:58:00Z (approx.)
- **Completed:** 2026-07-13T19:10:50Z
- **Tasks:** 3
- **Files modified:** 2 (both created)

## Accomplishments

- `src/dashboard/plots.py::build_choropleth(df, indicator_col, title)` — `px.choropleth` with `locationmode="ISO-3"`, `animation_frame="year"`, and `range_color` fixed to the indicator's global 2000–2022 min/max, so the color scale does not jump between animation frames (DASH-04, 05-RESEARCH.md Pitfall 4). UI-SPEC figure margins (`l=4, r=4, b=8, t=32`) applied via `update_layout`.
- `src/dashboard/plots.py::build_scenario_plot(results, title)` — consumes `simulate.bootstrap_counterfactual`'s output dict; plots one point per scenario with asymmetric error bars from `ci_2.5`/`ci_97.5`, using the UI-SPEC accent color `#1B6CA8` for the central-estimate marker. Central estimate and CI bounds are aggregated across both bootstrap replicas and surviving countries into a single scalar per scenario (documented aggregation choice, Claude's Discretion).
- `src/dashboard/plots.py::build_pdp(rf, X, features, ax=None)` — thin delegating wrapper over `interpret.partial_dependence_plots`, no PDP math reimplemented (INTERP-05).
- `tests/dashboard/test_plots.py` — 6 unit tests: `test_choropleth_has_all_years` (23-frame + fixed-range contract per VALIDATION.md's DASH-04 row), `test_choropleth_uses_iso3_locationmode`, `test_scenario_plot_has_ci_error_bars`, `test_scenario_plot_uses_accent_color`, `test_build_pdp_delegates` (monkeypatch-verified delegation), `test_plots_module_has_no_streamlit_import` (static purity guard).

## Task Commits

Each task was executed as a proper TDD RED→GREEN cycle, committed atomically:

1. **Task 1: build_choropleth (DASH-04)**
   - RED: `2c4b047` (test) — `test_choropleth_has_all_years`, `test_choropleth_uses_iso3_locationmode` written against a not-yet-existing `build_choropleth`; confirmed failing (`AttributeError`) before implementation.
   - GREEN: `a0716eb` (feat) — implemented `build_choropleth`; both tests pass.
2. **Task 2: build_scenario_plot + build_pdp**
   - RED: `c076623` (test) — `test_scenario_plot_has_ci_error_bars`, `test_scenario_plot_uses_accent_color`, `test_build_pdp_delegates` written; confirmed failing (3 failed, 2 prior passed) before implementation.
   - GREEN: `4c67e41` (feat) — implemented `build_scenario_plot` and `build_pdp`; all 5 tests pass.
3. **Task 3: Unit tests finalization (DASH-04)** — `f6310c0` (test) — added `test_plots_module_has_no_streamlit_import` static guard; full `tests/dashboard/test_plots.py` suite green (6/6); full repo suite green (98/98, no regression to Phases 1–4).

## Files Created/Modified

- `src/dashboard/plots.py` — `build_choropleth`, `build_scenario_plot`, `build_pdp`; pure functions, no `st.*` import, no I/O.
- `tests/dashboard/test_plots.py` — 6 unit tests using the `tiny_panel_df` fixture from `tests/dashboard/conftest.py` (never the real `data/panel.db`).

## Decisions Made

- `build_scenario_plot`'s central estimate aggregates `effect_draws` across BOTH bootstrap replicas AND surviving countries into a single scalar per scenario — not per-country — matching the project's "simulación de sensibilidad, no predicción por país" framing (Phase 4 INTERP-03 precedent). The plan left the exact aggregation mechanics to Claude's Discretion; documented explicitly in the function's docstring.
- The static no-Streamlit-import guard test checks for the literal substrings `"import streamlit"` / `"from streamlit"`, not the bare word `"streamlit"` — a bare-word check produced a false positive against `plots.py`'s own module docstring (which legitimately mentions "the Streamlit dashboard" in prose). Fixed during Task 3's GREEN run, before commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Static guard test false-positived on its own module docstring**
- **Found during:** Task 3 (writing `test_plots_module_has_no_streamlit_import`)
- **Issue:** A naive `"streamlit" not in source.lower()` check failed because `plots.py`'s own module docstring contains the prose phrase "the Streamlit dashboard" — not an import, but a legitimate description.
- **Fix:** Changed the assertion to check for the exact import-statement substrings (`"import streamlit"`, `"from streamlit"`) instead of the bare word.
- **Files modified:** `tests/dashboard/test_plots.py`
- **Commit:** `f6310c0`

No other deviations — the rest of the plan executed exactly as written. No auth gates, no architectural questions.

## Issues Encountered

None beyond the auto-fixed guard-test false positive documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `src/dashboard/plots.py`'s three builders are ready for `05-04`'s `app.py` to call directly: `build_choropleth` for the "Mapa e indicadores" tab (D-02's side-by-side comparison), `build_scenario_plot` for the "Simulación" tab, `build_pdp` for the "Interpretabilidad (SHAP)" tab.
- Full test suite (`pytest tests/ -q`) passes at 98/98 after this plan (92 prior + 6 new), confirming no regression to Phases 1–4 or Plan 05-01.
- `tests/dashboard/conftest.py`'s `tiny_panel_df` fixture proved sufficient for all of this plan's choropleth tests without modification — no parallel fixture set was created, per 05-01's guidance.

---
*Phase: 05-dashboard-y-preparaci-n-de-la-defensa*
*Completed: 2026-07-13*

## Self-Check: PASSED

All created files verified present on disk (src/dashboard/plots.py, tests/dashboard/test_plots.py, 05-02-SUMMARY.md). All 6 commits (2c4b047, a0716eb, c076623, 4c67e41, f6310c0, 1e6ce61) verified present in git log.
