---
phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita
plan: 01
subsystem: modeling
tags: [linearmodels, panel-data, fixed-effects, hausman-test, pesaran-cd-test, pytest]

# Dependency graph
requires:
  - phase: 02-construcci-n-del-panel-y-eda
    provides: panel_clean/panel_exclusions schema in data/panel.db (src/panel_build.py)
provides:
  - "src/panel_base.py: filter_by_exclusions, fit_panel_model, compare_specifications, hausman_test, pesaran_cd_test, choose_cov_type"
affects: [03-02 (live Model 1 fit), 06 (Model 2 -- reuses panel_base.py unmodified)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dependent-variable-agnostic panel-regression module (D-05) -- one shared src/panel_base.py for both Model 1 and Model 2, no duplication"
    - "Country-level (not row-level) exclusion filter mirroring PANEL-02's separation of panel_clean (never nulled) vs panel_exclusions (documented separately)"
    - "Manually-implemented Hausman/Pesaran diagnostic tests (neither linearmodels nor statsmodels provides them) with documented numerical-pathology fallbacks"

key-files:
  created:
    - src/panel_base.py
    - tests/test_panel_base.py
  modified: []

key-decisions:
  - "filter_by_exclusions reads only exclusions[country_code, indicator_code] -- country dropped entirely (all rows) if dep_var OR any indep_var is in exclusions for it, never a row-level NaN filter (D-01/D-02)"
  - "fit_panel_model does NOT call filter_by_exclusions internally -- caller passes an already-filtered df, keeping the fit function a thin, single-responsibility wrapper reusable by Model 2"
  - "compare_specifications fits Pooled/RE/FE all with cov_type=unadjusted -- SE methodology is fit_panel_model's separate concern"
  - "hausman_test restricts to fe_results.params.index (never RE's, which could include a const FE lacks) and falls back to numpy.linalg.pinv with an explicit warning on a singular var_diff"
  - "pesaran_cd_test's null-case test fixture uses entity_effects=True, time_effects=False (not the module's own two-way default) -- verified live that two-way FE residuals mechanically induce a small negative average pairwise cross-entity correlation (sum_i resid_it == 0 per period in a balanced panel, a known De Hoyos & Sarafidis 2006 time-demeaning artifact), which reliably makes the CD test reject at N=30/T=20 regardless of random seed and would test that mechanical artifact rather than the formula itself"
  - "choose_cov_type: alpha=0.05 threshold (Claude's Discretion per 03-CONTEXT.md), returns (\"kernel\", {\"kernel\": \"bartlett\"}) or (\"clustered\", {\"cluster_entity\": True})"

patterns-established:
  - "Synthetic-panel pytest fixtures via numpy.random.default_rng(seed) with an entity-level effect drawn independently of the regressor -- gives a clean, known-consistent null case for Hausman/Pesaran diagnostics"
  - "Hand-computable diagnostic-test fixtures (exact expected numeric result derived and verified independently, not just asserted qualitatively) for formulas with no reference library implementation to check against"

requirements-completed: [MODEL1-01, MODEL1-03, MODEL1-04]

coverage:
  - id: D1
    description: "filter_by_exclusions implements D-01/D-02's country-level (not row-level) coverage-exclusion rule"
    requirement: "MODEL1-01"
    verification:
      - kind: unit
        ref: "tests/test_panel_base.py#test_filter_by_exclusions_drops_full_country_not_row_level"
        status: pass
      - kind: unit
        ref: "tests/test_panel_base.py#test_filter_by_exclusions_keeps_surviving_countries_full_year_range"
        status: pass
      - kind: unit
        ref: "tests/test_panel_base.py#test_filter_by_exclusions_ignores_indicators_not_in_this_specification"
        status: pass
    human_judgment: false
  - id: D2
    description: "fit_panel_model implements D-05's exact parametric signature (dep_var/indep_vars/entity_effects/time_effects/cov_type-agnostic), builds the (country_code, year) MultiIndex internally, and its effects flags measurably change the fit"
    requirement: "MODEL1-01"
    verification:
      - kind: unit
        ref: "tests/test_panel_base.py#test_fit_panel_model_recovers_known_coefficient_sign_and_significance"
        status: pass
      - kind: unit
        ref: "tests/test_panel_base.py#test_fit_panel_model_effects_flags_change_the_fit"
        status: pass
      - kind: unit
        ref: "tests/test_panel_base.py#test_fit_panel_model_builds_index_internally_not_left_to_caller"
        status: pass
    human_judgment: false
  - id: D3
    description: "compare_specifications fits Pooled/RE/FE and returns linearmodels.panel.compare()'s side-by-side table, satisfying the pooled/RE/FE comparison half of MODEL1-03"
    requirement: "MODEL1-03"
    verification:
      - kind: unit
        ref: "tests/test_panel_base.py#test_compare_specifications_includes_all_three_estimators"
        status: pass
    human_judgment: false
  - id: D4
    description: "hausman_test: manually-implemented FE-vs-RE Hausman statistic (chi-squared), with a pinv fallback and explicit warning on a singular var_diff -- the diagnostic half of MODEL1-03"
    requirement: "MODEL1-03"
    verification:
      - kind: unit
        ref: "tests/test_panel_base.py#test_hausman_test_fails_to_reject_null_on_uncorrelated_entity_effect"
        status: pass
      - kind: unit
        ref: "tests/test_panel_base.py#test_hausman_test_falls_back_to_pinv_on_singular_var_diff"
        status: pass
    human_judgment: false
  - id: D5
    description: "pesaran_cd_test: manually-implemented cross-sectional-dependence statistic (standard normal), verified against a hand-computable 3-entity/3-period fixture (exact CD=-1.0) confirming unstack(level=0) is the correct MultiIndex level"
    requirement: "MODEL1-04"
    verification:
      - kind: unit
        ref: "tests/test_panel_base.py#test_pesaran_cd_test_hand_computable_fixture_returns_exact_expected_statistic"
        status: pass
      - kind: unit
        ref: "tests/test_panel_base.py#test_pesaran_cd_test_fails_to_reject_null_on_no_true_cross_sectional_dependence"
        status: pass
    human_judgment: false
  - id: D6
    description: "choose_cov_type implements the exact clustered-vs-Driscoll-Kraay decision rule MODEL1-04 requires (Pesaran p < 0.05 -> kernel/bartlett, else clustered/cluster_entity)"
    requirement: "MODEL1-04"
    verification:
      - kind: unit
        ref: "tests/test_panel_base.py#test_choose_cov_type_clustered_when_pesaran_does_not_reject"
        status: pass
      - kind: unit
        ref: "tests/test_panel_base.py#test_choose_cov_type_kernel_when_pesaran_rejects"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-12
status: complete
---

# Phase 3 Plan 1: Parametric Panel-Regression Module (panel_base.py) Summary

**`src/panel_base.py` -- a dependent-variable-agnostic PanelOLS fit/diagnose module with country-level coverage exclusion, pooled/RE/FE comparison, and manually-implemented Hausman + Pesaran CD diagnostic tests, unit-tested with 13 pytest tests including a hand-computable Pesaran fixture.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-12T00:00:00Z (approx, see git log timestamps)
- **Completed:** 2026-07-12
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `filter_by_exclusions` implements D-01/D-02's country-level exclusion rule exactly (a country is fully kept or fully dropped, never row-filtered)
- `fit_panel_model` is the D-05-mandated parametric entry point Model 1 (Plan 03-02) and Phase 6's future Model 2 will both call unmodified
- `compare_specifications` + `hausman_test` together produce the pooled/RE/FE comparison and Hausman statistic needed to justify the fixed-effects choice (MODEL1-03)
- `pesaran_cd_test` + `choose_cov_type` implement the clustered-vs-Driscoll-Kraay SE decision rule (MODEL1-04)
- 13 new pytest tests, all passing; full suite (84 tests) green with no regression

## Task Commits

Each task was committed atomically (both TDD: test-then-implementation within a single commit per task, mirroring the plan's `tdd="true"` flag):

1. **Task 1: Coverage-exclusion filter (D-01/D-02) and the parametric fit function (D-05)** - `ae7fca0` (feat)
2. **Task 2: Hausman test, Pesaran CD test, and the SE-type decision rule** - `a52dbcb` (feat)

**Plan metadata:** (this commit, made after this SUMMARY)

## Files Created/Modified
- `src/panel_base.py` - `filter_by_exclusions`, `fit_panel_model`, `compare_specifications`, `hausman_test`, `pesaran_cd_test`, `choose_cov_type` -- the full parametric panel-regression module Phase 3 and Phase 6 share
- `tests/test_panel_base.py` - 13 tests on synthetic panels: exclusion semantics, fit correctness/effects-flags, comparison table contents, Hausman null-case + pinv fallback, Pesaran hand-computable fixture + null-case, SE-choice decision rule

## Decisions Made
- `fit_panel_model` intentionally does NOT call `filter_by_exclusions` internally -- keeps it a thin, reusable wrapper; the caller (Plan 03-02's notebook) is responsible for the filter-then-fit sequence
- `hausman_test` restricts to `fe_results.params.index` (never RE's) since FE has no intercept -- this is the exact common-regressor set, robust regardless of whether RE/Pooled callers ever add an explicit constant column
- Pesaran CD test's null-case unit test uses `entity_effects=True, time_effects=False` residuals rather than the module's own two-way default -- see "Deviations from Plan" below for the full rationale; this is a test-design choice, not a change to `pesaran_cd_test`'s implementation itself (which is exactly the formula 03-RESEARCH.md Finding 2 specifies, verified independently against the hand-computable 3-entity fixture)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test-design bug, caught during TDD RED/GREEN] Pesaran CD null-case test needed entity-only-effects residuals, not two-way-effects residuals as originally planned**
- **Found during:** Task 2, writing the RED test for `pesaran_cd_test`'s null-hypothesis behavior
- **Issue:** The plan's `<action>` specified generating the null-case residuals from the same two-way (`entity_effects=True, time_effects=True`) FE spec `fit_panel_model` defaults to. Live testing across 20 random seeds at N=30/T=20 showed this **reliably rejects H0** (p in the 0.0014-0.0021 range, every single seed) -- not the "fails to reject, p > 0.05" qualitative outcome the plan's `<action>` and 03-RESEARCH.md Finding 2 (CD=-0.2814, p=0.778) both expected. Root cause: a two-way FE fit forces `sum_i(resid_it) == 0` within every period for a (near-)balanced panel -- a documented mechanical artifact of time-demeaning (De Hoyos & Sarafidis 2006) that induces a small negative average pairwise cross-entity correlation, unrelated to genuine cross-sectional dependence. This artifact scales with N and dominates the test statistic at N=30, meaning the original test design would have verified the mechanical artifact rather than the `pesaran_cd_test` formula's correctness.
- **Fix:** Generated the null-case residuals from an entity-effects-only FE fit (`entity_effects=True, time_effects=False`) instead. Verified across the same 20 seeds this reliably produces `p > 0.05` (typical range 0.26-0.99), correctly exercising the formula without the time-demeaning confound. `pesaran_cd_test`'s own implementation is unchanged from 03-RESEARCH.md Finding 2's exact formula -- this is a test-fixture correction, not an implementation change, and is independently corroborated by the hand-computable 3-entity fixture (exact `CD=-1.0`) passing without any adjustment.
- **Files modified:** `tests/test_panel_base.py` (one test function's fixture construction + docstring explaining the artifact)
- **Verification:** `.venv/Scripts/python.exe -m pytest tests/test_panel_base.py -q` -- all 13 tests pass; re-ran across the 20-seed sweep during investigation to confirm the fix is not seed-dependent luck
- **Committed in:** `a52dbcb` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (test-design correction, Rule 1)
**Impact on plan:** No change to `panel_base.py`'s public API or behavior -- `pesaran_cd_test` implements exactly the formula specified. This finding is worth flagging forward to Plan 03-02: when the live Model 1 notebook runs `pesaran_cd_test` on the real two-way-effects FE model's residuals (per D-03's base spec), a low p-value could reflect this same mechanical time-demeaning artifact rather than genuine cross-sectional dependence, and the notebook's interpretation/limitations section should account for that nuance when justifying the clustered-vs-Driscoll-Kraay SE choice.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `src/panel_base.py` is fully implemented, unit-tested (13/13 passing), and ready for Plan 03-02 to call against the real `data/panel.db` (`dep_var="8.1.1", indep_vars=["6.4.2"]`)
- Phase 6's future Model 2 can call the exact same module unmodified (`dep_var="2.3.1"`), satisfying MODEL2-01 by construction
- Flag for Plan 03-02's notebook: interpret the Pesaran CD test's result on the real two-way-effects model's residuals with the time-demeaning mechanical-artifact caveat above in mind, particularly given N=171 countries (03-RESEARCH.md Finding 4) is even larger than the N=30 synthetic case where the artifact was confirmed reliably significant

---
*Phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: src/panel_base.py
- FOUND: tests/test_panel_base.py
- FOUND: .planning/phases/03-modelo-1-regresi-n-de-panel-pib-per-c-pita/03-01-SUMMARY.md
- FOUND commit: ae7fca0 (Task 1)
- FOUND commit: a52dbcb (Task 2)
- FOUND commit: ee09315 (SUMMARY)
