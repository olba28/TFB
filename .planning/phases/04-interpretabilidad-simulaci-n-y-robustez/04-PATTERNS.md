# Phase 4: Interpretabilidad, Simulación y Robustez - Pattern Map

**Mapped:** 2026-07-12
**Files analyzed:** 6 (2 new src modules, 1 new notebook, 2 new test files, 1 new pkl artifact — no code)
**Analogs found:** 6 / 6 (all files have a strong same-project precedent from Phase 3)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `src/simulate.py` | service (statistical computation) | batch / transform | `src/panel_base.py` | exact (same layer, same "parametric module wrapping linearmodels" pattern, D-12 explicitly mandates replicating D-05) |
| `src/interpret.py` | service (statistical computation) | batch / transform | `src/panel_base.py` | role-match (same layer/parametric-design intent; different underlying library — scikit-learn/shap instead of linearmodels) |
| `notebook/4_1_interpretabilidad_simulacion.ipynb` | orchestration notebook | request-response (interactive, cell-by-cell) | `notebook/3_1_modelo1_pib.ipynb` | exact (same role: one notebook per phase, calls into `src/*.py`, serializes to `data/modelos/*.pkl`) |
| `tests/test_simulate.py` | test | CRUD/unit (pure-function assertions) | `tests/test_panel_base.py` | exact (same fixture style: synthetic panel via `np.random.default_rng`, `_make_synthetic_panel`-style helper) |
| `tests/test_interpret.py` | test | CRUD/unit (pure-function assertions) | `tests/test_panel_base.py` | role-match (same test framework/style; new domain — sklearn/shap fixtures instead of linearmodels fixtures) |
| `data/modelos/rf_shap_model.pkl` | serialized artifact (not code) | file-I/O | `data/modelos/model1_gdp.pkl` (produced by notebook cells, not hand-written) | exact (identical pickle-dump/reload-and-verify pattern) |

No `src/db.py` modification is needed — `simulate.py`/`interpret.py` call `db.get_engine()` exactly as-is (read-only reuse), so `src/db.py` is a **shared dependency**, not a file to modify.

## Pattern Assignments

### `src/simulate.py` (service, batch/transform)

**Analog:** `src/panel_base.py` (read in full: `C:\Users\olbap\source\repos\TFB\src\panel_base.py`)

**Module docstring / design-intent pattern** (lines 1-18):
```python
"""Parametric panel-regression module shared, unmodified, by Model 1
(Phase 3, dep_var="8.1.1") and Model 2 (Phase 6, dep_var="2.3.1") -- D-05
(03-CONTEXT.md). Every function is dependent-variable-agnostic.
...
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS, PooledOLS, RandomEffects, compare
from linearmodels.panel.results import (
    PanelEffectsResults,
    PanelModelComparison,
    RandomEffectsResults,
)
from scipy import stats
```
Copy the same docstring convention for `simulate.py`: state which future phase (Phase 6, `dep_var="2.3.1"`) will reuse it unmodified (D-12), and which decision numbers (D-01 through D-04) drove the design. Use `from __future__ import annotations` and a top-of-file typed-import block identically.

**Public function signature / thin-wrapper pattern** (lines 71-100, `fit_panel_model`):
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
    """The D-05-mandated public entry point: a thin wrapper around
    ``PanelOLS(...).fit(...)``. Does NOT call ``filter_by_exclusions``
    internally -- the caller is responsible for passing an already-filtered
    ``df`` ..."""
    indexed = _build_panel_index(df, dep_var, indep_vars)
    ...
    model = PanelOLS(indexed[dep_var], indexed[indep_vars], ...)
    return model.fit(cov_type=cov_type, **cov_config)
```
`simulate.py`'s public functions (`resample_entities`, `bootstrap_counterfactual`, `check_non_extrapolation`) must follow the same "thin, single-responsibility, dep_var/indep_var-agnostic" signature style — `bootstrap_counterfactual(fitted_results, df, dep_var, indep_var, reduction_pcts, baseline_year, n_replicas=1000, seed=42, entity_col="country_code")` per RESEARCH.md's live-verified Pattern 1 code. It should call `panel_base.fit_panel_model` internally (imported, never copy-pasted) exactly as `04-RESEARCH.md` Pattern 1 demonstrates.

**Private helper pattern** (lines 58-68, `_build_panel_index`):
```python
def _build_panel_index(df: pd.DataFrame, dep_var: str, indep_vars: list[str]) -> pd.DataFrame:
    """Build the ``(country_code, year)`` MultiIndex and defensively coerce
    the model's dependent/independent columns to numeric ..."""
    indexed = df.set_index(["country_code", "year"]).copy()
    for column in [dep_var, *indep_vars]:
        indexed[column] = pd.to_numeric(indexed[column], errors="coerce")
    return indexed
```
Use the same private-helper-with-leading-underscore convention for `resample_entities`'s internal relabeling logic, and reuse `pd.to_numeric(..., errors="coerce")` defensively on any new numeric columns touched.

**Pure decision-rule pattern** (lines 225-239, `choose_cov_type`):
```python
def choose_cov_type(
    pesaran_result: dict[str, float],
    alpha: float = 0.05,
) -> tuple[str, dict[str, Any]]:
    """Pure decision rule ..."""
    if pesaran_result["pvalue"] < alpha:
        return "kernel", {"kernel": "bartlett"}
    return "clustered", {"cluster_entity": True}
```
`check_non_extrapolation` should follow this exact "pure function returning a small structured result, docstring states the rule in prose + the decision citation" style — no side effects, no I/O.

**Warning pattern (belt-and-suspenders, non-fatal edge cases)** (lines 159-168):
```python
    try:
        inv_var_diff = np.linalg.inv(var_diff)
    except np.linalg.LinAlgError:
        warnings.warn(
            "Hausman test: var_diff is singular, using pseudo-inverse (pinv) "
            "-- known small-sample pathology, not a bug",
            UserWarning,
            stacklevel=2,
        )
        inv_var_diff = np.linalg.pinv(var_diff)
```
If `bootstrap_counterfactual` encounters a scenario where all countries are excluded by the non-extrapolation check (D-04), emit a `UserWarning` with `stacklevel=2` rather than silently returning an empty array — matches this project's established "warn, don't hide" convention.

---

### `src/interpret.py` (service, batch/transform)

**Analog:** `src/panel_base.py` (role-match — same layer, different library)

**Follow the same conventions as `simulate.py` above** (module docstring citing D-05/D-12/D-08, `from __future__ import annotations`, typed public signatures, private `_` helpers, `warnings.warn(..., stacklevel=2)` for non-fatal edge cases). Additionally:

**RF + SHAP training pattern** (from `04-RESEARCH.md` Pattern 3, live-verified against this project's own `panel_clean`):
```python
from sklearn.ensemble import RandomForestRegressor
import shap

predictors_num = ["6.4.2", "6.4.1", "8.2.1"]
cat = ["is_ldc", "is_lldc", "is_sids", "region"]

sub = panel_clean[predictors_num + cat + [dep_var]].dropna()  # complete-case
X = pd.get_dummies(sub[predictors_num + cat], columns=["region"], drop_first=True)
y = sub[dep_var]

rf = RandomForestRegressor(
    n_estimators=300, random_state=SEED, n_jobs=1,  # n_jobs MUST be 1 -- REPRO-02, Pitfall #2
    oob_score=True,
)
rf.fit(X, y)

explainer = shap.TreeExplainer(rf)
shap_values = explainer.shap_values(X)
```
`shap_analysis(df, dep_var, feature_vars, seed=SEED)` should encapsulate this, returning both `rf` (for serialization, D-08) and `shap_values`/`explainer` — same "one function, one clear return contract" style as `panel_base.fit_panel_model`.

**VIF helper** — promote the Phase-2 notebook-local `compute_vif_table` pattern (cells 13-15 of `notebook/2_1_construccion_panel_eda.ipynb`) into `src/interpret.py` as a small named function using `statsmodels.stats.outliers_influence.variance_inflation_factor`, per RESEARCH.md's "Don't Hand-Roll" table — do not reimplement VIF math from scratch.

---

### `notebook/4_1_interpretabilidad_simulacion.ipynb` (orchestration notebook)

**Analog:** `notebook/3_1_modelo1_pib.ipynb` (read via cell dump: `C:\Users\olbap\source\repos\TFB\notebook\3_1_modelo1_pib.ipynb`)

**sys.path/chdir bootstrap cell** (cell 1):
```python
import sys
from pathlib import Path

# Notebook lives in notebook/, but `src/` and `data/panel.db` are relative to
# the project root -- add the project root to sys.path and chdir there so
# this notebook runs correctly regardless of launch method (nbconvert,
# Jupyter Lab, VS Code) or invocation cwd. Identical bootstrap pattern to
# notebook/2_1_construccion_panel_eda.ipynb.
PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebook" else Path.cwd()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pickle

import numpy as np
import pandas as pd
from IPython.display import Markdown, display
from linearmodels.panel import RandomEffects

from src import db, panel_base

DEP_VAR = "8.1.1"
INDEP_VARS = ["6.4.2"]

engine = db.get_engine(str(PROJECT_ROOT / "data" / "panel.db"))
```
Copy verbatim (adjusting imports to `from src import db, panel_base, simulate, interpret`). Reuse `DEP_VAR = "8.1.1"`, `INDEP_VARS = ["6.4.2"]`, plus new constants for the RF feature set (D-05) and `SEED = 42` (REPRO-02).

**Drift-check pattern after loading/filtering data** (cell 3):
```python
filtered = panel_base.filter_by_exclusions(
    panel_clean, panel_exclusions, dep_var=DEP_VAR, indep_vars=INDEP_VARS
)
n_countries = filtered["country_code"].nunique()
n_obs = len(filtered)
EXPECTED_COUNTRIES = 171
EXPECTED_OBS = 3879
country_drift = abs(n_countries - EXPECTED_COUNTRIES) / EXPECTED_COUNTRIES
obs_drift = abs(n_obs - EXPECTED_OBS) / EXPECTED_OBS
print(f"Countries after filter_by_exclusions: {n_countries} (expected ~{EXPECTED_COUNTRIES}, drift {country_drift:.1%})")
if country_drift > 0.10 or obs_drift > 0.10:
    display(Markdown("**ALERTA:** la muestra se desvía más de un 10% ..."))
```
Reuse this exact "print expected-vs-actual + `display(Markdown(...))` alert if drift > 10%" pattern for the RF's complete-case row count (expected ~3473 per RESEARCH.md's live-verified numbers) and for the bootstrap's per-scenario excluded-country counts (D-04's "debe documentarse explícitamente" requirement — use the same Markdown-alert convention).

**Provisional-fit → Pesaran → final-refit pattern** (cells 5-6): reuse `panel_base.fit_panel_model` + `panel_base.pesaran_cd_test` + `panel_base.choose_cov_type` verbatim for the interaction-term heterogeneity models (INTERP-03) — do not re-derive cov_type choice logic.

**Serialize-and-verify-round-trip pattern** (cells 9-10):
```python
models_dir = PROJECT_ROOT / "data" / "modelos"
models_dir.mkdir(parents=True, exist_ok=True)
model_path = models_dir / "model1_gdp.pkl"
with open(model_path, "wb") as f:
    pickle.dump(final_fe_results, f)
print(f"Modelo serializado en: {model_path}")

with open(model_path, "rb") as f:
    reloaded_results = pickle.load(f)
params_match = np.allclose(reloaded_results.params.values, final_fe_results.params.values)
print("Los parámetros del modelo recargado coinciden con el modelo en memoria:", params_match)
assert params_match, "El modelo recargado desde .pkl no coincide con el modelo ajustado en memoria"
```
Copy verbatim for `rf_shap_model.pkl` (D-08): serialize the fitted `RandomForestRegressor`, reload, and assert `np.allclose` on `rf.feature_importances_` (or `predict()` on a fixed sample) to prove round-trip fidelity — matching this project's established "never trust an unverified pickle" convention.

---

### `tests/test_simulate.py` (test, unit)

**Analog:** `tests/test_panel_base.py` (read in full: `C:\Users\olbap\source\repos\TFB\tests\test_panel_base.py`)

**Imports + module-level constants** (lines 13-22):
```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import panel_base

DEP_VAR = "y"
INDEP_VARS = ["x"]
```
For `test_simulate.py`, mirror with `from src import panel_base, simulate` and reuse `DEP_VAR = "y"` / `INDEP_VARS = ["x"]` conventions for a tiny synthetic fixture (do NOT use the real 171-country panel in unit tests — RESEARCH.md's Wave 0 Gaps explicitly call for a small fixture).

**Synthetic-panel fixture generator pattern** (lines 25-50, `_make_synthetic_panel`):
```python
def _make_synthetic_panel(
    n_entities: int = 10,
    n_years: int = 10,
    seed: int = 0,
    beta: float = 2.0,
    entity_effect_sd: float = 1.0,
    noise_sd: float = 0.5,
) -> pd.DataFrame:
    """A synthetic (country_code, year) panel with a known dep_var/indep_var
    relationship (y = beta * x + entity_effect + noise) ..."""
    rng = np.random.default_rng(seed)
    entities = [f"C{i:02d}" for i in range(n_entities)]
    years = list(range(2000, 2000 + n_years))
    entity_effects = {c: rng.normal(0, entity_effect_sd) for c in entities}
    rows = []
    for country in entities:
        for year in years:
            x = rng.normal(5, 1)
            y = beta * x + entity_effects[country] + rng.normal(0, noise_sd)
            rows.append({"country_code": country, "year": year, "x": x, "y": y})
    return pd.DataFrame(rows)
```
Reuse this exact helper (or import it) for `resample_entities`/`bootstrap_counterfactual` tests — `np.random.default_rng(seed)`, `f"C{i:02d}"` naming, docstring stating the known ground-truth relationship.

**Assertion-style pattern** (lines 142-148, known-coefficient recovery test):
```python
def test_fit_panel_model_recovers_known_coefficient_sign_and_significance():
    df = _make_synthetic_panel(n_entities=10, n_years=10, beta=2.0)
    result = panel_base.fit_panel_model(df, DEP_VAR, INDEP_VARS)
    assert result.params["x"] > 0
    assert result.pvalues["x"] < 0.05
```
Use for `test_bootstrap_determinism` (REPRO-02): call `bootstrap_counterfactual` twice with `seed=42` and assert `np.array_equal` (not `pytest.approx`, per RESEARCH.md's determinism requirement) on the resulting coefficient/effect arrays.

**Entity-collision regression test** — no direct analog exists yet (this is a NEW bug class per RESEARCH.md Pitfall #1); write `test_resample_entities_unique_index` from scratch following the same docstring-explains-the-why convention as `test_pesaran_cd_test_hand_computable_fixture_returns_exact_expected_statistic` (lines 245-264) — a hand-computable fixture with a known, asserted expected count (e.g. 10 entities drawn with a fixed seed → assert exactly 10 unique post-relabel entity ids, matching RESEARCH.md's live-verified 171-draws-with-relabeling-still-171-entities finding, scaled down for a fast unit test).

---

### `tests/test_interpret.py` (test, unit)

**Analog:** `tests/test_panel_base.py` (role-match — same pytest conventions, new domain)

Reuse the same `from __future__ import annotations`, `np.random.default_rng(seed)` fixture-generation style, and docstring-per-test convention. New domain-specific fixture needed: a tiny synthetic DataFrame (~30-50 rows, a handful of countries) with the RF's predictor columns (`6.4.2`, `6.4.1`, `8.2.1`, `is_ldc`, `is_lldc`, `is_sids`, `region`) and a known linear-ish relationship to `dep_var`, analogous to `_make_synthetic_panel` but without the entity/year panel structure (RF training is not panel-structured). Cover:
- `test_shap_values_shape` — assert `shap_values.shape == (n_samples, n_features)`, mirrors `test_fit_panel_model_builds_index_internally_not_left_to_caller`'s "assert the right shape/index came out" style (lines 169-177).
- `test_oob_score_present` — assert `rf.oob_score_` is a real float, not NaN/None.
- `test_rf_determinism` — fit twice with `n_jobs=1, random_state=SEED`, assert `np.array_equal(rf1.feature_importances_, rf2.feature_importances_)` — directly tests RESEARCH.md's live-verified `n_jobs` non-determinism fix (Pitfall #2).

---

## Shared Patterns

### Database access (`src/db.py`, read-only reuse)
**Source:** `src/db.py` lines 44-52 (`get_engine`)
**Apply to:** `simulate.py`, `interpret.py`, and the Phase-4 notebook — never construct a new connection pattern.
```python
def get_engine(db_path: str = "data/panel.db") -> Engine:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")
```
Load `panel_clean`/`panel_exclusions` via `pd.read_sql("SELECT * FROM panel_clean", engine)` exactly as the Phase 3 notebook does (implied by cell 3's `panel_clean`/`panel_exclusions` variables) — never construct SQL from external input (Security V5, already established in `src/db.py`'s own docstring).

### Reproducible seeding (REPRO-02)
**Source:** `04-RESEARCH.md` "Reproducible seeding pattern" (live-verified against this project's pinned `.venv`)
**Apply to:** every stochastic step in `simulate.py` (bootstrap) and `interpret.py` (RF training)
```python
SEED = 42  # single project-wide constant, threaded through every stochastic step

ss = np.random.SeedSequence(SEED)
child_seeds = ss.spawn(1000)
replica_rngs = [np.random.default_rng(c) for c in child_seeds]

rf = RandomForestRegressor(random_state=SEED, n_jobs=1, oob_score=True)  # n_jobs MUST be 1
```

### Warning-not-crashing on statistical edge cases
**Source:** `src/panel_base.py` lines 159-180 (`hausman_test`'s singular-matrix / negative-statistic warnings)
**Apply to:** `simulate.py`'s non-extrapolation exclusion (D-04) when a scenario excludes all/most countries; `interpret.py` if VIF is undefined (perfect collinearity)
```python
warnings.warn(
    "<clear description of the pathology>",
    UserWarning,
    stacklevel=2,
)
```

### Serialize-to-`data/modelos/*.pkl` + round-trip verification
**Source:** `notebook/3_1_modelo1_pib.ipynb` cells 9-10 (full text above)
**Apply to:** `rf_shap_model.pkl` (D-08) in `notebook/4_1_interpretabilidad_simulacion.ipynb`

### Docstring convention: cite decision numbers and future reuse
**Source:** `src/panel_base.py` lines 1-18 (module docstring), every function docstring in the same file
**Apply to:** every new public function in `simulate.py`/`interpret.py` — state which `CONTEXT.md` decision (D-01..D-13) motivated the design, and which future phase will reuse it unmodified (Phase 6, `dep_var="2.3.1"`).

## No Analog Found

None. Every new file in this phase has a strong, same-project Phase 3 precedent (`panel_base.py` for the two new `src/` modules, `3_1_modelo1_pib.ipynb` for the notebook, `test_panel_base.py` for both new test files). The only genuinely new sub-patterns (block-bootstrap entity relabeling, SHAP/RF training, ALE/PDP) have no direct in-repo analog but are fully specified with live-verified code in `04-RESEARCH.md`'s Architecture Patterns 1-3 — the planner should treat those RESEARCH.md excerpts as the primary source for the parts of `simulate.py`/`interpret.py` that are novel to this phase, and the excerpts above as the primary source for project-convention conformance (naming, docstrings, error handling, module structure).

## Metadata

**Analog search scope:** `src/`, `tests/`, `notebook/` (whole-repo scope; project is small enough that no directory-level narrowing was needed)
**Files scanned:** `src/panel_base.py`, `src/db.py`, `tests/test_panel_base.py`, `notebook/3_1_modelo1_pib.ipynb` (15 cells, targeted dump), `04-CONTEXT.md`, `04-RESEARCH.md`
**Pattern extraction date:** 2026-07-12
