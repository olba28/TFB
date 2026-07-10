# Codebase Concerns

**Analysis Date:** 2026-07-10

## Critical Gaps (Early-Stage Project)

This is a skeleton-stage academic project with minimal implementation. The following concerns reflect the incomplete state and risks that should be addressed early.

---

## Tech Debt

**Missing Reproducibility Lockfile:**
- Issue: `requirements.txt` explicitly recommends creating `requirements.lock.txt` via `pip freeze` for exact reproducibility, noting this is "a criterion valued by the tribunal" (academic evaluation committee). No lockfile exists.
- Files: `requirements.txt` (lines 2-4)
- Impact: Environments built from requirements.txt will have different minor/patch versions across installations and over time, making results irreproducible and vulnerable to tribunal rejection on reproducibility grounds
- Fix approach: Run `pip freeze > requirements.lock.txt` after initial environment setup and commit it. Add to build/CI documentation that `requirements.lock.txt` is the source of truth for reproducible builds.

**Empty Implementation Skeleton:**
- Issue: `src/ingesta/` directory exists but is completely empty. Requirements reference data ingestion (API ODS de la ONU) but no code is implemented.
- Files: `src/ingesta/` (empty directory)
- Impact: Data pipeline cannot be executed; no way to fetch or validate UN ODS API data ingestion
- Fix approach: Create `src/ingesta/__init__.py`, `src/ingesta/api.py` with functions to query UN ODS API using requests library (specified in requirements)

**Missing Data Manifests:**
- Issue: `.gitignore` specifies that `data/**/manifest.json` should be committed (line 18) but manifests do not exist anywhere in the project
- Files: `data/` directory (empty), referenced in `gitignore` (line 18)
- Impact: Data provenance and versioning tracking is non-functional; cannot document which dataset versions were used for analysis
- Fix approach: Establish a manifest schema (e.g., timestamp, data source URL, row count, checksum) and create initial manifests when data is first ingested

**No Project Entry Points:**
- Issue: No `main.py`, `__init__.py`, or other executable entry points defined
- Files: None
- Impact: Unclear how to run the analysis pipeline or which scripts are entry points; no documented execution flow
- Fix approach: Create `src/__init__.py` and define main pipeline execution function(s); document in README

**Missing README and Documentation:**
- Issue: No README.md, project overview, or usage documentation
- Files: None (should be at project root)
- Impact: No onboarding for collaborators; unclear what the project does or how to use it
- Fix approach: Create README.md documenting project scope, setup instructions, data sources, and analysis workflow

---

## Fragile Areas

**Windows Geospatial Dependencies:**
- Files: `requirements.txt` (lines 32-33)
- Why fragile: GDAL (required by geopandas/folium) is notoriously difficult to install on Windows. Comments in requirements.txt note this: "geopandas / folium: opcionales; en Windows requieren GDAL, más frágil de instalar" (optional; on Windows require GDAL, more fragile to install). Current project uses plotly as a workaround.
- Safe modification: Keep geopandas/folium as optional dependencies in a separate `requirements-geospatial.txt` file with installation documentation. Document manual GDAL installation steps for Windows users or provide Docker container.
- Test coverage: Geospatial visualization (section 4.5 per comments) not yet implemented, so not currently blocking. Add geospatial tests only after implementation.

**Dependency Version Floors (Not Exact Versions):**
- Files: `requirements.txt` (lines 7-32)
- Why fragile: All dependencies specify only floor versions (>=). Pandas >=2.0, NumPy >=1.24, scikit-learn >=1.3 allow significant variation. New minor/patch releases may introduce breaking changes or behavioral differences.
- Safe modification: After initial environment setup and testing, run `pip freeze > requirements.lock.txt` and make that the canonical lock file. Use `pip-compile` or equivalent for future dependency updates.

**Multiple Machine Learning & Statistical Libraries:**
- Files: `requirements.txt` (lines 19-27)
- Why fragile: Project uses linearmodels for panel effects and scikit-learn for ML in same pipeline (sections 3.4, 3.5, 4.3 per comments). Different random seeds, preprocessing, and output formats between libraries can cause subtle bugs if not carefully integrated.
- Safe modification: Create a standardized analysis pipeline module (`src/analysis/models.py`) that wraps both linearmodels and scikit-learn with consistent interfaces and documented random seed control.

---

## Missing Critical Features

**No Environment Configuration Template:**
- Problem: `.gitignore` specifies `.env` (line 25) but no `.env.template` or documentation of required environment variables
- Blocks: Cannot document API credentials, data paths, or configuration needed to run pipeline
- Fix: Create `.env.template` documenting all required variables (at minimum: UN ODS API endpoint, data directory path)

**No Testing Framework:**
- Problem: No test files, test runner configuration (pytest/unittest), or testing strategy defined
- Blocks: Cannot validate data ingestion, model outputs, or analysis correctness
- Fix: Establish pytest configuration in `pytest.ini`; create `tests/` directory with initial tests for data validation and model components

**No Data Pipeline Definition:**
- Problem: Gitignore references "pipeline" but no ETL/DAG framework (Airflow, Prefect, Snakemake) or pipeline script exists
- Blocks: Unclear execution order for data ingestion → cleaning → analysis → visualization
- Fix: Create `src/pipeline.py` or Snakefile documenting data flow and dependencies

**No Setup/Installation Documentation:**
- Problem: Only `requirements.txt` exists; no setup.py, pyproject.toml, or installation instructions
- Blocks: New contributors cannot reliably set up the development environment
- Fix: Create `setup.py` or `pyproject.toml`; document Python version requirements; add virtual environment setup script

---

## Scaling Limits

**Hardcoded Assumptions:**
- Current capacity: Project structure assumes single-machine analysis (no distributed computing)
- Limit: If UN ODS dataset grows or analysis scales to subnational regions, in-memory pandas/numpy operations may exceed available RAM
- Scaling path: Design data loading to use chunked reading; consider Dask for parallel processing if dataset exceeds memory

**No Caching Strategy:**
- Problem: No documented caching of API responses, processed datasets, or model outputs
- Impact: Re-runs of analysis will re-fetch all data from UN ODS API, slowing iteration and potentially hitting rate limits
- Fix: Implement `src/cache.py` with file-based or Redis caching for API calls and intermediate datasets

---

## Security Considerations

**Secrets in Requirements / Docs:**
- Risk: `.env` is gitignored but template/documentation missing; potential for API credentials to be accidentally committed
- Files: `.gitignore` (line 25), no `.env.template` present
- Current mitigation: `.gitignore` blocks `.env` files
- Recommendations: Create `.env.template`; add pre-commit hook to scan for accidentally staged `.env` files; document secret rotation policy

**API Rate Limiting / Abuse:**
- Risk: UN ODS API access not documented; no rate limiting or error handling for API calls
- Files: Requirements mention requests library but no implementation yet
- Current mitigation: None
- Recommendations: Implement exponential backoff and rate limiting in API client; log all requests; document API quota and throttling strategy

**Data Provenance Tracking:**
- Risk: Missing manifests mean no audit trail of which data versions were used, allowing for undetectable data tampering
- Files: `data/` (no manifests), `.gitignore` (line 18 expects manifests that don't exist)
- Current mitigation: None
- Recommendations: Implement manifest creation with cryptographic hash (SHA256) of each dataset file; document data source URLs and download timestamps

---

## Known Gaps (By Planned Analysis Section)

Per comments in `requirements.txt`, the project plans these analysis sections. Current gaps:

| Section | Planned | Current Status | Gap |
|---------|---------|---|---|
| 3.3: Notebooks / exploratory analysis | jupyter, matplotlib, seaborn | Notebook directory empty | No notebooks yet |
| 3.4: Panel models with fixed effects | statsmodels, linearmodels | Not implemented | No model code |
| 3.5: Panel model interpretation | shap | Not implemented | No interpretation code |
| 4.3: Machine learning | scikit-learn | Not implemented | No ML pipeline |
| 4.4: Variable importance | shap | Not implemented | No SHAP integration |
| 4.5: Geospatial dashboard | plotly, streamlit | Not implemented | No dashboard app |

---

## Dependency Risk Summary

| Package | Risk | Reason |
|---------|------|--------|
| GDAL (indirect via geopandas) | HIGH | Windows installation fragility noted in comments; optional workaround (plotly) used |
| statsmodels, linearmodels | MEDIUM | Panel model libraries; compatibility/API changes possible with version updates |
| scikit-learn | MEDIUM | Version floor (>=1.3) is wide; preprocessing/model behavior can vary |
| pandas, numpy | MEDIUM | Foundation libraries; version mismatches can cascade |
| plotly, streamlit | LOW | Well-maintained; dashboard libraries are less critical path |

---

*Concerns audit: 2026-07-10*
