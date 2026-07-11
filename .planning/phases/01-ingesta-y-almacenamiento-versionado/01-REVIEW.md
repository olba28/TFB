---
phase: 01-ingesta-y-almacenamiento-versionado
reviewed: 2026-07-11T16:06:21Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - data/panel.db
  - data/raw/2.3.1/2026-07-11.json
  - data/raw/6.4.1/2026-07-11.json
  - data/raw/6.4.2/2026-07-11.json
  - data/raw/8.1.1/2026-07-11.json
  - data/raw/8.2.1/2026-07-11.json
  - src/ingesta/__init__.py
  - src/ingesta/client.py
  - src/ingesta/countries.py
  - src/ingesta/data/m49_countries.csv
  - src/ingesta/data/m49_countries.provenance.json
  - src/ingesta/manifest.py
  - tests/__init__.py
  - tests/conftest.py
  - tests/fixtures/.gitkeep
  - tests/fixtures/geoarea_tree_sample.json
  - tests/fixtures/mock_500_then_paginated.json
  - tests/ingesta/__init__.py
  - tests/ingesta/conftest.py
  - tests/ingesta/test_client.py
  - tests/ingesta/test_countries.py
  - tests/ingesta/test_fetch_data.py
  - tests/ingesta/test_isolation_guard.py
  - tests/ingesta/test_manifest.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-11T16:06:21Z
**Depth:** standard
**Files Reviewed:** 22 (24 listed; `tests/fixtures/.gitkeep` and empty `__init__.py` package markers carry no content to review)
**Status:** issues_found

## Summary

This pass targets gap-closure plan 01-06 (INGEST-04): the new `tests/ingesta/conftest.py` autouse write-guard, its self-tests in `test_isolation_guard.py`, the sandboxing fix applied to `test_run_ingestion_force_true_refetches_even_when_manifest_exists` in `test_fetch_data.py`, and the regenerated `data/raw/*.json` + `data/panel.db` artifacts, plus a full re-read of the rest of the phase's file list for regressions. `src/ingesta/fetch_data.py` itself is unchanged by 01-06 and is out of this pass's file scope, but was read for context since the tests under review exercise it directly.

The regenerated data artifacts check out: all 5 raw JSON files are non-empty (4,883-19,182 rows each), their manifest checksums match bytes recomputed independently from disk, `raw_observations` has zero duplicate `(country_code, indicator_code, year, dimension)` groups, and `panel`'s row/indicator counts are consistent with the raw counts. `48/48` tests in `tests/ingesta` pass (`.venv/Scripts/python.exe -m pytest tests/ingesta -q`). `client.py`, `manifest.py`, and `countries.py` are byte-for-byte unchanged from the prior review pass (WR-01 through WR-04 already applied there) and show no new regressions.

The new isolation guard itself is a real improvement, and its two core helpers (`snapshot_tree`/`diff_snapshots`) are correctly implemented and directly unit-tested. However, the guard has three gaps that undercut the very isolation property this gap-closure plan set out to establish: (1) the `force=True` test still performs an unmocked read of the real `data/raw/exclusion_log.json` through a second, unsandboxed path constant (`EXCLUSION_LOG_PATH`) that 01-06 didn't redirect alongside `RAW_DATA_ROOT`; (2) the guard's real-root resolution is cwd-relative and fails open (silently does nothing) rather than fail closed if pytest is ever invoked from a working directory other than the repo root; (3) the autouse fixture wiring itself (as opposed to its two helper functions) is never exercised by a test that proves it actually fires on a genuine violation. None of these rise to Critical today — no test currently writes through the unsandboxed path — but they are exactly the kind of latent gap that produced the original INGEST-04 corruption, in a guard whose sole purpose is to prevent a recurrence.

## Warnings

### WR-01: `EXCLUSION_LOG_PATH` is not sandboxed in the force=True refetch test, leaving an unmocked read (and a latent write path) into real production data

**File:** `tests/ingesta/test_fetch_data.py:127-171` (root cause: `src/ingesta/fetch_data.py:52,226-227`)
**Issue:** 01-06's fix redirects `fetch_data.manifest.RAW_DATA_ROOT` to `tmp_path / "data" / "raw"` (line 134) to stop `run_ingestion`'s un-mocked `raw_path.write_text()` from clobbering the real raw JSON files. But `run_ingestion` also touches a *second* hardcoded, unsandboxed path constant, `fetch_data.EXCLUSION_LOG_PATH = Path("data/raw/exclusion_log.json")`, via:
```python
if EXCLUSION_LOG_PATH.exists():
    existing_excluded = json.loads(EXCLUSION_LOG_PATH.read_text(encoding="utf-8"))
```
This constant is never patched in the test. Verified live: the real `data/raw/exclusion_log.json` (30,735 bytes, last written by the live ingestion run) exists on disk right now, so every run of this test currently performs an unmocked read of real production data — a non-hermetic test whose branch coverage silently depends on repo file-system state (behaves differently on a fresh checkout, where the file doesn't exist yet, than in this environment). `countries.write_exclusion_log` happens to be mocked in this specific test today, so no write occurs — but that mock is the *only* thing standing between this test and reproducing the exact INGEST-04 corruption class (`run_ingestion(force=True)` overwriting real `data/raw/` state with test-fixture data) a second time, this time for the exclusion log instead of the raw JSON. The autouse guard added by this same plan would only catch that after the fact, at teardown — by which point the real exclusion log history would already be gone.
**Fix:**
```python
monkeypatch.setattr(fetch_data.manifest, "RAW_DATA_ROOT", tmp_path / "data" / "raw")
monkeypatch.setattr(fetch_data, "EXCLUSION_LOG_PATH", tmp_path / "data" / "raw" / "exclusion_log.json")
```

### WR-02: The isolation guard's protective root resolution fails open (silently does nothing) when pytest's cwd isn't the repo root

**File:** `tests/ingesta/conftest.py:29`
**Issue:** `REAL_RAW_DATA_ROOT = manifest.RAW_DATA_ROOT.resolve()` resolves the relative `Path("data/raw")` against `os.getcwd()` at conftest import time. If pytest is ever invoked from a directory other than the repo root (a subdirectory, an IDE test runner with a different working directory, a CI step that `cd`s first), this resolves to a path that doesn't exist. `snapshot_tree()` explicitly returns `{}` when the root doesn't exist (by design, to tolerate "no raw data fetched yet") — so both the "before" and "after" snapshots are `{}`, `diff_snapshots` is always `[]`, and `forbid_writes_to_real_raw_data` passes silently even if a test is actively corrupting the real `data/raw/` tree from that same misresolved-cwd run. A safety net whose entire job is to catch exactly this class of production-data corruption should fail loudly on a misconfiguration, not silently no-op.
**Fix:** Anchor the root to the repo layout instead of trusting `os.getcwd()`, and assert it agrees with the module under test:
```python
REAL_RAW_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw"
assert REAL_RAW_DATA_ROOT == manifest.RAW_DATA_ROOT.resolve(), (
    "tests/ingesta/conftest.py's REAL_RAW_DATA_ROOT and manifest.RAW_DATA_ROOT "
    "disagree -- guard cannot verify it is watching the real data/raw tree."
)
```

### WR-03: The autouse fixture itself is never exercised by a test that proves it fires on a genuine violation

**File:** `tests/ingesta/test_isolation_guard.py` (whole file), `tests/ingesta/conftest.py:61-77`
**Issue:** `test_isolation_guard.py` only unit-tests the two helper functions (`snapshot_tree`, `diff_snapshots`) against a `tmp_path`. It never exercises `forbid_writes_to_real_raw_data` itself — the fixture that actually wires those helpers to `REAL_RAW_DATA_ROOT` and performs the `assert`. A regression in that wiring (e.g. someone accidentally swaps `before`/`after`, changes the assert to a no-op, or misresolves the root as in WR-02) would pass this suite undetected, since nothing calls the fixture against a real, controlled violation and checks that it raises.
**Fix:** Add a test that monkeypatches the module-level root the fixture reads (refactor `forbid_writes_to_real_raw_data` to read `conftest.REAL_RAW_DATA_ROOT` via the module rather than a closed-over local, if not already resolvable at call time) to a `tmp_path`, writes a file inside it during a nested pytest run (e.g. via `pytester`), and asserts the outer test reports the inner run as failed — proving the guard fires end-to-end, not just its building blocks.

## Info

### IN-01: Change-detection token can miss a same-tick, same-size overwrite

**File:** `tests/ingesta/conftest.py:32-48`
**Issue:** `snapshot_tree`'s token is `f"{st_size}:{st_mtime_ns}"`. A test that overwrites a file with different content of the exact same byte length, fast enough that the filesystem's mtime resolution doesn't distinguish the two writes, would produce identical before/after tokens and go undetected. This is a narrow edge case (the existing tests intentionally use a longer replacement string specifically to avoid it — see `test_snapshot_detects_content_change`), not currently exploited by any test in the suite, but worth noting since it is the sole detection mechanism for a plan whose entire purpose is preventing recurrence of real data loss.
**Fix:** Not required for this pass given the low likelihood and the guard's current size+mtime check already catching every scenario currently exercised; if stronger guarantees are wanted later, add a content hash (e.g. `sha256`, given the current tree is only ~33MB) as a third component of the token.

---

_Reviewed: 2026-07-11T16:06:21Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
