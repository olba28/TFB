# Stack Research

**Domain:** Python data-science pipeline — API ingestion → SQLite panel storage → fixed-effects panel econometrics → ML interpretability (SHAP) → local Streamlit/Plotly geospatial dashboard
**Researched:** 2026-07-10
**Confidence:** HIGH for package versions and cross-compatibility (empirically verified by installing and executing the actual stack, not just reading docs) · HIGH for UN SDG API request/response shape (verified via live requests against the production API) · MEDIUM for general best-practice conventions (official docs / community consensus, not independently re-derived)

## Verification method (why confidence is unusually high for this report)

Beyond documentation lookup, this research **installed the full candidate stack into an isolated virtual environment and actually executed it**: fit a `PanelOLS` model (weighted and unweighted, with entity+time effects), round-tripped a DataFrame through SQLite via SQLAlchemy, computed SHAP values with `TreeExplainer`, resolved a UN M49 numeric country code to ISO3 with `pycountry`, and built a Plotly choropleth figure — all on Python 3.12.4 with the latest available (2026-07-10) versions of every library. All steps passed. Separately, the UN SDG API was queried live (not from cached/secondary sources) to confirm the actual response schema, pagination ceiling, and a data-shape gotcha (see below). Where a claim rests only on documentation/web search rather than this direct execution, it is marked MEDIUM or LOW explicitly.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12.4 (already installed) | Runtime | Already the project's environment; satisfies the `>=3.12` floor required by `shap` 0.52 — do not downgrade Python or `shap` install will fail to resolve. |
| pandas | **3.0.3** (latest) | DataFrame engine for the whole pipeline | Initially flagged as a risk (a `linearmodels` source comment says "Fix this for pandas 3" for weighted-panel internals), but **empirically verified**: `linearmodels` 7.0 `PanelOLS` fits correctly under pandas 3.0.3 for both unweighted and weighted fixed-effects regressions in this environment. `pandas` 3.0 is the actively maintained line (2.3.3, released Sept 2025, was the last 2.x release before 3.0 shipped Jan 2026) — new projects should target it rather than pin to a sunset branch. |
| requests | 2.34.x (2.31+ as already pinned is compatible) | HTTP client for UN SDG API ingestion | Standard, zero-controversy choice for a REST/JSON API with no auth. No need for `httpx`/async here — the ingestion is a batch, one-time-per-run job over ~150 countries × a handful of indicators, not high-concurrency. |
| SQLite (stdlib `sqlite3`) + **SQLAlchemy 2.0.51** | 2.0.51 | Local panel storage engine + pandas I/O layer | SQLite itself needs no library (Python stdlib). For `DataFrame.to_sql`/`read_sql`, pandas' own docs describe a raw `sqlite3.Connection` as **legacy-only support** (no transaction rollback, no `read_sql_table`); a SQLAlchemy `Engine` is pandas' recommended connection object. Verified: `df.to_sql(name, engine, ...)` + `pd.read_sql(...)` round-trip works cleanly under pandas 3.0.3. |
| statsmodels | **0.14.6** | Diagnostics, OLS baseline, general econometrics utilities | Latest stable; a documented pandas-3.0 *import* bug was already patched by 0.14.x. Verified importable and usable alongside `linearmodels` in the same environment. |
| linearmodels | **7.0** (released Oct 2025) | `PanelOLS` fixed-effects panel regression (entity + time effects) | This is the standard, purpose-built library for panel fixed-effects in Python — `statsmodels` alone does not offer a first-class `PanelOLS`/entity-demeaning API; `linearmodels` builds on `statsmodels` for exactly this gap (this is also why the PROJECT.md constraint requires both packages). Verified: `PanelOLS(y, X, entity_effects=True, time_effects=True).fit(cov_type="clustered", cluster_entity=True)` runs correctly, including with `weights=`. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scikit-learn | **1.9.0** | Auxiliary tree-based model (`RandomForestRegressor` or `HistGradientBoostingRegressor`) purely to feed SHAP; also preprocessing/train-test utilities for the counterfactual simulation step | `linearmodels.PanelOLS` results are **not** scikit-learn compatible and have no native SHAP explainer. The correct, standard pattern (confirmed by SHAP's own docs and community usage) is to fit a *separate* scikit-learn model on the same panel features purely for `shap.TreeExplainer` interpretability — used as a corroborating/exploratory lens next to, not instead of, the causal PanelOLS results that anchor the thesis's econometric argument. |
| shap | **0.52.0** | SHAP value computation (`TreeExplainer` for the auxiliary sklearn model) | Requires Python ≥3.12 and `numpy>=2` — both already satisfied. Verified: `shap.TreeExplainer(RandomForestRegressor).shap_values(X)` returns correct-shaped output under numpy 2.4.6. Do **not** attempt `shap.KernelExplainer` directly on `PanelOLS.predict` as the primary interpretability method — it is model-agnostic but slow and awkward against a demeaned fixed-effects design matrix; use it only as an optional sanity-check, not the main path. |
| plotly (`plotly.express`) | **6.9.0** | Choropleth country map for the Streamlit dashboard | `px.choropleth(..., locationmode="ISO-3")` (the classic `go.Choropleth`-based geo trace, not the deprecated `Choroplethmapbox`) remains fully current in Plotly 6.x — only the *mapbox-tile* variant (`choroplethmapbox` → `choroplethmap`) was deprecated, which is irrelevant for a simple country-level world map. Verified: figure builds correctly. |
| streamlit | **1.59.1** | Local interactive dashboard shell | Installs cleanly alongside the rest of the stack (verified, no resolver conflicts). Use `st.cache_resource` for the SQLite/SQLAlchemy engine (long-lived, non-serializable) and `st.cache_data` for query results / DataFrames returned to the UI (per current Streamlit caching docs) — this is the standard split and avoids the common mistake of caching a live DB connection with `st.cache_data`. |
| **pycountry** | **26.2.16** *(new — not currently in requirements.txt)* | M49 numeric ↔ ISO3 alpha-3 crosswalk | The UN SDG API returns countries as **M49 numeric `geoAreaCode`** (e.g. `"36"` for Australia), while Plotly's `locationmode="ISO-3"` choropleth needs **ISO3 alpha-3** codes (`"AUS"`). `pycountry.countries.get(numeric=str(code).zfill(3)).alpha_3` performs this lookup and was verified to resolve correctly. It also gives a free, principled way to filter the SDG API's `GeoArea/List` (which mixes real countries with regional aggregates like "Africa" or "LDCs" and has no `type` field to distinguish them) down to actual countries: keep only codes that successfully resolve via `pycountry`. |
| matplotlib | 3.11.0 | Static plots for the written memoria (figures embedded in the 60-80 page document, where Plotly's interactive HTML is not usable) | Use for report-ready static figures (regression diagnostics, coefficient plots); use Plotly only for the interactive Streamlit dashboard. Keep both — they serve different deliverables. |
| seaborn | 0.13.2 | Statistical EDA plots (heatmaps, correlation matrices, distribution plots) on top of matplotlib | Standard EDA companion to matplotlib; no reason to introduce `plotnine` or similar alternatives for a solo academic project. |
| jupyter / ipykernel | 1.0+ / 6.25+ (as already pinned) | EDA and model-development notebooks | Fine as pinned; no changes needed. Keep exploratory work in notebooks, then promote stable ingestion/modeling code to `src/` modules (see PROJECT.md's `src/ingesta/` convention) so the pipeline is reproducibly re-runnable outside the notebook. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Ruff | Formatting + import linting | Already configured in `.vscode/settings.json`; keep. |
| `pip freeze > requirements.lock.txt` | Exact-version reproducibility snapshot | Explicit project requirement (PROJECT.md) — run this immediately after finalizing the stack below and again before each entrega, since the ecosystem (pandas especially) is moving fast right now. |

## Installation

```bash
# Core
pip install "pandas==3.0.3" "numpy>=2,<3" "requests>=2.31" "SQLAlchemy==2.0.51"

# Econometrics
pip install "statsmodels==0.14.6" "linearmodels==7.0"

# ML / interpretability
pip install "scikit-learn==1.9.0" "shap==0.52.0"

# Geo / dashboard
pip install "plotly==6.9.0" "streamlit==1.59.1" "pycountry==26.2.16"

# Plotting for the written memoria
pip install "matplotlib==3.11.0" "seaborn==0.13.2"

# Notebooks (as already pinned)
pip install "jupyter>=1.0" "ipykernel>=6.25"

# Freeze after installing (reproducibility requirement from PROJECT.md)
pip freeze > requirements.lock.txt
```

`pycountry` and `SQLAlchemy` are **new additions** relative to the current `requirements.txt` — both are justified above (pandas-recommended SQLite connection type; mandatory M49→ISO3 crosswalk for the choropleth). Everything else in the current `requirements.txt` (requests, pandas, numpy, jupyter, matplotlib, seaborn, statsmodels, linearmodels, scikit-learn, shap, plotly, streamlit) is confirmed as the right choice — only the exact pinned versions above are new information.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| pandas 3.0.3 | pandas 2.3.3 (last 2.x) | If, during development, a genuine pandas-3-specific bug is hit in `linearmodels`/`statsmodels` that isn't in this report's tested surface (e.g. an unusual weighting/clustering combination) — 2.3.3 is the safe fallback and is still officially supported. Don't downgrade preemptively; the tested happy path (fixed-effects PanelOLS, weighted and unweighted, SQLite round-trip) works on 3.0.3. |
| `linearmodels.PanelOLS` for causal inference + separate sklearn tree model for SHAP | Fit SHAP directly against `PanelOLS` via `KernelExplainer` | Only if a reviewer/tutor specifically insists on Shapley values *of the exact fixed-effects model itself* rather than a corroborating ML model — `KernelExplainer` can wrap `PanelOLS.predict`, but it is slow (model-agnostic sampling) and its permutation baseline is awkward to define sensibly for a within-entity demeaned design matrix. Prefer the dual-model approach unless there's a specific methodological reason not to. |
| SQLAlchemy `Engine` for `to_sql`/`read_sql` | Raw `sqlite3.Connection` | Acceptable for a first quick script/prototype in a notebook, since it's fewer moving parts and this is a solo academic project. Switch to SQLAlchemy before the ingestion pipeline becomes the canonical `src/ingesta/` module, since raw `sqlite3.Connection` can't roll back partial inserts if an API request fails mid-batch. |
| `px.choropleth` (geo trace) | `px.choropleth_map` (MapLibre, formerly `choropleth_mapbox`) | Only needed if you want a tile-based basemap (streets, satellite) behind the country polygons. For a plain "one color per country" world map — this project's actual need — the classic `geo` trace is simpler, has no tile-provider dependency, and is not deprecated. |
| `pycountry` for M49→ISO3 | Hand-maintained CSV crosswalk | If `pycountry` misses specific historical/disputed entities the thesis needs (rare edge cases in the M49 list), fall back to a small manual override dict layered on top of `pycountry` rather than replacing it wholesale. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| `geopandas` / `folium` | GDAL-based geo stack is notoriously fragile to install on Windows (already correctly identified and avoided in PROJECT.md/current STACK.md) | `plotly.express.choropleth` with `locationmode="ISO-3"` — no GDAL, no compiled geo dependencies, works identically on Windows. |
| Un-cached, unbounded API calls straight into the modeling notebook | The UN SDG API has no documented rate limit or SLA; a very large `pageSize` (tested: 50,000) can time out server-side, and re-running notebooks would re-hit the live API on every execution, risking flaky, non-reproducible results — this directly threatens the PROJECT.md requirement for a "versioned local snapshot." | A dedicated ingestion script (in `src/ingesta/`) that paginates with `pageSize` in the 500–2000 range, retries on 429/5xx with backoff, and writes each indicator's raw paginated JSON to `data/raw/<indicator>/<fetch_date>.json` before any transformation touches it. |
| `dimensions=` query parameter for server-side filtering on `/v1/sdg/Indicator/Data` | Tested live: passing `dimensions=Activity:TOTAL` (and a JSON-encoded variant) both returned HTTP 400 — the correct query syntax is undocumented and unreliable in practice. | Fetch all disaggregated rows for an indicator/country and filter **client-side in pandas** to the single "headline" dimension combination (see UN SDG API section below) — confirmed to work reliably. |
| `shap.KernelExplainer` as the *primary* interpretability method | Model-agnostic Kernel SHAP is slow and its results are sensitive to the choice of background/reference dataset; for ~150 countries × 23 years × several indicators, an exact tree-based explainer is both faster and more standard in applied econometrics-plus-ML theses. | `shap.TreeExplainer` on a `RandomForestRegressor`/`HistGradientBoostingRegressor` (already in scikit-learn — no new dependency) fit on the same panel features, used as the primary SHAP path. |
| Adding `xgboost`/`lightgbm` for the auxiliary ML model | Not currently in `requirements.txt`; adds a new binary/compiled dependency (extra Windows install risk) for marginal benefit over what's already available. | `sklearn.ensemble.RandomForestRegressor` or `HistGradientBoostingRegressor` — both native to the already-pinned scikit-learn, both fully supported by `shap.TreeExplainer`. |

## Stack Patterns by Variant

**If a genuine pandas-3-specific bug surfaces in `linearmodels`/`statsmodels` during development (not observed in this report's testing):**
- Pin `pandas==2.3.3` (last 2.x release) instead of 3.0.3.
- Because: 2.3.3 remains officially supported and has zero known `linearmodels`/`statsmodels` friction; the only reason to prefer 3.0.3 is "actively maintained line," which is a soft preference, not a hard requirement — reproducibility for the thesis trumps chasing the newest major version.

**If Modelo 2 (agricultural productivity, indicator 2.3.1) has materially worse country/year coverage than Modelo 1 (already a documented risk in PROJECT.md):**
- Reuse the exact same `PanelOLS` + auxiliary-sklearn-model + SHAP pattern for Modelo 2, just on a smaller filtered panel — no stack changes needed, only smaller `N`.
- Because: keeping methodology identical between the two models is itself a defensible point in the thesis's "Metodología" chapter (same pipeline, documented coverage-driven sample reduction).

## Version Compatibility

Empirically verified together in one Python 3.12.4 virtual environment (`pip install` succeeded with no resolver conflicts, and the cross-library smoke tests described above passed):

| Package | Version | Notes |
|---------|---------|-------|
| numpy | 2.4.6 | pip's resolver settled here (not the absolute-latest 2.5.1) once `shap`/`numba`(via streamlit/altair) were added to the mix — **don't hand-pin an exact numpy version**; constrain `numpy>=2,<3` and let pip resolve the rest. |
| pandas | 3.0.3 | Works with linearmodels 7.0 PanelOLS (weighted + unweighted, entity+time effects) and with SQLAlchemy 2.0.51 `to_sql`/`read_sql`. |
| scipy | 1.18.0 | Pulled in transitively by statsmodels/linearmodels/scikit-learn; no direct pin needed. |
| statsmodels | 0.14.6 | Confirmed importable alongside linearmodels 7.0; pandas-3 import bug already patched at this version. |
| linearmodels | 7.0 | Requires Python ≥3.10, pandas ≥1.4.0, numpy <3,>=1.22.3 — all satisfied. |
| scikit-learn | 1.9.0 | Requires Python ≥3.11. |
| shap | 0.52.0 | Requires Python ≥3.12 **and** numpy ≥2 — this is the binding constraint that sets the Python floor for the whole project. |
| plotly | 6.9.0 | `px.choropleth` (non-mapbox) unaffected by the `choroplethmapbox`→`choroplethmap` deprecation. |
| streamlit | 1.59.1 | Installs cleanly on top of the rest; pulls in pyarrow 25.0.0, altair 6.2.2 as its own dependencies (no action needed). |
| SQLAlchemy | 2.0.51 | Mature 2.0 line; works with sqlite3 out of the box via `create_engine("sqlite:///...")`. |
| pycountry | 26.2.16 | Requires Python ≥3.10. |

## UN SDG API — Concrete Usage Pattern

Verified live against `https://unstats.un.org/SDGAPI/v1/sdg/` on 2026-07-10.

**Base URL:** `https://unstats.un.org/SDGAPI/v1/sdg/`

**Primary endpoint for this project:** `GET /Indicator/Data`

Query parameters (from the live OpenAPI spec at `/SDGAPI/swagger/v1/swagger.json`):
- `indicator` (repeatable, e.g. `indicator=6.4.2`)
- `areaCode` (repeatable, M49 numeric, e.g. `areaCode=4` for Afghanistan)
- `timePeriodStart` / `timePeriodEnd` (float years) or `timePeriod` (repeatable exact years)
- `page`, `pageSize` (pagination)
- `dimensions` (documented but its query-string format returned HTTP 400 in live testing for the forms tried — **do not rely on it**; filter dimensions client-side instead, see below)

Example request (live-verified):
```
GET https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data?indicator=6.4.2&pageSize=100&page=1
```

Response shape (live-verified, abbreviated):
```json
{
  "totalElements": 20016,
  "totalPages": 201,
  "pageNumber": 1,
  "size": 100,
  "data": [
    {
      "goal": ["6"], "target": ["6.4"], "indicator": ["6.4.2"],
      "series": "ER_H2O_STRESS",
      "seriesDescription": "Level of water stress: freshwater withdrawal as a proportion of available freshwater resources (%)",
      "geoAreaCode": "4", "geoAreaName": "Afghanistan",
      "timePeriodStart": 2000.0,
      "value": "54.76",
      "source": "Food and Agriculture Organisation of United Nations (FAO)",
      "attributes": {"Nature": "E", "Units": "PERCENT", "Observation Status": "I"},
      "dimensions": {"Reporting Type": "G", "Activity": "TOTAL"}
    }
  ]
}
```

**Critical gotcha (live-verified — will silently break the panel join if missed):** indicators with sectoral breakdowns (6.4.2 confirmed) return **multiple rows per country-year**, one per `dimensions.Activity` value (`TOTAL`, `ISIC4_A01_A0210_A0322`, `INDUSTRIES`, `ISIC4_GTT` observed for 6.4.2). To get exactly one row per country-year, filter client-side after fetching to `dimensions == {"Reporting Type": "G", "Activity": "TOTAL"}` (the headline aggregate value). Always inspect `dimensions` for every new indicator pulled in — don't assume a flat one-row-per-country-year shape by default.

**Pagination guidance (live-tested):** `pageSize` up to 5,000 responded quickly; `pageSize=50,000` on the full 20,016-row 6.4.2 dataset timed out. Use `pageSize` in the 500–2000 range, loop over `page` until `page >= totalPages`, and add retry/backoff (`urllib3.Retry` via a `requests.Session` + `HTTPAdapter`, or a manual `try/except` with exponential sleep) around each request — no official rate limit is published, so treat 429/5xx as expected occasional events, not fatal errors.

**Country identification:** `GET /GeoArea/List` returns a **flat list** with no field distinguishing real countries from regional aggregates (e.g. `{"geoAreaCode":"2","geoAreaName":"Africa"}` sits alongside real countries with no `type` marker). Cross-reference every `geoAreaCode` against `pycountry.countries.get(numeric=str(code).zfill(3))`: codes that resolve are real (ISO) countries; codes that don't (regions, "LDCs", "World", etc.) should be excluded from the panel. This single step handles both the PROJECT.md requirement to work "at country level (not subnational)" and the choropleth's need for ISO3 codes.

**Local versioned snapshot (project requirement):** write each indicator's raw, unfiltered JSON pages to disk before any transformation, e.g. `data/raw/<indicator_code>/<fetch_date>.json` (or one file per page). This satisfies the PROJECT.md mitigation for "Cambios en la API de la ONU" and makes the whole pipeline replayable from disk without re-hitting the live API — plain `requests` + `pathlib`/`json` (stdlib) is sufficient; no need for `requests-cache` or similar for a project this size.

## Sources

- `https://unstats.un.org/SDGAPI/swagger/v1/swagger.json` — official OpenAPI spec, fetched directly — endpoint/parameter/response-schema definitions (HIGH)
- `https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data` (multiple live queries, indicator 6.4.2) — actual production API responses — response shape, pagination limits, dimensions gotcha (HIGH, directly observed)
- `https://unstats.un.org/SDGAPI/v1/sdg/GeoArea/List` — live query — flat list shape, no country/region type field (HIGH, directly observed)
- `https://pypi.org/pypi/<package>/json` for pandas, numpy, linearmodels, statsmodels, scikit-learn, shap, plotly, streamlit, SQLAlchemy, pycountry, matplotlib, seaborn — official PyPI release metadata — current versions and `requires_python` (HIGH, official source)
- Isolated virtual environment install + executed smoke tests (`PanelOLS` fit, SQLite round-trip via SQLAlchemy, `shap.TreeExplainer`, `pycountry` M49→ISO3 lookup, `plotly` choropleth figure construction) — run directly in this session on 2026-07-10 (HIGH, direct empirical verification — the strongest evidence tier available)
- `pandas.DataFrame.to_sql` / `pandas.read_sql` official docs (pandas.pydata.org) — SQLAlchemy vs raw `sqlite3.Connection` guidance (MEDIUM — doc-based, cross-checked against the empirical SQLite round-trip test above)
- Streamlit official caching docs (`docs.streamlit.io/develop/concepts/architecture/caching`) — `st.cache_data` vs `st.cache_resource` split (MEDIUM — doc-based, not independently re-tested against a live Streamlit app in this session)
- `github.com/bashtage/linearmodels` source (`panel/model.py`, via web search) — the pandas-3 TODO comment that prompted the empirical test above (LOW as a standalone claim — superseded by the direct empirical verification, which found no actual breakage in the tested code paths)
- Plotly official v6 migration guide (`plotly.com/python/v6-migration/`) — `choroplethmapbox` → `choroplethmap` deprecation scope (MEDIUM — doc-based; confirmed `px.choropleth`/non-mapbox geo trace unaffected)

---
*Stack research for: Python data-science TFB — UN SDG water-stress panel econometrics pipeline*
*Researched: 2026-07-10*
