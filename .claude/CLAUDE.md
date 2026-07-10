<!-- GSD:project-start source:PROJECT.md -->

## Project

**TFB — Impacto económico del estrés hídrico**

Trabajo Final de Bàtxelor (TFB) en Ciencia de Datos que cuantifica y modela la relación entre el estrés hídrico de un país y sus resultados económicos —crecimiento del PIB per cápita y productividad agrícola— usando exclusivamente indicadores públicos ODS de la API de la ONU para más de 150 países (series 2000–2022). El sistema resultante permite simular escenarios contrafactuales: cuánto mejorarían el PIB y la productividad agrícola si el estrés hídrico se redujera en X puntos porcentuales, y visualizar los resultados en un dashboard geoespacial interactivo. Es un trabajo académico individual, entregado y defendido ante tribunal (UCMA).

**Core Value:** Un pipeline reproducible de extremo a extremo (ingesta API → almacenamiento → modelado → simulación → visualización) que demuestre, con datos abiertos y trazables, la relación cuantitativa entre estrés hídrico y resultados económicos — y que sea defendible ante un tribunal académico.

### Constraints

- **Lenguaje/Stack**: Python, dependencias fijadas en `requirements.txt` (pandas, numpy, statsmodels, linearmodels, scikit-learn, shap, plotly, streamlit, jupyter) — no cambiar sin justificación
- **Fuente de datos**: Exclusivamente la API pública ODS de la ONU — ninguna otra fuente de datos, para garantizar trazabilidad y reproducibilidad total
- **Almacenamiento**: SQLite (decisión del alumno — cero configuración, un solo fichero, fácil de entregar/versionar)
- **Alcance geográfico/temporal**: Nivel país (no subnacional), 2000–2022, ~150–180 países según cobertura
- **Metodología**: Modelos de panel con efectos fijos (no solo regresión OLS simple) para controlar heterogeneidad no observada
- **Entregable académico**: Memoria de 60–80 páginas + defensa oral; debe seguir la estructura de índice ya propuesta (introducción, marco teórico, metodología, desarrollo, resultados, conclusiones, referencias APA, anexos)
- **Plazo**: Cronograma UCMA con hitos hasta octubre 2026 (ver Context) — sirve de referencia pero el roadmap de fases de GSD es independiente y puede tener más granularidad
- **Windows**: Entorno de desarrollo en Windows — se evitó GDAL/geopandas por fragilidad de instalación (ya reflejado en `requirements.txt`)

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.12.4 - Data science, analysis, API ingestion, and dashboard application

## Runtime

- Python 3.12.4
- pip 26.0.1
- Lockfile: Missing (project uses `requirements.txt` with version floors; exact versions should be frozen via `pip freeze > requirements.lock.txt` per project notes)

## Frameworks

- pandas 2.0+ - Data manipulation and tabular analysis
- numpy 1.24+ - Numerical computing
- statsmodels 0.14+ - Econometric modeling and panel data analysis
- linearmodels 5.3+ - PanelOLS for fixed effects models (Baltagi, Wooldridge methods)
- scikit-learn 1.3+ - Machine learning algorithms and preprocessing
- matplotlib 3.7+ - Base plotting library
- seaborn 0.12+ - Statistical data visualization
- plotly 5.18+ - Interactive choropleth maps and dashboards (chosen for Windows stability without GDAL)
- Streamlit 1.30+ - Interactive web dashboard for geospatial visualization
- Note: Dash considered as alternative but not selected
- SHAP 0.43+ - Feature importance and model interpretability (Molnar methods)
- Jupyter 1.0+ - Interactive notebooks for exploratory data analysis (EDA)
- ipykernel 6.25+ - Jupyter kernel support

## Key Dependencies

- requests 2.31+ - HTTP client for UN ODS/SDG API data ingestion
- pandas 2.0+ - Core tabular data framework
- numpy 1.24+ - Array operations and numerical computations
- statsmodels 0.14+ - Panel model estimation and diagnostics
- linearmodels 5.3+ - Fixed effects panel regression (PanelOLS)
- scikit-learn 1.3+ - Preprocessing, model selection, validation
- SHAP 0.43+ - Model interpretation and feature attribution
- matplotlib 3.7+ - Base plotting
- seaborn 0.12+ - Statistical visualization
- plotly 5.18+ - Interactive geospatial choropleth maps (avoids GDAL dependency for Windows stability)
- Streamlit 1.30+ - Web dashboard framework

## Configuration

- Virtual environment: `.venv/` (configured in VS Code via `python.defaultInterpreterPath`)
- VS Code settings configured in `.vscode/settings.json` with Ruff formatter and Pylance type checking
- No build configuration (pure Python data science project — no compilation required)
- Notebooks and scripts executed directly via Python/Jupyter
- Ruff (charliermarsh.ruff) - Code formatting and import organization
- Pylance - Type checking mode: "basic"

## Platform Requirements

- OS: Windows (project explicitly avoids geopandas/folium due to GDAL installation fragility on Windows)
- Python 3.12+
- pip 26.0+
- Virtual environment tool (venv built-in)
- VS Code with Python and Jupyter extensions
- Deployment target: Streamlit Cloud or local server hosting
- No production database specified (data ingestion from UN ODS/SDG API to CSV/Excel)

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Python modules: `lowercase_with_underscores.py` (implied by PEP 8, enforced by Ruff)
- Notebooks: `[number]_[descriptive_name].ipynb` (e.g., `3_3_eda_water_stress.ipynb`)
- Data files: `[dataset_name]_[version].csv` or `.json` (e.g., `water_stress_v1.csv`)
- Snake case: `def calculate_water_stress_index()` (enforced by Ruff via PEP 8)
- Descriptive, module-level: Functions in ingesta modules should name their purpose clearly (e.g., `fetch_un_ods_data()`, `transform_panel_data()`)
- Snake case throughout: `annual_precipitation`, `gdp_per_capita`, `panel_effects` (PEP 8 convention)
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `API_ENDPOINT_UNO`, `MIN_YEARS_PANEL`)
- Classes: `PascalCase` (e.g., `WaterStressModel`, `PanelRegressionAnalyzer`)
- Type hints: Expected in function signatures (Pylance in basic mode will check these)

## Code Style

- Tool: **Ruff** (`charliermarsh.ruff` extension)
- Applied: Automatically on file save (`editor.formatOnSave: true`)
- Style: PEP 8 compliant; line length, indentation, spacing handled by Ruff defaults
- Tool: **Ruff** (as primary linter; no separate `.flake8` or `.pylintrc` configured)
- Scope: No explicit linting config file exists; Ruff defaults apply (strictness for naming, imports, unused variables)
- Next step: Create `pyproject.toml` with `[tool.ruff]` section if stricter rules needed (unused imports, complexity checks, type hints)

## Import Organization

- None currently configured; standard `sys.path` and virtual environment imports expected
- Recommendation: If project grows, add `[tool.ruff]` or `sys.path` configuration for cleaner imports like `from ingesta.fetch import fetch_un_data` instead of relative paths
- Enabled by default in VS Code settings: `"source.organizeImports": "explicit"`
- Ruff will sort and group imports automatically on save

## Error Handling

- Not yet demonstrated in code
- Expected practices (based on project domain):
- No custom exception hierarchy established yet; should be defined in `src/exceptions.py` if needed

## Logging

- Not yet configured; no handlers or formatters defined
- Recommended: Configure logging in a setup module (e.g., `src/config.py`) with:

## Comments

- Explain *why*, not *what* (the code itself explains what)
- Document complex statistical transformations (e.g., "Fixed effects estimation per Baltagi (2013)")
- Note data assumptions (e.g., "Assumes balanced panel structure; see docstring")
- Flag temporary workarounds with `# TODO:` or `# FIXME:` (will be discovered by `grep -r "TODO\|FIXME"`)
- Not applicable (Python project, not TypeScript)
- Expected format: **Google-style docstrings** (compatible with Sphinx auto-documentation)
- Location: Module, class, and function definitions
- Example for data ingestion:

## Function Design

- Small, focused functions (< 50 lines typical)
- Data transformation functions in ingesta: Single responsibility (fetch, validate, transform are separate)
- Statistical estimation: Wrap statsmodels/linearmodels calls in domain-specific functions (e.g., `estimate_panel_ols_by_country()`)
- Type hints required for all parameters (Pylance in basic mode will validate)
- Limit to 4-5 parameters; use dataclass or dict for complex parameter groups
- Avoid mutable defaults (no `def func(data=[])`)
- Type hints required
- Return single, specific types (e.g., `pd.DataFrame`, `np.ndarray`, `dict`)
- Return early to reduce nesting

## Module Design

- Each module in `src/` has one primary responsibility:
- Not yet used; OK to define `__init__.py` in `src/ingesta/` and `src/analysis/` for convenience imports:

## Type Hints

- Pylance basic type checking enabled; full validation expected
- All public function signatures should include type hints
- Use `typing.Optional`, `typing.List`, `typing.Dict` as needed

## Virtual Environment

- Expected location: `.venv/Scripts/python.exe` (Windows, per `.vscode/settings.json`)
- On Linux/macOS: `.venv/bin/python`
- Create with: `python -m venv .venv`
- Install dependencies: `pip install -r requirements.txt`
- Lock versions: `pip freeze > requirements.lock.txt` (for tribunal grading: exact reproducibility)
- No actual code exists to enforce these patterns yet
- No `pyproject.toml` for Ruff configuration beyond VS Code defaults
- No linting strictness rules defined (complexity, type coverage, docstring validation)
- Logging not yet configured
- Error handling patterns need definition in early ingesta code

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

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

- Notebook-driven exploratory workflow (Jupyter for prototyping)
- Transition to modular `src/` structure for reproducible pipeline stages
- Panel data econometrics (country-level cross-sectional + time-series)
- Multiple modeling approaches (fixed-effects regression, ML, interpretability)
- Emphasis on reproducibility (requirements.txt, manifest-based data versioning)
- Windows-friendly dependencies (Plotly instead of GDAL-dependent GeoPandas)

## Layers

- Purpose: Fetch data from UN ODS API; document provenance
- Location: `src/ingesta/`
- Contains: API client, manifest generation, raw data storage coordination
- Depends on: `requests` library, UN ODS API
- Used by: Processing layer
- Purpose: Clean, transform, and merge multi-source data into analysis-ready format
- Location: `notebook/` (exploratory phase) → `src/etl/` (future modularization)
- Contains: Pandas operations, data validation, feature engineering
- Depends on: Ingestion layer, pandas, numpy
- Used by: Analysis and modeling layers
- Purpose: Exploratory data analysis, hypothesis generation, statistical validation
- Location: `notebook/` (Jupyter-based)
- Contains: Descriptive statistics, correlation analysis, visualization prototypes
- Depends on: Processing layer, matplotlib, seaborn, statsmodels
- Used by: Modeling layer, dashboard layer
- Purpose: Build econometric and ML models to answer research questions
- Location: `src/modelos/` (planned structure)
- Contains: Panel regression models (statsmodels, linearmodels), scikit-learn estimators
- Depends on: Processing layer, statsmodels, linearmodels, scikit-learn
- Used by: Interpretation layer, visualization/dashboard
- Purpose: Extract variable importance, causal inference, model explanations
- Location: Embedded in `notebook/` or `src/modelos/`
- Contains: SHAP analysis, coefficient interpretation
- Depends on: Modeling layer, shap library
- Used by: Visualization layer
- Purpose: Present findings via geospatial dashboard and static figures
- Location: `src/dashboard/` (planned) for Streamlit app; `figuras/` for exports
- Contains: Plotly choropleth maps, time-series interactives, summary tiles
- Depends on: All upstream layers, plotly, streamlit
- Used by: End users / thesis evaluators

## Data Flow

### Primary Request Path (Thesis Analysis Pipeline)

### State Management

- **Data state:** Managed via manifest files; raw data regenerable from API
- **Model state:** Serialized to `data/modelos/` as .pkl/.joblib files
- **Analysis state:** Embedded in notebook cells; reproducible if data unchanged
- **Configuration:** Environment variables (`.env`, not versioned); package versions (`requirements.txt`, versioned)

## Key Abstractions

- Purpose: Organize multi-country, multi-year economic/environmental observations
- Examples: Country × Year grid for regression analysis
- Pattern: DataFrame with MultiIndex (country, year) or hierarchical grouping
- Purpose: Encapsulate fit → predict → evaluate workflow
- Examples: scikit-learn Pipeline, statsmodels model classes
- Pattern: Fit on training subset, evaluate on holdout or time-forward
- Purpose: Document data source, download date, row count, checksum without storing large files
- Examples: `data/2024-07-10/manifest.json` records API query parameters
- Pattern: Scripts check manifest before re-downloading; enables reproducibility without storage bloat

## Entry Points

- Location: `src/ingesta/` (not yet implemented, skeleton folder)
- Triggers: Researcher runs Python script or Jupyter cell
- Responsibilities: Query UN ODS API, save manifest, download data
- Location: `notebook/`
- Triggers: Researcher opens Jupyter Lab and executes cells
- Responsibilities: Load data, analyze, prototype models, generate figures
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

### Notebook as Single Source of Truth

### Manual Data Download

## Error Handling

- Data ingestion: Check manifest checksum, row count; raise exception if unexpected
- Model fitting: Validate panel structure (no missing country-year combinations); check for multicollinearity warnings
- Visualization: Graceful fallback if geospatial data missing (show table instead of map)

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
