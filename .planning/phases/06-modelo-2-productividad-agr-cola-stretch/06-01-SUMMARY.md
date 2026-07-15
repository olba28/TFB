---
phase: 06-modelo-2-productividad-agr-cola-stretch
plan: 01
subsystem: modeling
tags: [pandas, panel-data, testing, filtering]

# Dependency graph
requires:
  - phase: 03-modelo-1-regresion-de-panel-pib-per-capita
    provides: "src/panel_base.py (filter_by_exclusions, fit_panel_model, hausman_test, pesaran_cd_test, choose_cov_type), pytest fixture/test-style conventions in tests/test_panel_base.py"
provides:
  - "filter_by_min_years(df, dep_var, indep_vars, min_years=3) -- Model 2's own >=N-observed-years coverage criterion, computed on panel_clean without touching panel_exclusions"
affects: [06-modelo-2-productividad-agr-cola-stretch plan 02 (model2_agri.py)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sibling coverage-filter functions coexisting in panel_base.py (filter_by_exclusions for the 70%-of-years rule, filter_by_min_years for the >=N-years rule) -- neither wraps the other, both share the country-level all-or-nothing exclusion semantics"

key-files:
  created: []
  modified:
    - src/panel_base.py
    - tests/test_panel_base.py

key-decisions:
  - "filter_by_min_years coerces [dep_var, *indep_vars] via pd.to_numeric(errors=coerce) before the non-null test, matching _build_panel_index's numeric-coercion convention -- string-typed indicator columns from panel_clean are handled identically to the rest of the module"
  - "Consolidated the plan's 5th behavior (guard against panel_exclusions dependency) into the existing test_filter_by_min_years_default_is_three test via an inspect.signature assertion, keeping exactly 4 named tests per the plan's explicit acceptance criterion (4 new test_filter_by_min_years_* tests)"

patterns-established:
  - "New panel_base.py coverage helpers must be pure (no I/O, no warnings.warn for deterministic bookkeeping) and place their design-rationale citations (D-xx) in the docstring, consistent with the rest of the module"

requirements-completed: [MODEL2-01, MODEL2-02]

coverage:
  - id: D1
    description: "filter_by_min_years(df, dep_var, indep_vars, min_years=3) added to src/panel_base.py as a pure, non-wrapping sibling of filter_by_exclusions"
    requirement: "MODEL2-01"
    verification:
      - kind: unit
        ref: "tests/test_panel_base.py#test_filter_by_min_years_keeps_countries_at_or_above_threshold"
        status: pass
      - kind: unit
        ref: "tests/test_panel_base.py#test_filter_by_min_years_counts_only_all_vars_nonnull_years"
        status: pass
      - kind: unit
        ref: "tests/test_panel_base.py#test_filter_by_min_years_drops_country_fully"
        status: pass
      - kind: unit
        ref: "tests/test_panel_base.py#test_filter_by_min_years_default_is_three"
        status: pass
    human_judgment: false
  - id: D2
    description: "Live-verified on the real panel_clean table: filter_by_min_years(panel_clean, '2.3.1', ['6.4.2'], min_years=3) yields exactly 39 countries (D-01 acceptance number)"
    requirement: "MODEL2-02"
    verification:
      - kind: other
        ref: "python -c script against data/panel.db -> n_countries: 39"
        status: pass
    human_judgment: false

# Metrics
duration: 6min
completed: 2026-07-15
status: complete
---

# Phase 6 Plan 1: filter_by_min_years coverage helper Summary

**Added `filter_by_min_years` to `src/panel_base.py` -- a pure, country-level, >=N-observed-years coverage filter for Model 2's sparse 2.3.1 indicator, coexisting with (never wrapping) the existing 70%-of-years `filter_by_exclusions`.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-15T06:44:51Z
- **Completed:** 2026-07-15T06:50:11Z
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- Four failing `test_filter_by_min_years_*` tests written first (RED), confirmed to fail with `AttributeError` (function not yet implemented), not a collection error
- `filter_by_min_years(df, dep_var, indep_vars, min_years=3)` implemented as a pure sibling of `filter_by_exclusions` -- computes observed-year counts directly on the passed `panel_clean`-shaped `df` via `country_code` grouping, never touching `panel_exclusions`
- All 17 tests in `tests/test_panel_base.py` pass (13 pre-existing + 4 new); full project test suite (113 tests) passes with no regressions
- Live-verified against the real `data/panel.db`: `filter_by_min_years(panel_clean, "2.3.1", ["6.4.2"], min_years=3)` returns exactly 39 countries, matching D-01's documented figure

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for filter_by_min_years** - `b9a22d7` (test)
2. **Task 2: Implement filter_by_min_years in panel_base.py** - `ffd57f9` (feat)

_TDD RED -> GREEN gate confirmed: `b9a22d7` (test) precedes `ffd57f9` (feat) in git log; no REFACTOR commit was needed (implementation was already minimal and clean on the first pass)._

## Files Created/Modified
- `tests/test_panel_base.py` - Added `_make_sparse_panel` synthetic-panel builder and 4 `test_filter_by_min_years_*` tests covering threshold keep/drop, all-vars-non-null year counting, full country-level drop, and default `min_years=3` + signature guard
- `src/panel_base.py` - Added `filter_by_min_years(df, dep_var, indep_vars, min_years=3)`, placed immediately after `filter_by_exclusions`

## Decisions Made
- Coerced `[dep_var, *indep_vars]` columns via `pd.to_numeric(errors="coerce")` before the non-null test (matches `_build_panel_index`'s existing numeric-coercion convention, per the plan's explicit instruction) so string-typed indicator columns from the real `panel_clean` table are handled identically to the rest of the module.
- The plan enumerated exactly 4 named tests (`test_filter_by_min_years_keeps_countries_at_or_above_threshold`, `test_filter_by_min_years_counts_only_all_vars_nonnull_years`, `test_filter_by_min_years_drops_country_fully`, `test_filter_by_min_years_default_is_three`) and its acceptance criteria asserted "4 new `test_filter_by_min_years_*` tests" -- the 5th behavior described in `<behavior>` (guard against the function referencing a `panel_exclusions`-shaped frame) was folded into `test_filter_by_min_years_default_is_three` as an `inspect.signature` assertion rather than added as a separate 5th test, to keep the exact count the plan's acceptance criteria checks for.

## Deviations from Plan

None - plan executed exactly as written (the signature-guard consolidation above is a test-organization detail within the plan's own stated acceptance criteria, not a scope change).

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
`filter_by_min_years` is ready for direct use by plan 06-02's `model2_agri.py`, which will call `panel_base.filter_by_min_years(panel_clean, dep_var="2.3.1", indep_vars=["6.4.2"], min_years=3)` to build the 39-country Model 2 panel before `fit_panel_model`. No blockers.

---
*Phase: 06-modelo-2-productividad-agr-cola-stretch*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: src/panel_base.py
- FOUND: tests/test_panel_base.py
- FOUND: b9a22d7 (test commit)
- FOUND: ffd57f9 (feat commit)
