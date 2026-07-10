# Coding Conventions

**Analysis Date:** 2026-07-10

**Status:** This project is in skeleton phase with minimal code. Conventions are defined through tooling configuration and project structure, not yet demonstrated in code.

## Naming Patterns

**Files:**
- Python modules: `lowercase_with_underscores.py` (implied by PEP 8, enforced by Ruff)
- Notebooks: `[number]_[descriptive_name].ipynb` (e.g., `3_3_eda_water_stress.ipynb`)
- Data files: `[dataset_name]_[version].csv` or `.json` (e.g., `water_stress_v1.csv`)

**Functions:**
- Snake case: `def calculate_water_stress_index()` (enforced by Ruff via PEP 8)
- Descriptive, module-level: Functions in ingesta modules should name their purpose clearly (e.g., `fetch_un_ods_data()`, `transform_panel_data()`)

**Variables:**
- Snake case throughout: `annual_precipitation`, `gdp_per_capita`, `panel_effects` (PEP 8 convention)
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `API_ENDPOINT_UNO`, `MIN_YEARS_PANEL`)

**Types:**
- Classes: `PascalCase` (e.g., `WaterStressModel`, `PanelRegressionAnalyzer`)
- Type hints: Expected in function signatures (Pylance in basic mode will check these)

## Code Style

**Formatting:**
- Tool: **Ruff** (`charliermarsh.ruff` extension)
- Applied: Automatically on file save (`editor.formatOnSave: true`)
- Style: PEP 8 compliant; line length, indentation, spacing handled by Ruff defaults

**Linting:**
- Tool: **Ruff** (as primary linter; no separate `.flake8` or `.pylintrc` configured)
- Scope: No explicit linting config file exists; Ruff defaults apply (strictness for naming, imports, unused variables)
- Next step: Create `pyproject.toml` with `[tool.ruff]` section if stricter rules needed (unused imports, complexity checks, type hints)

## Import Organization

**Order:**
1. Standard library imports (os, sys, json, etc.)
2. Third-party imports (pandas, numpy, requests, sklearn, etc.)
3. Local imports (from src.ingesta, from src.analysis, etc.)

**Path Aliases:**
- None currently configured; standard `sys.path` and virtual environment imports expected
- Recommendation: If project grows, add `[tool.ruff]` or `sys.path` configuration for cleaner imports like `from ingesta.fetch import fetch_un_data` instead of relative paths

**Auto-organization:**
- Enabled by default in VS Code settings: `"source.organizeImports": "explicit"`
- Ruff will sort and group imports automatically on save

## Error Handling

**Patterns:**
- Not yet demonstrated in code
- Expected practices (based on project domain):
  - Network errors in data ingestion (`requests` calls): Catch `requests.exceptions.RequestException` with retry logic
  - Data validation errors: Raise `ValueError` with descriptive messages for panel structure violations
  - Statistical model failures: Catch `RuntimeError` or model-specific exceptions (statsmodels, linearmodels)
- No custom exception hierarchy established yet; should be defined in `src/exceptions.py` if needed

## Logging

**Framework:** `logging` (Python standard library)

**Patterns:**
- Not yet configured; no handlers or formatters defined
- Recommended: Configure logging in a setup module (e.g., `src/config.py`) with:
  - Console handler for development
  - File handler pointing to `logs/` directory (add to .gitignore)
  - Format: `[%(asctime)s] %(name)s - %(levelname)s - %(message)s`
  - Data ingestion steps: Log API calls, row counts, transformations
  - Model training: Log epochs, loss values, model diagnostics

## Comments

**When to Comment:**
- Explain *why*, not *what* (the code itself explains what)
- Document complex statistical transformations (e.g., "Fixed effects estimation per Baltagi (2013)")
- Note data assumptions (e.g., "Assumes balanced panel structure; see docstring")
- Flag temporary workarounds with `# TODO:` or `# FIXME:` (will be discovered by `grep -r "TODO\|FIXME"`)

**JSDoc/TSDoc:**
- Not applicable (Python project, not TypeScript)

**Docstrings:**
- Expected format: **Google-style docstrings** (compatible with Sphinx auto-documentation)
- Location: Module, class, and function definitions
- Example for data ingestion:
  ```python
  def fetch_un_ods_data(indicator_code: str, year_range: tuple) -> pd.DataFrame:
      """
      Fetch UN Open Data Service (ODS) indicator data.

      Args:
          indicator_code: UN ODS API code (e.g., 'SP.RUR.TOTL.ZG')
          year_range: Tuple of (start_year, end_year) inclusive

      Returns:
          DataFrame with columns: ['country', 'year', 'value']
          All NaN values removed.

      Raises:
          requests.exceptions.RequestException: API call failed
          ValueError: Invalid indicator_code
      """
  ```

## Function Design

**Size:** 
- Small, focused functions (< 50 lines typical)
- Data transformation functions in ingesta: Single responsibility (fetch, validate, transform are separate)
- Statistical estimation: Wrap statsmodels/linearmodels calls in domain-specific functions (e.g., `estimate_panel_ols_by_country()`)

**Parameters:**
- Type hints required for all parameters (Pylance in basic mode will validate)
- Limit to 4-5 parameters; use dataclass or dict for complex parameter groups
- Avoid mutable defaults (no `def func(data=[])`)

**Return Values:**
- Type hints required
- Return single, specific types (e.g., `pd.DataFrame`, `np.ndarray`, `dict`)
- Return early to reduce nesting

## Module Design

**Exports:**
- Each module in `src/` has one primary responsibility:
  - `src/ingesta/un_ods.py`: Fetching and validating UN ODS data
  - `src/ingesta/transform.py`: Cleaning, structuring, and caching data
  - `src/analysis/panel_regression.py`: Panel data model estimation
  - `src/analysis/interpretability.py`: SHAP feature importance
  - `src/viz/dashboard.py`: Streamlit app or Plotly visualizations

**Barrel Files:**
- Not yet used; OK to define `__init__.py` in `src/ingesta/` and `src/analysis/` for convenience imports:
  ```python
  # src/ingesta/__init__.py
  from src.ingesta.un_ods import fetch_un_ods_data
  from src.ingesta.transform import prepare_panel_data
  __all__ = ['fetch_un_ods_data', 'prepare_panel_data']
  ```

## Type Hints

**Scope:**
- Pylance basic type checking enabled; full validation expected
- All public function signatures should include type hints
- Use `typing.Optional`, `typing.List`, `typing.Dict` as needed

**Example (data ingestion):**
```python
from typing import Optional, Tuple
import pandas as pd

def fetch_indicator(code: str, years: Optional[Tuple[int, int]] = None) -> pd.DataFrame:
    ...
```

## Virtual Environment

**Setup:**
- Expected location: `.venv/Scripts/python.exe` (Windows, per `.vscode/settings.json`)
- On Linux/macOS: `.venv/bin/python`
- Create with: `python -m venv .venv`
- Install dependencies: `pip install -r requirements.txt`
- Lock versions: `pip freeze > requirements.lock.txt` (for tribunal grading: exact reproducibility)

---

*Convention analysis: 2026-07-10*

**Key Gaps:**
- No actual code exists to enforce these patterns yet
- No `pyproject.toml` for Ruff configuration beyond VS Code defaults
- No linting strictness rules defined (complexity, type coverage, docstring validation)
- Logging not yet configured
- Error handling patterns need definition in early ingesta code
