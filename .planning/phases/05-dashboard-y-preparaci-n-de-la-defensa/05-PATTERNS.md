# Phase 5: Dashboard y Preparación de la Defensa - Pattern Map

**Mapped:** 2026-07-13
**Files analyzed:** 10 (4 new `src/dashboard/*`, 1 new `models.py`, 5 new `tests/dashboard/*`)
**Analogs found:** 10 / 10 (all role-match; no direct dashboard/UI analogs exist in this repo yet — this is the first Streamlit code in the project)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `src/dashboard/__init__.py` | config/package-init | — | `src/__init__.py` (empty package marker, if present) / none needed | trivial |
| `src/dashboard/data.py` | service (cached data/model loaders) | CRUD (read-only) + request-response (cache) | `src/db.py` (connection pattern) + `src/simulate.py`/`src/interpret.py` (parametric wrapper style) | role-match |
| `src/dashboard/plots.py` | utility (pure figure builders) | transform | `src/panel_base.py` (pure, parametric, dependent-variable-agnostic functions with no I/O) | role-match |
| `src/dashboard/models.py` | config (registry) | — | none (novel pattern in this repo) — modeled on D-07's own spec | no strict analog, spec is self-contained |
| `src/dashboard/app.py` | controller (Streamlit entry point / orchestration) | request-response (per-widget-interaction rerun) | none (first UI entry point in repo); orchestration style borrows from notebook-driven "call src/*.py functions, render result" pattern already used in `notebook/` | partial (no controller analog exists) |
| `tests/dashboard/__init__.py` | test | — | `tests/__init__.py` | exact |
| `tests/dashboard/conftest.py` | test (fixtures) | — | `tests/test_simulate.py::_make_synthetic_panel` (synthetic fixture generator, inlined rather than in conftest today) | role-match |
| `tests/dashboard/test_no_live_api.py` | test (static/unit) | — | `tests/test_panel_build.py` (unit test structure, docstring-per-test) | role-match |
| `tests/dashboard/test_caching.py` | test (unit) | — | `tests/test_panel_base.py` (unit test structure) | role-match |
| `tests/dashboard/test_app.py` | test (integration, `AppTest`) | — | none exact (first Streamlit `AppTest` in repo) — structure/docstring convention borrowed from `tests/test_simulate.py` | partial |
| `tests/dashboard/test_plots.py` | test (unit, pure functions) | — | `tests/test_interpret.py` (tests pure functions like `compute_vif_table` with synthetic DataFrames) | role-match |

## Pattern Assignments

### `src/dashboard/data.py` (service, CRUD read-only + cache)

**Analog 1 — connection pattern:** `src/db.py`

**Imports pattern** (`src/db.py` lines 21-26):
```python
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine, text
```

**Core pattern to reuse verbatim** — `get_engine` (`src/db.py` lines 44-52):
```python
def get_engine(db_path: str = "data/panel.db") -> Engine:
    """Return a SQLAlchemy Engine bound to the panel SQLite file.

    Creates the parent directory if it does not yet exist (skipped for the
    special SQLAlchemy in-memory DSN ``":memory:"``).
    """
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")
```
`data.py::get_engine()` should call `db.get_engine("data/panel.db")` directly (per RESEARCH.md Code Examples) rather than reimplement it — wrap it in `@st.cache_resource`, do not modify `src/db.py`.

**Security/SQL pattern to mirror** (`src/db.py` lines 1-19, module docstring): all SQL is parameterized or via `pd.read_sql`/`to_sql`; never f-string interpolation of user-selected values into SQL text. Applies directly to `data.load_panel_clean` — the table name is fixed (`panel_clean`), never built from a widget value.

**Analog 2 — reusable/parametric wrapping style (for `cached_bootstrap`/`cached_shap`):** `src/simulate.py::bootstrap_counterfactual` (lines 98-187) and `src/interpret.py::shap_analysis` (lines 94-148).

Pattern to copy: a thin wrapper function that calls an existing unmodified function (`panel_base.fit_panel_model`, here: `simulate.bootstrap_counterfactual` / `interpret.shap_analysis`) with explicit parameters (`dep_var`, `indep_var`, `feature_vars`), never hardcoded — mirrors D-07's "modelo activo" parametrization requirement. See `src/simulate.py` lines 98-116 for the wrapper-calls-existing-function shape:
```python
def bootstrap_counterfactual(
    fitted_results: PanelEffectsResults,
    df: pd.DataFrame,
    dep_var: str,
    indep_var: str,
    reduction_pcts: list[float] | None = None,
    baseline_year: int = 2022,
    n_replicas: int = 1000,
    seed: int = 42,
    entity_col: str = "country_code",
) -> dict:
```
`data.py::cached_bootstrap`/`cached_shap` should follow the same signature style (explicit `dep_var`/`indep_var`/`feature_vars` params, sensible defaults, Google-style docstring explaining the *why*) and internally call `get_engine()`/`load_model()` (both `@st.cache_resource`) rather than receiving the engine/model as parameters — per RESEARCH.md Pattern 5 (avoids `UnhashableParamError`).

**Docstring/module-header convention to copy** (module docstring style, see `src/simulate.py` lines 1-37 and `src/interpret.py` lines 1-35): open with a paragraph naming which decisions (D-xx) and requirement IDs (INTERP-xx, here DASH-xx) the module implements, explain *why* a design choice was made (not what the code does), and call out any known pitfall the pattern avoids (e.g. cite RESEARCH.md Pitfall 1/2/5 for `st.cache_resource` vs `st.cache_data`, non-hashable engine params).

**Error handling / warnings pattern:** `src/simulate.py` lines 171-178 and `src/panel_base.py` lines 162-168 use `warnings.warn(..., UserWarning, stacklevel=2)` for recoverable/degenerate conditions rather than silently swallowing or hard-failing. Apply the same idiom in `data.py` if a loader encounters an empty/missing table.

---

### `src/dashboard/plots.py` (utility, pure transform)

**Analog:** `src/panel_base.py` (pure-function, parametric style — no I/O, no `st.*` calls, fully unit-testable)

**Core pattern** (`src/panel_base.py` lines 71-100, `fit_panel_model`): a thin, single-responsibility, dependent-variable-agnostic function with explicit parameters and defaults, Google-style docstring stating what it does NOT do (e.g. "does NOT call `filter_by_exclusions` internally"). Apply the same shape to `build_choropleth`/`build_scenario_plot`/`build_pdp`: pure functions taking a DataFrame + column names, returning a Plotly `Figure`, never calling `st.*` (RESEARCH.md: "funciones puras testables"). Example signature to mirror:
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
```
becomes, in `plots.py`:
```python
def build_choropleth(df: pd.DataFrame, indicator_col: str, title: str) -> go.Figure:
```

**Concrete Plotly code to copy verbatim** (RESEARCH.md Code Examples, verified against official Plotly docs):
```python
import plotly.express as px

def build_choropleth(df, indicator_col: str, title: str):
    return px.choropleth(
        df,
        locations="country_code",
        locationmode="ISO-3",
        color=indicator_col,
        animation_frame="year",
        range_color=(df[indicator_col].min(), df[indicator_col].max()),
        color_continuous_scale="Viridis",
        title=title,
    )
```
`country_code` is confirmed ISO3 in `panel_clean` (RESEARCH.md, live-verified) — no transformation needed before passing to `locationmode="ISO-3"`.

**Type hints/imports convention** (`src/panel_base.py` lines 20-33 and `src/interpret.py` lines 37-47): `from __future__ import annotations` first, stdlib imports, then third-party (alphabetized-ish grouping: numpy/pandas, then domain libs), then local imports last (`from src import panel_base`).

---

### `src/dashboard/models.py` (config, registry)

**No direct analog exists in the repo** — this is a novel "config dict" pattern. Use the exact shape already specified in RESEARCH.md Pattern 4 (D-07), which itself mirrors the parametric-design philosophy of `panel_base.py`/`simulate.py`/`interpret.py` (every function `dep_var`-agnostic; here, every dashboard component `model`-agnostic via a registry lookup instead of hardcoded `.pkl` paths):
```python
# src/dashboard/models.py
ACTIVE_MODELS = {
    "Modelo 1 (PIB per cápita)": {
        "dep_var": "8.1.1",
        "indep_var": "6.4.2",
        "pkl_path": "data/modelos/model1_gdp.pkl",
    },
    # Fase 6 añade aquí "Modelo 2 (Productividad agrícola)" sin tocar app.py
}
```
Docstring convention: state explicitly (like `src/panel_base.py`'s module docstring does for `fit_panel_model`) that Phase 6 will extend this dict, not restructure `app.py` — this documents D-07 for future readers the same way `panel_base.py`'s docstring documents D-05.

---

### `src/dashboard/app.py` (controller, request-response / per-interaction rerun)

**No controller/entry-point analog exists yet in this repo** (first UI code). Compose it from the other three modules per RESEARCH.md's Recommended Project Structure — `app.py` should contain ONLY `st.set_page_config`/`st.tabs`/layout orchestration, calling into `data.py`/`plots.py`/`models.py`, mirroring the existing project convention of keeping I/O (here: Streamlit rendering) separate from pure computation (`plots.py`) and separate from data access (`data.py`) — the same separation `src/panel_base.py` (pure) / `src/db.py` (I/O) already embody.

**Concrete patterns to copy from RESEARCH.md** (verified against official Streamlit docs, already cross-checked against this project's constraints):
- Pattern 1 (`st.cache_resource`/`st.cache_data` split) — RESEARCH.md lines 194-213
- Pattern 2 (`st.columns` + unique `key=`) — RESEARCH.md lines 215-234
- Pattern 3 (choropleth `range_color`) — RESEARCH.md lines 236-256
- Pattern 5 (avoid non-hashable params in cached functions) — RESEARCH.md lines 277-296

**Security pattern to mirror** (`src/db.py` module docstring, lines 16-18): "API-sourced values are never interpolated into SQL text" — the dashboard equivalent (DASH-01) is: `app.py` must never construct a request to the UN SDG API at runtime; all data access flows through `data.py`'s cached loaders reading `data/panel.db` and `data/modelos/*.pkl` only.

---

### `tests/dashboard/*.py` (test)

**Analog:** `tests/test_simulate.py`, `tests/test_panel_base.py`, `tests/test_interpret.py`

**Module docstring convention** (`tests/test_simulate.py` lines 1-14): open by naming which source module is under test, which decisions/requirement IDs it covers, and what fixture style is reused/mirrored (e.g. "Mirrors tests/test_panel_base.py's fixture style"). Apply the same to each `tests/dashboard/test_*.py` file, citing DASH-01..05.

**Fixture pattern to copy** (`tests/test_simulate.py` lines 27-52, `_make_synthetic_panel`): small, deterministic, `np.random.default_rng(seed)`-based synthetic DataFrame generator with `f"C{i:02d}"` entity naming — for `tests/dashboard/conftest.py`, adapt this into a fixture that builds a tiny in-memory SQLite `panel_clean` table (few countries/years) plus toy `.pkl` model fixtures, exactly as RESEARCH.md's Wave 0 Gaps section specifies (do not depend on the real 171-country `data/panel.db` or production `.pkl` artifacts in unit tests).

**Test naming/structure convention:** one `def test_<behavior>():` per behavior, docstring-per-test explaining what's being verified and why (not just restating the assertion) — see any test function body in `tests/test_panel_base.py`/`tests/test_simulate.py` for the house style.

**`AppTest` pattern (test_app.py)** — no existing analog in this repo (first Streamlit test); follow RESEARCH.md's Validation Architecture section and official `streamlit.testing.v1.AppTest` docs (cited in RESEARCH.md Sources) rather than any in-repo pattern. Structure the test file docstring the same way as `tests/test_simulate.py`'s (cite DASH-03, note "Wave 0 requirement: fast fixture-based, never the real production `.pkl`/`panel.db`").

---

## Shared Patterns

### SQLAlchemy connection reuse (DASH-01)
**Source:** `src/db.py::get_engine` (lines 44-52)
**Apply to:** `src/dashboard/data.py::get_engine` — call `db.get_engine(...)` directly, wrapped in `@st.cache_resource`; never open a second/parallel connection mechanism.

### Parametric, dependent-variable-agnostic design (D-07, matching D-05/D-12 precedent)
**Source:** `src/panel_base.py` module docstring (lines 1-18), `src/simulate.py` module docstring (lines 1-37), `src/interpret.py` module docstring (lines 1-35)
**Apply to:** `src/dashboard/models.py::ACTIVE_MODELS` and every function in `data.py` that touches a model (`dep_var`/`indep_var`/`feature_vars` always explicit parameters or registry lookups, never hardcoded literals scattered through `app.py`).

### Warn-don't-hide for degenerate/recoverable conditions
**Source:** `src/panel_base.py` lines 162-168, 172-180; `src/simulate.py` lines 171-178; `src/interpret.py` lines 82-89
**Apply to:** Any loader/computation in `data.py` that can legitimately produce an empty/degenerate result (e.g. an indicator with no data for a selected year) — use `warnings.warn(..., UserWarning, stacklevel=2)`, not a silent `except: pass` or a hard crash.

### Module/function docstring convention (Google-style, explain "why")
**Source:** all of `src/db.py`, `src/panel_base.py`, `src/simulate.py`, `src/interpret.py` (module-level docstrings, every function docstring)
**Apply to:** All new files in `src/dashboard/`. Each module docstring should name the relevant DASH-xx requirement IDs and D-xx decisions from `05-CONTEXT.md`, matching the citation style already used for INTERP-xx/D-xx in Phase 4's modules.

### No-live-API-call constraint (DASH-01)
**Source:** `src/db.py` module docstring lines 16-18 ("API-sourced values are never interpolated into SQL text... traceability") — same spirit extended to network calls, not just SQL.
**Apply to:** `src/dashboard/app.py` and `data.py` — no `requests` calls to the UN SDG API anywhere in `src/dashboard/`; `tests/dashboard/test_no_live_api.py` should assert this statically (e.g. grep-style check that `requests`/`httpx`/API base URL do not appear in `src/dashboard/*.py`, or that no network fixture is invoked).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/dashboard/app.py` | controller | request-response | First UI/controller entry point in this repo — no prior Streamlit or web-layer code exists to mirror structurally; compose from RESEARCH.md's verified Streamlit/Plotly patterns instead. |
| `src/dashboard/models.py` | config/registry | — | Novel "active model registry" concept introduced by D-07; no prior config-registry file exists — use RESEARCH.md Pattern 4 verbatim. |
| `tests/dashboard/test_app.py` | test (integration) | — | First `streamlit.testing.v1.AppTest`-based test in the repo; follow official Streamlit AppTest docs (cited in RESEARCH.md Sources) rather than an in-repo precedent. |

## Metadata

**Analog search scope:** `src/*.py` (db.py, panel_base.py, panel_build.py, simulate.py, interpret.py), `tests/test_*.py`, `tests/conftest.py` (empty)
**Files scanned:** 5 source modules, 4 test files, 1 conftest
**Pattern extraction date:** 2026-07-13
</content>
