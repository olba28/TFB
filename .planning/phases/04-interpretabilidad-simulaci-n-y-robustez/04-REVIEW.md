---
phase: 04-interpretabilidad-simulaci-n-y-robustez
reviewed: 2026-07-13T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - notebook/4_1_interpretabilidad_simulacion.ipynb
  - scripts/verify_repro02.py
  - src/interpret.py
  - src/simulate.py
  - tests/test_interpret.py
  - tests/test_simulate.py
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-07-13
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the Phase 4 interpretability/simulation module (`src/interpret.py`, `src/simulate.py`), its orchestration notebook, its reproducibility-proof script, and both test files. The full `pytest tests/test_interpret.py tests/test_simulate.py` suite passes (8/8), and I independently re-ran key statistical paths against the real `data/panel.db` to verify claims empirically (e.g. confirming `fit_interaction_model`'s formula actually fits an `Intercept` term despite the docstring's claim that the interaction is the "only" regressor besides effects, and confirming that all 171 countries currently have complete 2022 `6.4.2` data so a latent NaN-handling gap in `check_non_extrapolation` does not currently manifest).

No BLOCKER-level defects were found — no crashes, no security vulnerabilities, no data-loss risks in the code as currently exercised against the real dataset. However, I found several WARNING-level correctness/robustness/documentation-accuracy gaps that should be fixed before this becomes load-bearing for Phase 6 (which reuses `simulate.py`/`interpret.py` "unmodified" per D-12), plus a few INFO-level cleanliness items.

## Warnings

### WR-01: `check_non_extrapolation` silently mislabels missing-data countries as "extrapolation exclusions"

**File:** `src/simulate.py:93-95` (called from `bootstrap_counterfactual`, `src/simulate.py:159-169`)
**Issue:** `bootstrap_counterfactual` builds `baseline` via `pd.to_numeric(df[df["year"] == baseline_year].set_index(entity_col)[indep_var], errors="coerce")`. If a country has a `baseline_year` row but a missing/non-numeric `indep_var` value for that row, `baseline` for that country becomes `NaN`. `check_non_extrapolation` then computes `survives = simulated_level >= historical_min`; in pandas, `NaN >= x` evaluates to `False`, so that country is silently placed in `excluded_countries` with the same semantics as a genuine "simulated level fell below the historical floor" exclusion. The notebook (`notebook/4_1_interpretabilidad_simulacion.ipynb`, cell `26b52943`) then reports this country to the reader with a specific, factually incorrect claim: "su nivel simulado de estrés hídrico caería por debajo del mínimo histórico global" — when the real cause would be missing data, not extrapolation.
This does not currently manifest: I verified against the real `data/panel.db` that all 171 filtered countries have a non-null `6.4.2` value for 2022. But D-04 explicitly requires *honest, explicit* documentation of exclusions, and D-12 states this module will be reused "unmodified" by Phase 6 against a different dependent variable (`2.3.1`, which has 96.5% missingness) — the country-level `filter_by_exclusions` 70%-coverage gate does not guarantee every surviving country has a non-null value specifically in `baseline_year`, so this gap is live for future reuse.
**Fix:** Distinguish "missing baseline data" from "extrapolation violation" explicitly, e.g.:
```python
def check_non_extrapolation(baseline, simulated_level, historical_min):
    missing = baseline.isna() | simulated_level.isna()
    below_floor = simulated_level < historical_min
    survives = ~missing & ~below_floor
    excluded_missing = baseline.index[missing].tolist()
    excluded_extrapolation = baseline.index[~missing & below_floor].tolist()
    return survives, excluded_extrapolation, excluded_missing
```
and update `bootstrap_counterfactual`/the notebook to report the two exclusion reasons separately.

### WR-02: `fit_interaction_model`'s docstring/design claim is contradicted by the actual fitted model — an `Intercept` term is estimated and silently dropped downstream

**File:** `src/simulate.py:198-232` (formula built at `src/simulate.py:224-227`)
**Issue:** The docstring states the model fits `indep_var : C(group_col)` as "the ONLY regressor term besides the effects" (D-09/D-11). The actual formula is `f'Q("{dep_var}") ~ 1 + Q("{indep_var}") : C({group_col}) + EntityEffects + TimeEffects'` — the explicit `1 +` requests an intercept. I confirmed by direct execution against a synthetic fixture that `PanelOLS.from_formula` does **not** drop or absorb this term: `result.params.index` contains `['Intercept', "Q('x'):C(group)[0]", "Q('x'):C(group)[1]"]`, with `Intercept` receiving a real, non-zero estimated coefficient and its own SE/CI. This directly contradicts the docstring's "ONLY... besides the effects" claim, and, unlike the `C(group_col)` main effect (which D-09 says correctly *would* raise `AbsorbingEffectError`), the redundant intercept neither errors nor gets flagged.
The notebook's `interaction_coef_table` helper (`notebook/4_1_interpretabilidad_simulacion.ipynb`, cell `f607f29f`) papers over this by filtering `p != "Intercept"` before display — so the bug is invisible in the rendered tables, and `tests/test_simulate.py::test_interaction_formula` doesn't assert on `Intercept`'s absence either, so nothing currently catches this docstring/implementation mismatch.
I additionally verified numerically that removing the redundant `1 +` produces **bit-identical** interaction coefficients (`1.985398`, `1.973454` in both cases), so this is not presently a numerical-correctness bug — but it is a real documentation-accuracy defect for an academic thesis whose methodology section needs to describe the fitted specification precisely, and a latent risk if a future `group_col` or `cov_type` combination causes the extraneous intercept term to interact with clustering/collinearity differently.
**Fix:** Drop the redundant `1 +` from the formula to match the documented "interaction term is the only regressor besides the effects" claim:
```python
formula = (
    f'Q("{dep_var}") ~ Q("{indep_var}") : C({group_col}) '
    "+ EntityEffects + TimeEffects"
)
```
and add an assertion in `test_interaction_formula` that `"Intercept" not in result.params.index`.

### WR-03: REPRO-02's bit-identical guarantee implicitly depends on undocumented SQLite row-order stability

**File:** `notebook/4_1_interpretabilidad_simulacion.ipynb` (cell `07328f33`); consumed by `src/simulate.py:67` (`resample_entities`'s `entities = df[entity_col].unique()`)
**Issue:** `panel_clean = pd.read_sql("SELECT * FROM panel_clean", engine)` has no `ORDER BY` clause. SQL does not guarantee row order without one. `resample_entities`'s reproducibility (and therefore the whole bootstrap's bit-for-bit determinism claimed by REPRO-02) depends on `df[entity_col].unique()` returning the countries in the *same* order across independent runs, because `rng.choice(entities, ...)` indexes into that array positionally. `scripts/verify_repro02.py` did empirically pass (per `04-03-SUMMARY.md`), so this is not presently broken, but it is an unenforced assumption: a future SQLite `VACUUM`, index addition, or engine/driver version change could silently reorder the physical scan without any code change or error, causing REPRO-02 to regress without warning. This pattern is inherited from Phases 2/3 (`SELECT * FROM panel_clean` also lacks `ORDER BY` there), but Phase 4 is the first phase whose correctness claim (bit-identical bootstrap output across independent executions) actually depends on it.
**Fix:** Add an explicit `ORDER BY country_code, year` to the `read_sql` calls that feed `resample_entities`/`bootstrap_counterfactual`, or explicitly `.sort_values(["country_code", "year"])` immediately after the read, so row order is a documented invariant rather than an implicit SQLite behavior.

### WR-04: `shap_analysis`'s categorical-column detection is hardcoded to `"region"`, contradicting its own "dependent-variable-agnostic"/D-12 reusability claim

**File:** `src/interpret.py:130-134`
**Issue:**
```python
cat_cols = [c for c in ["region"] if c in feature_vars]
if cat_cols:
    X = pd.get_dummies(complete[feature_vars], columns=cat_cols, drop_first=True)
else:
    X = complete[feature_vars].copy()
```
Only the literal string `"region"` is ever treated as categorical. D-12/the module docstring (`src/interpret.py:27-29`) explicitly claims "every public function here is dependent-variable-agnostic (dep_var, feature_vars are parameters, never hardcoded), so Phase 6 can call `shap_analysis(df, dep_var="2.3.1", feature_vars=[...])` unmodified." If Phase 6 (or any future caller) passes a `feature_vars` list containing any other non-numeric/string column, `pd.get_dummies` is never applied to it and it falls into the plain `complete[feature_vars].copy()` branch, which `RandomForestRegressor.fit` will reject with a `ValueError` (or silently misbehave if it happens to be a numeric-looking dtype). This is a real gap between the stated design goal (generic reusability) and the implementation (single hardcoded special case).
**Fix:** Detect categorical columns generically instead of hardcoding a name, e.g.:
```python
cat_cols = [c for c in feature_vars if complete[c].dtype == object or complete[c].dtype.name == "category"]
```

### WR-05: `scripts/verify_repro02.py`'s uncaught `RuntimeError` in `main()` produces a raw traceback instead of the script's own documented failure message

**File:** `scripts/verify_repro02.py:126-134` (raises originate at `scripts/verify_repro02.py:74-76`, `78-82`)
**Issue:** `run_notebook_and_capture_snapshot` raises a bare `RuntimeError` on nbconvert failure or a missing snapshot file. `main()` calls it directly (`run_a = run_notebook_and_capture_snapshot("runA")`) with no `try/except`, so this exception propagates out of `main()` and crashes the script with a raw Python traceback rather than the script's own carefully-worded, actionable failure guidance (the `"Root cause is almost certainly..."` message at lines 145-149 is only reached for a *mismatch*, not for an execution failure). This is a minor operator-experience defect for what is otherwise a well-documented diagnostic script, not a correctness bug (the exit code is still non-zero either way).
**Fix:** Wrap the two `run_notebook_and_capture_snapshot` calls in `main()` with a `try/except RuntimeError as e: print(f"FAIL: {e}"); return 1`.

## Info

### IN-01: Unused `import pytest` in `tests/test_interpret.py`

**File:** `tests/test_interpret.py:20`
**Issue:** `pytest` is imported but never referenced anywhere in the file (no `pytest.raises`, no markers, no fixtures) — confirmed via search, zero occurrences of `pytest.` in the file body.
**Fix:** Remove the unused import, or use `pytest.raises`/markers if error-path coverage is intended (e.g., asserting `shap_analysis` raises on an empty complete-case frame).

### IN-02: `bootstrap_counterfactual`'s `fitted_results` parameter is accepted but never validated against `dep_var`/`indep_var`

**File:** `src/simulate.py:98-117`
**Issue:** The docstring explains `fitted_results` is accepted "for API symmetry" and is not itself refit — which is a reasonable design choice — but nothing checks that the passed-in `fitted_results` actually corresponds to the same `dep_var`/`indep_var` being bootstrapped. A caller could pass a mismatched fitted model (e.g. Phase 6's Model 2 results) and no warning or error would occur, since the parameter is silently unused for computation.
**Fix:** A lightweight sanity check (e.g. `assert indep_var in fitted_results.params.index`) would catch an obviously mismatched `fitted_results` at low cost, without requiring a full refit-comparison.

### IN-03: VIF/correlation numbers shown alongside the SHAP correlation-bias caveat are computed on a different (smaller, differently-composed) sample than the RF actually trained on

**File:** `notebook/4_1_interpretabilidad_simulacion.ipynb`, cells `e26e0990`/`77cd1078` vs. `60d4a1b9`
**Issue:** The VIF/correlation table used to justify "solo multicolinealidad modesta" for the RF's predictors is computed on `panel_clean[INDICATOR_COLS].dropna()` (n≈171, complete-case across all 5 indicators including `2.3.1`'s 96.5%-missing column), while the RF itself is trained on a complete-case subset of only the 3 numeric predictors + dep_var (n=3473, per the printed cell output). The notebook's own comment acknowledges this is a deliberate choice to reproduce Phase 2's exact numbers rather than recomputing VIF on the RF's actual training sample, so this is not an oversight — but it means the "real numbers" quoted to characterize the RF's correlation-bias risk describe a materially different (and much smaller, likely non-representative) subpopulation than the one the RF/SHAP results are actually computed over.
**Fix:** No code change required, but consider adding an explicit caveat sentence noting the VIF is computed on a different (smaller) complete-case sample than the RF's own 3473-row training set, so a reader/tribunal member doesn't conflate the two.

---

_Reviewed: 2026-07-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
