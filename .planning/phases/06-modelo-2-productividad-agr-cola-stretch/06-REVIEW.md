---
phase: 06-modelo-2-productividad-agr-cola-stretch
reviewed: 2026-07-15T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - src/dashboard/app.py
  - src/dashboard/data.py
  - src/dashboard/models.py
  - src/model2_agri.py
  - src/panel_base.py
  - tests/dashboard/test_app.py
  - tests/dashboard/test_caching.py
  - tests/test_model2_agri.py
  - tests/test_panel_base.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-07-15
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

`src/panel_base.py`'s new `filter_by_min_years` helper and `src/model2_agri.py`'s
orchestration of the unmodified `panel_base`/`simulate`/`interpret` calls are
careful and well-tested for the pieces that are covered (coverage-table
construction, min-years filtering, Hausman/Pesaran fixtures). The dashboard
wiring in `src/dashboard/models.py` (the model registry) is clean and
data-driven as intended.

However, tracing the call chain from `src/dashboard/app.py`'s "Simulación"
tab through `src/dashboard/data.py::cached_bootstrap` into
`src/simulate.py::bootstrap_counterfactual`/`resample_entities` surfaces a
real correctness bug (CR-01, below): the dashboard's live bootstrap
recompute never applies Model 2's coverage filter that
`src/model2_agri.py::run_bootstrap` itself applies in the offline/production
pipeline. This means the dashboard silently bootstraps and reports simulated
effects for countries far outside Model 2's actual 39-country estimation
sample -- a methodological error that would be very visible (and hard to
defend) in front of the tribunal, since Model 2's whole premise (D-01/D-02)
is that its estimates are valid ONLY for the coverage-filtered panel.

Secondary issues: an API asymmetry between `build_coverage_table` and
`build_model2_panel` (one hardcodes `MIN_YEARS`, the other parameterizes
it), brittle display-name string-matching used to gate the reduced-coverage
caption, hardcoded country counts in that caption with no automated
cross-check, and a test-coverage gap around `model2_agri.py`'s orchestration
functions (`fit_model2`, `run_bootstrap`, `run_heterogeneity`, `run_shap`,
`run_robustness_no_covid`, `serialize_artifacts`, `write_coverage_table` are
all untested).

## Critical Issues

### CR-01: Dashboard's live bootstrap resamples from the wrong country population for Model 2 (and possibly Model 1)

**File:** `src/dashboard/data.py:101-159` (specifically the `df = load_panel_clean(engine)` / `simulate.bootstrap_counterfactual(fitted, df, ...)` call at lines 148-159)

**Issue:**

`cached_bootstrap` loads the FULL, unfiltered `panel_clean` table (`df =
load_panel_clean(engine)`, ~171-215 countries) and passes it straight into
`simulate.bootstrap_counterfactual` for whichever model is active -- it never
restricts `df` to the country set the active model was actually fit on.

Contrast this with the offline production pipeline in
`src/model2_agri.py:215-230` (`run_bootstrap`), which explicitly receives
and passes `panel_m2` -- the 39-country panel already filtered by
`build_model2_panel`/`panel_base.filter_by_min_years` (D-01/D-02). The
dashboard's live recompute path has no equivalent filtering step.

Tracing into `src/simulate.py`:
- `resample_entities` (line 51-74) draws `len(df[entity_col].unique())`
  entities WITH REPLACEMENT from **all** unique `country_code` values in
  whatever `df` it receives (line 67-68: `entities = df[entity_col].unique()`).
  For Model 2, that means it draws ~171-215 times from a population where
  only ~39 countries actually have non-null `2.3.1`/`6.4.2` data -- not 39
  draws from the 39 relevant countries.
- `panel_base.fit_panel_model` (called once per replica, line 148) does not
  drop NaN rows itself, but `linearmodels.panel.model.PanelOLS`'s
  constructor drops missing rows internally (verified in
  `.venv/Lib/site-packages/linearmodels/panel/model.py`, "Check input shape
  and remove missing"). So a replica's *effective* fitted sample ends up
  being whatever random subset of the true 39 relevant countries happened to
  be drawn in that pass over the inflated ~171-215-draw resample --
  typically fewer than 39 distinct real entities per replica (expected ~63%
  of them, by a coupon-collector argument), sometimes far fewer. This
  silently inflates/distorts the bootstrap variance relative to the
  documented "block bootstrap by country" methodology (D-01, `simulate.py`
  docstring), and in degenerate draws could make an individual replica's
  `PanelOLS.fit()` numerically unstable or raise (e.g. too few entities to
  identify two-way fixed effects) -- which the dashboard's blanket
  `except Exception: st.error(ARTIFACT_ERROR_MSG)` in `app.py`'s
  "Simulación" tab (line 223-224) would mask behind the generic
  "no se pudieron cargar los datos" message, misdiagnosing a statistics bug
  as a missing-artifact problem.
- Separately, and more visibly wrong: `baseline = df[df["year"] ==
  baseline_year].set_index(entity_col)[indep_var]` (simulate.py line 159-162)
  is built from the SAME unfiltered `df`. Since `indep_var` ("6.4.2", water
  stress) has much broader coverage than `2.3.1`, `baseline` -- and therefore
  the returned `effect_draws`/`ci_2.5`/`ci_97.5` per-country arrays -- include
  countries that were **never part of Model 2's 39-country estimation
  sample**. The dashboard's "Simulación" tab for Model 2 will report a
  simulated counterfactual effect (using a coefficient estimated from only
  39 countries) for every country that merely has a 2022 water-stress value
  -- a silent out-of-sample extrapolation that directly contradicts D-01/D-02's
  country-level "fully included or fully excluded" exclusion semantics that
  the rest of this phase's code (`panel_base.py`, `model2_agri.py`) is
  otherwise careful to enforce.

This is exactly the kind of scope-of-validity error that is highly visible
and damaging in an academic defense: the memoria explicitly documents Model
2's reduced 39-country coverage as a named limitation, but the live demo
would silently show simulated results for countries outside that coverage.

**Fix:** Restrict `df` to the country set the active fitted model actually
covers before resampling -- derive it from the fitted model itself (generic,
works for any `dep_var`, no per-model hardcoding needed in the dashboard
layer):

```python
@st.cache_data
def cached_bootstrap(
    dep_var: str,
    indep_var: str,
    active_model_name: str,
    reduction_pcts: tuple[float, ...] = (-0.10, -0.20, -0.30),
    n_replicas: int = 8,
    seed: int = 42,
) -> dict:
    engine = get_engine()
    df = load_panel_clean(engine)
    fitted = load_model(models.ACTIVE_MODELS[active_model_name]["pkl_path"])

    # Restrict resampling to the exact entity set the model was fit on --
    # mirrors model2_agri.run_bootstrap's use of the pre-filtered panel_m2,
    # generically for any active model (D-01/D-02 scope-of-validity).
    fitted_entities = fitted.fitted_values.index.get_level_values("country_code").unique()
    df = df[df["country_code"].isin(fitted_entities)]

    return simulate.bootstrap_counterfactual(
        fitted,
        df,
        dep_var,
        indep_var,
        reduction_pcts=list(reduction_pcts),
        n_replicas=n_replicas,
        seed=seed,
    )
```

Add a regression test asserting that, for `active_model_name="Modelo 2
(Productividad agrícola)"`, the `df` passed into
`simulate.bootstrap_counterfactual` contains only the ~39 Model-2-covered
countries (not the full panel) -- the existing
`test_cached_bootstrap_honors_active_model_name` only checks which `.pkl` is
loaded, not which countries are resampled, so it would not catch this.

## Warnings

### WR-01: `build_coverage_table` hardcodes `MIN_YEARS` instead of accepting the same parameter as `build_model2_panel`

**File:** `src/model2_agri.py:80-118` (threshold check at line 103), vs. `src/model2_agri.py:70-77`

**Issue:** `build_model2_panel(panel_clean, min_years: int = MIN_YEARS)` accepts
`min_years` as a parameter, but `build_coverage_table(panel_clean)` always
uses the module-level `MIN_YEARS` constant directly (`included =
years_available >= MIN_YEARS`, line 103). If `build_model2_panel` is ever
called with a non-default `min_years` (the signature explicitly invites
this), the `model2_coverage` table written by `write_coverage_table` would
silently disagree with which countries actually appear in the fitted panel
-- undermining the traceability the `model2_coverage` table exists to
provide (D-03).

**Fix:**
```python
def build_coverage_table(panel_clean: pd.DataFrame, min_years: int = MIN_YEARS) -> pd.DataFrame:
    ...
    included = years_available >= min_years
    reason = included.map({
        True: f"incluido: >={min_years} años observados",
        False: f"excluido: <{min_years} años observados con {INDEP_VAR} y {DEP_VAR}",
    })
```
and thread the same `min_years` value through `_main()` to both calls.

### WR-02: Reduced-coverage caption gated by brittle display-name string matching

**File:** `src/dashboard/app.py:102, 163, 188, 228`

**Issue:** All four tabs decide whether to show `MODEL2_COVERAGE_CAPTION`
via `ACTIVE_MODEL_NAME.startswith("Modelo 2")` -- a check against the
human-readable dict key in `models.ACTIVE_MODELS`, duplicated four times.
If the display name in `models.py` is ever edited (e.g., renamed to
"Productividad agrícola (Modelo 2)" or translated), this caption silently
stops appearing with no error and no test failure pointing at the actual
cause (the existing tests assert on the same string, so they'd pass
against a self-consistent but wrong rename).

**Fix:** Make this data-driven off the registry instead of the display
string, e.g. add a `"reduced_coverage": bool` (or a `"coverage_caption":
str | None`) field to each `ACTIVE_MODELS` entry and check
`models.ACTIVE_MODELS[ACTIVE_MODEL_NAME]["reduced_coverage"]`.

### WR-03: `MODEL2_COVERAGE_CAPTION` hardcodes country counts with no automated cross-check

**File:** `src/dashboard/app.py:67-72`

**Issue:** The caption text hardcodes "39 países" and "171 del Modelo 1" as
literal strings. If the underlying `panel_clean`/`model2_coverage` data is
regenerated (e.g., a UN SDG API refresh changes coverage), these numbers can
silently drift out of sync with the actual data with no test or runtime
check catching the mismatch -- only a substring-match test
(`test_modelo_2_selection_shows_reduced_coverage_caption`) that checks the
hardcoded string still exists, not that it's still accurate.

**Fix:** Compute the counts at runtime from `model2_coverage`/
`panel_exclusions` (e.g. `len(coverage_df[coverage_df.included])`) and
interpolate them into the caption, or at minimum add a smoke check (e.g. in
the CI pipeline or a dashboard test using the real `data/panel.db`) that
asserts the caption's hardcoded numbers match the live coverage table.

### WR-04: No test coverage for `model2_agri.py`'s orchestration functions

**File:** `tests/test_model2_agri.py` (whole file), vs. `src/model2_agri.py:121-286`

**Issue:** `tests/test_model2_agri.py` only exercises `build_coverage_table`
and `build_model2_panel` (pure bookkeeping). `fit_model2` (the manual
RE-fit + Hausman/Pesaran wiring, lines 121-182), `run_robustness_no_covid`
(185-212), `run_bootstrap` (215-230), `run_heterogeneity` (233-241),
`run_shap` (244-257), `serialize_artifacts` (260-276), and
`write_coverage_table` (279-285) have no tests at all in this file. These
functions contain real logic (e.g. `fit_model2`'s manual RE construction
with an explicit constant column, mirrored from
`panel_base.compare_specifications`) that could silently regress (e.g. a
future edit accidentally reusing the wrong `cov_type` for the Hausman-input
fit) without any test catching it.

**Fix:** At minimum add a synthetic-panel smoke test for `fit_model2`
(asserting it returns a `(PanelEffectsResults, dict)` tuple with the
expected `diagnostics` keys and a sane `cov_type`), and a test for
`run_robustness_no_covid` asserting it correctly drops `year >= 2020` rows
before fitting.

## Info

### IN-01: Misleading hardcoded fitted-column name in the map tab

**File:** `src/dashboard/app.py:113`

**Issue:** `fitted_col = "_modelo1_valores_ajustados"` is a leftover
Phase-5, Model-1-specific literal that is now used for whichever model is
active (including Model 2). It's harmless today (the label shown to the
user, `fitted_label`, is correctly parameterized by `ACTIVE_MODEL_NAME`),
but the internal key name is misleading to future maintainers reading the
merge/column logic and invites confusion or an accidental collision if a
second simultaneous fitted-values overlay is ever added.

**Fix:** Rename to a model-agnostic name, e.g.
`fitted_col = "_modelo_valores_ajustados"`.

### IN-02: `ACTIVE_MODELS` typed loosely as `dict[str, dict[str, object]]`

**File:** `src/dashboard/models.py:32`

**Issue:** Each entry's value type is declared as `dict[str, object]`,
which defeats static type checking on the individual fields
(`dep_var`/`indep_var`/`feature_vars`/`pkl_path`/`rf_shap_pkl_path`) that
every call site (`app.py`, `data.py`) accesses by string key. A typo in a
key name (e.g. `ACTIVE_MODEL["indep_vars"]` instead of `"indep_var"`) would
not be caught by Pylance in basic mode, only at runtime via `KeyError`.

**Fix:** Define a `TypedDict` (e.g. `ModelConfig`) with the five expected
fields and type `ACTIVE_MODELS: dict[str, ModelConfig]`, consistent with
the project's "type hints required for all parameters" convention.

---

_Reviewed: 2026-07-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
