"""Tests for src/db.py: raw_observations schema, insert guard, and panel pivot.

raw_observations is the immutable long table (single source of truth). Duplicate
(country_code, year, indicator_code) rows must be impossible to persist -- this is
enforced twice (D-11, belt-and-suspenders): an explicit ValueError check in
insert_observations() catches duplicates *within* the incoming DataFrame before
any row reaches SQLite, and the schema's own UNIQUE constraint catches duplicates
that slip past that check across separate insert calls.

panel is a derived wide table (D-12): always fully regenerated from
raw_observations via pivot, never hand-edited.
"""

from __future__ import annotations

import pandas as pd
import pytest
from pandas.errors import DatabaseError

from src import db


@pytest.fixture
def engine(tmp_path):
    """A fresh, initialized SQLite engine backed by a tmp-path file (never data/panel.db)."""
    eng = db.get_engine(str(tmp_path / "test_panel.db"))
    db.init_db(eng)
    return eng


def _row(country="ESP", indicator="6.4.2", year=2020, value=1.0, dimension="Activity=TOTAL", manifest="m1"):
    return {
        "country_code": country,
        "indicator_code": indicator,
        "year": year,
        "value": value,
        "dimension": dimension,
        "source_manifest_id": manifest,
    }


def test_insert_observations_raises_on_duplicate_keys_in_df(engine):
    """A df with a duplicate (country, year, indicator) pair must never reach SQLite.

    Uses ValueError (WR-01), not a bare assert, so the guard survives
    `python -O`/`PYTHONOPTIMIZE=1`."""
    df = pd.DataFrame([
        _row(value=1.0),
        _row(value=2.0),  # same (country_code, year, indicator_code) key
    ])

    with pytest.raises(ValueError, match="ESP"):
        db.insert_observations(engine, df)

    result = pd.read_sql("SELECT * FROM raw_observations", engine)
    assert result.empty


def test_unique_constraint_raises(engine):
    """Clean insert succeeds; a second insert of the same key is rejected by the schema UNIQUE."""
    df = pd.DataFrame([_row()])
    db.insert_observations(engine, df)

    result = pd.read_sql("SELECT * FROM raw_observations", engine)
    assert len(result) == 1

    # No duplicates *within* this single-row df, so the pre-insert assert passes;
    # the schema-level UNIQUE(country_code, year, indicator_code) must catch it.
    # pandas.to_sql wraps the underlying sqlalchemy.exc.IntegrityError in its own
    # pandas.errors.DatabaseError -- that wrapper is what callers actually see.
    with pytest.raises(DatabaseError, match="UNIQUE constraint failed"):
        db.insert_observations(engine, df)


def test_insert_observations_persists_null_value(engine):
    """A NaN value is stored as NULL in raw_observations, never dropped or coerced away."""
    df = pd.DataFrame([_row(indicator="2.3.1", dimension="Sex=BOTHSEX", value=float("nan"))])
    db.insert_observations(engine, df)

    result = pd.read_sql("SELECT * FROM raw_observations", engine)
    assert len(result) == 1
    assert pd.isna(result.loc[0, "value"])


def test_rebuild_panel_is_idempotent(engine):
    """Two consecutive rebuild_panel() runs over the same raw_observations produce identical output."""
    df = pd.DataFrame([
        _row(country="ESP", indicator="6.4.2", year=2020, value=10.0),
        _row(country="ESP", indicator="2.3.1", year=2020, value=20.0),
        _row(country="FRA", indicator="6.4.2", year=2020, value=30.0),
    ])
    db.insert_observations(engine, df)

    db.rebuild_panel(engine)
    first = pd.read_sql("SELECT * FROM panel", engine).sort_values(["country_code", "year"]).reset_index(drop=True)

    db.rebuild_panel(engine)
    second = pd.read_sql("SELECT * FROM panel", engine).sort_values(["country_code", "year"]).reset_index(drop=True)

    pd.testing.assert_frame_equal(first, second)


def test_rebuild_panel_shape_one_row_per_country_year_one_column_per_indicator(engine):
    """panel has one row per (country_code, year) and one column per distinct indicator_code."""
    df = pd.DataFrame([
        _row(country="ESP", indicator="6.4.2", year=2020, value=10.0),
        _row(country="ESP", indicator="2.3.1", year=2020, value=20.0),
        _row(country="ESP", indicator="6.4.2", year=2021, value=11.0),
        _row(country="FRA", indicator="6.4.2", year=2020, value=30.0),
    ])
    db.insert_observations(engine, df)

    db.rebuild_panel(engine)
    panel = pd.read_sql("SELECT * FROM panel", engine)

    # 3 distinct (country_code, year) pairs: (ESP,2020), (ESP,2021), (FRA,2020)
    assert len(panel) == 3
    assert set(panel.columns) == {"country_code", "year", "6.4.2", "2.3.1"}
