---
phase: 01-ingesta-y-almacenamiento-versionado
verified: 2026-07-11T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "Existe, por cada indicador, una copia local versionada del JSON crudo devuelto por la API junto con un manifiesto de procedencia (Success Criteria #3, INGEST-04)"
  gaps_remaining: []
  regressions: []
---

# Phase 01: Ingesta y Almacenamiento Versionado Verification Report

**Phase Goal:** El sistema obtiene y almacena de forma trazable y reproducible los 5 indicadores ODS de la ONU para 150+ países (2000–2022), sin duplicados ni agregados regionales, antes de cualquier transformación.
**Verified:** 2026-07-11
**Status:** passed
**Re-verification:** Yes — after gap closure (Plan 01-06)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `raw_observations` contiene una única fila por (país, año, indicador) tras el filtrado (Success Criteria #1) | ✓ VERIFIED | `src/db.py` DDL has `UNIQUE(country_code, year, indicator_code)`; `insert_observations()` raises before any duplicate row reaches SQLite. Live DB re-check: `SELECT COUNT(*)` = 18,086 and `SELECT COUNT(DISTINCT country_code,year,indicator_code)` = 18,086 — exact match, unchanged from prior verification. |
| 2 | Ningún código M49 de región aparece en el panel; crosswalk M49↔ISO3 y lista canónica filtran agregados (Success Criteria #2) | ✓ VERIFIED | `src/ingesta/countries.py` still keeps only `type=='Country'` leaves; `grep -rn "pycountry\|World Bank"` in `src/` returns only doc-comment mentions explaining what is *not* used, no actual import. Live DB re-check: 215 distinct `country_code` values, all 3-letter ISO3, sample confirms no region-like codes (ABW, AFG, AGO...). `data/raw/exclusion_log.json` has 182 documented exclusion entries. |
| 3 | Existe, por cada indicador, una copia local versionada del JSON crudo + manifiesto de procedencia (Success Criteria #3, INGEST-04) | ✓ VERIFIED (gap closed) | Re-ran the checksum-consistency check live: for all 5 `data/raw/{indicator}/2026-07-11.json` files, `sha256(file) == manifest['checksum']` for every file — zero mismatches, zero empty `{"data": []}` stubs. Ran the full suite (`pytest tests/ -q`, 48 passed) and **re-checked checksums immediately after** — still zero mismatches, proving the suite no longer corrupts the real `data/raw/` tree. `tests/ingesta/test_fetch_data.py` line 134 now monkeypatches `fetch_data.manifest.RAW_DATA_ROOT` to a `tmp_path` sandbox in the previously-offending test. `tests/ingesta/conftest.py` adds an autouse `forbid_writes_to_real_raw_data` fixture (snapshot/diff on `size:mtime_ns`) that fails any ingesta test that mutates the real tree; `tests/ingesta/test_isolation_guard.py`'s two self-tests (`test_snapshot_detects_new_file`, `test_snapshot_detects_content_change`) pass, proving the guard's detection logic. |
| 4 | El cliente pagina automáticamente y reintenta ante fallos transitorios (Success Criteria #4) | ✓ VERIFIED | `src/ingesta/client.py::build_session()` still mounts a `urllib3.util.retry.Retry(...)` object with `status_forcelist`; unchanged from prior verification, no regression. |
| 5 | `requirements.lock.txt` existe y refleja las versiones exactas vía `pip freeze` (Success Criteria #5) | ✓ VERIFIED | `diff <(.venv/Scripts/python.exe -m pip freeze) requirements.lock.txt` returns zero differences. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/db.py` | `get_engine`, `init_db`, `insert_observations`, `rebuild_panel` | ✓ VERIFIED | Unchanged since prior verification; regression check only. |
| `src/ingesta/client.py` | `build_session`, `fetch_all_pages` | ✓ VERIFIED | Unchanged; `Retry(` object confirmed present. |
| `src/ingesta/manifest.py` | `write_manifest`, `manifest_exists`, `load_manifest`, `sha256_of` | ✓ VERIFIED | Unchanged; manifest content now durably consistent with the raw files (see Truth #3). |
| `src/ingesta/countries.py` | `collect_countries`, `build_crosswalk`, `filter_to_countries`, `write_exclusion_log` | ✓ VERIFIED | Unchanged; regression check only. |
| `src/ingesta/data/m49_countries.csv` + `.provenance.json` | Official M49 table, versioned with provenance | ✓ VERIFIED | Tracked in git, present on disk. |
| `src/ingesta/fetch_data.py` | `HEADLINE_DIMENSIONS`, `filter_headline_rows`, `run_ingestion` | ✓ VERIFIED | Unchanged; orchestration order intact. |
| `data/raw/{indicator}/{fecha}.json` + `.manifest.json` (×5) | Live-ingested raw data + provenance | ✓ VERIFIED (was ⚠️ HOLLOW) | Restored via clean delete + live re-ingestion (Plan 01-06, Task 2). All 5 files now checksum-consistent with their manifests, no empty stubs, confirmed both before and after a full `pytest tests/ -q` run. |
| `data/panel.db` (`raw_observations` + `panel`) | Populated SQLite tables | ✓ VERIFIED | Live query: 18,086 `raw_observations` rows (unique), 4,923 `panel` rows, 215 distinct countries — matches Plan 01-05/01-06 SUMMARY figures exactly. |
| `requirements.lock.txt` | Frozen venv dependencies | ✓ VERIFIED | Exact match to current `pip freeze`. |
| `tests/ingesta/conftest.py` | Autouse write-guard for `data/raw/` (gap-closure artifact) | ✓ VERIFIED | Present, substantive: `REAL_RAW_DATA_ROOT`, `snapshot_tree()`, `diff_snapshots()`, `forbid_writes_to_real_raw_data` fixture all implemented and wired (autouse, function-scoped). |
| `tests/ingesta/test_isolation_guard.py` | Self-tests proving guard detection (gap-closure artifact) | ✓ VERIFIED | Both self-tests present and pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `fetch_data.run_ingestion` | `client.fetch_all_pages` | direct call, per-indicator loop | ✓ WIRED | Unchanged, confirmed in source. |
| `fetch_data.run_ingestion` | `countries.filter_to_countries` | direct call, results fed into `db.insert_observations` | ✓ WIRED | Unchanged, confirmed in source. |
| `fetch_data.run_ingestion` | `manifest.write_manifest` | called only after successful insert | ✓ WIRED | Confirmed; the previously corrupted downstream artifact (`raw_path`) is now durably consistent with what this writes about (see Truth #3). |
| `fetch_data.run_ingestion` | `db.insert_observations` → `db.rebuild_panel` | sequential calls | ✓ WIRED | Confirmed via live DB inspection matching row counts. |
| `tests/ingesta/test_fetch_data.py::test_run_ingestion_force_true_refetches_even_when_manifest_exists` | `tmp_path` sandbox | `monkeypatch.setattr(fetch_data.manifest, "RAW_DATA_ROOT", tmp_path / "data" / "raw")` | ✓ WIRED | Confirmed at line 134 — the previously un-sandboxed test now redirects writes away from production data. |
| `tests/ingesta/conftest.py::forbid_writes_to_real_raw_data` (autouse) | `snapshot_tree()`/`diff_snapshots()` over `REAL_RAW_DATA_ROOT` | pytest fixture yield/assert | ✓ WIRED | Confirmed active during the full suite run — a live full-suite run left the real `data/raw/` tree byte-identical (checksum re-check passed immediately after). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes | `.venv/Scripts/python.exe -m pytest tests/ -q` | 48 passed | ✓ PASS |
| Raw JSON ↔ manifest checksum consistency (all 5 indicators) | live sha256 vs manifest `checksum` comparison | 0 mismatches, 0 empty stubs | ✓ PASS |
| Checksum consistency re-checked immediately after full suite run | same check re-run post-`pytest tests/ -q` | 0 mismatches, 0 empty stubs (unchanged) | ✓ PASS |
| Isolation guard self-tests | `pytest tests/ingesta/test_isolation_guard.py -q` (implicit in full run) | both pass | ✓ PASS |
| DB uniqueness invariant | `SELECT COUNT(*) vs COUNT(DISTINCT ...)` on `raw_observations` | 18086 == 18086 | ✓ PASS |
| `.gitignore` correctness | `git check-ignore` on raw JSON / `panel.db` / manifest | Raw JSON + `panel.db` ignored; manifests tracked | ✓ PASS |
| `requirements.lock.txt` matches venv | `diff <(pip freeze) requirements.lock.txt` | No differences | ✓ PASS |
| Client retry object present | `grep -n "Retry(" src/ingesta/client.py` | Found (line 43) | ✓ PASS |
| No pycountry/World Bank import | `grep -rn "pycountry\|World Bank" src/` | Only doc-comment mentions, no import | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|--------------|-------------|--------------|--------|----------|
| INGEST-01 | 01-02, 01-05 | Obtiene 5 indicadores vía API SDG, 150+ países, 2000-2022, paginación+reintentos | ✓ SATISFIED | Client + orchestrator verified; live DB has all 5 indicators, 215 countries |
| INGEST-02 | 01-05 | Filtra por dimensión para evitar duplicados país-año | ✓ SATISFIED | Per-indicator `HEADLINE_DIMENSIONS`/`HEADLINE_SERIES`, DB uniqueness confirmed |
| INGEST-03 | 01-03 | Excluye agregados regionales M49 vía crosswalk + lista canónica | ✓ SATISFIED | 215 clean ISO3 codes, exclusion log with 182 documented exclusions |
| INGEST-04 | 01-02, 01-05, 01-06 | Guarda copia local versionada de JSON crudo + manifiesto de procedencia | ✓ SATISFIED (gap closed by Plan 01-06) | All 5 raw JSON files checksum-consistent with their manifests, verified live both before and after a full test-suite run; autouse guard now prevents recurrence |
| INGEST-05 | 01-04 | Almacena panel en SQLite (`raw_observations` larga + `panel` ancha) | ✓ SATISFIED | Schema, insert guard, pivot rebuild all verified against live DB |
| REPRO-01 | 01-01 | `requirements.lock.txt` vía `pip freeze` | ✓ SATISFIED | Exact match confirmed |

No orphaned requirements — all 6 IDs mapped to Phase 1 in `REQUIREMENTS.md`'s Traceability table are accounted for above and all are marked `[x]` (Complete) in `REQUIREMENTS.md`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/ingesta/data/DB.Browser.for.SQLite-v3.13.1-win64.msi` | n/a | A 19MB Windows installer file sitting untracked inside `src/ingesta/data/` (which is supposed to hold only the versioned M49 reference CSV + provenance JSON) | ℹ️ Info | Not a blocker — the file is untracked (`git status` shows `??`), not committed, and does not affect any Phase 1 truth, artifact, or wiring. Almost certainly a stray download from the DB Browser for SQLite installation mentioned in the 01-06 SUMMARY (used to inspect `data/panel.db`), saved to the wrong directory. Should be deleted or moved outside the source tree before it is accidentally `git add -A`'d in a future commit. |

No `TODO`/`FIXME`/`XXX`/`HACK`/`PLACEHOLDER` markers found in any Phase 1 source or gap-closure test file (`src/db.py`, `src/ingesta/*.py`, `tests/ingesta/conftest.py`, `tests/ingesta/test_isolation_guard.py`, `tests/ingesta/test_fetch_data.py`).

### Human Verification Required

None. All 5 truths are deterministically verifiable via direct file/DB inspection and a live test-suite run, which was performed as part of this verification.

### Gaps Summary

No gaps remain. This is a re-verification following gap-closure Plan 01-06, which addressed the single gap found in the initial verification (2026-07-11): Success Criterion #3 / INGEST-04, where the 5 on-disk raw JSON files had been silently corrupted into empty `{"data": []}` stubs by an un-sandboxed test (`test_run_ingestion_force_true_refetches_even_when_manifest_exists`) writing to the real `data/raw/` tree instead of a `tmp_path` sandbox.

Plan 01-06 fixed the offending test (line 134 now monkeypatches `fetch_data.manifest.RAW_DATA_ROOT` into a `tmp_path` sandbox), added a regression-proof autouse guard (`tests/ingesta/conftest.py::forbid_writes_to_real_raw_data`) with two self-tests proving its detection logic, and restored all 5 indicators via a clean delete + live re-ingestion against the real UN SDG API.

This verification independently re-confirmed the fix, not just the SUMMARY's claims: it re-ran the checksum-consistency check live (all 5 files match their manifests, zero empty stubs), ran the full test suite (48 passed), and re-ran the checksum check immediately afterward to prove the suite no longer corrupts the restored artifacts. It also re-confirmed the DB row counts (18,086 raw_observations / 4,923 panel, zero duplicates) and did a fast regression pass over the four previously-verified truths (uniqueness, region exclusion, client retry/pagination, lockfile) with no drift found.

All 6 Phase 1 requirement IDs (INGEST-01 through INGEST-05, REPRO-01) are satisfied and independently verified against the running codebase. The phase goal — trazable, reproducible ingestion of the 5 ODS indicators for 150+ countries (2000–2022), free of duplicates and regional aggregates, before any transformation — is achieved.

One informational (non-blocking) note: an untracked, misplaced 19MB installer file (`src/ingesta/data/DB.Browser.for.SQLite-v3.13.1-win64.msi`) should be cleaned up before it risks being committed accidentally, but it does not affect goal achievement or any requirement.

---

_Verified: 2026-07-11_
_Verifier: Claude (gsd-verifier)_
