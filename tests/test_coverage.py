"""Tests for src/coverage.py: presence-matrix (D-04) and region-ordering
(D-03) pure transforms for the Phase 7 coverage heatmap (COVER-01).

Both functions operate purely on DataFrames read from raw_observations +
country_reference -- coverage/exclusion status is never consulted (a
wholly-absent row and a stored value IS NULL row must resolve to the same
missing state).
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import coverage, db


@pytest.fixture
def engine(tmp_path):
    """A fresh, initialized SQLite engine backed by a tmp-path file (never the real project database)."""
    eng = db.get_engine(str(tmp_path / "test_panel.db"))
    db.init_db(eng)
    return eng


def _obs_row(country, indicator, year, value, dimension="Activity=TOTAL", manifest="m1"):
    return {
        "country_code": country,
        "indicator_code": indicator,
        "year": year,
        "value": value,
        "dimension": dimension,
        "source_manifest_id": manifest,
    }


def _seed_country_reference(engine):
    """Synthetic country_reference spanning two distinct regions, with
    country_code members deliberately interleaved (not pre-grouped) to
    exercise the region-sort logic."""
    df = pd.DataFrame(
        [
            {"country_code": "FRA", "region": "Europe", "subregion": "Western Europe"},
            {"country_code": "KEN", "region": "Africa", "subregion": "Sub-Saharan Africa"},
            {"country_code": "ESP", "region": "Europe", "subregion": "Southern Europe"},
            {"country_code": "TZA", "region": "Africa", "subregion": "Sub-Saharan Africa"},
        ]
    )
    df.to_sql("country_reference", engine, if_exists="replace", index=False)


# --- build_presence_matrix() ---------------------------------------------------


def test_build_presence_matrix_absent_row_is_missing(engine):
    """ESP has rows for 2000-2002 but no row at all for 2003 (a gap year)."""
    rows = [_obs_row("ESP", "6.4.2", year, float(year)) for year in range(2000, 2003)]
    db.insert_observations(engine, pd.DataFrame(rows))

    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    matrix = coverage.build_presence_matrix(raw, ["ESP"], "6.4.2", years=list(range(2000, 2005)))

    assert bool(matrix.loc["ESP", 2003]) is False


def test_build_presence_matrix_null_value_is_missing(engine):
    """A row exists for (ESP, 2001, 6.4.2) but value IS NULL -- a distinct,
    valid key (not a duplicate) that must resolve to the same missing state
    as an absent row (D-04)."""
    rows = [
        _obs_row("ESP", "6.4.2", 2000, 1.0),
        _obs_row("ESP", "6.4.2", 2001, None),
        _obs_row("ESP", "6.4.2", 2002, 3.0),
    ]
    db.insert_observations(engine, pd.DataFrame(rows))

    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    matrix = coverage.build_presence_matrix(raw, ["ESP"], "6.4.2", years=list(range(2000, 2005)))

    assert bool(matrix.loc["ESP", 2001]) is False


def test_build_presence_matrix_non_null_value_is_present(engine):
    rows = [_obs_row("ESP", "6.4.2", 2000, 42.0)]
    db.insert_observations(engine, pd.DataFrame(rows))

    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    matrix = coverage.build_presence_matrix(raw, ["ESP"], "6.4.2", years=list(range(2000, 2005)))

    assert bool(matrix.loc["ESP", 2000]) is True


# --- ordered_countries_with_boundaries() ---------------------------------------


def test_ordered_countries_with_boundaries_groups_by_region(engine):
    _seed_country_reference(engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)
    countries = ["FRA", "KEN", "ESP", "TZA"]

    ordered, boundaries = coverage.ordered_countries_with_boundaries(country_reference, countries)

    # Africa < Europe alphabetically: KEN/TZA (Sub-Saharan Africa) then ESP/FRA (Europe).
    assert ordered == ["KEN", "TZA", "ESP", "FRA"]
    assert boundaries == [0, 2]


# --- coverage source independence (Pitfall 3 guard) -----------------------------


def test_coverage_module_never_reads_panel_clean(engine):
    """No derived clean-panel table exists in this engine at all -- both
    functions must still succeed reading only raw_observations +
    country_reference, proving they operate purely on the DataFrames
    passed in."""
    rows = [_obs_row("ESP", "6.4.2", 2000, 42.0)]
    db.insert_observations(engine, pd.DataFrame(rows))
    _seed_country_reference(engine)

    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", engine)["name"].tolist()
    assert "panel_clean" not in tables

    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

    matrix = coverage.build_presence_matrix(raw, ["ESP"], "6.4.2")
    ordered, boundaries = coverage.ordered_countries_with_boundaries(country_reference, ["ESP"])

    assert matrix.loc["ESP", 2000] == True  # noqa: E712
    assert ordered == ["ESP"]
    assert boundaries == [0]
