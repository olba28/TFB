# Phase 6: Modelo 2 — Productividad Agrícola (stretch) - Pattern Map

**Mapped:** 2026-07-14
**Files analyzed:** 7 (1 new module/notebook, 3 modified files, 1 new helper inside an existing file, 1 new pkl artifact, plus dashboard call-site edits)
**Analogs found:** 7 / 7 (this phase is explicitly parametric reuse — every analog is the exact same function called with different arguments, not a structurally different pattern)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/panel_base.py::filter_by_min_years` (new function, existing file) | utility (data filter) | transform | `src/panel_base.py::filter_by_exclusions` (same file, lines 36-55) | exact — same file, same role, sibling function |
| `src/model2_agri.py` or `notebook/6_1_modelo2_agricultura.ipynb` (new, name at Claude's discretion) | service/orchestration (notebook-driven pipeline stage) | batch / CRUD (fit → diagnose → simulate → interpret → serialize) | `notebook/3_1_modelo1_pib.ipynb` (Model 1's equivalent orchestration notebook) | exact — same phase-shape, different dep_var only |
| `data/modelos/model2_agri.pkl` (new artifact) | config/data (serialized model) | file-I/O | `data/modelos/model1_gdp.pkl` (produced by Phase 3, loaded via `src/dashboard/data.py::load_model`) | exact |
| `src/dashboard/models.py` (modify: complete the commented Model 2 stub) | config | CRUD (dict registry) | same file, `"Modelo 1 (PIB per cápita)"` entry (lines 33-47) | exact — stub already written for this exact edit |
| `src/dashboard/app.py` (modify: add sidebar selectbox, replace hardcoded `ACTIVE_MODEL_NAME`) | controller (Streamlit page) | request-response (rerun-on-interaction) | same file, `ARTIFACT_ERROR_MSG` / `ACTIVE_MODEL_NAME` lines (61-78) | exact — same file, editing its own existing pattern |
| `src/dashboard/data.py` (possible modify: `cached_bootstrap`/`cached_shap` currently hardcode `"Modelo 1 (PIB per cápita)"` lookup for `fitted`/`rf`) | service (cached data-access layer) | CRUD / cache | same file, `cached_bootstrap` (lines 101-149), `cached_shap` (lines 152-207) | exact — same file, needs `active_model_name` parameterization |
| Memoria — sección de limitaciones del Modelo 2 (docs, out of code scope) | n/a (documentation) | n/a | n/a | no code analog — handled at write-up time, not in PATTERNS.md scope |

## Pattern Assignments

### `src/panel_base.py::filter_by_min_years` (new helper — D-02)

**Analog:** `src/panel_base.py::filter_by_exclusions` (same file, lines 36-55)

**Signature/contract pattern to copy** (lines 36-55):
```python
def filter_by_exclusions(
    df: pd.DataFrame,
    exclusions: pd.DataFrame,
    dep_var: str,
    indep_vars: list[str],
) -> pd.DataFrame:
    """Drop a country's ENTIRE row set if it fails the 70%-coverage
    threshold on ``dep_var`` OR any of ``indep_vars`` (D-01/D-02) -- a
    country either fully survives (all its rows kept) or is fully dropped
    (zero rows), never partially filtered row-by-row.

    ``df`` must still contain a plain ``country_code`` column (not yet
    indexed) -- indexing into the ``(entity, time)`` MultiIndex happens
    inside ``fit_panel_model``/``compare_specifications``, not here.
    """
    variables = [dep_var, *indep_vars]
    excluded_countries = set(
        exclusions.loc[exclusions["indicator_code"].isin(variables), "country_code"]
    )
    return df[~df["country_code"].isin(excluded_countries)]
```

**What to change for `filter_by_min_years`** (per D-02, 06-CONTEXT.md):
- Same public-function shape: takes an un-indexed `df` with a plain `country_code` column, `dep_var`, `indep_vars`, returns a filtered `df` — country either fully kept or fully dropped (same country-level, never row-level, exclusion semantics as `filter_by_exclusions`).
- Different input: computed **directly on `panel_clean`** (via `df.groupby("country_code")` counting non-null `year`s per `[dep_var, *indep_vars]`), NOT on the `panel_exclusions` table (that table is fixed to the 70% criterion — D-02 explicitly forbids reusing it here).
- New parameter: `min_years: int` (default should NOT silently duplicate the 70% threshold's implicit default — make it explicit, e.g. `min_years: int = 3` documented as "Model 2's own criterion, D-01").
- Docstring must state the two criteria "coexist as separate explicit functions" (D-02) — do not have `filter_by_min_years` call or wrap `filter_by_exclusions`.
- Keep same warn/return conventions as the rest of the file: pure function, no I/O, no `warnings.warn` needed here (this isn't a numerically-degenerate-statistic case like Hausman/Pesaran — unlike those, this is deterministic bookkeeping) — but DO follow the module-level pattern of copious docstrings citing the D-xx decision that motivates each design choice (see every function in this file).

**Everything else in `panel_base.py`** (`fit_panel_model`, `hausman_test`, `pesaran_cd_test`, `choose_cov_type`) is invoked **unmodified** with `dep_var="2.3.1"`, `indep_vars=["6.4.2"]` — no pattern extraction needed beyond "call as-is," per D-05/06-CONTEXT.md canonical refs.

---

### `src/model2_agri.py` / `notebook/6_1_modelo2_agricultura.ipynb` (new — orchestration)

**Analog:** `notebook/3_1_modelo1_pib.ipynb` (Model 1's orchestration notebook — not read in full per phase-mapper scope limits, but its role is unambiguous from `panel_base.py`/`simulate.py`/`interpret.py` docstrings, which explicitly describe "the Phase-3/4 notebook" as the caller of every function below)

**Core pattern to replicate** (call sequence, assembled from the docstrings of the three shared modules read in full):
```python
from src import panel_base, simulate, interpret

# 1. Coverage filter — Model 2's own criterion (D-01/D-02), NOT filter_by_exclusions
panel_m2 = panel_base.filter_by_min_years(
    panel_clean, dep_var="2.3.1", indep_vars=["6.4.2"], min_years=3
)  # -> 39 countries (D-01)

# 2. Fit + diagnostics — same calls as Model 1, different dep_var/indep_vars (D-04)
fe_res = panel_base.fit_panel_model(panel_m2, dep_var="2.3.1", indep_vars=["6.4.2"])
re_res = ...  # RandomEffects fit, same pattern as Model 1's notebook, for Hausman input
hausman = panel_base.hausman_test(fe_res, re_res)
pesaran = panel_base.pesaran_cd_test(fe_res.resids)
cov_type, cov_config = panel_base.choose_cov_type(pesaran)
fe_res_final = panel_base.fit_panel_model(
    panel_m2, dep_var="2.3.1", indep_vars=["6.4.2"], cov_type=cov_type, **cov_config
)

# 3. Robustness — same sin-COVID criterion as Model 1 (D-10)
panel_m2_no_covid = panel_m2[panel_m2["year"] < 2020]  # -> 35/39 countries survive

# 4. Bootstrap counterfactual — same n_replicas=1000 (D-05)
boot_results = simulate.bootstrap_counterfactual(
    fe_res_final, panel_m2, dep_var="2.3.1", indep_var="6.4.2", n_replicas=1000
)

# 5. Heterogeneity — is_ldc only, NOT region (D-11)
interaction_res = simulate.fit_interaction_model(
    panel_m2, dep_var="2.3.1", indep_var="6.4.2", group_col="is_ldc"
)

# 6. SHAP — same 3 predictors + typology, dep_var excluded from features (D-06)
rf, shap_values, X, explainer = interpret.shap_analysis(
    panel_clean, dep_var="2.3.1",
    feature_vars=["6.4.2", "6.4.1", "8.2.1", "is_ldc", "is_lldc", "is_sids", "region"],
)

# 7. Coverage documentation table (D-03) — same style as panel_exclusions
coverage_table = pd.DataFrame({
    "country_code": ..., "years_available": ..., "included": ..., "reason": ...,
})

# 8. Serialize — same round-trip pattern as model1_gdp.pkl (Phase 3)
import pickle
with open("data/modelos/model2_agri.pkl", "wb") as f:
    pickle.dump(fe_res_final, f)
```

**Naming convention to follow** (Claude's Discretion, 06-CONTEXT.md): `src/model2_agri.py` alongside `panel_base.py`/`simulate.py`/`interpret.py`, or `notebook/6_1_modelo2_agricultura.ipynb` following the `[phase]_[seq]_[descriptive_name].ipynb` convention already used by `3_1_modelo1_pib.ipynb` and `4_1_interpretabilidad_simulacion.ipynb`.

---

### `src/dashboard/models.py` (modify — complete the Model 2 stub, D-07)

**Analog:** same file, `"Modelo 1 (PIB per cápita)"` entry (lines 32-47)

**Exact pattern already staged as a comment** (lines 48-54):
```python
    # Fase 6 añade aquí, sin tocar app.py (D-07):
    # "Modelo 2 (Productividad agrícola)": {
    #     "dep_var": "2.3.1",
    #     "indep_var": "6.4.2",
    #     "feature_vars": [...],
    #     "pkl_path": "data/modelos/model2_agri.pkl",
    # },
```

**Change required:** uncomment and complete this dict entry, filling `feature_vars` with the exact same list as Model 1's (D-06): `["6.4.2", "6.4.1", "8.2.1", "is_ldc", "is_lldc", "is_sids", "region"]`. Add an `"rf_shap_pkl_path"` key mirroring Model 1's if Model 2 serializes its own RF artifact (Claude's Discretion in 06-CONTEXT.md leaves the RF pkl location open — but the dict shape in `ACTIVE_MODELS` already expects this key per Model 1's entry, so Model 2's entry should include it for consistency, e.g. `"data/modelos/rf_shap_model_m2.pkl"` if a separate RF is trained, or omit only if D-06's shared-predictor RF is somehow reused — clarify at implementation time).

Do NOT touch `INDICATOR_LABELS` — `"2.3.1"` is already present (line 62).

---

### `src/dashboard/app.py` (modify — sidebar selector, D-07/D-08)

**Analog:** same file's existing hardcoded lines (77-78) and `ARTIFACT_ERROR_MSG` pattern (lines 61-65)

**Current pattern to replace** (lines 77-78):
```python
ACTIVE_MODEL_NAME = "Modelo 1 (PIB per cápita)"
ACTIVE_MODEL = models.ACTIVE_MODELS[ACTIVE_MODEL_NAME]
```

**New pattern (D-07):** replace the hardcoded literal with a `st.sidebar.selectbox`:
```python
ACTIVE_MODEL_NAME = st.sidebar.selectbox(
    "Modelo activo",
    list(models.ACTIVE_MODELS.keys()),
)
ACTIVE_MODEL = models.ACTIVE_MODELS[ACTIVE_MODEL_NAME]
```
This must be placed BEFORE the 4 tabs are defined (line 85) since all four tab bodies already read from `ACTIVE_MODEL`/`ACTIVE_MODEL_NAME` — no tab body changes needed per D-07 ("las 4 pestañas existentes ya leen de ACTIVE_MODEL sin reestructurarse").

**Reduced-coverage caption pattern (D-08)** — copy the existing error-message-as-constant convention (`ARTIFACT_ERROR_MSG`, lines 61-65) for a new constant, e.g.:
```python
MODEL2_COVERAGE_CAPTION = (
    "Modelo 2 (productividad agrícola) cubre solo 39 países (vs. 171 del "
    "Modelo 1) debido a la baja frecuencia de reporte del indicador 2.3.1 "
    "-- ver limitaciones metodológicas, Fase 6."
)
```
and add `if ACTIVE_MODEL_NAME.startswith("Modelo 2"): st.caption(MODEL2_COVERAGE_CAPTION)` at the top of each of the 4 `with tab_...:` blocks (mirrors the `st.caption(NO_DATA_CAPTION)` pattern already used per-map-column at lines 130/146, and the `try/except -> st.error(ARTIFACT_ERROR_MSG)` visible-status convention used in every tab body, lines 168-169, 205-206, 238-239).

**Existing map tab labels reference `"8.1.1"`/Model 1 specifically** (lines 100-101, 107, 187): these are currently hardcoded to Model 1's dep_var wording ("Modelo 1: valores ajustados (8.1.1)", "...sobre el crecimiento del PIB per cápita"). If the map/simulation tab captions should reflect the active model's label when Model 2 is selected, these string literals will need to reference `ACTIVE_MODEL_NAME`/`models.INDICATOR_LABELS[ACTIVE_MODEL["dep_var"]]` dynamically instead — flag this to the planner as a likely necessary edit beyond the minimal D-07/D-08 scope, since the tabs currently only fully parameterize `ACTIVE_MODEL["pkl_path"]`/`["dep_var"]`/["indep_var"]`/["feature_vars"]`, not their display strings.

---

### `src/dashboard/data.py` (modify — cached loaders currently hardcode Model 1)

**Analog:** same file, `cached_bootstrap` (lines 101-149) and `cached_shap` (lines 152-207)

**Problem pattern found live** (lines 140, 199):
```python
fitted = load_model(models.ACTIVE_MODELS["Modelo 1 (PIB per cápita)"]["pkl_path"])
...
rf = load_model(models.ACTIVE_MODELS["Modelo 1 (PIB per cápita)"]["rf_shap_pkl_path"])
```
These two lines hardcode the Model 1 registry key by name — they do NOT yet honor D-07's "changes `ACTIVE_MODEL` globally" design. This is the one place in the existing codebase that is NOT already model-agnostic despite the module's own docstring claim (line 3-10) that every dashboard component reads the registry rather than a literal.

**Required change (not explicitly listed in 06-CONTEXT.md's canonical file list, but implied by D-07's "cambia ACTIVE_MODEL globalmente"):** add an `active_model_name: str` parameter to both `cached_bootstrap` and `cached_shap`, replacing the hardcoded string literal with the passed-in parameter, e.g.:
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
    ...
    fitted = load_model(models.ACTIVE_MODELS[active_model_name]["pkl_path"])
```
And update `app.py`'s call sites (lines 181-184, 222-225) to pass `active_model_name=ACTIVE_MODEL_NAME`. This keeps `st.cache_data`'s hashable-argument requirement satisfied (a `str` is hashable) and preserves the existing "never accept the Engine/fitted-model object itself as an argument" rule documented at lines 21-26.

**Flag to planner:** confirm this edit is in-scope — 06-CONTEXT.md's canonical refs describe `data.py` only as "patrón de lectura de ACTIVE_MODEL ... base directa de D-07/D-08" without listing this hardcoded-literal bug explicitly; it is a necessary consequence of D-07 but should be called out as a required (not optional) modification.

---

## Shared Patterns

### "Warn, don't hide" (numerically degenerate statistics)
**Source:** `src/panel_base.py::hausman_test` (lines 162-180), `pesaran_cd_test`, `src/interpret.py::compute_vif_table` (lines 82-89)
**Apply to:** Model 2's Hausman/Pesaran calls in the new notebook/module — D-04 requires these to run unmodified even on the ~3.5-obs/country sparse panel; if the resulting statistic is degenerate (singular matrix, negative statistic), the existing functions already emit a `UserWarning` with `stacklevel=2` — the new notebook must surface these warnings in its output/markdown rather than suppressing them, and the memoria's limitations section must transcribe them (D-04).
```python
warnings.warn(
    "Hausman test: negative test statistic (...) "
    "treat this result as uninterpretable, not as evidence for H0",
    UserWarning,
    stacklevel=2,
)
```

### Parametric, dependent-variable-agnostic module design
**Source:** `src/panel_base.py`, `src/simulate.py`, `src/interpret.py` (module docstrings, all state "shared, unmodified, by Model 1 ... and Model 2 ... D-05/D-12")
**Apply to:** every call in the new Model 2 module/notebook — never reimplement `fit_panel_model`/`bootstrap_counterfactual`/`shap_analysis`/`compute_vif_table`; call with `dep_var="2.3.1"` and appropriate `indep_vars`/`feature_vars`/`group_col` arguments only.

### Registry-driven dashboard component (no hardcoded dep_var/pkl_path in tab bodies)
**Source:** `src/dashboard/models.py::ACTIVE_MODELS`, consumed via `ACTIVE_MODEL["..."]` throughout `src/dashboard/app.py`
**Apply to:** any new Model 2 dashboard code — read exclusively from `ACTIVE_MODEL`, never introduce a new `if model == "Modelo 2": ...` branch with hardcoded `"2.3.1"` literals inside tab bodies (the one exception being the D-08 coverage-caption conditional itself, which necessarily branches on `ACTIVE_MODEL_NAME`).

### Visible-status caption/error convention
**Source:** `src/dashboard/app.py::ARTIFACT_ERROR_MSG` (lines 61-65), `NO_DATA_CAPTION` (lines 80-83), each tab's `try/except -> st.error(...)` (lines 168-169, 205-206, 238-239)
**Apply to:** D-08's reduced-coverage caption — define as a module-level string constant near the top of `app.py`, alongside the existing constants, and render via `st.caption(...)` (not `st.warning`/`st.error`, since it is informational, not a failure state) at the top of each tab body when Model 2 is active.

## No Analog Found

None — this phase is explicitly scoped as pure parametric reuse (06-CONTEXT.md domain statement: "no modifica" `panel_base.py`/`simulate.py`/`interpret.py`); every file to touch has a direct, exact analog either in the same file (sibling function/dict entry) or in the prior-phase notebook/artifact it mirrors.

## Metadata

**Analog search scope:** `src/panel_base.py`, `src/simulate.py`, `src/interpret.py`, `src/dashboard/models.py`, `src/dashboard/app.py`, `src/dashboard/data.py`, `notebook/*.ipynb` (names only), `.planning/phases/06-.../06-CONTEXT.md`
**Files scanned:** 6 source files read in full (all under 250 lines each, single-pass reads), 1 context file, 1 notebook directory glob
**Pattern extraction date:** 2026-07-14
