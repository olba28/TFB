---
phase: 01-ingesta-y-almacenamiento-versionado
plan: 06
subsystem: testing
tags: [pytest, sqlite, sha256, un-sdg-api, test-isolation, gap-closure]

# Dependency graph
requires:
  - phase: 01-ingesta-y-almacenamiento-versionado (plans 01-05)
    provides: fetch_data.run_ingestion, manifest.write_manifest, db.insert_observations, the 5-indicator ingestion pipeline this plan restores data for
provides:
  - "An autouse pytest guard (tests/ingesta/conftest.py) that fails the ingesta suite if any test mutates the real data/raw/ tree"
  - "A fixed test_run_ingestion_force_true_refetches_even_when_manifest_exists that sandboxes RAW_DATA_ROOT under tmp_path"
  - "Restored, checksum-consistent raw JSON + manifest artifacts for all 5 indicators (6.4.2, 6.4.1, 8.1.1, 8.2.1, 2.3.1)"
  - "A freshly rebuilt data/panel.db with 18,086 raw_observations rows and 4,923 panel rows, zero duplicates"
affects: [phase-02-panel-eda, any future phase reading data/raw/ or data/panel.db]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Autouse snapshot/diff pytest fixture (size:mtime_ns token map) to guard a real filesystem tree against accidental test writes, scoped to tests/ingesta/conftest.py rather than the shared tests/conftest.py"

key-files:
  created:
    - tests/ingesta/conftest.py
    - tests/ingesta/test_isolation_guard.py
  modified:
    - tests/ingesta/test_fetch_data.py
    - data/raw/6.4.2/2026-07-11.json (regenerated, gitignored)
    - data/raw/6.4.1/2026-07-11.json (regenerated, gitignored)
    - data/raw/8.1.1/2026-07-11.json (regenerated, gitignored)
    - data/raw/8.2.1/2026-07-11.json (regenerated, gitignored)
    - data/raw/2.3.1/2026-07-11.json (regenerated, gitignored)
    - data/panel.db (regenerated, gitignored)

key-decisions:
  - "Restoration was performed as a clean delete + live re-ingestion (not a partial patch), per plan Task 2, because insert_observations' UNIQUE(country,year,indicator) constraint forbids re-inserting rows into a DB that already holds them."
  - "The 5 tracked manifest sidecars (data/raw/*/2026-07-11.manifest.json) came back byte-identical to their prior git-committed content, confirming the live UN SDG API data has not been revised since the original correct 01-05 ingestion -- zero data drift, and nothing new to commit under data/raw/ since the manifests already matched HEAD."
  - "data/panel.db lock (held by DB Browser for SQLite, opened by the user to inspect the corrupted DB) was resolved by asking the user to close the application rather than force-killing it, since a GUI DB editor could hold uncommitted edit state -- once confirmed closed, deletion proceeded cleanly."

patterns-established:
  - "Guard forbid_writes_to_real_raw_data is autouse and function-scoped; any future ingesta test that writes to data/raw/ (even outside test_fetch_data.py) will now fail loudly at teardown with the offending path named, rather than silently corrupting versioned data."

requirements-completed: [INGEST-04]

coverage:
  - id: D1
    description: "Offending test isolated to a tmp_path sandbox via monkeypatch of fetch_data.manifest.RAW_DATA_ROOT"
    requirement: "INGEST-04"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_fetch_data.py::test_run_ingestion_force_true_refetches_even_when_manifest_exists"
        status: pass
    human_judgment: false
  - id: D2
    description: "Autouse regression guard (forbid_writes_to_real_raw_data) fails the ingesta suite if any test mutates the real data/raw/ tree; proven by two self-tests"
    requirement: "INGEST-04"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_isolation_guard.py::test_snapshot_detects_new_file"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_isolation_guard.py::test_snapshot_detects_content_change"
        status: pass
    human_judgment: false
  - id: D3
    description: "All 5 raw JSON indicators restored via live UN SDG API re-ingestion; sha256 of each matches its sibling manifest checksum; no empty {\"data\": []} stubs remain; data/panel.db repopulated with 18,086 raw_observations / 4,923 panel rows and no duplicates"
    requirement: "INGEST-04"
    verification:
      - kind: other
        ref: "python -c checksum-consistency one-liner (see plan Task 2 verify) -> OK"
        status: pass
      - kind: other
        ref: "sqlite3 data/panel.db row-count query -> raw_observations=18086 (distinct=18086), panel=4923"
        status: pass
      - kind: unit
        ref: "pytest tests/ -q (48 passed), re-run after restoration -> checksum-consistency still OK"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-11
status: complete
---

# Phase 01 Plan 06: Restore INGEST-04 raw-JSON gap closure Summary

**Sandboxed the test that was silently corrupting versioned raw JSON, added an autouse write-guard for data/raw/, and restored all 5 indicators via a clean live re-ingestion (18,086 raw_observations / 4,923 panel rows, checksums verified against manifests)**

## Performance

- **Duration:** ~25 min across two sessions (Task 1 committed in a prior session at `fb06271`; Task 2 completed in this continuation session)
- **Completed:** 2026-07-11
- **Tasks:** 2/2 completed
- **Files modified:** 3 test files created/modified + 5 raw JSON + data/panel.db (gitignored, regenerated in place)

## Accomplishments

- Fixed `test_run_ingestion_force_true_refetches_even_when_manifest_exists` to monkeypatch `fetch_data.manifest.RAW_DATA_ROOT` into a `tmp_path` sandbox, eliminating the root cause: an un-sandboxed `run_ingestion(force=True)` call that overwrote the real `data/raw/` tree with mock-derived empty data every time the documented test command ran.
- Added `tests/ingesta/conftest.py` with an autouse `forbid_writes_to_real_raw_data` fixture (snapshot/diff on `size:mtime_ns` tokens) that fails any future ingesta test at teardown if it mutates the real `data/raw/` tree, naming the offending path(s).
- Added `tests/ingesta/test_isolation_guard.py` with two self-tests proving `snapshot_tree`/`diff_snapshots` correctly detect an added file and a content rewrite under a controlled `tmp_path` directory.
- Restored all 5 corrupted raw JSON indicators (6.4.2, 6.4.1, 8.1.1, 8.2.1, 2.3.1) and their manifest sidecars via a clean delete + live re-ingestion against the real UN SDG API (`python -m src.ingesta.fetch_data`).
- Rebuilt `data/panel.db` from the restored data: 18,086 `raw_observations` rows (zero duplicates on `(country_code, year, indicator_code)`), 4,923 `panel` rows -- matching the 01-05 SUMMARY counts exactly, confirming no data drift from the live API.

## Task Commits

1. **Task 1: Isolate offending test + add autouse write-guard** - `fb06271` (test)
2. **Task 2: Restore corrupted raw JSON + manifests via clean live re-ingestion** - no new commit; the 5 raw JSON files and `data/panel.db` are gitignored regenerated artifacts, and the 5 tracked manifest sidecars came back byte-identical to their existing git-committed content (verified via `git diff --stat` on all 5 -- zero diff), so there was nothing new to stage under `data/raw/`. The evidentiary state (checksum consistency, row counts, and post-suite immutability) is recorded in this SUMMARY and reproducible on demand.

**Plan metadata:** committed as part of the final docs commit below.

## Files Created/Modified

- `tests/ingesta/conftest.py` - `REAL_RAW_DATA_ROOT`, `snapshot_tree()`, `diff_snapshots()`, autouse `forbid_writes_to_real_raw_data` fixture
- `tests/ingesta/test_fetch_data.py` - sandboxed `RAW_DATA_ROOT` monkeypatch in the previously-offending test
- `tests/ingesta/test_isolation_guard.py` - two self-tests proving guard detection logic
- `data/raw/{6.4.2,6.4.1,8.1.1,8.2.1,2.3.1}/2026-07-11.json` - regenerated via live re-ingestion (gitignored, not committed)
- `data/raw/{6.4.2,6.4.1,8.1.1,8.2.1,2.3.1}/2026-07-11.manifest.json` - regenerated, byte-identical to prior git-tracked content (no diff to commit)
- `data/panel.db` - regenerated (gitignored, not committed)

## Decisions Made

- Restoration performed as delete-then-reingest, not a partial in-place patch, because `insert_observations`'s `UNIQUE(country, year, indicator)` constraint would raise on re-inserting rows into a DB that already holds them from the corrupted run.
- Manifest sidecars required no new commit: their regenerated content matched git HEAD byte-for-byte, proving the live UN SDG API data is unchanged since the original 01-05 ingestion.
- `data/panel.db`'s file lock (held by DB Browser for SQLite, which the user had open to inspect the corrupted database) was resolved by asking the user to close the application rather than force-terminating it, to avoid risking loss of any unsaved GUI edit state.

## Deviations from Plan

None - plan executed exactly as written. The DB Browser for SQLite file-lock delay was an external environmental blocker, not a code deviation; it was resolved by the user closing the application, after which deletion and restoration proceeded exactly per Task 2's `<action>`.

## Issues Encountered

- **`data/panel.db` file lock:** Mid-deletion, `rm -f data/panel.db` failed with "Device or resource busy" because DB Browser for SQLite (PID 24488) had the file open. Rather than force-killing the user's GUI application, execution paused and asked the user to close it. The user closed DB Browser for SQLite; the orchestrator independently verified the process was gone and the file unlocked before deletion proceeded. No data was lost -- the panel.db is a fully regenerable artifact.
- **Hash-algorithm mismatch during self-verification:** An early sanity check used `md5sum` (available via git-bash fallback) for a "before" snapshot and a Python `sha256` one-liner for the "after" snapshot, producing apparently different digests. This was a false alarm from comparing two different hash algorithms' output for the same files, not real content drift -- confirmed by the independent checksum-consistency check (raw file sha256 vs. manifest's recorded `checksum` field), which passed identically both before and after the full test suite re-run.

## User Setup Required

None - no external service configuration required. The user was asked to close a locally running GUI application (DB Browser for SQLite) that was holding a file lock; no credentials or environment variables were involved.

## Next Phase Readiness

- INGEST-04 / Success Criterion #3 is now durably satisfied: all 5 indicators have on-disk raw JSON whose sha256 matches its sibling manifest's checksum, and the documented test command (`pytest tests/ -q`) no longer corrupts them (regression-guarded by the new autouse fixture).
- `data/panel.db` is fully repopulated (18,086 raw_observations / 4,923 panel rows, no duplicates) and ready for Phase 02 (panel EDA) to consume.
- No blockers for Phase 02.

## Self-Check: PASSED

- `tests/ingesta/conftest.py` FOUND
- `tests/ingesta/test_isolation_guard.py` FOUND
- `tests/ingesta/test_fetch_data.py` FOUND (modified)
- `data/raw/6.4.2/2026-07-11.json` FOUND (13.5MB-class real data, not `{"data": []}`)
- `data/raw/6.4.1/2026-07-11.json` FOUND
- `data/raw/8.1.1/2026-07-11.json` FOUND
- `data/raw/8.2.1/2026-07-11.json` FOUND
- `data/raw/2.3.1/2026-07-11.json` FOUND
- `data/panel.db` FOUND (1,957,888 bytes; raw_observations=18086, panel=4923)
- Commit `fb06271` FOUND in `git log --oneline --all`

---
*Phase: 01-ingesta-y-almacenamiento-versionado*
*Completed: 2026-07-11*
