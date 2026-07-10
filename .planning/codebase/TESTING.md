# Testing Patterns

**Analysis Date:** 2026-07-10

**Status:** No testing framework is currently configured. This is a critical gap for an academic TFB project where reproducibility and rigor are tribunal evaluation criteria.

## Test Framework

**Runner:**
- **NOT YET CONFIGURED** – Recommended: **pytest** (most popular for Python data science projects)
- Alternative: `unittest` (Python standard library, but verbose)
- Rationale: pytest offers fixtures, parametrization, and excellent Jupyter integration

**Setup Required:**
```bash
pip install pytest pytest-cov pytest-xdist
```

**Assertion Library:**
- Built-in `assert` statements (pytest captures these)
- Optional: Install `pytest-assert-rewrite` for better error messages (included with pytest)

**Run Commands (once pytest installed):**
```bash
pytest                          # Run all tests
pytest -v                       # Verbose output (show each test)
pytest --cov=src                # Coverage report for src/ directory
pytest -n auto                  # Parallel execution (if pytest-xdist installed)
pytest tests/test_ingesta.py    # Run specific test file
pytest -k "test_fetch"          # Run tests matching pattern
```

## Test File Organization

**Location:**
- **Decision not yet made** – Two common patterns:
  - **Separate directory (recommended for academic projects):** `tests/` at repo root
    - Structure mirrors `src/`: `tests/ingesta/`, `tests/analysis/`, `tests/viz/`
    - Pro: Clean separation; tournament graders expect this
    - Con: More setup required
  - **Co-located (exploratory convenience):** Next to source code
    - Structure: `src/ingesta/test_un_ods.py` alongside `src/ingesta/un_ods.py`
    - Pro: Easy to find; closer to code
    - Con: More intrusive; not typical in TFB submissions

**Recommended:** Use separate `tests/` directory to signal rigor to tribunal.

**Naming:**
- Test files: `test_[module_name].py` (e.g., `test_un_ods.py`, `test_panel_regression.py`)
- Test functions: `test_[what_is_being_tested]` (e.g., `test_fetch_returns_dataframe()`, `test_invalid_code_raises_error()`)
- Test classes (optional): `TestClassName` for organization

**Structure:**
```
tests/
├── conftest.py                 # pytest fixtures, shared setup
├── __init__.py
├── ingesta/
│   ├── __init__.py
│   ├── test_un_ods.py          # Tests for src/ingesta/un_ods.py
│   └── test_transform.py       # Tests for src/ingesta/transform.py
├── analysis/
│   ├── __init__.py
│   ├── test_panel_regression.py
│   └── test_interpretability.py
└── fixtures/
    ├── sample_panel_data.py     # Reusable test data factories
    └── mock_responses.py        # Mock API responses
```

## Test Structure

**Suite Organization:**
```python
# Example: tests/ingesta/test_un_ods.py
import pytest
import pandas as pd
from src.ingesta.un_ods import fetch_un_ods_data

class TestFetchUnOdsData:
    """Tests for UN ODS API data fetching."""

    def test_returns_dataframe(self):
        """fetch_un_ods_data returns a pandas DataFrame."""
        result = fetch_un_ods_data('SP.RUR.TOTL.ZG', (2015, 2020))
        assert isinstance(result, pd.DataFrame)

    def test_required_columns_present(self):
        """Result contains 'country', 'year', 'value' columns."""
        result = fetch_un_ods_data('SP.RUR.TOTL.ZG', (2015, 2020))
        assert set(['country', 'year', 'value']).issubset(result.columns)

    def test_invalid_indicator_raises_error(self):
        """Invalid indicator code raises ValueError."""
        with pytest.raises(ValueError):
            fetch_un_ods_data('INVALID_CODE', (2015, 2020))

    @pytest.mark.skip(reason="API call — skip in CI")
    def test_actual_api_call(self):
        """Integration test: real API call (skipped in CI)."""
        result = fetch_un_ods_data('SP.RUR.TOTL.ZG', (2015, 2020))
        assert len(result) > 0
```

**Patterns:**
- **Setup (via fixtures):** Use `@pytest.fixture` for shared test data (see fixtures below)
- **Teardown:** `pytest` fixtures with `yield` (replaces `setUp`/`tearDown`)
- **Assertions:** Simple `assert` statements; pytest displays full context on failure

## Mocking

**Framework:** **unittest.mock** (Python standard library)

**Patterns (when testing data ingestion):**
```python
# Example: tests/ingesta/test_un_ods.py
from unittest.mock import patch, MagicMock
import pytest

class TestFetchWithMocking:
    
    @patch('src.ingesta.un_ods.requests.get')
    def test_fetch_handles_api_timeout(self, mock_get):
        """fetch_un_ods_data gracefully handles API timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(requests.exceptions.Timeout):
            fetch_un_ods_data('SP.RUR.TOTL.ZG', (2015, 2020))

    @patch('src.ingesta.un_ods.requests.get')
    def test_fetch_parses_json_response(self, mock_get):
        """fetch_un_ods_data correctly parses JSON response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': [
                {'country': 'Argentina', 'year': 2020, 'value': 42.5},
                {'country': 'Argentina', 'year': 2019, 'value': 41.2}
            ]
        }
        mock_get.return_value = mock_response
        
        result = fetch_un_ods_data('SP.RUR.TOTL.ZG', (2015, 2020))
        assert len(result) == 2
        assert result.loc[0, 'value'] == 42.5
```

**What to Mock:**
- External API calls (`requests.get`, `requests.post`)
- File I/O (when testing without writing to disk)
- Database connections
- Long-running external services

**What NOT to Mock:**
- Pandas operations (test with real DataFrames)
- NumPy/SciPy calculations (test with real arrays)
- Statsmodels/linearmodels model fitting (test with sample panel data)
- Your own ingesta transformation functions (test with fixtures, not mocks)

**Rationale:** For a TFB about econometric analysis, validating the actual statistical correctness of transformations and models is critical. Mocking them away defeats the purpose.

## Fixtures and Factories

**Test Data (recommended approach):**
```python
# tests/conftest.py
import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def sample_balanced_panel():
    """A balanced panel dataset: 5 countries, 10 years."""
    countries = ['Argentina', 'Brazil', 'Chile', 'Mexico', 'Peru']
    years = range(2010, 2020)
    data = []
    for country in countries:
        for year in years:
            data.append({
                'country': country,
                'year': year,
                'gdp_per_capita': np.random.uniform(5000, 15000),
                'water_stress_index': np.random.uniform(0, 100),
                'annual_precipitation': np.random.uniform(300, 3000)
            })
    return pd.DataFrame(data)

@pytest.fixture
def sample_un_ods_response():
    """Mock response structure from UN ODS API."""
    return {
        'data': [
            {'country': 'Argentina', 'year': 2020, 'value': 42.5},
            {'country': 'Brazil', 'year': 2020, 'value': 38.1}
        ]
    }
```

**Location:**
- Global fixtures: `tests/conftest.py` (accessible to all test modules)
- Module-specific fixtures: In the test file itself or in `tests/[module]/conftest.py`
- Data factories: `tests/fixtures/sample_data.py` (for complex objects)

## Coverage

**Requirements:**
- **Not yet enforced** – Recommend: Minimum **80% for submission**
- Critical areas (highest priority):
  - Data ingestion (`src/ingesta/`) – 100% (affects all downstream analysis)
  - Panel transformation (`src/ingesta/transform.py`) – 90%+
  - Model fitting wrappers (`src/analysis/panel_regression.py`) – 85%+
  - Statistical validity is more important than line coverage; prioritize edge cases

**View Coverage:**
```bash
pytest --cov=src --cov-report=html
# Opens htmlcov/index.html in browser
# Shows line-by-line coverage per file

pytest --cov=src --cov-report=term-missing
# Shows which lines lack coverage in terminal
```

**Configuration (add to `pyproject.toml` once created):**
```toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=html --cov-report=term-missing"
testpaths = ["tests"]
```

## Test Types

**Unit Tests:**
- Scope: Individual functions in isolation
- Data ingestion: `test_fetch_un_ods.py` (with mocked API)
- Transformation: `test_transform.py` (with fixtures; real DataFrame operations)
- Approach: Fast, deterministic, no external dependencies
- Example: `test_panel_structure_validation()` checks that missing values are detected

**Integration Tests:**
- Scope: Multiple modules together (but not external APIs)
- Example: Fetch → Transform → Validate pipeline on sample data
- Location: `tests/integration/test_pipeline.py`
- Approach: Use real fixtures; slower but catches module interactions
- Skip in CI if they take >30 seconds

**E2E Tests:**
- Scope: Full workflow (notebooks or Streamlit dashboard)
- Framework: **Not yet configured** – Options:
  - **Jupyter notebook testing:** Use `nbval` or `pytest-notebook` to run actual notebooks as tests
  - **Streamlit testing:** `streamlit run --client.toolbarMode=minimal` + `pytest-streamlit` (alpha)
- Approach: Run notebooks with real data (or cached); validate outputs match expectations
- Example: Execute `notebook/3_4_panel_regression.ipynb` and assert model R² > 0.5

**Current Gap:** No E2E test approach defined. For TFB submission, notebook reproducibility is critical.

## Common Patterns

**Async Testing:**
- Not applicable (pure Python data science, no async code expected)

**Error Testing:**
```python
# Example: tests/ingesta/test_un_ods.py
import pytest

def test_missing_required_parameter_raises():
    """Calling fetch without indicator_code raises TypeError."""
    with pytest.raises(TypeError):
        fetch_un_ods_data()  # Missing argument

def test_invalid_year_range_raises():
    """Year range (end < start) raises ValueError."""
    with pytest.raises(ValueError, match="start_year must be <= end_year"):
        fetch_un_ods_data('SP.RUR.TOTL.ZG', year_range=(2020, 2010))

def test_network_error_propagates():
    """API network error propagates as RequestException."""
    with pytest.raises(requests.exceptions.RequestException):
        # Code that calls fetch_un_ods_data with mocked network failure
        pass
```

**Parametrized Testing:**
```python
@pytest.mark.parametrize("indicator_code,expected_columns", [
    ('SP.RUR.TOTL.ZG', ['country', 'year', 'value']),
    ('NY.GDP.PCAP.CD', ['country', 'year', 'value']),
])
def test_all_indicators_return_standard_columns(indicator_code, expected_columns):
    """All UN ODS indicators follow same column structure."""
    result = fetch_un_ods_data(indicator_code, (2015, 2020))
    assert set(expected_columns).issubset(result.columns)
```

---

*Testing analysis: 2026-07-10*

## Critical Gaps

1. **No testing framework installed** – pytest not in requirements.txt
2. **No test directory structure** – `tests/` does not exist
3. **No fixtures or sample data** – No test data factories
4. **No mocking strategy** – unittest.mock not configured
5. **No coverage tracking** – pytest-cov not in requirements
6. **No E2E notebook validation** – Jupyter notebook tests not set up
7. **No CI/CD testing** – No GitHub Actions or equivalent for automated test runs

## Action Items for Phase 1

1. Add to `requirements-dev.txt`:
   ```
   pytest>=7.4
   pytest-cov>=4.1
   pytest-xdist>=3.3
   ```

2. Create test structure:
   ```bash
   mkdir -p tests/ingesta tests/analysis tests/fixtures
   touch tests/conftest.py tests/__init__.py tests/ingesta/__init__.py
   ```

3. Write first test suite: `tests/ingesta/test_un_ods.py` alongside first ingesta code

4. Add to `.github/workflows/test.yml` (if using GitHub):
   ```yaml
   - name: Run tests
     run: pytest --cov=src --cov-report=xml
   ```

5. Document tribunal expectations: Add testing section to submission README
