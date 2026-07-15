"""Tests for src/model2_agri.py: deterministic bookkeeping only (no live DB
needed for these) -- MODEL2-01, MODEL2-02.

Mirrors tests/test_panel_base.py's synthetic-sparse-panel construction style
(_make_sparse_panel), but uses the REAL Model 2 column names (2.3.1 / 6.4.2)
so build_coverage_table/build_model2_panel are exercised against their real
column contract (D-01, 06-CONTEXT.md).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import model2_agri

DEP_VAR = model2_agri.DEP_VAR
INDEP_VAR = model2_agri.INDEP_VAR


def _make_sparse_m2_panel(year_presence: dict[str, list[int]]) -> pd.DataFrame:
    """All years 2000-2009 are present as rows for every country; years not
    listed in ``year_presence[country]`` get an explicit NaN in BOTH the
    dep_var and indep_var columns -- controlling each country's
    joint-non-null-year count precisely, without depending on
    panel_exclusions or filter_by_exclusions (same rationale as
    tests/test_panel_base.py's _make_sparse_panel)."""
    all_years = list(range(2000, 2010))
    rows = []
    for country, present_years in year_presence.items():
        for year in all_years:
            value = 1.0 if year in present_years else np.nan
            rows.append(
                {
                    "country_code": country,
                    "year": year,
                    DEP_VAR: value,
                    INDEP_VAR: value,
                }
            )
    return pd.DataFrame(rows)


# --- build_coverage_table() -------------------------------------------------


def test_build_coverage_table_has_expected_columns():
    df = _make_sparse_m2_panel({"A": [2000, 2001, 2002], "B": [2000]})

    coverage = model2_agri.build_coverage_table(df)

    assert list(coverage.columns) == ["country_code", "years_available", "included", "reason"]
    assert set(coverage["country_code"]) == {"A", "B"}


def test_build_coverage_table_marks_included_iff_at_or_above_min_years():
    df = _make_sparse_m2_panel(
        {
            "A": [2000, 2001, 2002],  # 3 joint-non-null years -- included
            "B": [2000, 2001],  # 2 -- excluded
        }
    )

    coverage = model2_agri.build_coverage_table(df).set_index("country_code")

    assert bool(coverage.loc["A", "included"]) is True
    assert int(coverage.loc["A", "years_available"]) == 3
    assert bool(coverage.loc["B", "included"]) is False
    assert int(coverage.loc["B", "years_available"]) == 2


def test_build_coverage_table_honors_non_default_min_years():
    """WR-01 regression test (06-REVIEW.md): build_coverage_table must use
    the passed min_years, not the hardcoded module-level MIN_YEARS constant
    -- otherwise the model2_coverage table would disagree with a
    build_model2_panel call using a non-default min_years."""
    df = _make_sparse_m2_panel(
        {
            "A": [2000, 2001, 2002, 2003],  # 4 joint-non-null years
            "B": [2000, 2001],  # 2
        }
    )

    coverage = model2_agri.build_coverage_table(df, min_years=4).set_index("country_code")

    assert bool(coverage.loc["A", "included"]) is True
    assert bool(coverage.loc["B", "included"]) is False
    # With the default min_years=3, A would still be included, but B's
    # `reason` text must reflect the min_years actually passed (4), not the
    # module-level default (3).
    assert "excluido: <4 años observados" in coverage.loc["B", "reason"]


def test_build_coverage_table_default_min_years_matches_build_model2_panel():
    """Same min_years default (MIN_YEARS=3) as build_model2_panel, so calling
    both with no explicit min_years stays mutually consistent (D-03)."""
    df = _make_sparse_m2_panel({"A": [2000, 2001, 2002], "B": [2000, 2001]})

    coverage = model2_agri.build_coverage_table(df).set_index("country_code")
    filtered = model2_agri.build_model2_panel(df)

    assert bool(coverage.loc["A", "included"]) is True
    assert "A" in set(filtered["country_code"].unique())
    assert bool(coverage.loc["B", "included"]) is False
    assert "B" not in set(filtered["country_code"].unique())


def test_build_coverage_table_excludes_countries_with_zero_dep_var_observations():
    """A country with NO 2.3.1 data at all must not appear in the coverage
    table -- it documents every country with ANY 2.3.1 data, not every
    country present in panel_clean (D-03)."""
    df = _make_sparse_m2_panel({"A": [2000, 2001, 2002]})
    all_nan_rows = pd.DataFrame(
        [
            {"country_code": "Z", "year": year, DEP_VAR: np.nan, INDEP_VAR: 1.0}
            for year in range(2000, 2010)
        ]
    )
    df = pd.concat([df, all_nan_rows], ignore_index=True)

    coverage = model2_agri.build_coverage_table(df)

    assert "Z" not in set(coverage["country_code"])


# --- build_model2_panel() ---------------------------------------------------


def test_build_model2_panel_keeps_only_countries_meeting_threshold():
    df = _make_sparse_m2_panel(
        {
            "A": [2000, 2001, 2002, 2003],
            "B": [2000, 2001],
        }
    )

    filtered = model2_agri.build_model2_panel(df, min_years=3)

    assert set(filtered["country_code"].unique()) == {"A"}
    assert (filtered["country_code"] == "B").sum() == 0


def test_build_model2_panel_default_min_years_is_three():
    df = _make_sparse_m2_panel(
        {
            "A": [2000, 2001, 2002],  # exactly 3 -- kept under default
            "B": [2000, 2001],  # 2 -- dropped under default
        }
    )

    filtered = model2_agri.build_model2_panel(df)

    assert set(filtered["country_code"].unique()) == {"A"}
