# Architecture Research

**Domain:** Solo academic data-science pipeline (econometrics thesis) — API ingestion → SQLite panel store → panel regression modeling → counterfactual simulation → SHAP interpretability → local Streamlit dashboard
**Researched:** 2026-07-10
**Confidence:** MEDIUM (cross-verified against multiple independent web sources; no official "one true" architecture exists for this exact combination, but each layer maps to a well-established, widely-documented pattern)

## Standard Architecture

### System Overview

There is no single canonical template for "API → SQLite → panel econometrics → simulation → SHAP → dashboard," but the individual layers are each standard, and the composition follows the well-established **Cookiecutter Data Science** shape (raw-data-immutable, `src/` as importable logic, notebooks for orchestration/narrative) extended with an econometrics-specific modeling layer and a read-only presentation layer. This matches — and validates — the skeleton already mapped in `.planning/codebase/ARCHITECTURE.md`.

```
┌─────────────────────────────────────────────────────────────────────┐
│  PRESENTATION — src/dashboard/  (Streamlit + Plotly, local only)     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ app.py        │  │ plots.py     │  │ Read-only cached loaders │   │
│  │ (page layout) │  │ (choropleth, │  │ (st.cache_data /         │   │
│  │               │  │  time series)│  │  st.cache_resource)      │   │
│  └──────┬────────┘  └──────┬───────┘  └───────────┬───────────────┘  │
├─────────┴──────────────────┴──────────────────────┴──────────────────┤
│  INTERPRETABILITY — src/modelos/interpret.py (SHAP, post-hoc)         │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │ Loads fitted model(s) + feature matrix → SHAP values →       │      │
│  │ writes summary tables/plots to data/resultados/               │      │
│  └────────────────────────────────────────────────────────────┘      │
├─────────────────────────────────────────────────────────────────────┤
│  SIMULATION — src/simulacion/  (counterfactual sensitivity)           │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │ Loads fitted Model 1 / Model 2 → perturbs water-stress input  │      │
│  │ → recomputes predicted GDP/agri-productivity + CI → writes    │      │
│  │ scenario tables to data/resultados/                           │      │
│  └────────────────────────────────────────────────────────────┘      │
├─────────────────────────────────────────────────────────────────────┤
│  MODELING — src/modelos/  (linearmodels.PanelOLS, fixed effects)      │
│  ┌───────────────────┐        ┌────────────────────────────────┐    │
│  │ Model 1: GDP       │        │ Model 2: Agri. productivity     │    │
│  │ panel_regression.py│───────▶│ (extends Model 1 code/features) │    │
│  └───────────────────┘        └────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────┤
│  EDA / EXPLORATION — notebook/  (Jupyter, narrative + prototyping)    │
├─────────────────────────────────────────────────────────────────────┤
│  TRANSFORMATION / FEATURE ENGINEERING — src/etl/                      │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │ clean.py (nulls, outliers, 70%-coverage filter)                │    │
│  │ merge.py (join indicators into country×year panel)             │    │
│  │ features.py (growth rates, lags, derived ratios)                │    │
│  └────────────────────────────────────────────────────────────┘      │
├─────────────────────────────────────────────────────────────────────┤
│  STORAGE — data/panel.db  (SQLite, single source of truth)            │
│  ┌──────────────┐  ┌───────────────────┐  ┌───────────────────┐      │
│  │ raw_observ.  │  │ panel (clean, wide)│  │ resultados/*.db or │     │
│  │ (long, as    │  │ table indexed by   │  │ tables (model      │     │
│  │  fetched)    │  │ country_code, year │  │  outputs, sim, SHAP)│    │
│  └──────────────┘  └───────────────────┘  └───────────────────┘      │
├─────────────────────────────────────────────────────────────────────┤
│  INGESTION — src/ingesta/  (UN SDG API client)                        │
│  ┌────────────────┐  ┌───────────────┐  ┌─────────────────────┐      │
│  │ client.py       │  │ manifest.py   │  │ fetch_data.py        │     │
│  │ (HTTP + retry/  │  │ (provenance:  │  │ (orchestrator:       │     │
│  │  pagination)    │  │  checksum,    │  │  client → raw file → │     │
│  │                 │  │  date, params)│  │  manifest → SQLite)  │     │
│  └────────────────┘  └───────────────┘  └─────────────────────┘      │
├─────────────────────────────────────────────────────────────────────┤
│  EXTERNAL — UN SDG API (unstats.un.org/SDGAPI/v1)                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Ingestion (`src/ingesta/`) | Call UN SDG API per indicator (6.4.2, 2.3.1, GDP growth, labor productivity), page through results, write raw response + manifest (source, date, params, checksum, row count) | `requests` + simple retry/backoff; one function per indicator; JSON/CSV dumped to `data/raw/<indicator>/<date>/` |
| Storage (`data/panel.db`, SQLite) | Single versioned file holding both a `raw_observations` long table (as fetched) and a cleaned `panel` wide table (country × year); the manifest documents provenance, but SQLite itself is the reproducible artifact | `sqlite3` / `pandas.to_sql()`; simple star-like schema, no ORM needed for this scale |
| Transformation / Feature Engineering (`src/etl/`) | Clean (nulls, outliers), apply the 70%-country-coverage filter, merge multi-indicator sources into one panel, engineer derived features (growth rates, lags) | Pandas functions with explicit input/output tables; idempotent — always rebuildable from `raw_observations` |
| EDA (`notebook/01-eda.ipynb`) | Descriptive stats, correlations, visual exploration of water-stress ↔ GDP/agri relationship (global, regional, by country typology); generates hypotheses that inform model spec | Jupyter, calls `src/etl` and `src/modelos` helpers rather than reimplementing logic inline |
| Modeling — Model 1 (`src/modelos/panel_regression.py`) | Fixed-effects panel regression (`linearmodels.PanelOLS`) predicting real GDP-per-capita growth from water stress + controls; diagnostics (Hausman, serial correlation, heteroskedasticity) | MultiIndex `(country, year)` DataFrame; `entity_effects=True`; clustered SE; serialized to `data/modelos/model1_gdp.pkl` |
| Modeling — Model 2 (`src/modelos/panel_regression.py` or a sibling module) | Same methodology applied to agricultural productivity (indicator 2.3.1); explicitly built as an extension/reuse of Model 1's code and feature set, not a parallel effort | Same fitting function parameterized by target/coverage; may restrict to a country subset with documented exclusions |
| Simulation (`src/simulacion/`) | Given a fitted model, perturb the water-stress input by X points and recompute predicted outcome + confidence interval — framed as sensitivity analysis, not causal prediction | Function that takes a fitted `PanelOLS` result + scenario deltas, returns a DataFrame of counterfactual outcomes; bootstrap or delta-method CIs |
| Interpretability (`src/modelos/interpret.py`) | Post-hoc SHAP analysis of variable importance (water stress vs. controls) | Runs strictly after model fitting/validation; see caveat below — `linearmodels.PanelOLS` is a linear estimator, not directly SHAP-native |
| Dashboard (`src/dashboard/`) | Read-only presentation: geospatial choropleth of water stress/results, time series, scenario explorer, SHAP summary | Streamlit app that loads pre-computed artifacts (`data/panel.db`, `data/resultados/*.parquet`) via `st.cache_data`/`st.cache_resource`; never trains anything itself |
| Static Output (`figuras/`) | Publication-ready exports for the thesis manuscript | PNG/PDF exported from notebooks or the dashboard, organized by thesis chapter |

## Recommended Project Structure

This is a refinement of the existing skeleton (`src/ingesta/`, `data/`, `notebook/`, `figuras/`) — additive, not a rewrite. It follows Cookiecutter Data Science conventions adapted for a single SQLite store instead of raw/interim/processed CSV layers, since SQLite is already the chosen storage engine (Key Decision in PROJECT.md).

```
TFB/
├── data/
│   ├── raw/                    # Raw API dumps, one dir per fetch: {indicator}/{date}/*.json + manifest.json
│   │   └── <indicator>/<date>/{response.json, manifest.json}
│   ├── panel.db                 # SQLite: raw_observations (long) + panel (wide, clean) tables
│   ├── modelos/                 # Serialized fitted models: model1_gdp.pkl, model2_agri.pkl
│   └── resultados/              # Model predictions, simulation scenarios, SHAP tables (parquet/csv)
│       ├── simulacion/
│       └── shap/
├── notebook/
│   ├── 01-eda.ipynb
│   ├── 02-modelos-panel.ipynb   # Model 1 first, Model 2 appended once Model 1 is stable
│   ├── 03-simulacion.ipynb
│   ├── 04-interpretability.ipynb
│   └── 05-visualizacion.ipynb   # Dashboard prototyping only — logic lives in src/dashboard/
├── figuras/
│   └── <chapter>/
├── src/
│   ├── ingesta/
│   │   ├── client.py            # UN SDG API HTTP client (pagination, retry)
│   │   ├── manifest.py          # Provenance metadata: checksum, date, params, row count
│   │   └── fetch_data.py        # Orchestrator: client → data/raw → data/panel.db (raw_observations)
│   ├── etl/
│   │   ├── clean.py             # Nulls, outliers, 70%-coverage country filter
│   │   ├── merge.py             # Join indicators into one country×year panel
│   │   └── features.py          # Growth rates, lags, derived ratios
│   ├── modelos/
│   │   ├── panel_base.py        # Shared PanelOLS fitting/diagnostics helpers (used by both models)
│   │   ├── model1_gdp.py        # Model 1: water stress → GDP growth
│   │   ├── model2_agri.py       # Model 2: extends model1_gdp.py's approach for 2.3.1
│   │   └── interpret.py         # SHAP analysis (post-hoc, reads fitted models)
│   ├── simulacion/
│   │   └── contrafactual.py     # Scenario engine: perturb water stress, recompute outcome + CI
│   ├── dashboard/
│   │   ├── app.py               # Streamlit entry point (thin, declarative)
│   │   └── plots.py             # Reusable Plotly figure builders
│   ├── config.py                # Paths, thresholds (70% coverage), API base URL, indicator codes
│   └── db.py                    # SQLite connection/schema helpers shared by ingesta/etl/modelos
├── requirements.txt
├── requirements.lock.txt
└── README.md
```

### Structure Rationale

- **`data/raw/` + `data/panel.db` (not `data/raw|interim|processed` as separate CSV trees):** The project's own decision is SQLite as the single storage engine. Keep `data/raw/` only for the untouched API responses (audit trail + manifest), and let SQLite itself hold both the long raw table and the cleaned wide panel — this avoids duplicating "interim/processed" as extra file trees when a database already serves that purpose.
- **`src/modelos/panel_base.py` shared by Model 1 and Model 2:** Directly implements the PROJECT.md decision that "Modelo 2 (agricultura) [es una] extensión del Modelo 1." A shared fitting/diagnostics function parameterized by target variable and country subset avoids duplicating econometric logic and keeps the two models methodologically consistent (both defensible with the same diagnostic battery).
- **`src/simulacion/` and `src/dashboard/` as separate top-level packages, not nested under `modelos/`:** Simulation and dashboard are downstream *consumers* of fitted models, not part of model-fitting itself — keeping them separate makes the dependency direction explicit (simulation/dashboard import from `modelos`, never the reverse).
- **`src/modelos/interpret.py` inside `modelos/` (not a separate top-level package):** SHAP is tightly coupled to "explaining a specific fitted model," so it lives next to the model code it explains, but its logic runs strictly after training (see Anti-Patterns).
- **`data/resultados/`:** A single destination for everything the dashboard needs to read (simulation tables, SHAP tables, headline model outputs) — this is what makes `src/dashboard/` a pure, read-only consumer with no knowledge of how those artifacts were produced.
- **Notebooks numbered to mirror the pipeline stages, not the thesis chapters 1:1:** `02-modelos-panel.ipynb` builds Model 1 first and only appends Model 2 once Model 1 is validated, directly reflecting the time-risk mitigation in PROJECT.md.

## Architectural Patterns

### Pattern 1: Immutable raw layer + regenerable derived layers

**What:** Raw API responses (`data/raw/`) and the `raw_observations` SQLite table are never edited in place. Every cleaning/merge/feature step reads from a lower layer and writes to a higher one (`raw_observations` → `panel` table → model input DataFrame).
**When to use:** Always, for this project — it is what makes the pipeline "reproducible end-to-end from `data/raw` + `src/`," a requirement both for the SQLite decision and for defensibility before the tribunal.
**Trade-offs:** Slightly more disk/DB usage (raw + clean coexist) in exchange for full auditability and easy re-runs after fixing a cleaning bug.

**Example:**
```python
# src/etl/clean.py
def build_panel_table(conn: sqlite3.Connection) -> pd.DataFrame:
    raw = pd.read_sql("SELECT * FROM raw_observations", conn)
    panel = raw.pipe(drop_nulls_below_threshold).pipe(apply_coverage_filter, min_years=0.7)
    panel.to_sql("panel", conn, if_exists="replace", index=False)
    return panel
```

### Pattern 2: Shared fitting function for Model 1 and Model 2

**What:** One `fit_panel_fixed_effects(df, target, controls, entity="country", time="year")` helper in `panel_base.py`, called by both `model1_gdp.py` (target = GDP growth) and `model2_agri.py` (target = agricultural productivity), so both models share diagnostics, CI computation, and serialization code.
**When to use:** Whenever two models share methodology and differ only in target/feature subset — exactly the case described in PROJECT.md ("mismo enfoque metodológico").
**Trade-offs:** Slightly more upfront abstraction than copy-pasting a notebook cell, but it directly de-risks "Modelo 2 as time permits" — Model 2 becomes a thin configuration on top of already-tested code rather than a second full implementation.

**Example:**
```python
# src/modelos/panel_base.py
def fit_panel_fixed_effects(panel_df, target, controls):
    panel_df = panel_df.set_index(["country_code", "year"])
    exog = sm.add_constant(panel_df[controls])
    model = PanelOLS(panel_df[target], exog, entity_effects=True)
    return model.fit(cov_type="clustered", cluster_entity=True)
```

### Pattern 3: Post-hoc interpretability decoupled from model fitting

**What:** `interpret.py` never trains a model — it loads an already-serialized, already-validated `model1_gdp.pkl`/`model2_agri.pkl` and computes SHAP values against it.
**When to use:** Always for interpretability work; this is universal SHAP practice (see research findings) and also keeps thesis defensibility clean — the reader can see model validation and interpretation as separate, independently reviewable steps.
**Trade-offs / caveat specific to this project:** `linearmodels.PanelOLS` is a linear fixed-effects estimator, not a scikit-learn-style model SHAP's fast explainers expect. Two viable approaches, to decide explicitly during the modeling phase (flag for phase-specific research):
1. Wrap the fitted PanelOLS `predict()` in a plain Python function and use `shap.KernelExplainer` (works with any predict function, but slower — panel size of ~150–180 countries × ~20 years keeps this tractable).
2. Since `scikit-learn` is already a pinned dependency, fit a complementary tree-based model (e.g. `RandomForestRegressor`) on the same panel-flattened features purely for SHAP's `TreeExplainer`, and present it as a robustness/variable-importance cross-check alongside — not a replacement for — the PanelOLS coefficients. This is arguably the more defensible academic framing: PanelOLS answers "what is the causal-ish, fixed-effects-controlled association," SHAP-on-a-tree-model answers "how does an ML model rank the same variables' predictive importance."

### Pattern 4: Dashboard as pure artifact consumer

**What:** `src/dashboard/app.py` performs zero training, zero API calls, and zero heavy computation at runtime. It reads `data/panel.db` and `data/resultados/*` (already-computed model outputs, simulations, SHAP tables) and renders them.
**When to use:** Always for a local-only academic demo dashboard — this keeps `streamlit run` startup fast and the defense demo resilient to network issues (no live UN API dependency during the oral defense).
**Trade-offs:** Any change to model outputs requires re-running the upstream pipeline before the dashboard reflects it (acceptable — this is a batch, not real-time, system per PROJECT.md's explicit Out of Scope).

## Data Flow

### Primary Pipeline Flow

```
UN SDG API (unstats.un.org/SDGAPI/v1)
    ↓  (src/ingesta/client.py — HTTP GET per indicator, paginated)
data/raw/<indicator>/<date>/response.json + manifest.json
    ↓  (src/ingesta/fetch_data.py — load + insert)
SQLite: raw_observations table (long: country, year, indicator, value, source_date)
    ↓  (src/etl/clean.py, merge.py, features.py)
SQLite: panel table (wide: country_code, year, water_stress, gdp_growth, agri_productivity, controls...)
    ↓  (notebook/01-eda.ipynb — descriptive stats, correlation, hypothesis generation)
    ↓  (src/modelos/model1_gdp.py, then model2_agri.py — fit PanelOLS fixed effects)
data/modelos/model1_gdp.pkl, model2_agri.pkl  (+ diagnostics logged/printed)
    ↓  (src/simulacion/contrafactual.py — perturb water-stress input, recompute + CI)
data/resultados/simulacion/*.parquet
    ↓  (src/modelos/interpret.py — SHAP on fitted model(s))
data/resultados/shap/*.parquet
    ↓  (src/dashboard/app.py — reads panel table + resultados/*)
Streamlit local dashboard (choropleth, time series, scenario explorer, SHAP summary)
    ↓  (exports)
figuras/*.png, *.pdf  →  thesis manuscript (60–80 pages)
```

### Key Data Flows

1. **Provenance flow:** every ingestion run writes a manifest (source, date, query params, checksum, row count) alongside the raw dump — this manifest, not the raw file itself, is what gets committed to Git, satisfying the "local versioned raw snapshot" requirement without bloating the repo.
2. **Fixed-point re-run flow:** because `raw_observations` is immutable and every later table/artifact is derived and regenerable, the entire pipeline (panel table → models → simulation → SHAP → dashboard artifacts) can be rebuilt from `data/raw/` + `src/` alone — this is the reproducibility contract the thesis committee will expect to see demonstrated.
3. **Model-to-downstream flow:** simulation and interpretability both depend on a *fitted, serialized* model, never on live training — this decoupling means Model 2 being incomplete does not block Model 1's simulation/SHAP/dashboard work, directly supporting the "prioritize Model 1" risk mitigation.

## Scaling / Growth Considerations

This is not a scaling problem in the traditional sense (no concurrent users, no production load) — the relevant axis is *scope growth* over the thesis timeline.

| Scope | Architecture Adjustments |
|-------|--------------------------|
| Model 1 only (Entrega 2 milestone, ~60%) | Ingestion + storage + ETL + EDA + Model 1 fully wired through to a minimal dashboard view; simulation/SHAP for Model 1 can lag slightly if time-constrained, since Entrega 2 does not require them |
| Model 1 + Model 2 (Entrega 3, 100%) | `panel_base.py` abstraction pays off — Model 2 reuses fitting/diagnostics code; simulation and SHAP modules become parameterized by model rather than rewritten |
| Full dashboard (Entrega 3) | Dashboard reads whatever artifacts exist in `data/resultados/`; build it to degrade gracefully if Model 2 outputs are missing/incomplete (documented exclusion, not a crash) |

### Scaling Priorities

1. **First real constraint: developer time, not data volume.** 150–180 countries × 23 years × ~5 indicators is a small dataset (low thousands of rows) — SQLite and pandas handle it trivially. The actual bottleneck is solo-author time against the UCMA calendar, which is why the shared `panel_base.py` fitting function and the "simulation/SHAP depend on serialized models, not live training" decoupling both matter architecturally: they let Model 2, simulation, and SHAP be added incrementally without touching Model 1's already-defended code.
2. **Second constraint: SDG indicator 2.3.1 coverage.** If country coverage for agricultural productivity is too sparse even after the 70% filter, Model 2's scope narrows (per PROJECT.md) rather than the architecture changing — `model2_agri.py` simply takes a smaller country list as a parameter.

## Anti-Patterns

### Anti-Pattern 1: Business logic living only in notebook cells

**What people do:** Write cleaning, feature engineering, or model-fitting code directly in `notebook/*.ipynb` cells with no corresponding `src/` function.
**Why it's wrong:** Notebook diffs are not reviewable, cell execution order is easy to break, and the thesis committee's reproducibility bar ("run this and get the same numbers") is hard to meet when logic isn't callable/testable outside the notebook.
**Do this instead:** Notebooks import and call functions from `src/etl`, `src/modelos`, etc. Notebooks own narrative, exploration, and figure generation — not core logic.

### Anti-Pattern 2: Training a model inside the SHAP or simulation module

**What people do:** Fit the model as a side effect of running the interpretability or simulation script, instead of loading an already-serialized model.
**Why it's wrong:** Couples interpretability/simulation to training, making it impossible to interpret a specific validated model version, and makes re-runs slower and less deterministic (random seeds, refit variance).
**Do this instead:** `model1_gdp.py`/`model2_agri.py` are the only places that call `.fit()`; they serialize to `data/modelos/*.pkl`. Everything downstream (`simulacion/`, `interpret.py`, `dashboard/`) loads the pickle.

### Anti-Pattern 3: Treating SHAP output as equivalent to PanelOLS coefficients

**What people do:** Present SHAP values as if they were the causal effect size the fixed-effects regression already estimated.
**Why it's wrong:** SHAP explains *predictive* contribution of a (possibly different, tree-based) model; PanelOLS coefficients are the *fixed-effects-controlled association* the thesis's causal-inference framing relies on. Conflating the two is an easy defensibility misstep before a tribunal familiar with Wooldridge/Baltagi.
**Do this instead:** Present them explicitly as complementary: PanelOLS section = "controlled association / effect size," SHAP section = "relative predictive importance," and state which model produced each (per Pattern 3 caveat above).

### Anti-Pattern 4: Dashboard querying the live UN API or refitting models on each interaction

**What people do:** Wire Streamlit widgets directly to API calls or model `.fit()`/`.predict()` calls on every user interaction.
**Why it's wrong:** Slow, network-dependent, non-deterministic during a live oral defense — exactly the failure mode to avoid given the "local only, demo during defense" requirement.
**Do this instead:** Precompute everything the dashboard needs into `data/resultados/` ahead of time; the dashboard only reads and caches (`st.cache_data`).

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| UN SDG API (`unstats.un.org/SDGAPI/v1`) | Simple `requests`-based GET client, one function per indicator code, pagination handled explicitly; response is dumped raw before any processing | No auth required (public API) but rate limits/downtime are the reason for the manifest + local raw copy risk mitigation already decided in PROJECT.md |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `ingesta` ↔ `data/panel.db` | Direct SQLite writes (`raw_observations` table) | `ingesta` never reads from `panel` table — one-directional |
| `etl` ↔ `data/panel.db` | Reads `raw_observations`, writes `panel` table | Idempotent — safe to re-run after a cleaning fix |
| `modelos` ↔ `data/panel.db` / `data/modelos/` | Reads `panel` table, writes serialized `.pkl` | Model 2 imports shared logic from Model 1's `panel_base.py`, not from `model1_gdp.py` directly (avoid coupling the two target-specific modules to each other) |
| `simulacion`/`interpret` ↔ `data/modelos/`, `data/resultados/` | Reads `.pkl`, writes result tables | Never re-fits; purely downstream consumers |
| `dashboard` ↔ `data/panel.db`, `data/resultados/` | Read-only, cached | Never writes; never calls `ingesta`/`modelos`/`simulacion` directly at runtime |

## Sources

- [Cookiecutter Data Science (drivendata, official)](https://cookiecutter-data-science.drivendata.org/) — MEDIUM confidence, cross-verified against multiple independent tutorials/blog posts describing the same `data/{raw,interim,processed}` + `src/` shape
- [drivendataorg/cookiecutter-data-science (GitHub)](https://github.com/drivendataorg/cookiecutter-data-science)
- [Reproducible Data Science — Project Organization](https://ecorepsci.github.io/reproducible-science/project-organization.html) — MEDIUM confidence
- [Build a Reproducible and Maintainable Data Science Project — Project Structure](https://khuyentran1401.github.io/reproducible-data-science/structure_project/introduction.html) — MEDIUM confidence
- [linearmodels PyPI documentation](https://pypi.org/project/linearmodels/) — MEDIUM confidence, cross-verified against tutorials (Pew Research Center, Towards Data Science) describing the same PanelOLS/MultiIndex/entity_effects workflow
- [Panel Data Analysis in StatsModels — GeeksforGeeks](https://www.geeksforgeeks.org/data-analysis/panel-data-analysis-in-statsmodels/)
- [SHAP official repository (shap/shap)](https://github.com/shap/shap) — MEDIUM confidence on placement-as-post-hoc-stage claim, cross-verified against InterpretML docs and independent guides
- [Streamlit — Working with Streamlit's execution model (official docs)](https://docs.streamlit.io/develop/concepts/architecture) — MEDIUM confidence, cross-verified against multiple deployment tutorials on caching pretrained-model artifacts
- `.planning/codebase/ARCHITECTURE.md` and `.planning/codebase/STRUCTURE.md` (existing skeleton mapping, HIGH confidence — direct repo inspection)
- `.planning/PROJECT.md` (project requirements and explicit risk-mitigation decisions, HIGH confidence — primary source)

---
*Architecture research for: solo academic econometrics data-science pipeline (UN SDG API → SQLite → panel modeling → simulation → SHAP → Streamlit dashboard)*
*Researched: 2026-07-10*
