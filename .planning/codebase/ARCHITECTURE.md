<!-- refreshed: 2026-07-10 -->
# Architecture

**Analysis Date:** 2026-07-10

## System Overview

This is a Python data science pipeline project for an academic thesis on "Impacto económico del estrés hídrico" (Economic impact of water stress). The architecture follows a sequential pipeline pattern common in data analysis projects: ingest → transform → analyze → model → visualize.

```text
┌─────────────────────────────────────────────────────────────┐
│                     Dashboard Layer                         │
│        Streamlit Geospatial Visualization (4.5)             │
│  `notebook/` or future `src/dashboard/` (plotly)           │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  Modeling & Analysis Layer                  │
│  Panel Models (statsmodels, linearmodels)                  │
│  ML Models (scikit-learn)                                  │
│  Interpretability (SHAP)                                   │
│  `src/modelos/` or embedded in `notebook/`                │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│          Exploratory Analysis & Transformation Layer         │
│  Jupyter Notebooks — descriptive analysis                  │
│  Pandas/NumPy data manipulation                            │
│  `notebook/`                                               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│               Data Ingestion & Processing                   │
│  UN ODS API ingestion via requests library                 │
│  Data versioning: manifests only (CSV/JSON in .gitignore) │
│  `src/ingesta/`                                            │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              External Data Sources & Storage                │
│  UN ODS API (Open Data Portal)                             │
│  Local `/data/` directory (manifests + downloaded files)   │
│  Model serialization: `/data/modelos/` (.pkl, .joblib)     │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File/Location |
|-----------|----------------|------|
| Data Ingestion | Fetch water stress, economic, and environmental data from UN ODS API | `src/ingesta/` |
| Data Processing | Clean, merge, and prepare panel data for modeling | `notebook/` (exploratory) |
| Statistical Modeling | Panel data regression with fixed effects (Baltagi, Wooldridge methods) | `src/modelos/` (planned) |
| ML Modeling | scikit-learn models for prediction and pattern discovery | `src/modelos/` (planned) |
| Analysis & Interpretation | SHAP values, variable importance, hypothesis testing | `notebook/` |
| Visualization | Geospatial choropleth, time-series plots, summary dashboards | `src/dashboard/` (planned, Streamlit) |
| Output | Static figures and reports | `figuras/` |

## Pattern Overview

**Overall:** Sequential Analysis Pipeline

**Key Characteristics:**
- Notebook-driven exploratory workflow (Jupyter for prototyping)
- Transition to modular `src/` structure for reproducible pipeline stages
- Panel data econometrics (country-level cross-sectional + time-series)
- Multiple modeling approaches (fixed-effects regression, ML, interpretability)
- Emphasis on reproducibility (requirements.txt, manifest-based data versioning)
- Windows-friendly dependencies (Plotly instead of GDAL-dependent GeoPandas)

## Layers

**Data Ingestion Layer:**
- Purpose: Fetch data from UN ODS API; document provenance
- Location: `src/ingesta/`
- Contains: API client, manifest generation, raw data storage coordination
- Depends on: `requests` library, UN ODS API
- Used by: Processing layer

**Data Processing Layer:**
- Purpose: Clean, transform, and merge multi-source data into analysis-ready format
- Location: `notebook/` (exploratory phase) → `src/etl/` (future modularization)
- Contains: Pandas operations, data validation, feature engineering
- Depends on: Ingestion layer, pandas, numpy
- Used by: Analysis and modeling layers

**Analysis Layer:**
- Purpose: Exploratory data analysis, hypothesis generation, statistical validation
- Location: `notebook/` (Jupyter-based)
- Contains: Descriptive statistics, correlation analysis, visualization prototypes
- Depends on: Processing layer, matplotlib, seaborn, statsmodels
- Used by: Modeling layer, dashboard layer

**Modeling Layer:**
- Purpose: Build econometric and ML models to answer research questions
- Location: `src/modelos/` (planned structure)
- Contains: Panel regression models (statsmodels, linearmodels), scikit-learn estimators
- Depends on: Processing layer, statsmodels, linearmodels, scikit-learn
- Used by: Interpretation layer, visualization/dashboard

**Interpretation Layer:**
- Purpose: Extract variable importance, causal inference, model explanations
- Location: Embedded in `notebook/` or `src/modelos/`
- Contains: SHAP analysis, coefficient interpretation
- Depends on: Modeling layer, shap library
- Used by: Visualization layer

**Visualization/Dashboard Layer:**
- Purpose: Present findings via geospatial dashboard and static figures
- Location: `src/dashboard/` (planned) for Streamlit app; `figuras/` for exports
- Contains: Plotly choropleth maps, time-series interactives, summary tiles
- Depends on: All upstream layers, plotly, streamlit
- Used by: End users / thesis evaluators

## Data Flow

### Primary Request Path (Thesis Analysis Pipeline)

1. **Data Collection** (`src/ingesta/`) — Researcher triggers manual API call or scheduler
   - Calls UN ODS API for water stress, economic indicators, environmental data
   - Saves manifest JSON to `data/[date]/manifest.json`
   - Downloads CSV/JSON to `data/[date]/` (not version-controlled)

2. **Exploratory Analysis** (`notebook/`) — Jupyter notebooks for each section
   - Load data from `data/[date]/manifest.json`
   - Clean and validate (remove nulls, outliers, duplicates)
   - Compute descriptive statistics, visualizations
   - Generate hypotheses

3. **Model Development** (`src/modelos/` / `notebook/`) — Econometric and ML models
   - Prepare panel structure (country-time dimensions)
   - Fit fixed-effects panel regression (linearmodels.PanelOLS)
   - Fit ML models (scikit-learn)
   - Serialize trained models to `data/modelos/*.pkl`

4. **Interpretation** (`notebook/` or `src/modelos/`) — Extract insights
   - SHAP feature importance
   - Coefficient analysis
   - Robustness checks

5. **Visualization** (`src/dashboard/` or `notebook/`) — Present findings
   - Streamlit dashboard with Plotly choropleth (country-level water stress)
   - Time-series and heatmaps
   - Summary metrics

6. **Export** (`figuras/`) — Static output for thesis
   - PNG/PDF figures from notebooks or Streamlit exports

### State Management

- **Data state:** Managed via manifest files; raw data regenerable from API
- **Model state:** Serialized to `data/modelos/` as .pkl/.joblib files
- **Analysis state:** Embedded in notebook cells; reproducible if data unchanged
- **Configuration:** Environment variables (`.env`, not versioned); package versions (`requirements.txt`, versioned)

## Key Abstractions

**Panel Data Structure:**
- Purpose: Organize multi-country, multi-year economic/environmental observations
- Examples: Country × Year grid for regression analysis
- Pattern: DataFrame with MultiIndex (country, year) or hierarchical grouping

**Model Pipeline:**
- Purpose: Encapsulate fit → predict → evaluate workflow
- Examples: scikit-learn Pipeline, statsmodels model classes
- Pattern: Fit on training subset, evaluate on holdout or time-forward

**Manifest-Based Versioning:**
- Purpose: Document data source, download date, row count, checksum without storing large files
- Examples: `data/2024-07-10/manifest.json` records API query parameters
- Pattern: Scripts check manifest before re-downloading; enables reproducibility without storage bloat

## Entry Points

**Manual Data Ingestion:**
- Location: `src/ingesta/` (not yet implemented, skeleton folder)
- Triggers: Researcher runs Python script or Jupyter cell
- Responsibilities: Query UN ODS API, save manifest, download data

**Jupyter Notebooks (EDA & Modeling):**
- Location: `notebook/`
- Triggers: Researcher opens Jupyter Lab and executes cells
- Responsibilities: Load data, analyze, prototype models, generate figures

**Streamlit Dashboard (Future):**
- Location: `src/dashboard/app.py` (not yet implemented)
- Triggers: `streamlit run src/dashboard/app.py`
- Responsibilities: Load trained models, serve interactive geospatial visualizations

## Architectural Constraints

- **Data versioning:** Raw CSV/JSON files excluded from Git; only manifests committed. Requires manual or CI-triggered API calls to regenerate.
- **Windows compatibility:** GeoPandas/GDAL avoided in favor of Plotly (no complex C library dependencies on Windows).
- **Reproducibility:** All package versions pinned via `requirements.txt` (floors); exact reproducibility via `requirements.lock.txt` (post-install freeze).
- **Notebook dependencies:** Jupyter notebooks assume cell execution order; no formal import/dependency management within notebooks (future: extract functions to `src/`).
- **Model persistence:** Serialized models (.pkl/.joblib) not versioned; regenerated from scripts (assumed `.py` files in `src/modelos/` are maintained separately).

## Anti-Patterns

### Embedded Configuration

**What happens:** Paths, API endpoints, threshold values hardcoded in notebook cells or scripts.
**Why it's wrong:** Makes analysis non-reproducible across environments; requires manual edits to run elsewhere.
**Do this instead:** Use `.env` file (loaded via `python-dotenv` or similar) for secrets/paths; use configuration section in `src/config.py` for thresholds.

### Notebook as Single Source of Truth

**What happens:** All analysis lives in `notebook/`; no modular functions in `src/`.
**Why it's wrong:** Notebooks are not easily imported, tested, or reused; difficult to parallelize analyses; version control shows raw cell outputs.
**Do this instead:** Move utility functions (data loading, cleaning, feature engineering) to `src/` modules; notebooks orchestrate, not implement.

### Manual Data Download

**What happens:** Researcher manually downloads CSV from web, copies to `data/` folder.
**Why it's wrong:** Not reproducible; no audit trail of source/date; easy to accidentally use stale data.
**Do this instead:** Use `src/ingesta/fetch_data.py` to programmatically download and manifest each update.

## Error Handling

**Strategy:** Early validation; fail fast on data anomalies

**Patterns:**
- Data ingestion: Check manifest checksum, row count; raise exception if unexpected
- Model fitting: Validate panel structure (no missing country-year combinations); check for multicollinearity warnings
- Visualization: Graceful fallback if geospatial data missing (show table instead of map)

## Cross-Cutting Concerns

**Logging:** Currently ad-hoc via `print()` in notebooks; future: use Python `logging` module in `src/` modules with handlers writing to `data/logs/`.

**Validation:** Manual inspection in notebooks; future: unit tests in `src/tests/` for data pipelines.

**Reproducibility:** Environment isolation via virtual environment + `requirements.txt`; data versioning via manifests.

---

*Architecture analysis: 2026-07-10*
