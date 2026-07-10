# Technology Stack

**Analysis Date:** 2026-07-10

## Languages

**Primary:**
- Python 3.12.4 - Data science, analysis, API ingestion, and dashboard application

## Runtime

**Environment:**
- Python 3.12.4

**Package Manager:**
- pip 26.0.1
- Lockfile: Missing (project uses `requirements.txt` with version floors; exact versions should be frozen via `pip freeze > requirements.lock.txt` per project notes)

## Frameworks

**Core Analysis:**
- pandas 2.0+ - Data manipulation and tabular analysis
- numpy 1.24+ - Numerical computing
- statsmodels 0.14+ - Econometric modeling and panel data analysis
- linearmodels 5.3+ - PanelOLS for fixed effects models (Baltagi, Wooldridge methods)
- scikit-learn 1.3+ - Machine learning algorithms and preprocessing

**Visualization:**
- matplotlib 3.7+ - Base plotting library
- seaborn 0.12+ - Statistical data visualization
- plotly 5.18+ - Interactive choropleth maps and dashboards (chosen for Windows stability without GDAL)

**Dashboard/Web UI:**
- Streamlit 1.30+ - Interactive web dashboard for geospatial visualization
- Note: Dash considered as alternative but not selected

**Data Science/Interpretability:**
- SHAP 0.43+ - Feature importance and model interpretability (Molnar methods)

**Development & Notebooks:**
- Jupyter 1.0+ - Interactive notebooks for exploratory data analysis (EDA)
- ipykernel 6.25+ - Jupyter kernel support

## Key Dependencies

**Critical:**
- requests 2.31+ - HTTP client for UN ODS/SDG API data ingestion

**Data Processing:**
- pandas 2.0+ - Core tabular data framework
- numpy 1.24+ - Array operations and numerical computations
- statsmodels 0.14+ - Panel model estimation and diagnostics
- linearmodels 5.3+ - Fixed effects panel regression (PanelOLS)

**Machine Learning & Analytics:**
- scikit-learn 1.3+ - Preprocessing, model selection, validation
- SHAP 0.43+ - Model interpretation and feature attribution

**Visualization:**
- matplotlib 3.7+ - Base plotting
- seaborn 0.12+ - Statistical visualization
- plotly 5.18+ - Interactive geospatial choropleth maps (avoids GDAL dependency for Windows stability)
- Streamlit 1.30+ - Web dashboard framework

## Configuration

**Environment:**
- Virtual environment: `.venv/` (configured in VS Code via `python.defaultInterpreterPath`)
- VS Code settings configured in `.vscode/settings.json` with Ruff formatter and Pylance type checking

**Build:**
- No build configuration (pure Python data science project — no compilation required)
- Notebooks and scripts executed directly via Python/Jupyter

**Formatter & Linting:**
- Ruff (charliermarsh.ruff) - Code formatting and import organization
- Pylance - Type checking mode: "basic"

## Platform Requirements

**Development:**
- OS: Windows (project explicitly avoids geopandas/folium due to GDAL installation fragility on Windows)
- Python 3.12+
- pip 26.0+
- Virtual environment tool (venv built-in)
- VS Code with Python and Jupyter extensions

**Production:**
- Deployment target: Streamlit Cloud or local server hosting
- No production database specified (data ingestion from UN ODS/SDG API to CSV/Excel)

---

*Stack analysis: 2026-07-10*
