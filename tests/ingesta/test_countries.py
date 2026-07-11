"""Tests for src/ingesta/countries.py: M49 canonical list, ISO3 crosswalk,
and exclusion log (D-13-D-16, INGEST-03).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ingesta import countries

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

with open(FIXTURES_DIR / "geoarea_tree_sample.json", encoding="utf-8") as f:
    TREE_SAMPLE = json.load(f)


# --- collect_countries() ----------------------------------------------------


def test_collect_countries_returns_only_country_leaves():
    result = countries.collect_countries(TREE_SAMPLE)

    assert result == {
        "818": "Egypt",
        "404": "Kenya",
        "724": "Spain",
        "901": "Kosovo",
    }
    # No regional aggregate ("World", "Africa", "Sub-Saharan Africa", "Europe",
    # "Southern Europe", "Other areas") survives into the country dict.
    assert "001" not in result
    assert "002" not in result
    assert "202" not in result
    assert "150" not in result
    assert "039" not in result
    assert "900" not in result


def test_collect_countries_logs_all_aggregates_with_parent_names():
    excluded: list[dict] = []
    countries.collect_countries(TREE_SAMPLE, excluded=excluded)

    excluded_by_code = {entry["code"]: entry for entry in excluded}

    assert excluded_by_code["001"] == {
        "code": "001",
        "name": "World",
        "type": "Region",
        "parent": "ROOT",
    }
    assert excluded_by_code["002"]["parent"] == "World"
    assert excluded_by_code["202"]["parent"] == "Africa"
    assert excluded_by_code["150"]["parent"] == "World"
    assert excluded_by_code["039"]["parent"] == "World"
    assert excluded_by_code["900"] == {
        "code": "900",
        "name": "Other areas",
        "type": "Other",
        "parent": "World",
    }
    # Exactly the 6 non-Country nodes in the fixture, no more, no less.
    assert len(excluded) == 6


def test_collect_countries_dedupes_same_country_under_two_parents():
    """Spain (724) appears under both 'Europe' and 'Southern Europe' groupings
    in the fixture; the canonical dict must dedupe by geoAreaCode."""
    result = countries.collect_countries(TREE_SAMPLE)

    assert result["724"] == "Spain"
    assert len(result) == 4  # Egypt, Kenya, Spain, Kosovo -- not 5


# --- build_crosswalk() -------------------------------------------------------


def test_build_crosswalk_resolves_known_sample_spain():
    """Spain M49 724 -> ESP, resolved from the real acquired M49 CSV
    (src/ingesta/data/m49_countries.csv, default M49_CSV_PATH)."""
    crosswalk = countries.build_crosswalk()

    assert crosswalk["724"] == "ESP"


def test_build_crosswalk_resolves_multiple_known_samples():
    crosswalk = countries.build_crosswalk()

    assert crosswalk["818"] == "EGY"  # Egypt
    assert crosswalk["404"] == "KEN"  # Kenya


def test_build_crosswalk_loads_from_explicit_csv_path(tmp_path):
    csv_path = tmp_path / "sample_m49.csv"
    csv_path.write_text(
        "Global Code;Global Name;M49 Code;ISO-alpha2 Code;ISO-alpha3 Code\n"
        "001;World;724;ES;ESP\n"
        "001;World;818;EG;EGY\n",
        encoding="utf-8-sig",
    )

    crosswalk = countries.build_crosswalk(csv_path)

    assert crosswalk == {"724": "ESP", "818": "EGY"}


# --- filter_to_countries() ---------------------------------------------------


def test_filter_to_countries_keeps_rows_that_resolve_to_country_leaf():
    country_set = countries.collect_countries(TREE_SAMPLE)
    crosswalk = {"724": "ESP", "818": "EGY", "404": "KEN", "901": "XKX"}
    rows = [
        {"geoAreaCode": "724", "value": "1.0"},
        {"geoAreaCode": "818", "value": "2.0"},
    ]

    kept, excluded = countries.filter_to_countries(rows, country_set, crosswalk)

    assert excluded == []
    assert {r["geoAreaCode"]: r["iso3"] for r in kept} == {"724": "ESP", "818": "EGY"}


def test_filter_to_countries_drops_rows_not_a_country_leaf():
    """A regional aggregate code ('001' == World) present in the observation
    rows must be dropped and logged, never silently kept."""
    country_set = countries.collect_countries(TREE_SAMPLE)
    crosswalk = countries.build_crosswalk()
    rows = [
        {"geoAreaCode": "724", "value": "1.0"},
        {"geoAreaCode": "001", "value": "999.0"},  # "World" aggregate
    ]

    kept, excluded = countries.filter_to_countries(rows, country_set, crosswalk)

    assert [r["geoAreaCode"] for r in kept] == ["724"]
    assert len(excluded) == 1
    assert excluded[0]["geoAreaCode"] == "001"
    assert excluded[0]["exclusion_reason"] == "not_a_country_leaf"


def test_filter_to_countries_logs_country_leaf_missing_from_crosswalk():
    """A geoAreaCode that resolves to a Country leaf but has no matching M49
    CSV crosswalk entry (source mismatch) must be excluded and logged, not
    silently dropped or inserted without an ISO3 code."""
    country_set = countries.collect_countries(TREE_SAMPLE)
    crosswalk = {"724": "ESP"}  # deliberately missing Kosovo's "901"
    rows = [{"geoAreaCode": "901", "value": "1.0"}]

    kept, excluded = countries.filter_to_countries(rows, country_set, crosswalk)

    assert kept == []
    assert excluded[0]["exclusion_reason"] == "missing_from_m49_crosswalk"


def test_filter_to_countries_disputed_territory_kept_iff_type_country():
    """D-14 operationalized: Kosovo (a disputed/non-UN-member territory) is
    KEPT because it resolves to a type=='Country' leaf in GeoArea/Tree -- no
    manual exception list is consulted. It is treated identically to any
    other Country-leaf code."""
    country_set = countries.collect_countries(TREE_SAMPLE)
    crosswalk = {"901": "XKX"}
    rows = [{"geoAreaCode": "901", "value": "5.0"}]

    kept, excluded = countries.filter_to_countries(rows, country_set, crosswalk)

    assert excluded == []
    assert kept[0]["iso3"] == "XKX"
    assert kept[0]["geoAreaCode"] == "901"


# --- write_exclusion_log() ---------------------------------------------------


def test_write_exclusion_log_persists_to_file(tmp_path):
    excluded = [{"code": "001", "name": "World", "type": "Region", "parent": "ROOT"}]
    log_path = tmp_path / "exclusions" / "log.json"

    result_path = countries.write_exclusion_log(excluded, log_path)

    assert result_path == log_path
    assert log_path.exists()
    loaded = json.loads(log_path.read_text(encoding="utf-8"))
    assert loaded == excluded


def test_write_exclusion_log_creates_parent_directories(tmp_path):
    excluded: list[dict] = []
    log_path = tmp_path / "nested" / "dir" / "exclusions.json"

    countries.write_exclusion_log(excluded, log_path)

    assert log_path.exists()


# --- D-13 anti-pattern guard --------------------------------------------------


def test_module_does_not_import_pycountry_or_world_bank_lists():
    """D-13: the canonical list source must be the UN's own M49 classification
    -- never pycountry, never a World Bank list."""
    source = Path(countries.__file__).read_text(encoding="utf-8")
    assert "import pycountry" not in source
    assert "worldbank" not in source.lower()
