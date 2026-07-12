---
phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita
fixed_at: 2026-07-12T15:45:00Z
review_path: .planning/phases/03-modelo-1-regresi-n-de-panel-pib-per-c-pita/03-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-07-12T15:45:00Z
**Source review:** .planning/phases/03-modelo-1-regresi-n-de-panel-pib-per-c-pita/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (fix_scope: critical_warning -- CR-01, WR-01, WR-02, WR-03; IN-01/IN-02 excluded by scope)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: `fit_panel_model`'s default `cov_type="clustered"` silently produces non-clustered (per-observation) standard errors

**Files modified:** `src/panel_base.py`
**Commit:** 0c7fdc6
**Applied fix:** When `cov_type == "clustered"` and no clustering config is
supplied, `fit_panel_model` now defaults `cov_config` to
`{"cluster_entity": True}` instead of silently letting `linearmodels`
degrade to `clusters = np.arange(nobs)` (i.e. per-observation/robust SEs).

**Numerical verification (required by task instructions, not just Tier
1/2 syntax checks):** reproduced the review's before/after behavior on
the same 10-entity/10-year synthetic panel used by the test suite.

```
default (post-fix) std err:       [0.05360098]
explicit cluster_entity=True:     [0.05360098]   <- matches
robust std err:                   [0.04990955]   <- no longer matches
```

Before the fix, the default matched the robust value (0.04990955,
per REVIEW.md CR-01); after the fix, the default matches the explicit
entity-clustered value (0.05360098) exactly. This confirms the fix
changes the actual computed standard errors, not just the code path
taken.

### WR-01: `hausman_test` has no guard against a negative (uninterpretable) test statistic

**Files modified:** `src/panel_base.py`
**Commit:** ad337df
**Applied fix:** Added an explicit `warnings.warn(...)` when the computed
Hausman statistic is negative, explaining that the classical chi2
approximation is invalid in that case (most likely because both sides
were fit with a non-classical robust/clustered/kernel covariance
estimator) and that the result should be treated as uninterpretable
rather than as evidence for H0. Applied verbatim from the review's
suggested fix; `test_hausman_test_falls_back_to_pinv_on_singular_var_diff`
(statistic == 0.0, not negative) continues to pass since no new warning
fires in that case.

### WR-02: `compare_specifications` fits `PooledOLS`/`RandomEffects` with no intercept term

**Files modified:** `src/panel_base.py`
**Commit:** 61b5f1d
**Applied fix:** Added an explicit `const=1.0` column (`exog_with_const =
exog.assign(const=1.0)`) and passed it to both `PooledOLS` and
`RandomEffects`; `PanelOLS` is left unchanged since its two-way
(entity + time) demeaning already absorbs any level shift. This matches
the review's suggested fix. Note: `hausman_test`'s existing docstring
already anticipated RE being fit with a `const` column not present in
FE's `params.index` (`common = fe_results.params.index`), so this change
does not affect Hausman-test correctness.

### WR-03: `pesaran_cd_test` divides by zero if fewer than 2 entities survive filtering

**Files modified:** `src/panel_base.py`
**Commit:** 079a6fe
**Applied fix:** Added a guard immediately after computing `n_entities =
wide.shape[1]` that raises `ValueError(f"pesaran_cd_test requires at
least 2 entities, got {n_entities}")` when `n_entities < 2`, replacing
the previous unguarded `ZeroDivisionError` with a clear, actionable
error message. Applied verbatim from the review's suggested fix.

## Skipped Issues

None — all in-scope findings were fixed.

## Verification

- Tier 1 (re-read modified sections): passed for all 4 fixes.
- Tier 2 (syntax check via `python -c "import ast; ast.parse(...)"`):
  passed for all 4 fixes.
- Full test suite (`.venv/Scripts/python.exe -m pytest tests/ -q`) after
  all 4 fixes: **84 passed** (matches the 84-passed baseline captured
  before any fix was applied — no regressions).
- CR-01 additionally received direct numerical before/after verification
  (see above) per explicit task instructions, since Tier 1/2 checks alone
  cannot confirm semantic/statistical correctness of a changed default.

---

_Fixed: 2026-07-12T15:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
