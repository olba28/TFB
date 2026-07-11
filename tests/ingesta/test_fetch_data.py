"""Tests for src/ingesta/fetch_data.py: the ingestion orchestrator composing
client, manifest, countries, and db (INGEST-01, INGEST-02, INGEST-04).

All tests mock the client/network layer -- no live network calls (per plan).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.ingesta import fetch_data

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

with open(FIXTURES_DIR / "indicator_dimension_samples.json", encoding="utf-8") as f:
    SAMPLES = json.load(f)


# --- filter_headline_rows(): per-indicator dimension filter (INGEST-02) -----


@pytest.mark.parametrize("indicator_code", ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"])
def test_filter_headline_rows_yields_one_row_per_country_year(indicator_code):
    rows = SAMPLES[indicator_code]

    filtered = fetch_data.filter_headline_rows(rows, indicator_code)

    keys = [(r["geoAreaCode"], r["timePeriodStart"]) for r in filtered]
    assert len(keys) == len(set(keys)), "duplicate (country, year) rows survived the filter"
    assert len(filtered) == 2  # each fixture sample has exactly 2 distinct (country, year) pairs


@pytest.mark.parametrize("indicator_code", ["8.1.1", "8.2.1", "2.3.1"])
def test_global_activity_total_rule_would_zero_out_non_water_indicators(indicator_code):
    """Regression guard for Pitfall 1: a hardcoded global `Activity: TOTAL` rule
    (instead of the per-indicator HEADLINE_DIMENSIONS table) would silently drop
    8.1.1/8.2.1/2.3.1 to zero rows, since none of them carry an `Activity` key."""
    rows = SAMPLES[indicator_code]

    naively_filtered = [r for r in rows if r["dimensions"].get("Activity") == "TOTAL"]
    assert len(naively_filtered) == 0

    # The real per-indicator filter does not make this mistake.
    assert len(fetch_data.filter_headline_rows(rows, indicator_code)) > 0


def test_filter_headline_rows_raises_when_zero_rows_survive():
    """Loud-failure guard (Pitfall 1): if nothing matches the per-indicator
    headline combo, filter_headline_rows must raise rather than silently
    return an empty list."""
    rows = [
        {
            "geoAreaCode": "840",
            "timePeriodStart": 2020,
            "dimensions": {"Reporting Type": "N", "Activity": "TOTAL"},
        }
    ]

    with pytest.raises(AssertionError, match="No rows survived"):
        fetch_data.filter_headline_rows(rows, "6.4.2")


def test_headline_dimensions_is_per_indicator_not_a_single_global_rule():
    assert fetch_data.HEADLINE_DIMENSIONS["6.4.2"] == {"Activity": "TOTAL"}
    assert fetch_data.HEADLINE_DIMENSIONS["6.4.1"] == {"Activity": "TOTAL"}
    assert fetch_data.HEADLINE_DIMENSIONS["8.1.1"] == {}
    assert fetch_data.HEADLINE_DIMENSIONS["8.2.1"] == {}
    assert fetch_data.HEADLINE_DIMENSIONS["2.3.1"] == {"Sex": "BOTHSEX"}


# --- value coercion (Pitfall 5) ----------------------------------------------


def test_value_coercion_handles_literal_nan_string():
    """2.3.1 can return the literal JSON string "NaN" -- pd.to_numeric(errors=
    'coerce') must turn it into a float NaN rather than raising."""
    filtered = fetch_data.filter_headline_rows(SAMPLES["2.3.1"], "2.3.1")

    values = pd.to_numeric([r["value"] for r in filtered], errors="coerce")

    assert pd.isna(values).any()  # the "NaN"-string row coerced to NaN, not raised
    assert not pd.isna(values).all()  # the other kept row still has a real numeric value


# --- run_ingestion(): idempotency guard (D-07) -------------------------------


def test_run_ingestion_skips_fetch_when_manifest_exists_for_all_indicators(monkeypatch):
    """With manifest_exists always True and force=False, run_ingestion must not
    open a session or fetch any pages -- a full idempotent no-op skip."""
    monkeypatch.setattr(fetch_data.manifest, "manifest_exists", lambda code, day: True)
    mock_fetch_pages = MagicMock()
    monkeypatch.setattr(fetch_data.client, "fetch_all_pages", mock_fetch_pages)
    mock_build_session = MagicMock()
    monkeypatch.setattr(fetch_data.client, "build_session", mock_build_session)
    monkeypatch.setattr(fetch_data.db, "get_engine", MagicMock())
    monkeypatch.setattr(fetch_data.db, "init_db", MagicMock())
    mock_rebuild = MagicMock()
    monkeypatch.setattr(fetch_data.db, "rebuild_panel", mock_rebuild)

    fetch_data.run_ingestion(force=False)

    mock_fetch_pages.assert_not_called()
    mock_build_session.assert_not_called()
    mock_rebuild.assert_called_once()


def test_run_ingestion_force_true_refetches_even_when_manifest_exists(monkeypatch):
    """force=True must bypass the manifest-exists skip and fetch every indicator."""
    monkeypatch.setattr(fetch_data.manifest, "manifest_exists", lambda code, day: True)
    monkeypatch.setattr(fetch_data.manifest, "write_manifest", MagicMock())

    mock_fetch_pages = MagicMock(return_value=[])
    monkeypatch.setattr(fetch_data.client, "fetch_all_pages", mock_fetch_pages)
    monkeypatch.setattr(fetch_data.client, "build_session", MagicMock())
    monkeypatch.setattr(
        fetch_data, "_fetch_country_reference", MagicMock(return_value=({}, {}, []))
    )
    monkeypatch.setattr(fetch_data.countries, "write_exclusion_log", MagicMock())
    monkeypatch.setattr(fetch_data.db, "get_engine", MagicMock())
    monkeypatch.setattr(fetch_data.db, "init_db", MagicMock())
    monkeypatch.setattr(fetch_data.db, "rebuild_panel", MagicMock())

    # Every indicator returns zero rows -> filter_headline_rows would assert;
    # patch it too so we can isolate testing the fetch-count/skip behavior.
    monkeypatch.setattr(fetch_data, "filter_headline_rows", MagicMock(return_value=[]))

    fetch_data.run_ingestion(force=True)

    assert mock_fetch_pages.call_count == len(fetch_data.INDICATOR_CODES)


# --- path-construction safety (Security V5) ----------------------------------


def test_indicator_codes_is_a_fixed_constant_list():
    """Paths must be built only from this fixed 5-code list + date.today() --
    never from unvalidated API response content."""
    assert fetch_data.INDICATOR_CODES == ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"]
