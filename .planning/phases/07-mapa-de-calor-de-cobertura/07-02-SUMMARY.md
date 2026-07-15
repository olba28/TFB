---
phase: 07-mapa-de-calor-de-cobertura
plan: 02
subsystem: visualization
tags: [matplotlib, seaborn, jupyter, coverage, heatmap, sqlite]

# Dependency graph
requires:
  - phase: 07-mapa-de-calor-de-cobertura (Plan 01)
    provides: "src/coverage.py::build_presence_matrix, ordered_countries_with_boundaries, INDICATOR_CODES, YEARS -- the pure pandas presence-matrix module this notebook orchestrates"
provides:
  - "notebook/7_1_mapa_calor_cobertura.ipynb -- D-05 reproducible entry point; loads raw_observations + country_reference, calls src.coverage for each of the 5 ODS indicators, renders the combined 1x5 heatmap grid, saves the PNG"
  - "figuras/07_mapa_calor_cobertura.png -- the single static coverage-heatmap PNG for the thesis annex (COVER-02), human-verified against all 4 Roadmap Success Criteria"
affects: [memoria annex figures, Phase 7 milestone close]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Thin orchestrator notebook pattern: all analytical logic lives in src/coverage.py (Plan 07-01); the notebook only loads, calls, plots, saves -- zero duplicated transform logic"
    - "Binary status ListedColormap (light gray / blue) for presence-absence, explicitly not a sequential Reds magnitude ramp, to avoid implying a false ordinal reading of a boolean state"

key-files:
  created:
    - notebook/7_1_mapa_calor_cobertura.ipynb
    - figuras/07_mapa_calor_cobertura.png
  modified: []

key-decisions:
  - "Figure sized around the real 8 SDG region distribution (sizes 4-49, 215 countries total) rather than the ~40-45/5-7 pre-verification estimate in 07-CONTEXT.md -- noted inline in the notebook"
  - "Leftmost subplot renders per-country y-tick labels at ~3.5-4pt targeting 300 DPI digital/PDF-zoom legibility, not physical print-page legibility (resolves 07-RESEARCH.md Open Question 2 / Assumption A3)"
  - "User approved the PNG against all 4 Roadmap Success Criteria at the Task 2 human-verify checkpoint with no requested changes"

patterns-established:
  - "Notebook-as-sole-entry-point (D-05): no CLI/script duplicate of the coverage heatmap generation exists or is planned"

requirements-completed: [COVER-02]

coverage:
  - id: D1
    description: "notebook/7_1_mapa_calor_cobertura.ipynb runs end-to-end via nbconvert with no cell error and produces exactly one PNG at figuras/07_mapa_calor_cobertura.png"
    requirement: "COVER-02"
    verification:
      - kind: automated_ui
        ref: "jupyter nbconvert --to notebook --execute notebook/7_1_mapa_calor_cobertura.ipynb (Task 1 verify step)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The PNG shows a grid of 5 labeled ODS-indicator sub-heatmaps (country x year, 2000-2022), grouped by SDG region with separator lines, binary Sin dato/Dato presente legend, and raw pre-filter coverage (not panel_clean-filtered)"
    requirement: "COVER-02"
    verification: []
    human_judgment: true
    rationale: "Visual/layout correctness against the 4 Roadmap Success Criteria requires human judgment of the rendered figure -- confirmed via the Task 2 checkpoint:human-verify gate, approved by the user ('APROVED') with all 4 criteria explicitly walked through and satisfied, including the raw-coverage sanity check (24,725 total cells / 16,834 present / 7,891 missing, matching the notebook's own live-computed cell)."

# Metrics
duration: 20min
completed: 2026-07-15
status: complete
---

# Phase 07 Plan 02: Coverage Heatmap Notebook and PNG Summary

**Thin-orchestrator Jupyter notebook rendering a 1x5 binary-status coverage heatmap (5 ODS indicators x country x year, region-grouped) from raw_observations, saved as a single 300 DPI PNG for the thesis annex — human-verified against all 4 Roadmap Success Criteria**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-15T19:23:29Z (approx, per STATE.md)
- **Completed:** 2026-07-15 (checkpoint approved same session)
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `notebook/7_1_mapa_calor_cobertura.ipynb` — thin orchestrator: PROJECT_ROOT/sys.path bootstrap, loads `raw_observations` + `country_reference` via `src.db.get_engine` with fixed-literal table names, calls `src.coverage.build_presence_matrix` once per ODS indicator (6.4.2, 6.4.1, 8.1.1, 8.2.1, 2.3.1) and `src.coverage.ordered_countries_with_boundaries` once, renders a 1x5 `sns.heatmap` grid with a binary `ListedColormap` (light gray = Sin dato, blue = Dato presente), region-separator `axhline`s (D-03), per-country y-tick labels on the leftmost subplot, and a shared figure legend + suptitle.
- `figuras/07_mapa_calor_cobertura.png` — single 300 DPI PNG, exactly one `plt.savefig` call, containing a raw-data sanity-check cell that reports 7,891 missing cells (matching 07-RESEARCH.md's live-verified count) confirming the figure reflects `raw_observations` coverage, not the Phase 2 70%-filtered `panel_clean`.
- Human-verify checkpoint (Task 2) walked through all 4 Roadmap Success Criteria against the rendered PNG and was approved by the user ("APROVED") with no requested changes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create and execute notebook/7_1_mapa_calor_cobertura.ipynb producing the single PNG** - `e95f296` (feat)
2. **Task 2: Human-verify the coverage-heatmap PNG against the 4 Roadmap Success Criteria** - checkpoint, no code changes; approved by user, no commit (verification-only task)

**Plan metadata:** (this commit) `docs(07-02): complete coverage heatmap notebook plan`

## Files Created/Modified
- `notebook/7_1_mapa_calor_cobertura.ipynb` - reproducible entry point loading raw_observations/country_reference, calling src.coverage, rendering and saving the 5-indicator coverage grid
- `figuras/07_mapa_calor_cobertura.png` - the single static PNG deliverable for the memoria annex (COVER-02)

## Decisions Made
- Figure sized around the real 8 SDG region distribution (sizes 4-49, 215 countries) rather than the smaller pre-verification estimate in 07-CONTEXT.md.
- Leftmost-subplot country labels tuned for 300 DPI digital/PDF-zoom legibility (not physical print-page legibility), resolving 07-RESEARCH.md's Open Question 2.
- Binary `ListedColormap` (gray/blue) chosen over a sequential `Reds` ramp to correctly represent a present/absent boolean state rather than implying a magnitude gradient.

## Deviations from Plan

None - plan executed exactly as written. Task 1 completed cleanly per its acceptance criteria (verified in the prior execution session: nbconvert ran clean, single PNG produced, zero `panel_clean`/`panel_exclusions` references, no `src/dashboard/`/`src/db.py`/`src/panel_build.py` modifications, five `build_presence_matrix` calls + one `ordered_countries_with_boundaries` call, exactly one `plt.savefig` at dpi=300). Task 2's checkpoint was approved by the user with no requested changes.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 07 (mapa-de-calor-de-cobertura) is now fully delivered: both plans (07-01: `src/coverage.py` module, 07-02: notebook + PNG) are complete, and the PNG has been human-approved against all 4 Roadmap Success Criteria.
- `figuras/07_mapa_calor_cobertura.png` is ready to be referenced in the memoria annex.
- No blockers. This closes the v1.1 "Coverage Heatmap" milestone's sole phase (EXTRA-01 deferred item, now delivered as COVER-01/COVER-02).

---
*Phase: 07-mapa-de-calor-de-cobertura*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: notebook/7_1_mapa_calor_cobertura.ipynb
- FOUND: figuras/07_mapa_calor_cobertura.png
- FOUND: .planning/phases/07-mapa-de-calor-de-cobertura/07-02-SUMMARY.md
- FOUND commit: e95f296 (Task 1)
