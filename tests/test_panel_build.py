"""Tests for src/panel_build.py: 70%-of-years coverage filter, exclusion
table, and the idempotent clean-panel build (PANEL-01, PANEL-02).

panel_clean is a faithful, unmodified pivot of raw_observations (plus
country_reference columns) -- coverage/exclusion status is documented
separately in panel_exclusions, never by nulling real reported values (see
02-01-PLAN.md's Review Notes, fix #3, for the rationale).
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import db, panel_build

INDICATOR_CODES = ["6.4.2", "2.3.1"]


@pytest.fixture
def engine(tmp_path):
    """A fresh, initialized SQLite engine backed by a tmp-path file (never data/panel.db)."""
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


def _seed_raw_observations(engine):
    """Synthetic dataset covering the 3 coverage scenarios PANEL-02 must handle:

    - ESP/6.4.2: 20 distinct years (>= 17) -> covered, not excluded.
    - ESP/2.3.1: 5 distinct years (< 17) -> excluded, "coverage_below_70pct_threshold".
    - FRA/6.4.2: 10 distinct years (< 17) -> excluded.
    - FRA/2.3.1: ZERO rows at all -> must still appear in compute_coverage
      with years_available=0, reason="no_data_reported" (the completeness
      gap fixed in 02-01-PLAN.md's Review Notes, fix #4).
    - KEN/6.4.2: 18 distinct years (>= 17) -> covered.
    - KEN/2.3.1: exactly 17 distinct years -> covered (boundary: 17 is NOT < 17).
    """
    rows = []
    for year in range(2000, 2020):  # 20 years
        rows.append(_obs_row("ESP", "6.4.2", year, float(year)))
    for year in range(2000, 2005):  # 5 years
        rows.append(_obs_row("ESP", "2.3.1", year, float(year) * 2))
    for year in range(2000, 2010):  # 10 years
        rows.append(_obs_row("FRA", "6.4.2", year, float(year) * 3))
    # FRA has NO 2.3.1 rows at all.
    for year in range(2000, 2018):  # 18 years
        rows.append(_obs_row("KEN", "6.4.2", year, float(year) * 4))
    for year in range(2000, 2017):  # exactly 17 years
        rows.append(_obs_row("KEN", "2.3.1", year, float(year) * 5))

    df = pd.DataFrame(rows)
    db.insert_observations(engine, df)


def _seed_country_reference(engine):
    df = pd.DataFrame(
        [
            {"country_code": "ESP", "region": "Europe", "subregion": "Southern Europe", "is_ldc": False, "is_lldc": False, "is_sids": False},
            {"country_code": "FRA", "region": "Europe", "subregion": "Western Europe", "is_ldc": False, "is_lldc": False, "is_sids": False},
            {"country_code": "KEN", "region": "Africa", "subregion": "Sub-Saharan Africa", "is_ldc": True, "is_lldc": False, "is_sids": False},
        ]
    )
    df.to_sql("country_reference", engine, if_exists="replace", index=False)


# --- compute_coverage() -------------------------------------------------------


def test_compute_coverage_counts_distinct_non_null_years(engine):
    _seed_raw_observations(engine)
    _seed_country_reference(engine)
    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

    coverage = panel_build.compute_coverage(raw, country_reference, INDICATOR_CODES)

    esp_642 = coverage[(coverage.country_code == "ESP") & (coverage.indicator_code == "6.4.2")].iloc[0]
    assert esp_642["years_available"] == 20
    assert esp_642["excluded"] == False  # noqa: E712

    esp_231 = coverage[(coverage.country_code == "ESP") & (coverage.indicator_code == "2.3.1")].iloc[0]
    assert esp_231["years_available"] == 5
    assert esp_231["excluded"] == True  # noqa: E712


def test_compute_coverage_boundary_exactly_17_years_is_not_excluded(engine):
    """17 is the threshold; 17 must NOT be excluded (strict less-than 17)."""
    _seed_raw_observations(engine)
    _seed_country_reference(engine)
    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

    coverage = panel_build.compute_coverage(raw, country_reference, INDICATOR_CODES)

    ken_231 = coverage[(coverage.country_code == "KEN") & (coverage.indicator_code == "2.3.1")].iloc[0]
    assert ken_231["years_available"] == 17
    assert ken_231["excluded"] == False  # noqa: E712


def test_compute_coverage_includes_zero_row_pairs():
    """FRA has ZERO rows for 2.3.1 -- this pair must still appear with
    years_available=0, not be silently absent from the coverage accounting
    (the completeness gap fixed in 02-01-PLAN.md's Review Notes, fix #4)."""
    engine = db.get_engine(":memory:")
    db.init_db(engine)
    _seed_raw_observations(engine)
    _seed_country_reference(engine)
    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

    coverage = panel_build.compute_coverage(raw, country_reference, INDICATOR_CODES)

    fra_231 = coverage[(coverage.country_code == "FRA") & (coverage.indicator_code == "2.3.1")]
    assert len(fra_231) == 1
    assert fra_231.iloc[0]["years_available"] == 0
    assert fra_231.iloc[0]["excluded"] == True  # noqa: E712


def test_compute_coverage_full_cross_product_size():
    """3 countries x 2 indicator_codes = 6 rows, regardless of which pairs
    have zero rows in raw_observations."""
    engine = db.get_engine(":memory:")
    db.init_db(engine)
    _seed_raw_observations(engine)
    _seed_country_reference(engine)
    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

    coverage = panel_build.compute_coverage(raw, country_reference, INDICATOR_CODES)

    assert len(coverage) == 3 * len(INDICATOR_CODES)


# --- build_exclusion_table() --------------------------------------------------


def test_build_exclusion_table_uses_distinct_reason_strings():
    engine = db.get_engine(":memory:")
    db.init_db(engine)
    _seed_raw_observations(engine)
    _seed_country_reference(engine)
    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)
    coverage = panel_build.compute_coverage(raw, country_reference, INDICATOR_CODES)

    exclusions = panel_build.build_exclusion_table(coverage)

    assert (exclusions.excluded == True).all()  # noqa: E712

    fra_231_reason = exclusions[
        (exclusions.country_code == "FRA") & (exclusions.indicator_code == "2.3.1")
    ].iloc[0]["reason"]
    assert fra_231_reason == "no_data_reported"

    esp_231_reason = exclusions[
        (exclusions.country_code == "ESP") & (exclusions.indicator_code == "2.3.1")
    ].iloc[0]["reason"]
    assert esp_231_reason == "coverage_below_70pct_threshold"


# --- build_clean_panel() -------------------------------------------------------


def test_build_clean_panel_preserves_real_values_even_when_excluded():
    """ESP/2.3.1 fails the 70% threshold, but its real reported values must
    still be present, unmodified, in panel_clean -- NOT nulled."""
    engine = db.get_engine(":memory:")
    db.init_db(engine)
    _seed_raw_observations(engine)
    _seed_country_reference(engine)
    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

    clean = panel_build.build_clean_panel(raw, country_reference)

    esp_2000 = clean[(clean.country_code == "ESP") & (clean.year == 2000)].iloc[0]
    assert not pd.isna(esp_2000["2.3.1"])
    assert esp_2000["2.3.1"] == float(2000) * 2  # matches _seed_raw_observations' ESP/2.3.1 value formula


def test_build_clean_panel_includes_country_reference_columns():
    engine = db.get_engine(":memory:")
    db.init_db(engine)
    _seed_raw_observations(engine)
    _seed_country_reference(engine)
    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

    clean = panel_build.build_clean_panel(raw, country_reference)

    assert {"region", "subregion", "is_ldc", "is_lldc", "is_sids"} <= set(clean.columns)
    ken_row = clean[clean.country_code == "KEN"].iloc[0]
    assert ken_row["is_ldc"] == True  # noqa: E712


def test_build_clean_panel_never_drops_a_country_row_for_failing_one_indicator():
    """FRA fails 6.4.2's threshold AND has zero 2.3.1 data -- FRA must still
    have rows in panel_clean for every year it reported ANY indicator."""
    engine = db.get_engine(":memory:")
    db.init_db(engine)
    _seed_raw_observations(engine)
    _seed_country_reference(engine)
    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

    clean = panel_build.build_clean_panel(raw, country_reference)

    fra_rows = clean[clean.country_code == "FRA"]
    assert len(fra_rows) == 10  # FRA reported 6.4.2 for 10 distinct years


# --- rebuild_clean_panel() / idempotency --------------------------------------


def test_idempotency(engine):
    """Calling rebuild_clean_panel twice against the same underlying data
    produces a byte-for-byte identical panel_clean table."""
    _seed_raw_observations(engine)
    _seed_country_reference(engine)

    panel_build.rebuild_clean_panel(engine)
    first = (
        pd.read_sql("SELECT * FROM panel_clean", engine)
        .sort_values(["country_code", "year"])
        .reset_index(drop=True)
    )

    panel_build.rebuild_clean_panel(engine)
    second = (
        pd.read_sql("SELECT * FROM panel_clean", engine)
        .sort_values(["country_code", "year"])
        .reset_index(drop=True)
    )

    pd.testing.assert_frame_equal(first, second)


def test_rebuild_clean_panel_writes_both_tables(engine):
    _seed_raw_observations(engine)
    _seed_country_reference(engine)

    panel_build.rebuild_clean_panel(engine)

    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", engine)["name"].tolist()
    assert "panel_clean" in tables
    assert "panel_exclusions" in tables
