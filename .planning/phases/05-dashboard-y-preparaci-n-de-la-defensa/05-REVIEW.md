---
phase: 05-dashboard-y-preparaci-n-de-la-defensa
reviewed: 2026-07-14T09:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - .streamlit/config.toml
  - figuras/plan_b/README.md
  - src/dashboard/__init__.py
  - src/dashboard/app.py
  - src/dashboard/data.py
  - src/dashboard/models.py
  - src/dashboard/plots.py
  - src/interpret.py
  - tests/dashboard/__init__.py
  - tests/dashboard/conftest.py
  - tests/dashboard/test_app.py
  - tests/dashboard/test_caching.py
  - tests/dashboard/test_no_live_api.py
  - tests/dashboard/test_plots.py
findings:
  critical: 2
  warning: 7
  info: 2
  total: 11
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-07-14T09:00:00Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the Phase 5 Streamlit dashboard (`src/dashboard/*.py`), the `src/interpret.py` changes made during the 05-05 live rehearsal (pre-fitted RF loading, `check_additivity=False`, sampled SHAP explanation), `.streamlit/config.toml`, the Plan B fallback screenshots, and the full `tests/dashboard/` suite.

The two specific items flagged by the task brief check out clean:
- `interpret.shap_analysis`'s new `rf`/`explain_sample_size`/`check_additivity` parameters all default to values that reproduce the pre-rehearsal production behavior (`rf=None` → fresh fit, `check_additivity=True` → SHAP's own default, `explain_sample_size=None` → full sample); no caller that omits them is affected.
- `.streamlit/config.toml`'s `[server]\naddress = "localhost"` is syntactically correct and matches the project's documented local-only threat mitigation (T-5-03).

However, the actual delivered artifacts surfaced two verifiable rendering defects, plus several design/consistency issues in `data.py`/`app.py`/`plots.py`/`interpret.py` that were not caught by the existing test suite (the tests check structural shape — trace lengths, cache-type decorators, color values — but never inspect axis typing, error-message specificity, or cross-module hard-coding). Notably, the Plan B fallback screenshots (`figuras/plan_b/*.png`) — the tribunal's safety net if the live demo fails — themselves contain visible rendering bugs, which is a serious finding given their purpose.

## Critical Issues

### CR-01: `build_scenario_plot`'s x-axis is not pinned to a category type, producing a misleading numeric axis with phantom scenario ticks

**File:** `src/dashboard/plots.py:108-145`
**Issue:** `build_scenario_plot` builds `x=labels` from percent-formatted strings (`f"{pct:+.0%}"` → `"-30%"`, `"-20%"`, `"-10%"`) and never sets an explicit x-axis type. The shipped Plan B screenshot (`figuras/plan_b/03_simulacion.png`), captured against the real production data, shows the rendered chart with x-axis ticks at `-30, -25, -20, -15, -10` — a continuous, evenly-spaced numeric axis with the `%` sign stripped and two phantom tick positions (`-25`, `-15`) that have no underlying scenario/data point at all (only 3 markers exist, at -30/-20/-10). This is empirical proof that Plotly is auto-inferring a linear/continuous axis instead of a discrete category axis, which is confusing and misleading for a chart whose entire point is "three discrete counterfactual scenarios" — exactly the kind of thing a tribunal member would notice and question.
**Fix:**
```python
fig.update_layout(
    title=title,
    xaxis_title="Escenario (reducción del estrés hídrico)",
    yaxis_title="Efecto simulado sobre la variable dependiente",
    xaxis=dict(type="category"),
    margin=_FIGURE_MARGIN,
)
```
Also add a regression test asserting `fig.layout.xaxis.type == "category"` (or that `fig.data[0].x` renders with exactly `len(results)` category positions), since none of the current `test_scenario_plot_*` tests check axis typing.

### CR-02: SHAP tab's Plan B fallback screenshot is visibly broken (clipped/overlapping content)

**File:** `src/dashboard/app.py:228-231`; `figuras/plan_b/04_interpretabilidad_shap.png`
**Issue:** The delivered `figuras/plan_b/04_interpretabilidad_shap.png` — the artifact that stands in for the live demo if it fails during the defense — shows a SHAP summary plot with a duplicated, overlapping "High" colorbar label, a y-axis tick ("0.8") overlapping the "6.4.2" feature-name label, and content (additional feature rows, e.g. "region_Latin America and the Caribbean") cut off at the bottom edge of the image. This directly violates the capture contract documented in `figuras/plan_b/README.md` ("Capturar cada una de las 4 pestañas después de que todos los datos/gráficos hayan renderizado por completo... una captura a mitad de carga se ve poco profesional ante un tribunal"). Root cause is either (a) `app.py`'s `fig_shap = plt.figure()` followed by `shap.summary_plot(shap_values, X_shap, show=False)` not being captured/screenshotted after full layout settles, or (b) the screenshot itself was taken as a partial-viewport capture rather than a full-page capture. Either way, the artifact as committed is not fit for its stated purpose.
**Fix:** Before recapturing, explicitly size the matplotlib figure for the number of features being displayed (SHAP's own `plot_size="auto"` logic sizes height as `len(feature_order) * 0.4 + 1.5` inches, but only resizes the *current* figure — verify `st.pyplot(fig_shap, clear_figure=False)` isn't truncating), e.g.:
```python
n_features = X_shap.shape[1]
fig_shap = plt.figure(figsize=(10, max(6, 0.4 * n_features + 2.5)))
shap.summary_plot(shap_values, X_shap, show=False)
st.pyplot(fig_shap)
plt.close(fig_shap)
```
Then recapture `04_interpretabilidad_shap.png` as a full-page screenshot (scroll-to-bottom or "Print to PDF" full page, not a viewport crop) and verify no overlapping/duplicated legend elements before committing it.

## Warnings

### WR-01: `plots.build_pdp` is dead code — never invoked by the actual dashboard, contradicting the phase's own documentation

**File:** `src/dashboard/app.py:208-233`; `src/dashboard/plots.py:148-162`
**Issue:** `05-02-SUMMARY.md` explicitly records `affects: ["05-04 (... SHAP tab consumes build_pdp)"]`, and `05-04-PLAN.md`'s Task 3 `read_first` lists `src/dashboard/plots.py (build_scenario_plot, build_pdp)` as a dependency for the SHAP tab. The actual `tab_shap` body in `app.py` only renders the VIF table and `shap.summary_plot` — `plots.build_pdp`/`interpret.partial_dependence_plots` is never called anywhere in `src/dashboard/`. `build_pdp` is exercised only by its own unit test (`test_build_pdp_delegates`), never by the running application. This is either a silently dropped requirement (INTERP-05's partial-dependence deliverable, expected in the dashboard per the phase's own cross-plan documentation) or a stale forward-reference in `05-02-SUMMARY.md` that was never corrected — either way, it's an inconsistency between what the project's own artifacts claim was delivered and what `app.py` actually does.
**Fix:** Either wire `plots.build_pdp` into the "Interpretabilidad (SHAP)" tab (e.g., one `PartialDependenceDisplay` per numeric predictor, embedded via `st.pyplot`), or update `05-02-SUMMARY.md`/`05-04-PLAN.md` to explicitly record the decision to scope PDP out of the dashboard, so the docs stop asserting a delivered feature that doesn't exist in `app.py`.

### WR-02: `cached_shap` returns non-copyable resource objects (`RandomForestRegressor`, `shap.TreeExplainer`) from an `@st.cache_data` function, contradicting the module's own documented cache-type split

**File:** `src/dashboard/data.py:152-207`
**Issue:** The module docstring (lines 9-13) is explicit: `st.cache_resource` is for "objects that are shared/non-copyable (the SQLAlchemy Engine, a fitted PanelEffectsResults/RandomForestRegressor)" and `st.cache_data` is for "results that can be safely copied (DataFrames, bootstrap effect arrays, SHAP values)". `cached_shap` is decorated with `@st.cache_data` yet returns `(rf, shap_values, X, explainer)` — `rf` is precisely the `RandomForestRegressor` class the docstring calls out as needing `cache_resource`, and `explainer` is a `shap.TreeExplainer` wrapping the same fitted trees. `st.cache_data` deep-copies its return value on every cache hit, so every rerun that hits this cache silently deep-copies a 300-tree RandomForest plus a TreeExplainer for no benefit — `_explainer` is even discarded unused by the caller in `app.py:222`. This is a real violation of the pattern this same file asserts elsewhere, not just a style nit — it's the exact anti-pattern the docstring/05-RESEARCH.md Pitfall 1 was written to prevent.
**Fix:** Split the return: cache the shared model/explainer objects (`rf`, `explainer`) via a small `@st.cache_resource`-wrapped helper, and keep only the copyable `shap_values`/`X` under `@st.cache_data`; or explicitly document/justify why the RF and explainer are cheap enough to deep-copy here despite the stated convention.

### WR-03: `cached_bootstrap`/`cached_shap` hard-code the model registry key `"Modelo 1 (PIB per cápita)"` internally, undermining the documented D-07 extensibility contract

**File:** `src/dashboard/data.py:140,199`
**Issue:** `models.py`'s own docstring states: "Phase 6 adds Model 2 ... by appending one more entry to `ACTIVE_MODELS` — it never needs to restructure `src/dashboard/app.py` or any tab-rendering code, because every tab already reads its `dep_var`/`indep_var`/`feature_vars`/`pkl_path` from this registry rather than from literals scattered through the app." This is false for the Simulación/SHAP tabs: `cached_bootstrap` (`data.py:140`) and `cached_shap` (`data.py:199`) both hard-code the literal string `"Modelo 1 (PIB per cápita)"` to look up `pkl_path`/`rf_shap_pkl_path` from `models.ACTIVE_MODELS`, instead of accepting the path as a parameter from the caller (which already has `ACTIVE_MODEL` in scope in `app.py`). When Phase 6 adds `"Modelo 2 (Productividad agrícola)"`, these two functions cannot be reused as-is — they will keep loading Model 1's artifacts regardless of which model the caller intends, silently producing wrong results (bootstrap/SHAP for Model 1 shown under a "Model 2" label) rather than an error, unless `data.py` itself is modified.
**Fix:** Add a `pkl_path`/`rf_shap_pkl_path` (or `model_name`) parameter to `cached_bootstrap`/`cached_shap`, e.g.:
```python
@st.cache_data
def cached_bootstrap(dep_var, indep_var, pkl_path, reduction_pcts=..., n_replicas=8, seed=42): ...
    fitted = load_model(pkl_path)
```
and have `app.py` pass `ACTIVE_MODEL["pkl_path"]` explicitly — matching the pattern already used for `dep_var`/`indep_var`/`feature_vars`.

### WR-04: All four top-level `try/except Exception` blocks in `app.py` show the same generic "panel.db missing" message regardless of which artifact actually failed, and swallow the exception with no logging

**File:** `src/dashboard/app.py:70-75,148-169,172-206,208-233`
**Issue:** `ARTIFACT_ERROR_MSG` explicitly says "Verifica que 'data/panel.db' existe y contiene la tabla 'panel_clean'". This is reused verbatim for the top-level panel load AND for the Modelo 1 tab's `.pkl` load, the Simulación tab's live bootstrap recompute, and the SHAP tab's VIF/SHAP recompute. A genuinely different failure (e.g. `data/modelos/rf_shap_model.pkl` missing/corrupt, or a `simulate.bootstrap_counterfactual` runtime error unrelated to `panel.db`) would still show "Verifica que 'data/panel.db' existe..." — actively misleading during the live demo or a post-mortem, since the operator would check the wrong file. None of the four `except Exception:` blocks logs or surfaces the actual exception (no `logging`, no `st.exception(e)` even behind a debug flag), so there is no way to diagnose a real failure from the rendered UI alone.
**Fix:** Use tab-specific messages (or at minimum interpolate the failing artifact name), and log the underlying exception for operator diagnosis, e.g.:
```python
except Exception as exc:
    logging.getLogger(__name__).exception("Modelo 1 tab failed to load %s", ACTIVE_MODEL["pkl_path"])
    st.error(f"No se pudo cargar el Modelo 1 ({ACTIVE_MODEL['pkl_path']}). ...")
```

### WR-05: `build_choropleth`'s fixed linear `range_color` is dominated by extreme outliers, making most countries visually indistinguishable

**File:** `src/dashboard/plots.py:75-86`
**Issue:** `range_color=(df[indicator_col].min(), df[indicator_col].max())` is a plain linear range across the full 2000-2022 history. The shipped `figuras/plan_b/01_mapa_e_indicadores.png` shows the real consequence: the 6.4.2 (water stress) colorbar spans roughly 0-3000+ and the 6.4.1 colorbar spans roughly 0-1000+, so nearly every country renders as the same dark, near-zero-intensity color — the map conveys almost no information for the vast majority of countries, only for the handful of extreme outliers pulling the scale. This is the dashboard's headline visualization (D-01/D-02) and, as committed, it is not usable for the comparison it is meant to support.
**Fix:** Consider a `color_continuous_scale` with a perceptually-robust transform for skewed data (e.g. clip at a high percentile, or a `np.log1p` transform with a documented caveat caption), rather than the raw global min/max.

### WR-06: `shap_analysis`'s externally-supplied `rf` is never validated against the freshly-built `X`'s columns

**File:** `src/interpret.py:164-179`
**Issue:** When `rf is not None` (the `cached_shap` demo path), the function skips fitting and proceeds directly to `explainer = shap.TreeExplainer(rf)` / `explainer.shap_values(X, ...)`, where `X` is freshly one-hot-encoded (`pd.get_dummies(..., columns=["region"], drop_first=True)`) from whatever `df` is currently loaded. There is no assertion that `X.columns` matches the feature set/order `rf` was trained on. If `data/panel.db` is ever regenerated with a different set of `region` categories present in the complete-case subset (e.g. a region drops out, or `drop_first` picks a different reference category), `pd.get_dummies` will silently produce a different column set. If the column *count* happens to still match, scikit-learn's feature-name check only warns (does not error) on a name mismatch in many versions, and the resulting SHAP values would be silently wrong (attributed to the wrong feature) rather than raising — a serious risk for a document whose central claim is interpretability of the water-stress relationship.
**Fix:** Assert column identity before explaining, e.g.:
```python
if rf is not None and hasattr(rf, "feature_names_in_"):
    missing = set(rf.feature_names_in_) - set(X.columns)
    extra = set(X.columns) - set(rf.feature_names_in_)
    if missing or extra:
        raise ValueError(f"rf/X feature mismatch: missing={missing}, extra={extra}")
    X = X[list(rf.feature_names_in_)]  # enforce identical order
```

### WR-07: `check_additivity=False` is silently applied in the live demo path with no user-visible caveat

**File:** `src/dashboard/data.py:178-207`; `src/dashboard/app.py:208-233`
**Issue:** The demo path deliberately disables SHAP's own internal consistency check (values sum to model output) for performance reasons — a reasonable engineering trade-off, well documented in code comments — but nothing in the rendered "Interpretabilidad (SHAP)" tab tells the (tribunal) viewer that this specific run skipped that verification. For an academic deliverable whose defense hinges on methodological rigor, silently dropping a named correctness check without any UI-visible caveat is a transparency gap, distinct from the "sampling caveat" already shown via the Plan-B-screenshots note in the README.
**Fix:** Add a small `st.caption` in the SHAP tab noting that the live demo skips the additivity re-check for performance, with a pointer to the full-fidelity notebook run (mirrors the existing sampling-size framing already present in the code comments, just not surfaced to the UI).

## Info

### IN-01: Unused `y`/`explainer` values on the pre-fitted-`rf` path

**File:** `src/interpret.py:162`; `src/dashboard/app.py:222`
**Issue:** `y = complete[dep_var]` is computed unconditionally in `shap_analysis` but only used inside the `if rf is None:` branch — harmless, but slightly wasteful/confusing on the `rf is not None` path. Separately, `cached_shap`'s fourth return value (`explainer`) is unpacked as `_explainer` in `app.py:222` and never used.
**Fix:** Move `y = complete[dep_var]` inside the `if rf is None:` block; consider dropping `explainer` from `cached_shap`'s public return shape if the caller never needs it (or use it to also render `shap.plots.bar`/dependence plots, addressing WR-01's PDP gap with the SHAP explainer's own tooling instead).

### IN-02: Hard-coded relative artifact paths assume the process CWD is the project root

**File:** `src/dashboard/data.py:55`; `src/dashboard/models.py:45-46`
**Issue:** `db.get_engine("data/panel.db")` and the `data/modelos/*.pkl` paths in `models.py` are relative literals. This matches the project's existing convention elsewhere, but nothing guards against `streamlit run` being invoked from a different working directory (a plausible mistake during a live defense), in which case the top-level try/except would correctly show `ARTIFACT_ERROR_MSG`, but the message ("Verifica que 'data/panel.db' existe...") doesn't hint that the actual problem could be an unexpected working directory rather than a truly missing file.
**Fix:** Not required to change (consistent with the rest of the codebase), but consider resolving paths relative to the module file (`Path(__file__).resolve().parents[2] / "data" / "panel.db"`) or documenting the required launch CWD in the run command used for the defense.

---

_Reviewed: 2026-07-14T09:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
