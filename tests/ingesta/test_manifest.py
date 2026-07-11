"""Tests for src/ingesta/manifest.py: provenance manifest schema and idempotency guard."""

from __future__ import annotations

import hashlib
import json

import pytest

from src.ingesta import manifest


@pytest.fixture
def raw_file(tmp_path):
    """A raw JSON file living under an indicator/date-shaped path, per D-06."""
    raw_path = tmp_path / "6.4.2" / "2026-07-10.json"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        json.dumps({"data": [{"value": "1"}, {"value": "2"}]}),
        encoding="utf-8",
    )
    return raw_path


def test_sha256_of_matches_stdlib_hashlib(raw_file):
    expected = hashlib.sha256(raw_file.read_bytes()).hexdigest()
    assert manifest.sha256_of(raw_file) == expected


def test_write_manifest_creates_sidecar_with_all_five_required_fields(raw_file):
    manifest_path = manifest.write_manifest(
        raw_file,
        url="https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data",
        params={"indicator": "6.4.2", "page": 1, "pageSize": 1000},
        row_count=2,
    )

    assert manifest_path.exists()
    assert manifest_path.name == "2026-07-10.manifest.json"
    assert manifest_path.parent == raw_file.parent

    loaded = manifest.load_manifest(manifest_path)
    assert set(loaded.keys()) == {"date", "url", "params", "row_count", "checksum"}
    # WR-03: `date` is derived from raw_path's own filename stem, not a fresh
    # `date.today()` call, so it stays consistent even for backfills/repairs
    # run on a different day than the raw file's own download date.
    assert loaded["date"] == raw_file.stem
    assert loaded["url"] == "https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data"
    assert loaded["params"] == {"indicator": "6.4.2", "page": 1, "pageSize": 1000}
    assert loaded["row_count"] == 2
    assert loaded["checksum"] == hashlib.sha256(raw_file.read_bytes()).hexdigest()


def test_manifest_exists_false_before_write_true_after(tmp_path, monkeypatch):
    monkeypatch.setattr(manifest, "RAW_DATA_ROOT", tmp_path / "data" / "raw")
    raw_path = manifest.RAW_DATA_ROOT / "6.4.2" / "2026-07-10.json"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(json.dumps({"data": []}), encoding="utf-8")

    assert manifest.manifest_exists("6.4.2", "2026-07-10") is False

    manifest.write_manifest(
        raw_path,
        url="https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data",
        params={"indicator": "6.4.2"},
        row_count=0,
    )

    assert manifest.manifest_exists("6.4.2", "2026-07-10") is True


def test_manifest_exists_false_when_only_raw_json_present_no_manifest(tmp_path, monkeypatch):
    """manifest_exists requires BOTH the raw file and its manifest sidecar."""
    monkeypatch.setattr(manifest, "RAW_DATA_ROOT", tmp_path / "data" / "raw")
    raw_path = manifest.RAW_DATA_ROOT / "8.1.1" / "2026-07-10.json"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(json.dumps({"data": []}), encoding="utf-8")

    assert manifest.manifest_exists("8.1.1", "2026-07-10") is False


def test_manifest_exists_false_for_different_day(tmp_path, monkeypatch):
    monkeypatch.setattr(manifest, "RAW_DATA_ROOT", tmp_path / "data" / "raw")
    raw_path = manifest.RAW_DATA_ROOT / "6.4.2" / "2026-07-10.json"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(json.dumps({"data": []}), encoding="utf-8")
    manifest.write_manifest(
        raw_path,
        url="https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data",
        params={"indicator": "6.4.2"},
        row_count=0,
    )

    assert manifest.manifest_exists("6.4.2", "2026-07-11") is False
