---
phase: 06-modelo-2-productividad-agr-cola-stretch
verified: 2026-07-15T12:00:00Z
status: passed
score: 3/3 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 6: Modelo 2 — Productividad Agrícola (stretch) Verification Report

**Phase Goal:** Si el avance del proyecto lo permite, la misma metodología del Modelo 1 se extiende al indicador de productividad agrícola (2.3.1), reutilizando la infraestructura compartida en lugar de reimplementarla.
**Verified:** 2026-07-15
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `model2_agri.py` reutiliza `panel_base.py` sin duplicar lógica y aplica la misma especificación metodológica (efectos fijos bidireccionales, SEs clustered, mismos diagnósticos) que el Modelo 1 | ✓ VERIFIED | `src/model2_agri.py::fit_model2` calls `panel_base.fit_panel_model(..., entity_effects=True, time_effects=True)`, `panel_base.hausman_test`, `panel_base.pesaran_cd_test`, `panel_base.choose_cov_type` unmodified. Live re-run confirms: `cov_type=clustered`, Hausman stat=5.995 (df=1, p=0.0143), Pesaran CD p=0.867 (see `data/modelos/model2_agri.pkl` summary reproduced below). No `PanelOLS(`/manual chi2/pinv re-implementation found in `model2_agri.py` (only `RandomEffects` used directly for the Hausman RE-input, matching Model 1's own `compare_specifications` pattern). |
| 2 | Si la muestra de países se reduce por la cobertura del indicador 2.3.1, la limitación queda documentada explícitamente con una tabla de cobertura/exclusiones específica del Modelo 2 | ✓ VERIFIED | Live query against `data/panel.db`: `model2_coverage` table exists with columns `country_code, years_available, included, reason` (panel_exclusions style), 49 total rows (every country with any 2.3.1 data), exactly **39 marked `included=1`** matching D-01/MODEL2-02's documented figure. |
| 3 | El dashboard, la simulación contrafactual y el análisis SHAP incluyen una vista o selector que permite explorar los resultados del Modelo 2 junto a los del Modelo 1 | ✓ VERIFIED | `src/dashboard/models.py::ACTIVE_MODELS` has both model entries; `src/dashboard/app.py` sidebar `st.sidebar.selectbox("Modelo activo", ..., key="active_model_name")` drives `ACTIVE_MODEL` read by all 4 tabs; `cached_bootstrap`/`cached_shap` in `src/dashboard/data.py` take `active_model_name` and index the registry with it (no hardcoded `"Modelo 1 ..."` literal remains — confirmed via grep). **CR-01 fix independently re-verified** (see below): `cached_bootstrap` now restricts `df` to the fitted model's own country coverage before resampling — code re-read directly (not summary-trusted) and a dedicated regression test (`test_cached_bootstrap_restricts_df_to_fitted_model_coverage`) passes. |

**Score:** 3/3 truths verified

### Critical-Fix Re-Verification (CR-01, per explicit user request)

The phase's REVIEW/REVIEW-FIX cycle found and claimed to fix a critical bug: the dashboard's live bootstrap (`src/dashboard/data.py::cached_bootstrap`) was resampling from the full unfiltered panel (~171-215 countries) instead of Model 2's actual 39-country fitted coverage. This was independently re-checked against the CURRENT code (not the fix report's narrative):

- Read `src/dashboard/data.py::cached_bootstrap` directly (current state, commit `e5cdef0` and later): confirms the function now computes `fitted_entities = fitted.fitted_values.index.get_level_values("country_code").unique()` and applies `df = df[df["country_code"].isin(fitted_entities)]` **before** calling `simulate.bootstrap_counterfactual`.
- Traced into `src/simulate.py::bootstrap_counterfactual`: both `resample_entities` (the block-bootstrap draw) and the `baseline = df[df["year"]==baseline_year]...` computation operate on the SAME `df` passed in — since `cached_bootstrap` now passes the pre-restricted `df`, both the resampling population and the baseline are correctly scoped to the fitted model's actual entities. This closes both sub-issues CR-01 described (the resample-population issue AND the "more visibly wrong" baseline/out-of-sample-extrapolation issue).
- Ran `tests/dashboard/test_caching.py::test_cached_bootstrap_restricts_df_to_fitted_model_coverage` in isolation and as part of the full suite — PASSED. This test constructs a 4-country synthetic panel with a fake fitted model covering only 2 of them and asserts the `df` actually captured by a monkeypatched `simulate.bootstrap_counterfactual` contains exactly those 2 countries — this is a genuine regression test on the actual resampled entity set, not merely which `.pkl` path was requested.
- Live full pipeline check (`data/modelos/model2_agri.pkl` deserialized): `fitted_values` carries the expected `(country_code, year)` MultiIndex with 39 unique entities, confirming the assumption `cached_bootstrap`'s fix relies on (`fitted.fitted_values.index.get_level_values("country_code")`) holds for the real artifact, not just a test double.

**Conclusion: the CR-01 fix holds** — verified against current code and a real regression test, not the fix report's assertions alone.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/panel_base.py` (`filter_by_min_years`) | New pure sibling coverage helper, D-01/D-02 | ✓ VERIFIED | Present at lines 58-93, pure (no I/O, no `warnings.warn`), does not reference `filter_by_exclusions`/`panel_exclusions`/`indicator_code`. |
| `tests/test_panel_base.py` | Unit tests for `filter_by_min_years` | ✓ VERIFIED | 4 tests present and passing (`test_filter_by_min_years_*`). |
| `src/model2_agri.py` | Full Model 2 pipeline module | ✓ VERIFIED | All documented functions present (`build_model2_panel`, `build_coverage_table`, `fit_model2`, `run_robustness_no_covid`, `run_bootstrap`, `run_heterogeneity`, `run_shap`, `serialize_artifacts`, `write_coverage_table`, `_main`); calls shared modules unmodified; no re-implemented PanelOLS/Hausman/Pesaran/RF/SHAP math. |
| `tests/test_model2_agri.py` | Unit + orchestration tests | ✓ VERIFIED | 12 tests present and passing, covering both pure bookkeeping and (post-review-fix) the 7 previously-untested orchestration functions. |
| `data/modelos/model2_agri.pkl` | Fitted `PanelEffectsResults`, dep_var=2.3.1 | ✓ VERIFIED | Live-deserialized: `isinstance(m, PanelEffectsResults)` True; `6.4.2` coefficient present; `Included effects: Entity, Time`; `Cov. Estimator: Clustered`. |
| `data/modelos/rf_shap_model_m2.pkl` | Fitted `RandomForestRegressor` | ✓ VERIFIED | Live-deserialized: `isinstance(rf, RandomForestRegressor)` True. |
| `data/panel.db` (`model2_coverage` table) | Coverage/exclusions table, D-03 | ✓ VERIFIED | Live query: columns `country_code, years_available, included, reason`; 49 rows; 39 `included=1`. |
| `src/dashboard/models.py` | `ACTIVE_MODELS` registry with Model 2 entry | ✓ VERIFIED | Both `"Modelo 1 (PIB per cápita)"` and `"Modelo 2 (Productividad agrícola)"` keys present; Model 2 entry has correct `dep_var`, `pkl_path`, `rf_shap_pkl_path`, matching `feature_vars` to Model 1's, plus a `reduced_coverage: bool` field added by the review fix (WR-02). |
| `src/dashboard/data.py` (`cached_bootstrap`/`cached_shap`) | Parameterized on `active_model_name` | ✓ VERIFIED | Both functions accept `active_model_name: str` and use it to index `models.ACTIVE_MODELS`; zero occurrences of the hardcoded `ACTIVE_MODELS["Modelo 1 ..."]` literal remain (confirmed via grep on current file). |
| `src/dashboard/app.py` | Sidebar selector + D-08 caption + dynamic labels | ✓ VERIFIED | `st.sidebar.selectbox("Modelo activo", ..., key="active_model_name")` present; `MODEL2_COVERAGE_CAPTION` rendered on all 4 tabs, gated by the registry's `reduced_coverage` flag (post-fix, not brittle string-matching); Mapa tab / Simulación tab labels are dynamic (`ACTIVE_MODEL_NAME`/`models.INDICATOR_LABELS`), old Model-1-hardcoded strings confirmed absent via grep. |
| `tests/dashboard/test_app.py`, `tests/dashboard/test_caching.py` | AppTest + unit coverage for selector/caption/propagation | ✓ VERIFIED | All present and passing, including the CR-01 regression test. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `filter_by_min_years` (06-01) | `src/model2_agri.py::build_model2_panel` | direct function call | ✓ WIRED | `build_model2_panel` calls `panel_base.filter_by_min_years(panel_clean, DEP_VAR, [INDEP_VAR], min_years)`. |
| `data/modelos/model2_agri.pkl` / `rf_shap_model_m2.pkl` | dashboard `ACTIVE_MODELS` registry | `pkl_path`/`rf_shap_pkl_path` string match | ✓ WIRED | Registry paths match `serialize_artifacts`'s default output paths exactly. |
| `model2_coverage` table | dashboard | (not directly read by app.py; Model 2's runtime coverage count is instead recomputed live via `panel_base.filter_by_min_years`, per WR-03 fix) | ✓ WIRED (via equivalent live computation) | `app.py::_model2_coverage_caption` calls `panel_base.filter_by_min_years` directly against the loaded `df` rather than reading the `model2_coverage` SQL table — functionally equivalent (same underlying function, same result), and more robust to data drift (WR-03's whole point). Deviates from the plan's literal "table is read by dashboard" key_link wording but achieves the same "N is visible and accurate" goal by a strictly better mechanism (no separate query needed since `panel_clean`/`filter_by_min_years` are already loaded/cached). Not a gap. |
| sidebar `selectbox` | `data.cached_bootstrap`/`data.cached_shap` | `active_model_name=ACTIVE_MODEL_NAME` kwarg at both call sites | ✓ WIRED | Confirmed via grep (2 matches) and via `test_cached_bootstrap_honors_active_model_name`/`test_cached_bootstrap_restricts_df_to_fitted_model_coverage` passing. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Model 2 pkl round-trips to correct types | `pickle.load` + `isinstance` check on both artifacts | `PanelEffectsResults` / `RandomForestRegressor` confirmed | ✓ PASS |
| `model2_coverage` documents exactly 39 included countries | `SELECT COUNT(*) FROM model2_coverage WHERE included=1` | 39 | ✓ PASS |
| `filter_by_min_years` unit tests | `pytest tests/test_panel_base.py -k filter_by_min_years` | 4 passed (via full suite run) | ✓ PASS |
| `model2_agri.py` orchestration tests | `pytest tests/test_model2_agri.py` | 12 passed | ✓ PASS |
| Dashboard AppTest suite (selector, caption, propagation) | `pytest tests/dashboard/` | 21 tests, all passed (see note on ordering below) | ✓ PASS |
| Full project suite (natural discovery order) | `pytest -q` (repo root, no explicit paths) | **132 passed**, 0 failed | ✓ PASS |

**Note on test-ordering flakiness (Info, not a blocker):** Running `pytest tests/test_panel_base.py tests/test_model2_agri.py tests/dashboard/` as explicit space-separated paths triggered a `Windows fatal exception: code 0x80000003` crash partway through `tests/dashboard/test_app.py` (at `test_missing_panel_shows_ui_spec_error`, which passed both in isolation and as part of `tests/dashboard/test_app.py` run alone). The crash did NOT reproduce when running the full suite via bare `pytest -q` (natural collection order, 132/132 passed) or when running `tests/dashboard/test_app.py` alone (5/5 passed). This looks like a native-library / thread-teardown interaction specific to a particular test-collection ordering (Streamlit `AppTest` runs the app script in a separate thread; SQLite in-memory engines are thread-local — already documented as a known gotcha in 06-REVIEW-FIX.md's WR-03 notes) rather than a logic defect in Phase 6's code. Recorded here for visibility; does not block the phase goal since the standard `pytest -q` invocation (and CI's presumed invocation) passes cleanly.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MODEL2-01 | 06-01, 06-02 | Modelo 2 reutiliza `panel_base.py` con la misma metodología que Modelo 1 | ✓ SATISFIED | `fit_model2` calls `fit_panel_model`/`hausman_test`/`pesaran_cd_test`/`choose_cov_type` unmodified; live diagnostics reproduced above. |
| MODEL2-02 | 06-01, 06-02 | Documenta limitaciones de cobertura de países para 2.3.1 | ✓ SATISFIED | `model2_coverage` table (39/49 included) + `filter_by_min_years` helper, both live-verified. |
| MODEL2-03 | 06-02, 06-03 | Simulación, SHAP y dashboard se extienden a Modelo 2 | ✓ SATISFIED | `run_bootstrap`/`run_heterogeneity`/`run_shap` in `model2_agri.py` (offline pipeline) + dashboard sidebar selector wired end-to-end with CR-01 fix re-verified. |

No orphaned requirements: REQUIREMENTS.md's traceability table maps MODEL2-01/02/03 to Phase 6 only, and all three appear in at least one plan's `requirements:` frontmatter field (06-01: MODEL2-01/02; 06-02: MODEL2-01/02/03; 06-03: MODEL2-03).

### Anti-Patterns Found

None. Scanned `src/model2_agri.py`, `src/dashboard/app.py`, `src/dashboard/data.py`, `src/panel_base.py` for `TODO|FIXME|XXX|TBD|HACK|PLACEHOLDER` and empty-implementation patterns — no debt markers found (one regex false-positive on ordinary Spanish prose in `app.py`, manually confirmed benign).

## Gaps Summary

None. All 3 ROADMAP Success Criteria are verified against the current codebase (not SUMMARY narrative alone). The user-flagged CR-01 critical fix was independently re-traced through `src/dashboard/data.py` and `src/simulate.py` and confirmed to hold, backed by a real regression test that asserts on the actual resampled entity set. Full project test suite passes (132/132) under normal invocation.

---

*Verified: 2026-07-15*
*Verifier: Claude (gsd-verifier)*
