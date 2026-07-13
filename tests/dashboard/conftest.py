"""Wave 0 shared pytest fixtures for tests/dashboard/* (DASH-01..04,
05-VALIDATION.md).

These fixtures are the single source of a tiny, deterministic, synthetic
panel + toy model artifacts consumed by every dashboard test file
(test_plots.py in 05-02, test_caching.py in 05-03, test_app.py in 05-04).
They exist so the dashboard test suite NEVER reads the real 215-country
``data/panel.db`` or the real production ``.pkl`` artifacts
(``data/modelos/model1_gdp.pkl``, ``data/modelos/rf_shap_model.pkl``) --
mirrors the synthetic-fixture convention already established by
``tests/test_simulate.py``/``tests/test_panel_base.py`` (``np.random.
default_rng(seed)``-based generators), adapted here to real ISO3 country
codes (required by Plotly's ``locationmode="ISO-3"``) instead of the
``f"C{i:02d}"`` synthetic entity naming those modules use.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy import Engine

from src import db

# Real ISO3 codes -- required for Plotly's locationmode="ISO-3" to resolve
# each country on the choropleth (RESEARCH.md: country_code is ISO3 in the
# real panel_clean).
COUNTRY_CODES: list[str] = ["ESP", "FRA", "DEU", "ITA"]
YEARS: list[int] = list(range(2000, 2023))  # 2000-2022 inclusive, 23 years
INDICATOR_CODES: list[str] = ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"]

_REGION_BY_COUNTRY: dict[str, str] = {code: "Europa" for code in COUNTRY_CODES}


@pytest.fixture
def tiny_panel_df() -> pd.DataFrame:
    """A small, deterministic ``panel_clean``-shaped DataFrame: 4 ISO3
    countries x 23 years (2000-2022) x the 5 ODS indicator columns, plus the
    typology columns (``region``, ``is_ldc``, ``is_lldc``, ``is_sids``).

    One (country, year, indicator) cell is deliberately set to ``NaN`` (FRA,
    2000, ``"2.3.1"``) so downstream no-data handling (choropleth gray fill,
    coverage caveats) is exercised by every consumer of this fixture, not
    just the all-finite case.
    """
    rng = np.random.default_rng(seed=0)
    rows = []
    for country in COUNTRY_CODES:
        for year in YEARS:
            row = {
                "country_code": country,
                "year": year,
                "region": _REGION_BY_COUNTRY[country],
                "is_ldc": False,
                "is_lldc": False,
                "is_sids": False,
            }
            for indicator in INDICATOR_CODES:
                row[indicator] = float(rng.normal(loc=50.0, scale=10.0))
            rows.append(row)

    df = pd.DataFrame(rows)
    nan_mask = (df["country_code"] == "FRA") & (df["year"] == 2000)
    df.loc[nan_mask, "2.3.1"] = np.nan
    return df


@pytest.fixture
def tiny_panel_engine(tiny_panel_df: pd.DataFrame) -> Engine:
    """An in-memory SQLite Engine (never the real ``data/panel.db`` file)
    with ``tiny_panel_df`` written as ``panel_clean`` plus a minimal
    ``panel_exclusions`` table matching the real schema built by
    ``src/panel_build.py::build_exclusion_table`` (country_code,
    indicator_code, years_available, years_required, coverage_pct, excluded,
    reason) -- one excluded pair so exclusion-aware consumers have a
    non-empty table to query.
    """
    engine = db.get_engine(":memory:")
    tiny_panel_df.to_sql("panel_clean", engine, if_exists="replace", index=False)

    exclusions = pd.DataFrame(
        [
            {
                "country_code": "FRA",
                "indicator_code": "2.3.1",
                "years_available": 5,
                "years_required": 17,
                "coverage_pct": 5 / 23,
                "excluded": True,
                "reason": "coverage_below_70pct_threshold",
            }
        ]
    )
    exclusions.to_sql("panel_exclusions", engine, if_exists="replace", index=False)
    return engine


@pytest.fixture
def toy_model_pkl(tmp_path: Path) -> Path:
    """A tiny fitted ``RandomForestRegressor`` (2 synthetic features, few
    trees) pickled to a ``tmp_path`` file -- lets ``data.load_model`` be
    exercised against a real, loadable pickle without depending on the
    production ``data/modelos/*.pkl`` artifacts (which require the exact
    pinned scikit-learn/linearmodels versions they were serialized with).
    """
    rng = np.random.default_rng(seed=0)
    X = rng.normal(size=(20, 2))
    y = X[:, 0] * 2.0 + rng.normal(scale=0.1, size=20)

    model = RandomForestRegressor(n_estimators=5, random_state=0, n_jobs=1)
    model.fit(X, y)

    pkl_path = tmp_path / "toy_model.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump(model, f)
    return pkl_path
