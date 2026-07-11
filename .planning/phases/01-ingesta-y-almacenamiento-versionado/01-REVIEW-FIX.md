---
phase: 01-ingesta-y-almacenamiento-versionado
fixed_at: 2026-07-11T10:01:27Z
review_path: .planning/phases/01-ingesta-y-almacenamiento-versionado/01-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-07-11T10:01:27Z
**Source review:** .planning/phases/01-ingesta-y-almacenamiento-versionado/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (2 critical, 4 warning; fix_scope = critical_warning, IN-01 excluded)
- Fixed: 6
- Skipped: 0

All 46 existing tests pass after every fix (`.venv/Scripts/python.exe -m pytest tests/ -q`). Four test files required corresponding updates because they asserted on the exact pre-fix behavior (bare `AssertionError`, `date.today()`-derived manifest date, and a synthetic zero-row fixture that the new WR-04 guard now correctly rejects) — these updates are documented per finding below.

## Fixed Issues

### CR-01: Manifest is written before data is validated/inserted, so a mid-pipeline failure permanently and silently skips that indicator on every future run

**Files modified:** `src/ingesta/fetch_data.py`
**Commit:** `41be5f2`
**Applied fix:** Reordered `run_ingestion`'s per-indicator loop so `filter_headline_rows`, `countries.filter_to_countries`, and `db.insert_observations` all run and succeed *before* `manifest.write_manifest` is called. The raw JSON file is still written immediately after fetch (unchanged), but the provenance manifest — the artifact `manifest_exists()` checks to decide whether to skip re-fetching — is now written last, only once the row has actually landed in `raw_observations`. Updated the module docstring's numbered orchestration sequence to reflect the new order.

### CR-02: Exclusion log is unconditionally overwritten with only the current run's processed indicators, silently destroying previously-documented exclusions on a partial re-run

**Files modified:** `src/ingesta/fetch_data.py`
**Commit:** `2fa373e`
**Applied fix:** Before calling `countries.write_exclusion_log`, `run_ingestion` now loads any existing `data/raw/exclusion_log.json` (if present), merges its entries with the current run's `all_excluded` keyed by `(code, exclusion_reason)` (current-run entries win on conflict), and writes the merged result. A full run still produces the same output as before; a partial re-run (some indicators skipped via the per-indicator `continue`) no longer discards those skipped indicators' previously-recorded exclusions.

### WR-01: Critical data-integrity guards rely on bare `assert`, which is silently stripped under `python -O` / `PYTHONOPTIMIZE`

**Files modified:** `src/ingesta/fetch_data.py`, `src/db.py`, `tests/ingesta/test_fetch_data.py`, `tests/ingesta/test_db.py`
**Commit:** `114d91c`
**Applied fix:** Replaced the bare `assert len(filtered) > 0, ...` in `filter_headline_rows` with `if len(filtered) == 0: raise ValueError(...)`, and the bare `assert not duplicated_mask.any(), ...` in `db.insert_observations` with `if duplicated_mask.any(): raise ValueError(...)`. Both guards now survive `-O`/`-OO`/`PYTHONOPTIMIZE=1`. Updated `test_filter_headline_rows_raises_when_zero_rows_survive` and `test_insert_observations_raises_on_duplicate_keys_in_df` to assert on `ValueError` instead of `AssertionError` (the only behavioral change visible to callers), and updated the module docstrings in `src/db.py` and `tests/ingesta/test_db.py` that described the old "Python-level assert" language.

### WR-02: `fetch_all_pages`'s `total_pages` is re-read from every page's response, contradicting its own docstring and risking silent premature truncation

**Files modified:** `src/ingesta/client.py`
**Commit:** `aad91bf`
**Applied fix:** Guarded the `total_pages = body["totalPages"]` reassignment with `if page == 1:` so it is captured only from the first response, matching the function's own docstring and preventing a later page's smaller `totalPages` value from silently truncating the pagination loop.

### WR-03: `write_manifest`'s `date` field is derived independently of the raw file's own date, rather than from it

**Files modified:** `src/ingesta/manifest.py`, `tests/ingesta/test_manifest.py`
**Commit:** `68bfaf8`
**Applied fix:** `write_manifest` now sets `"date": raw_path.stem` instead of calling `date.today().isoformat()` independently, deriving the manifest's date field structurally from the raw file's own `{date}.json` filename (D-06 convention) so the two can never silently diverge (e.g. on a midnight-boundary re-write or a backfill/repair run on a different day). Removed the now-unused `from datetime import date` import from `manifest.py`. Updated `test_write_manifest_creates_sidecar_with_all_five_required_fields` to assert `loaded["date"] == raw_file.stem` instead of `date.today().isoformat()` (the fixture's raw file path already carries a fixed, non-today date, `2026-07-10`, so this assertion is now meaningful rather than incidentally true) and removed the now-unused `date` import from the test file.

### WR-04: No loud-failure guard when `filter_to_countries` excludes every row for an indicator

**Files modified:** `src/ingesta/fetch_data.py`, `tests/ingesta/test_fetch_data.py`
**Commit:** `a895c94`
**Applied fix:** Added a symmetrical guard immediately after `countries.filter_to_countries` in `run_ingestion`: `if len(kept) == 0: raise ValueError(...)`, mirroring `filter_headline_rows`'s own zero-rows guard. Updated `test_run_ingestion_force_true_refetches_even_when_manifest_exists`, which deliberately drives `filter_headline_rows` to return `[]` to isolate testing fetch-count/skip behavior — this synthetic scenario now also needs `countries.filter_to_countries` patched to return one well-formed dummy kept row (otherwise the new guard correctly rejects the synthetic empty-row scenario), and `db.insert_observations` patched too since the mocked `get_engine()` is not a real SQLAlchemy engine.

## Skipped Issues

None — all 6 in-scope findings were fixed.

---

_Fixed: 2026-07-11T10:01:27Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
