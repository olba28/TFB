---
phase: 06-modelo-2-productividad-agr-cola-stretch
fixed_at: 2026-07-15T11:15:00Z
review_path: .planning/phases/06-modelo-2-productividad-agr-cola-stretch/06-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-07-15T11:15:00Z
**Source review:** .planning/phases/06-modelo-2-productividad-agr-cola-stretch/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (1 critical, 4 warnings, 2 info -- fix_scope: all)
- Fixed: 7
- Skipped: 0

## Fixed Issues

### CR-01: Dashboard's live bootstrap resamples from the wrong country population for Model 2 (and possibly Model 1)

**Files modified:** `src/dashboard/data.py`, `tests/dashboard/test_caching.py`
**Commit:** e5cdef0
**Applied fix:** `cached_bootstrap` now restricts `df` to the exact country
set the active fitted model was actually fit on (derived from
`fitted.fitted_values.index.get_level_values("country_code")`) before
calling `simulate.bootstrap_counterfactual` -- mirrors
`model2_agri.run_bootstrap`'s use of the pre-filtered `panel_m2`, generically
for any active model. Verified the assumption that `PanelEffectsResults.
fitted_values` carries a `(country_code, year)` MultiIndex against a real
`PanelOLS` fit before applying the fix. Updated the existing
`test_cached_bootstrap_honors_active_model_name` fixture (its fake fitted
object needed a real `fitted_values` MultiIndex to survive the new code
path) and added a new regression test,
`test_cached_bootstrap_restricts_df_to_fitted_model_coverage`, which asserts
on the actual resampled entity set (not just which `.pkl` path was
requested) -- the exact gap the review flagged in the pre-existing test.

### WR-01: `build_coverage_table` hardcodes `MIN_YEARS` instead of accepting the same parameter as `build_model2_panel`

**Files modified:** `src/model2_agri.py`, `tests/test_model2_agri.py`
**Commit:** 4d932f4
**Applied fix:** `build_coverage_table` now accepts `min_years: int =
MIN_YEARS` and uses it throughout (threshold check and `reason` text),
matching `build_model2_panel`'s signature. `_main()` threads the same
`MIN_YEARS` value through both calls. Added
`test_build_coverage_table_honors_non_default_min_years` (asserts a
non-default `min_years=4` changes both `included` and the `reason` text) and
`test_build_coverage_table_default_min_years_matches_build_model2_panel`
(asserts the two functions stay mutually consistent under the shared
default).

### WR-02: Reduced-coverage caption gated by brittle display-name string matching

**Files modified:** `src/dashboard/app.py`, `src/dashboard/models.py`
**Commit:** bd46d3d
**Applied fix:** Added a `"reduced_coverage": bool` field to each
`ACTIVE_MODELS` entry (`False` for Model 1, `True` for Model 2). Replaced
all four `ACTIVE_MODEL_NAME.startswith("Modelo 2")` checks in `app.py` with
a single `MODEL2_COVERAGE_CAPTION` computed once (`None` unless
`ACTIVE_MODEL["reduced_coverage"]` is true) and referenced identically
across the four tabs -- no longer depends on the human-readable display
string at all.

### WR-03: `MODEL2_COVERAGE_CAPTION` hardcodes country counts with no automated cross-check

**Files modified:** `src/dashboard/app.py`, `tests/dashboard/test_app.py`
**Commit:** 6c53e96
**Applied fix:** Added `_model2_coverage_caption()`, which computes both
country counts at runtime instead of hardcoding literals: Model 1's count
reuses `panel_base.filter_by_exclusions` (the same function Model 1's own
exclusion pipeline calls) against the already-loaded `df`/
`panel_exclusions`; Model 2's count reuses `panel_base.filter_by_min_years`
(the same function `model2_agri.build_model2_panel` calls). Falls back to a
count-free caption if the computation itself raises, so a schema surprise
degrades gracefully instead of crashing the dashboard. Replaced
`test_modelo_2_selection_shows_reduced_coverage_caption`'s hardcoded
"39 países"/"171" assertions with a purpose-built synthetic panel
(`_make_reduced_coverage_panel`, 5 countries, 3 Model-2-covered) so the
dynamic-count assertion is meaningful (3 vs. 5) instead of accidentally
trivial. Along the way, discovered and worked around two pre-existing test
gotchas (documented inline in the test): (1) `load_panel_exclusions`'s
`st.cache_data` key is constant across calls since its only parameter is
underscore-prefixed/cache-key-excluded, so it must be monkeypatched (not
just given a differently-seeded in-memory engine) inside `AppTest`-based
tests; (2) `AppTest.from_file` runs the script in a different thread than
the test, and SQLite `:memory:` connections are thread-local
(`SingletonThreadPool`), so a real DB write from the test thread is
invisible to a real DB read from the app's thread -- both loaders touching
`panel_exclusions` must be monkeypatched rather than exercised against a
live in-memory engine in this test file.

### WR-04: No test coverage for `model2_agri.py`'s orchestration functions

**Files modified:** `tests/test_model2_agri.py`
**Commit:** 8fd38fd
**Applied fix:** Added a synthetic-panel smoke test for each of the 7
previously-untested orchestration functions: `fit_model2` (asserts the
`(PanelEffectsResults, dict)` return contract, the `diagnostics` key set,
and a `cov_type` from `choose_cov_type`'s `{"clustered", "kernel"}`
contract), `run_robustness_no_covid` (asserts it fits on exactly the
`year < 2020` sub-sample via `nobs`), `run_bootstrap` and `run_heterogeneity`
(each verified via a monkeypatched capture of the exact call made to
`simulate.bootstrap_counterfactual`/`simulate.fit_interaction_model`, since
running the real 1000-replica bootstrap in a unit test would be too slow),
`run_shap` (monkeypatched capture of the call to `interpret.shap_analysis`),
`serialize_artifacts` (real pickle round-trip via `tmp_path`), and
`write_coverage_table` (real write-then-read against an in-memory engine).

### IN-01: Misleading hardcoded fitted-column name in the map tab

**Files modified:** `src/dashboard/app.py`
**Commit:** 8105ea3
**Applied fix:** Renamed the internal (non-user-facing) `fitted_col` literal
from `"_modelo1_valores_ajustados"` to `"_modelo_valores_ajustados"` -- no
test depended on the old literal (verified by grep before renaming).

### IN-02: `ACTIVE_MODELS` typed loosely as `dict[str, dict[str, object]]`

**Files modified:** `src/dashboard/models.py`
**Commit:** c29d4e6
**Applied fix:** Added a `ModelConfig` `TypedDict` with the five original
fields plus WR-02's new `reduced_coverage: bool` field, and typed
`ACTIVE_MODELS: dict[str, ModelConfig]`. Purely a static-typing change (no
runtime behavior change) -- verified the module still imports and its
values are accessed identically at runtime; no `pyright`/`mypy` was
available in the project's `.venv` to run a live static-type check, so
verification relied on Tier 1 (re-read) + the full test suite passing
unchanged.

## Skipped Issues

None -- all 7 in-scope findings were fixed.

---

_Fixed: 2026-07-15T11:15:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
