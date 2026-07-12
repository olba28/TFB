---
phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita
status: complete
completed: 2026-07-12
---

# Phase 03 Research: Modelo 1 — Regresión de Panel (PIB per cápita)

> ⚠️ **Deviation notice:** Produced in a single-context inline flow (no
> independent subagent) — same runtime constraint as Phase 2 (no
> `Agent`/`Task` tool available). This file is the sole input to the
> planning pass; the plan is the sole input to the self-check pass.
> User-approved deviation pattern, established in Phase 2.

## Objective

Answer: "What do I need to know to PLAN Phase 3 well?"

Phase 3 goal (ROADMAP.md): fit and diagnose a two-way fixed-effects panel
model for real GDP per-capita growth, with the specification/SEs/robustness
checks a tribunal expects, serialized for reuse. Requirements: MODEL1-01..06,
REPRO-03. A `/gsd-discuss-phase 3` session already locked 5 decisions in
`03-CONTEXT.md` (D-01..D-05) — this research does not re-litigate those,
only fills in the technical/library details needed to implement them
correctly.

## Inputs Read

- `.planning/phases/03-modelo-1-regresi-n-de-panel-pib-per-c-pita/03-CONTEXT.md` (locked decisions D-01..D-05, Claude's Discretion items)
- `.planning/phases/03-modelo-1-regresi-n-de-panel-pib-per-c-pita/03-DISCUSSION-LOG.md` (audit trail, confirms CONTEXT.md is a faithful distillation)
- `.planning/ROADMAP.md` §Phase 3 (goal, 7 success criteria)
- `.planning/REQUIREMENTS.md` §"Modelo 1 — PIB per cápita" + REPRO-03 (exact wording)
- `.planning/phases/02-construcci-n-del-panel-y-eda/02-01-SUMMARY.md`, `02-02-SUMMARY.md`, `02-VERIFICATION.md` (panel_clean/panel_exclusions schema, known limitations carried forward)
- `src/panel_build.py`, `src/db.py` (existing patterns to follow: always-regenerate convention, fixed table names)
- **Live introspection of the actually-installed `linearmodels==7.0` package** in this project's `.venv` (module `dir()`, `inspect.signature()`, docstrings) — more reliable than external docs since it reflects the exact installed version.
- **Live numeric verification** of the Hausman test and Pesaran CD test formulas against real `linearmodels` fitted-model objects (both tests are NOT provided by any installed library — see Finding 2).
- **Live query against the real `data/panel.db`** to compute the actual expected Model 1 sample size after applying D-01/D-02's exclusion rule.

## Key Findings

### Finding 1 — Exact `linearmodels` API surface (verified against the installed v7.0, not assumed from training data)

```python
from linearmodels.panel import PanelOLS, PooledOLS, RandomEffects, compare

# Constructor: entity_effects/time_effects are PanelOLS-only kwargs (PooledOLS/RandomEffects don't take them)
PanelOLS(dependent, exog, entity_effects=True, time_effects=True)   # dependent/exog must have a (entity, time) MultiIndex
PooledOLS(dependent, exog)
RandomEffects(dependent, exog)

# .fit() signature (all three share it):
model.fit(cov_type="unadjusted")  # default
```

**Standard errors — exact `cov_type` strings (this is where a wrong guess would silently produce the wrong SEs):**
- `cov_type="clustered", cluster_entity=True` → clustered-by-country SEs (MODEL1-04's "clustered por país").
- `cov_type="kernel"` (optionally `kernel="bartlett"`, the default) → **this IS the Driscoll-Kraay HAC estimator.** There is NO `cov_type="driscoll-kraay"` string — the class is named `DriscollKraay` internally but the public `cov_type` key is `"kernel"`. Getting this wrong (e.g. passing a nonexistent string) would raise `KeyError` at `.fit()` time, not silently misfire — but the planner/executor must know the correct string is `"kernel"`, not a guess based on the class name.

**Pooled/RE/FE comparison (satisfies ROADMAP Success Criterion #3's "documented" requirement directly):**
```python
compare({"Pooled": pooled_res, "RE": re_res, "FE": fe_res})
```
Returns a `PanelModelComparison` object whose `str()` renders a clean side-by-side table (Dep. Variable, Estimator, R-squared variants, F-statistic, per-coefficient estimate+t-stat) — verified live, output is directly usable/embeddable in a notebook or memoria section, no further formatting work needed.

**Serialization:** a fitted `PanelEffectsResults` (what `PanelOLS(...).fit()` returns) pickles and round-trips cleanly with the standard `pickle` module — verified live (`pickle.dumps`/`pickle.loads`, confirmed `loaded.params == original.params`). No special handling, no custom `__reduce__`, no need for `joblib` over stdlib `pickle` for this object type. Satisfies MODEL1-06 directly.

### Finding 2 — CRITICAL: neither `linearmodels` nor `statsmodels` provides a Hausman test or Pesaran CD test for panel data. Both must be manually implemented — formulas verified numerically below.

Searched the full source of both installed packages (`linearmodels==7.0`,
already-installed `statsmodels`) for "hausman"/"pesaran" — the only hits are
`linearmodels/iv/` (a completely different Hausman-type test for
instrumental-variables endogeneity, not applicable here) and
`statsmodels/tsa/ardl/` (Pesaran-Shin-Smith cointegration bounds test, also
unrelated — different "Pesaran" test entirely). **Neither the FE-vs-RE
Hausman test (Success Criterion #3) nor the Pesaran cross-sectional-dependence
test (Success Criterion #4, "test de dependencia transversal de Pesaran")
exists as a library function anywhere in this project's dependencies.** Both
must be implemented from the standard textbook formulas. This is the single
most important finding for the plan — an executor guessing at a
non-existent `linearmodels.panel.hausman_test(...)`-style call would fail or,
worse, silently call the wrong (IV-context) function.

**Hausman test formula (verified numerically, see below):**

```
H = (b_FE - b_RE)' [Var(b_FE) - Var(b_RE)]^(-1) (b_FE - b_RE)  ~  chi2(k)
```
where `b_FE`/`b_RE` are the coefficient vectors on the regressors common to
both specifications (exclude RE's constant — FE has no explicit intercept,
since `entity_effects` absorbs it), `Var(...)` are the corresponding
sub-blocks of `.cov` (the coefficient covariance matrix each `PanelEffectsResults`/
`RandomEffectsResults` object exposes), and `k` is the number of common
regressors. Implementation:
```python
common = fe_res.params.index  # regressors present in both (excludes RE's const)
diff = fe_res.params[common].values - re_res.params[common].values
var_diff = fe_res.cov.loc[common, common].values - re_res.cov.loc[common, common].values
stat = diff @ np.linalg.inv(var_diff) @ diff
pvalue = 1 - scipy.stats.chi2.cdf(stat, df=len(common))
```
**Verified live** against a synthetic 30-entity × 20-year panel with a
per-entity random effect uncorrelated with the regressor (Hausman's null
should hold): stat=0.0605, p=0.806 — correctly fails to reject H0, confirming
the formula is implemented correctly. **Numerical caveat:** `var_diff` can
be non-positive-definite in finite samples even when the asymptotic theory
holds; the plan should use `numpy.linalg.pinv` as a documented fallback if
`numpy.linalg.inv` raises `LinAlgError` (Moore-Penrose pseudo-inverse is the
standard practical workaround cited in applied econometrics texts for this
exact issue), and should surface a warning rather than crash if `var_diff`
has negative eigenvalues (a known small-sample pathology of the test, not a
bug).

**Pesaran CD test formula (verified numerically, see below):**

```
CD = sqrt(2 / (N(N-1))) * sum_{i<j} sqrt(T_ij) * rho_hat_ij   ~  N(0,1) under H0 (no cross-sectional dependence)
```
where `N` = number of entities, `rho_hat_ij` = sample correlation between
entity i's and entity j's model residuals over their T_ij commonly-observed
time periods. Implementation (handles unbalanced panels natively via
per-pair `.dropna()`, which matters here — D-02's exclusion rule filters at
the *country* level, not row level, so included countries can still have a
handful of individually-missing years within their qualifying 17-23 year
span):
```python
resids = fe_res.resids  # Series with (entity, time) MultiIndex
wide = resids.unstack(level=0)  # index=time, columns=entity
N = wide.shape[1]
total = 0.0
for i in range(N):
    for j in range(i + 1, N):
        common = wide.iloc[:, [i, j]].dropna()
        if len(common) < 2:
            continue
        rho = common.iloc[:, 0].corr(common.iloc[:, 1])
        if pd.notna(rho):
            total += np.sqrt(len(common)) * rho
cd_stat = np.sqrt(2.0 / (N * (N - 1))) * total
pvalue = 2 * (1 - scipy.stats.norm.cdf(abs(cd_stat)))
```
**Verified live** against the same synthetic panel (residuals from a
correctly-specified FE model, so no true cross-sectional dependence
expected): CD=-0.2814, p=0.778 — correctly fails to reject H0 (435 of 435
possible entity pairs used, confirming the pairwise-overlap logic runs
correctly even framed generally for unbalanced panels). **Performance note:**
this is O(N²) in the number of entities; with N≈171 (Finding 4's real
sample), that's ~14,535 pairs — verified fast enough in practice (the
30-entity synthetic test completed in well under a second; 171 entities is
~30x more pairs, still trivially fast for a one-time diagnostic computation,
no optimization needed).

**Decision rule (Claude's Discretion per CONTEXT.md):** compute the Pesaran
CD test on the base FE model's residuals; if `pvalue < 0.05` (reject H0 of
no cross-sectional dependence), use `cov_type="kernel"` (Driscoll-Kraay);
otherwise use `cov_type="clustered", cluster_entity=True`. This is a
standard, defensible threshold (5% significance) and directly implements
MODEL1-04's "clustered por país (o Driscoll-Kraay si el test... lo indica)."

### Finding 3 — `panel_clean`'s indicator columns are all `float64` (verified on the full table; a `LIMIT`-based sample read misled an initial check)

A first check via `pd.read_sql("SELECT * FROM panel_clean LIMIT 3", engine)`
showed 4 of 5 indicator columns as `object` dtype — this looked like a data
quality bug in Phase 2's output. **It was not:** re-checking against the
*full* table (`SELECT * FROM panel_clean`, no `LIMIT`) shows all 5 indicator
columns (`2.3.1`, `6.4.1`, `6.4.2`, `8.1.1`, `8.2.1`) are correctly
`float64`. The `LIMIT 3` sample happened to land on rows where the sparser
indicators were `NULL` in all 3 sampled rows, and `pandas.read_sql` infers
`object` dtype for an apparently-all-null column slice when it lacks a
non-null value to type from. **Action for the plan:** always read the full
table (no `LIMIT`) when building the model's regression DataFrame; as a
cheap defensive practice (already an established convention in
`fetch_data.py`'s value parsing), coerce the model's dependent/independent
columns via `pd.to_numeric(errors="coerce")` before passing to
`PanelOLS`/`PooledOLS`/`RandomEffects` regardless, in case a future
`panel_clean` rebuild ever introduces a genuine string value.

### Finding 4 — Real expected Model 1 sample size, computed live against `data/panel.db`

Applying D-01/D-02's exclusion rule (exclude a country from the fit if
*either* `6.4.2` or `8.1.1` — the two variables the base specification
uses — appears in `panel_exclusions` for that country):

- **77 of 248** countries excluded (fail the 70% threshold on `6.4.2` and/or `8.1.1`).
- **171 countries** included in the Model 1 fit.
- **3,879 observation-rows** after dropping any remaining row-level NaN on `6.4.2`/`8.1.1` within the included countries.
- Years span 2000–2022 (23 years); average 22.7 years per included country — the panel is close to calendar-balanced at the country level (most included countries report nearly every year), though not perfectly, which is why Finding 2's Pesaran CD implementation must handle unbalanced pairs rather than assume a strictly rectangular panel.

These are the real numbers the plan's acceptance criteria should assert
against (e.g., "171 countries, ~3,879 observations" as an expected range,
not an exact literal if the live API data could still be revised — mirrors
how Phase 1/2 handled this same caveat).

### Finding 5 — `data/modelos/` does not exist yet; `.pkl` is already gitignored

`ls data/` shows only `panel.db` and `raw/` — `data/modelos/` (the location
CLAUDE.md's own "State Management" section already anticipates: "Model
state: Serialized to `data/modelos/` as .pkl/.joblib files") must be created
by the plan (`mkdir -p data/modelos`). `.gitignore` already has a bare
`*.pkl` line (confirmed) — no gitignore change needed; `model1_gdp.pkl` is
automatically excluded from git, consistent with CLAUDE.md's "Model
persistence: Serialized models (.pkl/.joblib) not versioned; regenerated
from scripts" constraint.

### Finding 6 — `panel_base.py`'s parametric design (D-05) maps cleanly onto a small set of composable functions

Given D-05's exact required signature
(`fit_panel_model(df, dep_var, indep_vars, entity_effects=True,
time_effects=True, ...)`) and the need to also expose the comparison/
Hausman/Pesaran/SE-choice machinery for reuse (Success Criteria #1, #3,
#4), the natural function set for `panel_base.py` is:

- `filter_by_exclusions(df, exclusions, dep_var, indep_vars) -> pd.DataFrame` — implements D-01/D-02: excludes a country's rows entirely if `dep_var` or any `indep_vars` entry appears in `exclusions` for that country (not a row-level NaN filter — a country-level exclusion, per D-02's exact wording "se excluye el país... panel balanceado respecto a las variables del modelo").
- `fit_panel_model(df, dep_var, indep_vars, entity_effects=True, time_effects=True, cov_type="clustered", **cov_config) -> PanelEffectsResults` — the D-05-mandated public entry point; thin wrapper around `PanelOLS(...).fit(...)` after building the `(entity, time)` MultiIndex from `df`.
- `compare_specifications(df, dep_var, indep_vars) -> PanelModelComparison` — fits Pooled/RE/FE on the same `dep_var`/`indep_vars` and returns `linearmodels.panel.compare(...)`'s output (Success Criterion #3).
- `hausman_test(fe_results, re_results) -> dict` — Finding 2's manual formula, returns `{statistic, df, pvalue}`.
- `pesaran_cd_test(residuals) -> dict` — Finding 2's manual formula, returns `{statistic, pvalue}`.
- `choose_cov_type(pesaran_result, alpha=0.05) -> tuple[str, dict]` — Finding 2's decision rule, returns the `cov_type` string plus the `cov_config` kwargs (`cluster_entity=True` or `kernel="bartlett"`) ready to splat into `fit_panel_model`.

This function set is **entirely dependent-variable-agnostic** — Phase 6's
Model 2 can call every one of these with `dep_var="2.3.1"` and different
`indep_vars` without modifying `panel_base.py`, satisfying MODEL2-01 "by
construction" exactly as D-05 intends.

### Finding 7 — Deliverable split: testable `src/panel_base.py` (Success Criteria #1-4 are code-testable) + a notebook for the live fit, comparison tables, robustness check, and REPRO-03's limitations section (inherently document-facing, mirrors Phase 2's EDA-notebook precedent)

Success Criteria #1 (reusable function), #2 (FE spec), #3 (pooled/RE/FE +
Hausman), #4 (SE choice) are all properties of `panel_base.py`'s functions
and are directly pytest-testable against synthetic panel data (mirrors
Phase 2's `src/panel_build.py` + `tests/test_panel_build.py` pattern
exactly). Success Criteria #5 (robustness check), #6 (serialized `.pkl`),
and #7 (limitations section prose) are the *live, real-data* application of
those functions plus document-facing narrative — naturally a notebook
deliverable, per CLAUDE.md's "Notebook-driven exploratory workflow" +
Phase 2's already-established `notebook/2_1_...ipynb` precedent and naming
convention (`notebook/3_1_modelo1_pib.ipynb`, following the `[number]_
[descriptive_name].ipynb` pattern).

## Architecture Recommendation Summary

```
src/
  panel_base.py            # NEW — filter_by_exclusions, fit_panel_model, compare_specifications,
                            #        hausman_test, pesaran_cd_test, choose_cov_type
notebook/
  3_1_modelo1_pib.ipynb    # NEW — live fit against data/panel.db, pooled/RE/FE comparison table,
                            #        Hausman result, Pesaran CD + SE-choice justification, robustness
                            #        check (2000-2019 sub-sample per D-04), limitations section (REPRO-03)
data/
  modelos/
    model1_gdp.pkl          # NEW — serialized fitted PanelEffectsResults (gitignored, regenerable)
tests/
  test_panel_base.py        # NEW — synthetic-panel unit tests for every panel_base.py function
```

## Open Questions Flagged for the Plan (already resolved by CONTEXT.md — listed for traceability)

All 5 methodological decisions this research would otherwise have had to
flag as open questions were already locked by `/gsd-discuss-phase 3`
(D-01..D-05) — no new open decisions from this research pass. The one
implementation-level choice research resolves (not a decision needing user
sign-off, per CONTEXT.md's "Claude's Discretion" list): the Pesaran-CD
significance threshold for the clustered-vs-Driscoll-Kraay SE choice is
**α=0.05** (Finding 2), a standard default.

## Validation Architecture

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`) |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_panel_base.py -q` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/ -q` |
| **Estimated runtime** | ~3-5 seconds (synthetic panels are small; the Pesaran CD test's O(N²) pair loop is the slowest part but trivial at unit-test scale with a handful of synthetic entities) |

**Sampling rate:** run the quick command after every task commit; full suite
after each plan; full suite must be green before `/gsd-verify-work`.

**Manual-only verifications:** the notebook's limitations/threats-to-validity
prose (REPRO-03) and the qualitative "robustness check produces consistent
results" judgment (Success Criterion #5) are human-judgment deliverables —
route to `human_judgment: true` in each plan's SUMMARY coverage block, not
automated pass/fail.

## Wave 0 / Test Infrastructure Notes

No new test framework needed — `pytest` + `pyproject.toml` already
established (Phase 1/2). New test file: `tests/test_panel_base.py` (mirrors
`tests/test_panel_build.py`'s existing top-level-`tests/` placement, since
`panel_base.py` is a top-level `src/` module, not under `src/ingesta/`).

New dependencies: **none.** `linearmodels>=5.3` (already in
`requirements.lock.txt`, installed as v7.0) covers `PanelOLS`/`PooledOLS`/
`RandomEffects`/`compare`; `numpy`/`scipy`/`pandas` (all already present)
cover the manual Hausman/Pesaran implementations; `pickle` is stdlib.
