---
phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita
reviewed: 2026-07-12T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/panel_base.py
  - tests/test_panel_base.py
  - notebook/3_1_modelo1_pib.ipynb
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-07-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed `src/panel_base.py`, `tests/test_panel_base.py`, and
`notebook/3_1_modelo1_pib.ipynb` at standard depth, with extra scrutiny on
the manually-coded `hausman_test` and `pesaran_cd_test` functions (no
library backstop for either) and on whether the notebook uses a consistent
covariance type on both sides of its Hausman comparison.

The notebook's Hausman comparison is correctly consistent: both
`final_fe_results` (cell 6) and `hausman_re_results` (cell 8) are fit with
the same `chosen_cov_type`/`chosen_cov_config` selected by
`choose_cov_type`, and this is verified against live output (`cov_type=
"kernel"` on both sides, H=0.2566, df=1, p=0.6125). That specific
requirement holds.

However, direct execution of `fit_panel_model` against the same synthetic
panel used in the test suite surfaces a real defect: the function's own
default (`cov_type="clustered"` with no default cluster configuration)
silently computes heteroskedasticity-robust standard errors that are
**not** clustered by entity at all -- identical to `cov_type="robust"`,
and measurably different from the entity-clustered result the parameter
name implies (0.049910 vs. 0.053601 in a controlled comparison, see
CR-01). Because this module is explicitly designed to be reused
unmodified by Model 2 (Phase 6, D-05), and three of the tests in
`tests/test_panel_base.py` exercise exactly this silently-wrong default
without asserting anything about the resulting standard errors, this is a
live trap for any future caller who omits `cluster_entity=True`.

Two further statistical-correctness gaps were found in the manually-coded
tests themselves: `hausman_test` has no guard against a negative test
statistic (a well-documented possibility whenever `Var(FE) - Var(RE)` is
not positive semi-definite, which is exactly the situation this codebase
creates by design when it fits both sides with non-classical robust/
clustered/kernel covariance types -- see CR/WR discussion below), and
`compare_specifications` fits `PooledOLS` with no intercept term, which
(unlike `RandomEffects`'s quasi-demeaning or `PanelOLS`'s exact demeaning)
forces the pooled regression through the origin.

## Critical Issues

### CR-01: `fit_panel_model`'s default `cov_type="clustered"` silently produces non-clustered (per-observation) standard errors

**File:** `src/panel_base.py:77-94`
**Issue:** `fit_panel_model` defaults to `cov_type="clustered"` but supplies
no default clustering configuration (`cluster_entity`, `cluster_time`, or
`clusters`). `linearmodels`'s `ClusteredCovariance` falls back to
`clusters = np.arange(nobs)` when none is supplied -- i.e., every
observation is its own cluster, which is mathematically identical to
`cov_type="robust"` (heteroskedasticity-robust/White SEs), **not**
entity-clustered SEs. Verified empirically on a 10-entity/10-year synthetic
panel identical in shape to the test fixtures:

```
default clustered (no config) std err: [0.04990955]
robust std err:                        [0.04990955]   <- identical
clustered by entity std err:           [0.05360098]   <- actually different
```

Three tests in `tests/test_panel_base.py`
(`test_fit_panel_model_recovers_known_coefficient_sign_and_significance`,
`test_fit_panel_model_effects_flags_change_the_fit`,
`test_fit_panel_model_builds_index_internally_not_left_to_caller`) call
`fit_panel_model(df, DEP_VAR, INDEP_VARS)` with no `cov_type`/`cov_config`
override, so this silently-wrong default is exercised by the suite but
never actually checked. The live notebook happens to always pass an
explicit `cov_config` (cell 5's provisional fit passes
`cluster_entity=True`; cells 6/12 pass `chosen_cov_type`/`chosen_cov_config`
from `choose_cov_type`), so Model 1's reported results are not affected --
but `panel_base.py` is explicitly documented (module docstring, D-05) as
the unmodified shared entry point Model 2 (Phase 6) will call directly.
Any future call of `fit_panel_model(df, dep_var, indep_vars)` without an
explicit `cluster_entity=True` will silently report standard errors/
p-values under a misleading label ("clustered"), which is exactly the kind
of silent statistical-inference error that matters for a thesis defended
before an academic tribunal.

**Fix:** Either supply a sensible default clustering config when
`cov_type == "clustered"` and none was given, or fail loudly instead of
silently degrading:

```python
def fit_panel_model(
    df: pd.DataFrame,
    dep_var: str,
    indep_vars: list[str],
    entity_effects: bool = True,
    time_effects: bool = True,
    cov_type: str = "clustered",
    **cov_config: Any,
) -> PanelEffectsResults:
    indexed = _build_panel_index(df, dep_var, indep_vars)
    if cov_type == "clustered" and not cov_config:
        # linearmodels silently degrades an unconfigured "clustered" to a
        # per-observation (i.e. plain "robust") covariance -- make the
        # entity-clustering intent explicit rather than relying on that
        # fallback.
        cov_config = {"cluster_entity": True}
    model = PanelOLS(
        indexed[dep_var],
        indexed[indep_vars],
        entity_effects=entity_effects,
        time_effects=time_effects,
    )
    return model.fit(cov_type=cov_type, **cov_config)
```

## Warnings

### WR-01: `hausman_test` has no guard against a negative (uninterpretable) test statistic

**File:** `src/panel_base.py:147-160`
**Issue:** The classic Hausman statistic `H = diff' * inv(Var(FE)-Var(RE)) * diff`
is only guaranteed non-negative when `Var(FE) - Var(RE)` is positive
semi-definite, which itself is only guaranteed under the classical
Hausman assumption that RE is the *efficient* estimator under H0 --
i.e., when both covariance matrices are computed with the classical
(homoskedastic, "unadjusted") estimator. This codebase's own documented
methodology (notebook cell 8, and this phase's Success Criterion #3)
deliberately fits both sides with **non-classical** robust/clustered/
kernel covariance types (whatever `choose_cov_type` selects), which does
not guarantee `Var(FE) - Var(RE)` stays positive semi-definite. When it
doesn't, `np.linalg.inv` still succeeds (the matrix is merely
negative-definite, not singular, so the existing `LinAlgError` fallback at
line 149 never triggers), and the resulting `statistic` can be negative.
`stats.chi2.cdf(negative_value, df)` returns `0.0` unconditionally (chi2's
support is `x >= 0`), so `pvalue = 1 - 0 = 1.0` -- i.e. a negative,
invalid statistic is silently reported as "fail to reject H0 with p=1.0",
indistinguishable from a genuinely well-behaved non-rejection. This run
happened to produce a positive statistic (H=0.2566), but nothing in the
code detects or flags the case when it doesn't, despite the module
already treating the sibling "singular `var_diff`" pathology as worth an
explicit warning.

**Fix:**
```python
statistic = float(diff @ inv_var_diff @ diff)
if statistic < 0:
    warnings.warn(
        "Hausman test: negative test statistic (Var(FE) - Var(RE) is not "
        "positive semi-definite) -- the classical chi2 approximation is "
        "not valid here, likely because both sides were fit with a "
        "non-classical (robust/clustered/kernel) covariance estimator; "
        "treat this result as uninterpretable, not as evidence for H0",
        UserWarning,
        stacklevel=2,
    )
degrees_of_freedom = len(common)
pvalue = float(1 - stats.chi2.cdf(statistic, degrees_of_freedom))
```

### WR-02: `compare_specifications` fits `PooledOLS`/`RandomEffects` with no intercept term

**File:** `src/panel_base.py:110-120`
**Issue:** `exog = indexed[indep_vars]` never includes a constant column,
and none of `PooledOLS`, `RandomEffects`, or `PanelOLS` are given one.
For `PanelOLS` with `entity_effects=True, time_effects=True` this is
correct (two-way demeaning absorbs any level shift, no intercept needed).
For `RandomEffects`, the quasi-demeaning transformation
(`y_it - theta * ybar_i`) plays a similar role, so omitting an explicit
constant is defensible. But `PooledOLS` performs **no** demeaning at all
-- it is literal OLS on the pooled panel. Without an intercept, the
regression is forced through the origin; since a country's GDP per
capita (`8.1.1`) and water-stress index (`6.4.2`) are not naturally
mean-zero variables, the resulting Pooled coefficient/R-squared reported
in the comparison table (03-RESEARCH.md Finding 1 describes this table as
"directly embeddable" in the thesis) is likely biased relative to a
correctly-specified Pooled OLS baseline, undermining its value as the
"naive" comparison point against RE/FE.

**Fix:** Add an explicit constant to the exog used for `PooledOLS` (and
optionally `RandomEffects`, for symmetry), leaving `PanelOLS` unchanged:

```python
exog_with_const = exog.assign(const=1.0)
pooled_res = PooledOLS(dependent, exog_with_const).fit(cov_type="unadjusted")
re_res = RandomEffects(dependent, exog_with_const).fit(cov_type="unadjusted")
fe_res = PanelOLS(dependent, exog, entity_effects=True, time_effects=True).fit(
    cov_type="unadjusted"
)
```

### WR-03: `pesaran_cd_test` divides by zero if fewer than 2 entities survive filtering

**File:** `src/panel_base.py:182-194`
**Issue:** `n_entities * (n_entities - 1)` is used as a divisor
(`np.sqrt(2.0 / (n_entities * (n_entities - 1)))`) with no check that
`n_entities >= 2`. If `residuals` ever carries only 0 or 1 distinct
entities (e.g., a mis-specified call, or an extreme exclusion scenario
upstream), this raises an unguarded `ZeroDivisionError` rather than a
clear, actionable error message. Unlikely in the current ~171-country
Model 1 run, but this function is shared with Model 2 and has no input
validation at all.

**Fix:**
```python
n_entities = wide.shape[1]
if n_entities < 2:
    raise ValueError(
        f"pesaran_cd_test requires at least 2 entities, got {n_entities}"
    )
```

## Info

### IN-01: Redundant local `import numpy as np` in test already imported at module scope

**File:** `tests/test_panel_base.py:223`
**Issue:** `numpy` is already imported at module level (line 15,
`import numpy as np`); `test_hausman_test_falls_back_to_pinv_on_singular_var_diff`
re-imports it locally, which is unnecessary and inconsistent with every
other test in the file.
**Fix:** Remove the local `import numpy as np` on line 223; rely on the
module-level import.

### IN-02: Local `linearmodels` imports duplicated across two test functions

**File:** `tests/test_panel_base.py:206`, `tests/test_panel_base.py:285`
**Issue:** `from linearmodels.panel import PanelOLS, RandomEffects` (line
206) and `from linearmodels.panel import PanelOLS` (line 285) are
imported inside individual test functions rather than once at module
scope, unlike `src.panel_base`'s own top-level import style. Minor
inconsistency, no functional impact.
**Fix:** Hoist both imports to the top of the file alongside the existing
`from src import panel_base`.

---

_Reviewed: 2026-07-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
