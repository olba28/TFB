---
phase: 07-mapa-de-calor-de-cobertura
plan: 01
subsystem: data
tags: [pandas, pivot, reindex, sqlite, coverage, missingness]

# Dependency graph
requires:
  - phase: 02-construcción-del-panel-y-eda
    provides: country_reference table (region/subregion) and the pivot+reindex idiom established in panel_build.py::compute_coverage
provides:
  - "src/coverage.py::build_presence_matrix -- pure function, country x year presence/absence boolean grid per indicator (D-04)"
  - "src/coverage.py::ordered_countries_with_boundaries -- pure function, region-grouped country order + boundary indices (D-03)"
  - "src/coverage.py::INDICATOR_CODES / YEARS module constants"
  - "tests/test_coverage.py -- five passing COVER-01 unit tests"
affects: [07-02 (notebook orchestration/plotting), coverage heatmap PNG]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pivot()+reindex()+.notna() collapses 'row absent' and 'value IS NULL' into one missing state with zero per-cell branching (D-04)"
    - "region-sort + boundary-index walk for axhline separator positions (D-03)"

key-files:
  created:
    - src/coverage.py
    - tests/test_coverage.py
  modified: []

key-decisions:
  - "Docstrings in src/coverage.py and tests/test_coverage.py avoid the literal strings 'panel_clean'/'panel_exclusions'/'data/panel.db' (paraphrased as 'Phase 2's derived clean-panel table' / 'the real project database') so the plan's grep-based Pitfall-3 guard acceptance criteria return zero matches while still documenting the rationale"

patterns-established:
  - "src/coverage.py mirrors src/panel_build.py's exact module shape (docstring style, literal INDICATOR_CODES copy, pivot+reindex idiom) with no CLI entry point, per D-05 (notebook is the sole entry point)"

requirements-completed: [COVER-01]

coverage:
  - id: D1
    description: "build_presence_matrix treats a wholly-absent (country, year) row as missing"
    requirement: "COVER-01"
    verification:
      - kind: unit
        ref: "tests/test_coverage.py#test_build_presence_matrix_absent_row_is_missing"
        status: pass
    human_judgment: false
  - id: D2
    description: "build_presence_matrix treats a present row with value IS NULL as missing (same state as absent-row, D-04)"
    requirement: "COVER-01"
    verification:
      - kind: unit
        ref: "tests/test_coverage.py#test_build_presence_matrix_null_value_is_missing"
        status: pass
    human_judgment: false
  - id: D3
    description: "build_presence_matrix treats a present row with a non-null value as present"
    requirement: "COVER-01"
    verification:
      - kind: unit
        ref: "tests/test_coverage.py#test_build_presence_matrix_non_null_value_is_present"
        status: pass
    human_judgment: false
  - id: D4
    description: "ordered_countries_with_boundaries groups countries by region and returns correct boundary indices"
    requirement: "COVER-01"
    verification:
      - kind: unit
        ref: "tests/test_coverage.py#test_ordered_countries_with_boundaries_groups_by_region"
        status: pass
    human_judgment: false
  - id: D5
    description: "Coverage computation reads raw_observations/country_reference only, never Phase 2's derived clean-panel table"
    requirement: "COVER-01"
    verification:
      - kind: unit
        ref: "tests/test_coverage.py#test_coverage_module_never_reads_panel_clean"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-15
status: complete
---

# Phase 07 Plan 01: Coverage Presence-Matrix Module Summary

**`src/coverage.py` pure pandas pivot+reindex module (build_presence_matrix, ordered_countries_with_boundaries) plus five passing unit tests, proving D-04's unified missing-state logic and D-03's region grouping without ever touching Phase 2's filtered clean panel**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-15T19:06:00Z (approx)
- **Completed:** 2026-07-15T19:21:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `src/coverage.py::build_presence_matrix` — per-indicator country x year boolean presence grid via `pivot()` + `.reindex()` + `.notna()`; a wholly-absent row and a stored `value IS NULL` row both surface as `NaN` through the pivot+reindex mechanics, so a single `.notna()` unifies D-04's two missing-state cases with zero per-cell branching.
- `src/coverage.py::ordered_countries_with_boundaries` — restricts `country_reference` to the countries present in `raw_observations`, sorts by `(region, subregion, country_code)`, and returns the ordered country list plus the 0-based row indices where each region group starts (D-03, for `axhline` separators in Plan 07-02's notebook).
- `tests/test_coverage.py` — the five contract-named COVER-01 unit tests all pass, plus the full project test suite (137 tests) stays green with no regression.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/coverage.py with build_presence_matrix and ordered_countries_with_boundaries** - `b525880` (feat)
2. **Task 2: Create tests/test_coverage.py with the five COVER-01 unit tests** - `76adf03` (test)

_Note: Task 1 was marked `tdd="true"` in the plan, but its `<action>` is a direct pure-function build (its own test file is Task 2, not an interleaved RED/GREEN cycle within Task 1 itself) — both commits are `feat`/`test` per the plan's own task-type framing, matching the plan author's intended shape rather than a strict RED→GREEN→REFACTOR sequence._

## Files Created/Modified
- `src/coverage.py` - `build_presence_matrix`, `ordered_countries_with_boundaries`, `INDICATOR_CODES`, `YEARS`; no `panel_clean`/`panel_exclusions` reference, no CLI entry point
- `tests/test_coverage.py` - five COVER-01 unit tests using a `tmp_path`-backed SQLite engine fixture (never the real project database)

## Decisions Made
- Docstrings in both new files paraphrase references to Phase 2's derived clean-panel/exclusion tables and the real database filename (e.g. "Phase 2's derived clean-panel table", "the real project database") instead of using the literal strings `panel_clean`, `panel_exclusions`, `data/panel.db` — this was necessary because the plan's own acceptance criteria run a literal `grep` for those exact substrings and expect zero matches (the Pitfall-3 guard), and an earlier draft's explanatory prose (correctly describing what the module does NOT do) tripped that same grep. Functionality and rationale are unchanged; only the wording avoiding the literal guarded strings.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Docstring prose accidentally matched the plan's own grep-based negative-guard acceptance criteria**
- **Found during:** Task 1 and Task 2 (post-write acceptance-criteria verification)
- **Issue:** The module docstring's rationale for *why* `panel_clean`/`panel_exclusions` are never read literally contained those table names as substrings, and the test fixture's docstring literally contained `data/panel.db` — both intended as explanatory negatives, but the plan's acceptance criteria run a literal substring grep expecting zero matches.
- **Fix:** Reworded both docstrings to describe the same behavior without using the guarded literal strings (e.g. "Phase 2's derived clean-panel table", "the real project database").
- **Files modified:** `src/coverage.py`, `tests/test_coverage.py`
- **Verification:** `grep -n "panel_clean\|panel_exclusions" src/coverage.py` and `grep -n "data/panel.db" tests/test_coverage.py` both now return no matches; import and full test suite re-verified green after the edit.
- **Committed in:** `b525880` (Task 1), `76adf03` (Task 2) — fixed inline before each task's commit, not a separate commit.

---

**Total deviations:** 1 auto-fixed (1 bug/wording)
**Impact on plan:** No functional/logic change — a wording adjustment to satisfy the plan's own literal-grep acceptance criteria. No scope creep.

## Issues Encountered
- **Ruff not installed:** The plan's Task 1 acceptance criteria and the plan-level `<verification>` block both specify `.venv/Scripts/python.exe -m ruff check src/coverage.py [tests/test_coverage.py]`, but `ruff` is not installed as a Python package anywhere in this project (`requirements.txt`, `requirements-dev.txt`, and `.venv` all confirmed to lack it) — it is configured only as a VS Code editor extension (`charliermarsh.ruff`, per `CLAUDE.md`'s Code Style section: "Applied: Automatically on file save"), never as a CLI dependency, in any of the 6 prior phases. This is a pre-existing, project-wide environment gap unrelated to this plan's changes (out of scope per the deviation rules' Scope Boundary — it is not "directly caused by the current task's changes"), so it was not auto-installed (Rule 3's package-manager-install exclusion also applies: an unverified `pip install ruff` mid-task is exactly the kind of action that rule reserves for a `checkpoint:human-verify` gate, and this isn't blocking the task's actual deliverable). Both new files were manually reviewed for PEP 8 / project Code Style compliance (type hints on every signature, functions under 50 lines, `from __future__ import annotations`, snake_case, no mutable defaults) as a substitute check. Logged here rather than silently skipped.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `src/coverage.py`'s two pure functions and constants are ready for Plan 07-02's notebook (`notebook/7_1_mapa_calor_cobertura.ipynb`) to import and call for each of the 5 ODS indicators, building the 5-panel heatmap PNG (COVER-02).
- No blockers. One informational note for the phase owner: if a project-wide Ruff CLI dependency is desired going forward (beyond the VS Code extension), it should be added to `requirements-dev.txt` in a dedicated tooling task — out of scope for this plan.

---
*Phase: 07-mapa-de-calor-de-cobertura*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: src/coverage.py
- FOUND: tests/test_coverage.py
- FOUND: .planning/phases/07-mapa-de-calor-de-cobertura/07-01-SUMMARY.md
- FOUND commit: b525880 (Task 1)
- FOUND commit: 76adf03 (Task 2)
- FOUND commit: bb9ffb7 (docs: summary)
