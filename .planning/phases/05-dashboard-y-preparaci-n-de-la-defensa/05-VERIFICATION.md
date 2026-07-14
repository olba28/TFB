---
phase: 05-dashboard-y-preparaci-n-de-la-defensa
verified: 2026-07-14T05:22:30Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 5: Dashboard y Preparación de la Defensa Verification Report

**Phase Goal:** Un dashboard local que consume exclusivamente artefactos ya calculados responde con fluidez y fiabilidad durante la demo en directo de la defensa oral.
**Verified:** 2026-07-14T05:22:30Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Dashboard consumes only local artifacts, never the UN SDG API (DASH-01) | ✓ VERIFIED | `src/dashboard/data.py` imports only `src.db`/`pickle`; `tests/dashboard/test_no_live_api.py` (2 tests) statically scans all `src/dashboard/*.py` for `requests`/`httpx`/`urllib.request`/`src.ingesta`/`unstats.un.org` — passes. Confirmed by running the test live (not just SUMMARY claim). |
| 2 | Every heavy resource loaded via `st.cache_resource`, every tabular/array result via `st.cache_data` (DASH-02) | ✓ VERIFIED | `data.py`: `get_engine`/`load_model` decorated `@st.cache_resource`; `load_panel_clean`/`load_panel_exclusions`/`cached_bootstrap`/`cached_shap` decorated `@st.cache_data`, verified live in `tests/dashboard/test_caching.py` (7 tests, all pass). Note: `cached_shap` returns the `rf`/`explainer` objects through a `cache_data` wrapper — a design smell flagged as REVIEW.md WR-02 (non-blocking, does not violate the literal must-have since the underlying load still goes through `cache_resource`). |
| 3 | Side-by-side choropleth comparison, distinct selector keys, same year (DASH-03/D-02) | ✓ VERIFIED | `app.py` Mapa tab: `st.columns(2, gap="large")`, `key="indicator_left"`/`"indicator_right"`; `tests/dashboard/test_app.py::test_side_by_side_comparison` runs the real `AppTest` headless render and asserts both selectbox keys exist and the app raises no exception (incl. no `DuplicateWidgetID` — this exact crash was found and fixed live during 05-05's rehearsal, commit `250c8b9`). |
| 4 | Animated choropleth over all 23 years (2000–2022) with fixed color range, no flicker (DASH-04) | ✓ VERIFIED | `plots.build_choropleth` uses `animation_frame="year"`, `range_color=(df[col].min(), df[col].max())` computed over the full frame. `tests/dashboard/test_plots.py::test_choropleth_has_all_years` asserts 23 frames + fixed cmin/cmax — passes live. |
| 5 | App shows a wide single-page layout with exactly the 4 D-06 tabs | ✓ VERIFIED | `app.py`: `st.set_page_config(layout="wide")` once; `st.tabs([...])` with the exact 4 labels. `test_app.py::test_side_by_side_comparison` asserts `tab_labels == [...]` verbatim — passes. |
| 6 | App degrades gracefully with the UI-SPEC `st.error` copy on missing/corrupt artifacts | ✓ VERIFIED | Top-level `try/except` around `data.get_engine()`/`load_panel_clean` renders `ARTIFACT_ERROR_MSG` + `st.stop()`. `test_app.py::test_missing_panel_shows_ui_spec_error` monkeypatches a raising `get_engine` and asserts the verbatim error text renders — passes. |
| 7 | Cold-cache rehearsal on the presentation machine completes first render inside the <5s target and is documented (DASH-05) | ✓ VERIFIED | `figuras/plan_b/README.md` records "Cold-start time: 2.01s (target <5s)". `05-05-SUMMARY.md` documents 3 live bugs found and fixed during the rehearsal (DuplicateElementId crash, non-localhost binding, 9+min SHAP cold-start from live RF refit) with individual commits (`250c8b9`, `f6659fd`, `9d6ae4b`, `bfb5c25`, `1494e5b`) each showing a concrete before/after measurement — a credible, git-verifiable trail, not a bare claim. |
| 8 | Pre-rendered Plan B backup (4 tabs, real data) exists and is legible as a defense fallback (DASH-05/D-08) | ✓ VERIFIED | `figuras/plan_b/{01_mapa_e_indicadores,02_modelo_1,03_simulacion,04_interpretabilidad_shap,04_interpretabilidad_shap2}.png` exist (107–194KB each, distinct real content). Visually inspected: `01_mapa_e_indicadores.png` shows two real, distinct choropleths; `03_simulacion.png` shows a correctly-rendered category x-axis (`-30%`/`-20%`/`-10%`, no phantom ticks — CR-01 fix confirmed); `04_interpretabilidad_shap2.png` shows a fully legible, non-overlapping, non-clipped SHAP summary plot (CR-02 fix confirmed) after being split into 2 captures and recaptured (commit `b41fe4a`). |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/dashboard/__init__.py` | package marker | ✓ VERIFIED | exists |
| `src/dashboard/models.py` | ACTIVE_MODELS registry + INDICATOR_LABELS, no `st.*` import | ✓ VERIFIED | present, wired into `data.py`/`app.py`; no streamlit import |
| `.streamlit/config.toml` | UI-SPEC theme, no `[server]` override at plan-01 time | ✓ VERIFIED (evolved) | `[theme]` matches UI-SPEC exactly; a `[server]\naddress="localhost"` block was later added in 05-05 as a deliberate live-rehearsal fix for T-5-03 (a real bug: default `streamlit run` was NOT localhost-only) — this is an intentional, documented superset of the 05-01 must-have, not a violation |
| `src/dashboard/plots.py` | build_choropleth/build_scenario_plot/build_pdp, no `st.*` | ✓ VERIFIED | all three present; `test_plots_module_has_no_streamlit_import` passes |
| `src/dashboard/data.py` | cached loaders + cached_bootstrap/cached_shap | ✓ VERIFIED | all present with correct decorators |
| `src/dashboard/app.py` | 4-tab controller, side-by-side maps, error handling | ✓ VERIFIED | present and wired (see truths 3, 5, 6) |
| `tests/dashboard/*` (conftest, test_plots, test_caching, test_app, test_no_live_api) | full test coverage | ✓ VERIFIED | 17/17 dashboard tests pass; 109/109 full suite passes |
| `figuras/plan_b/README.md` + 5 PNG captures | Plan B index + real-data captures | ✓ VERIFIED | present, content matches README's documented filenames (README explicitly documents the SHAP tab split into 2 files) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `models.ACTIVE_MODELS[...]["pkl_path"]` | `data/modelos/model1_gdp.pkl` | `data.load_model` | ✓ WIRED | real file exists (612KB) |
| `models.ACTIVE_MODELS[...]["rf_shap_pkl_path"]` | `data/modelos/rf_shap_model.pkl` | `data.cached_shap` → `load_model` | ✓ WIRED | real file exists (91.7MB); added live during 05-05 to fix the 9-min cold-start bug |
| `app.py` Mapa tab | `plots.build_choropleth` | direct call, 2 columns | ✓ WIRED | confirmed in source + `AppTest` |
| `app.py` Simulación tab | `data.cached_bootstrap` → `plots.build_scenario_plot` | direct call chain | ✓ WIRED | confirmed in source + Plan B screenshot shows real rendered output |
| `app.py` SHAP tab | `data.cached_shap` → `shap.summary_plot` | direct call | ✓ WIRED | confirmed in source + Plan B screenshot (post-fix) shows legible output |
| `src/dashboard/*.py` | UN SDG API | (must NOT exist) | ✓ CONFIRMED ABSENT | static test passes; manual grep confirms no `requests`/`httpx`/`src.ingesta` import |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full dashboard test suite | `.venv/Scripts/python.exe -m pytest tests/dashboard -q` | 17 passed | ✓ PASS |
| Full project test suite (regression check) | `.venv/Scripts/python.exe -m pytest tests/ -q` | 109 passed | ✓ PASS |
| No-live-API static guard | (included in dashboard suite) | 2/2 pass | ✓ PASS |
| CR-01 fix (category x-axis) present in code | `grep xaxis=dict(...type="category"...)` in `plots.py` | found at line 143 | ✓ PASS |
| CR-02 fix (SHAP figure sizing) present in code | inspected `app.py:228-237` | `plot_size=` param + `tight_layout()` present | ✓ PASS |
| CR-01/CR-02 fixes visually confirmed in retaken screenshots | read `03_simulacion.png`, `04_interpretabilidad_shap2.png` | category axis correct, no overlap/clipping | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| DASH-01 | 05-01, 05-03, 05-04 | Dashboard consumes only local artifacts, no live API calls | ✓ SATISFIED | `test_no_live_api.py`, `models.py`/`data.py` docstrings + code |
| DASH-02 | 05-03 | Caching (`st.cache_data`/`st.cache_resource`) prevents freezes | ✓ SATISFIED | `test_caching.py`, cold-start 2.01s measured |
| DASH-03 | 05-04 | Side-by-side indicator comparison | ✓ SATISFIED | `test_app.py::test_side_by_side_comparison`, Plan B screenshot |
| DASH-04 | 05-02 | Temporal choropleth animation 2000–2022 | ✓ SATISFIED | `test_plots.py::test_choropleth_has_all_years` |
| DASH-05 | 05-05 | Cold-cache rehearsal + Plan B backup on presentation machine | ✓ SATISFIED | `figuras/plan_b/README.md`, 5 PNG captures, 05-05-SUMMARY.md rehearsal log |

No orphaned requirements — REQUIREMENTS.md maps exactly DASH-01..05 to Phase 5, and all 5 appear across the 5 plans' `requirements` frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/dashboard/data.py:152-207` | `cached_shap` | `@st.cache_data` returns non-copyable `rf`/`explainer` objects (REVIEW.md WR-02) | ⚠️ Warning | Deep-copies a 300-tree RF on every cache hit; wasteful but not a correctness bug. Not a phase-goal blocker. |
| `src/dashboard/data.py:140,199` | `cached_bootstrap`/`cached_shap` | Hard-coded `"Modelo 1 (PIB per cápita)"` registry key internally (REVIEW.md WR-03) | ⚠️ Warning | Undermines the D-07 "Phase 6 appends one dict entry" contract for these two functions specifically; will need a small refactor when Phase 6 (Model 2) is built. Documented, tracked, not a Phase 5 goal blocker. |
| `src/dashboard/app.py` (4 try/except blocks) | generic `ARTIFACT_ERROR_MSG` reused for unrelated failure causes (REVIEW.md WR-04) | ⚠️ Warning | Could mislead an operator diagnosing a non-panel.db failure mid-demo; graceful degradation itself still works (no raw traceback). |
| `src/dashboard/plots.py` (build_choropleth) | fixed linear `range_color` dominated by outliers (REVIEW.md WR-05) | ⚠️ Warning | Confirmed visually in `01_mapa_e_indicadores.png` — most countries render as near-identical dark color. Reduces the map's visual usefulness but the truth as literally scoped ("no flicker across frames," DASH-04) still holds; this is a UX quality issue, not a DASH-01..05 contract violation. |
| `src/interpret.py:164-179` | no validation that externally-supplied `rf`'s feature columns match freshly-built `X` (REVIEW.md WR-06) | ⚠️ Warning | Latent risk if `panel.db` is regenerated with a different `region` category set; not triggered by current data. |
| `src/dashboard/data.py:178-207` | `check_additivity=False` silently applied with no UI-visible caveat (REVIEW.md WR-07) | ⚠️ Warning | Transparency gap for the SHAP tab; does not affect dashboard fluidity/reliability (the phase goal). |
| `tests/dashboard/test_plots.py` | no regression test for the CR-01 x-axis category-type fix | ℹ️ Info | REVIEW.md explicitly suggested adding `assert fig.layout.xaxis.type == "category"`; the fix (`plots.py:143`) is present and confirmed working, but no automated regression test guards against it silently regressing later. |

No 🛑 Blockers found. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in any phase-modified file.

### Human Verification Required

None. DASH-05's inherently-human items (wall-clock cold-start timing, visual screenshot legibility) were already executed as interactive `checkpoint:human-verify` gates during 05-05's execution (not autonomous), with a git-verifiable trail of live bug fixes and a human-rejected-then-retaken screenshot batch (the first Plan B attempt produced 4 identical 9,669-byte blank placeholders, caught and redone). The subsequent code-review Critical fixes (CR-01, CR-02) were verified by this agent directly: (a) the fix code is present in the current `plots.py`/`app.py`, (b) the Plan B screenshots were retaken after the fixes (commit `b41fe4a`, file mtimes 07:09–07:17 vs. the earlier 00:43–00:44 batch), and (c) visual inspection of the retaken screenshots confirms both defects are gone.

### Gaps Summary

No gaps. All 5 DASH requirements are satisfied with live, re-run evidence (109/109 tests passing at verification time, not just per SUMMARY claims). Both Critical findings from `05-REVIEW.md` (CR-01 misleading numeric x-axis, CR-02 broken/overlapping SHAP screenshot) are confirmed fixed in the current source and in the retaken Plan B captures — the code-review pass did its job and the fixes are real, not just narrated. The 7 Warning-level and 2 Info-level findings from `05-REVIEW.md` remain open (as expected — they were not required to be fixed before phase completion) and are re-surfaced above as non-blocking anti-patterns for awareness ahead of Phase 6 (Model 2), particularly WR-03's hard-coded registry key, which will need addressing when Model 2 is added to `ACTIVE_MODELS`.

---

_Verified: 2026-07-14T05:22:30Z_
_Verifier: Claude (gsd-verifier)_
