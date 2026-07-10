# External Integrations

**Analysis Date:** 2026-07-10

## APIs & External Services

**Data Ingestion:**
- UN ODS/SDG (Sustainable Development Goals) API - Source for economic and water stress data
  - SDK/Client: `requests` library (2.31+)
  - Auth: Unknown (likely public API, no credentials mentioned in requirements)
  - Endpoint: Not documented yet (project skeleton — implementation in `src/ingesta/` pending)

## Data Storage

**Databases:**
- None configured (project skeleton stage)
- Planned: Local CSV/Excel data cache in `data/` directory
- ORM/Client: None (using pandas DataFrame as in-memory data structure)

**File Storage:**
- Local filesystem only
  - Raw data: `data/raw/` (structure planned, directory exists but empty)
  - Processed data: `data/processed/` (pending implementation)
  - Figures/outputs: `figuras/` (for analysis output visualizations)

**Caching:**
- None configured (planned: local CSV cache for UN API responses to avoid repeated API calls)

## Authentication & Identity

**Auth Provider:**
- Custom/None - No authentication framework configured
- UN ODS/SDG API likely public access (no credentials identified in requirements)

## Monitoring & Observability

**Error Tracking:**
- None (project skeleton — no integration configured)

**Logs:**
- print() / console output only (no structured logging framework configured)
- Jupyter notebooks: Cell output logs (in `notebook/` directory)

## CI/CD & Deployment

**Hosting:**
- Streamlit Cloud (target platform for dashboard deployment)
- Alternative: Local server execution

**CI Pipeline:**
- None configured (project skeleton)
- Recommended: GitHub Actions or similar for requirements.lock generation and testing

## Environment Configuration

**Required env vars:**
- None identified yet (UN ODS/SDG API access likely public or will require API_KEY when implemented)

**Secrets location:**
- .env file not present (should be added if UN API requires authentication)
- Credentials location: TBD per implementation

## Webhooks & Callbacks

**Incoming:**
- None (data pull-based, not event-driven)

**Outgoing:**
- None configured

## Data Pipeline Architecture

**Planned Flow (based on requirements.txt structure):**

```
UN ODS/SDG API
    ↓
requests library (src/ingesta/)
    ↓
pandas DataFrame
    ↓
statsmodels (panel analysis) / scikit-learn (ML)
    ↓
SHAP (interpretability)
    ↓
Streamlit dashboard (plotly choropleth visualization)
```

**Data Formats:**
- Input: JSON from UN API
- Processing: pandas DataFrame
- Storage: CSV (local cache in `data/`)
- Output: Streamlit interactive dashboard with plotly choropleth maps

## Notable Architectural Decisions

**No GDAL/GeoPandas:**
- Project explicitly avoids geopandas and folium on Windows due to GDAL installation fragility
- Alternative: Plotly choropleth maps (pure Python, stable on Windows)

**No Database:**
- Project is analysis-focused with no transactional workload
- Data stored locally as CSV files in `data/` directory
- Planned: Cache mechanism for UN API responses to minimize API calls

**Notebook-First Development:**
- Jupyter notebooks in `notebook/` directory for exploratory data analysis (EDA)
- Production code in `src/` modules for reproducibility

---

*Integration audit: 2026-07-10*
