---
phase: 01-ingesta-y-almacenamiento-versionado
reviewed: 2026-07-11T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/db.py
  - src/ingesta/__init__.py
  - src/ingesta/client.py
  - src/ingesta/countries.py
  - src/ingesta/data/m49_countries.csv
  - src/ingesta/data/m49_countries.provenance.json
  - src/ingesta/fetch_data.py
  - src/ingesta/manifest.py
  - tests/__init__.py
  - tests/conftest.py
  - tests/fixtures/.gitkeep
  - tests/fixtures/geoarea_tree_sample.json
  - tests/fixtures/indicator_dimension_samples.json
  - tests/fixtures/mock_500_then_paginated.json
  - tests/ingesta/__init__.py
  - tests/ingesta/test_client.py
  - tests/ingesta/test_countries.py
  - tests/ingesta/test_db.py
  - tests/ingesta/test_fetch_data.py
  - tests/ingesta/test_manifest.py
findings:
  critical: 2
  warning: 4
  info: 1
  total: 7
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 15 source files (+ 5 empty/placeholder `__init__.py`/`.gitkeep` files, reviewed and confirmed intentionally empty)
**Status:** issues_found

## Summary

Reviewed the Phase 1 ingestion/storage pipeline: the UN SDG API client (`client.py`), the M49 country crosswalk and exclusion logic (`countries.py`), the SQLite storage layer (`db.py`), the provenance manifest reader/writer (`manifest.py`), and the orchestrator (`fetch_data.py`) that composes all four, plus their test suites. All 46 existing tests pass (`.venv/Scripts/python.exe -m pytest tests/ -q`), and the M49 CSV's provenance checksum/row-count were independently verified against the file on disk (match).

The module-level docstrings are unusually rigorous about documented decisions (D-01 through D-16) and several genuine historical pitfalls (integer vs. zero-padded country codes, the 2.3.1 dual-series multiplex) are correctly guarded against with dedicated tests. However, the orchestrator (`run_ingestion`) has two data-integrity gaps in its partial-failure and partial-refetch paths that are not exercised by any existing test — both are classified as blockers because they lead to silent, hard-to-detect gaps in the very dataset this project's econometric conclusions will be built on. There are also a few robustness/quality warnings around use of `assert` for production-critical guards and a pagination bound that is re-read every page contrary to its own docstring.

## Critical Issues

### CR-01: Manifest is written before data is validated/inserted, so a mid-pipeline failure permanently and silently skips that indicator on every future run

**File:** `src/ingesta/fetch_data.py:172-195`
**Issue:**
In `run_ingestion`, for each indicator the raw JSON file and its provenance manifest are written to disk (lines 174-186) *before* `filter_headline_rows` (line 188, can raise `AssertionError` if zero rows survive the dimension filter) and `db.insert_observations` (line 195, can raise `AssertionError` on an internal duplicate key or `sqlalchemy`/`pandas` `DatabaseError` on a cross-call `UNIQUE` violation) run. Neither call is wrapped in `try/except`, so either exception propagates straight out of `run_ingestion` and aborts the whole run.

The idempotency check that decides whether to (re-)fetch an indicator, `manifest.manifest_exists()` (`src/ingesta/manifest.py:63-74`), only checks that the raw JSON file and its sidecar manifest exist on disk — it has no way to know whether that indicator's rows were ever actually inserted into `raw_observations`. Because the raw file + manifest are written *before* the code that can fail, a failure on line 188 or 195 leaves exactly the artifacts `manifest_exists()` checks for, while `raw_observations` never receives a single row for that indicator.

On the next invocation of `run_ingestion(force=False)` (the normal, no-argument entry point — see `if __name__ == "__main__": run_ingestion()` at line 202), `manifest.manifest_exists(indicator_code, today)` returns `True` for the broken indicator and the per-indicator loop `continue`s past it (line 169-170) without ever retrying. The indicator is now silently and permanently missing from `raw_observations` for that day, with no error, warning, or log message anywhere — the only way to notice is to manually cross-check `raw_observations` row counts against the 5 expected indicators, and the only way to recover is `force=True`, which expensively re-fetches *all 5* indicators (not just the broken one).

Given this project's core value proposition is "a reproducible pipeline ... that demonstrates, with data abiertos y trazables, the relación cuantitativa" for a thesis defended before a tribunal, a silently-incomplete `raw_observations` table is a direct data-loss/data-integrity risk to the final econometric results.

**Fix:** Only write the manifest after the row has been successfully filtered and inserted (or track fetch-vs-ingest state separately, e.g. write the manifest but check `raw_observations` row presence — not just file presence — before deciding to skip). Minimal fix:
```python
rows = client.fetch_all_pages(session, indicator_code)

raw_path = manifest.RAW_DATA_ROOT / indicator_code / f"{today}.json"
raw_path.parent.mkdir(parents=True, exist_ok=True)
raw_path.write_text(json.dumps({"data": rows}, ensure_ascii=False), encoding="utf-8")

# Do the parts that can raise BEFORE writing the manifest that gates future re-fetches.
filtered = filter_headline_rows(rows, indicator_code)
kept, row_excluded = countries.filter_to_countries(filtered, country_set, crosswalk)
all_excluded.extend(row_excluded)

df = _build_observations_df(kept, indicator_code, source_manifest_id=f"{indicator_code}:{today}")
db.insert_observations(engine, df)

# Only now, once the data has actually landed in raw_observations, record success.
manifest.write_manifest(
    raw_path,
    url=client.API_BASE_URL,
    params={"indicator": indicator_code, "timePeriod": f"{client.YEAR_START}-{client.YEAR_END}"},
    row_count=len(rows),
)
```

### CR-02: Exclusion log is unconditionally overwritten with only the current run's processed indicators, silently destroying previously-documented exclusions on a partial re-run

**File:** `src/ingesta/fetch_data.py:47, 168-197`
**Issue:**
`EXCLUSION_LOG_PATH = Path("data/raw/exclusion_log.json")` (line 47) is a single fixed path — unlike the raw data/manifest files, it carries no date component, so every successful call to `run_ingestion` fully overwrites it (`countries.write_exclusion_log` → `path.write_text(...)`, `src/ingesta/countries.py:145-150`).

`all_excluded` (line 166) is seeded only with `tree_excluded` (the `GeoArea/Tree` non-country nodes, always recomputed) and then extended, per indicator, only for indicators that are *actually processed this run* — indicators skipped via the `continue` at line 169-170 (because their manifest already exists and `force=False`) never contribute their `row_excluded` entries to `all_excluded` this run, because `countries.filter_to_countries` is never called for them.

Concretely: run A fetches all 5 indicators and writes `exclusion_log.json` containing tree exclusions + row exclusions for all 5. The next day, run B is invoked and only indicator `8.2.1` lacks today's manifest (the other 4 already have one from run A, or from a manual partial re-run); `needs_fetch` is `True` (line 157-159) so the whole pipeline proceeds, but the loop `continue`s past the 4 already-fetched indicators and only computes `row_excluded` for `8.2.1`. At line 197, `countries.write_exclusion_log(all_excluded, EXCLUSION_LOG_PATH)` unconditionally overwrites `data/raw/exclusion_log.json` with just `tree_excluded + 8.2.1`'s exclusions — permanently discarding the previously-documented row-level exclusions for the other 4 indicators. This directly contradicts the module's own stated invariant (D-16, `src/ingesta/countries.py:18-20`): "every excluded code ... is recorded in a documented exclusion log -- never silently dropped." No test exercises this partial-refetch scenario (`test_run_ingestion_skips_fetch_when_manifest_exists_for_all_indicators` only covers the full-skip case, `test_run_ingestion_force_true_refetches_even_when_manifest_exists` only covers the full-refetch case).
**Fix:** Either (a) accumulate exclusions per-indicator into per-indicator/per-date sidecar files (mirroring the `data/raw/{indicator}/{date}.json` convention) and merge them at read time, or (b) load any existing `exclusion_log.json`, merge the current run's `all_excluded` into it keyed by code, and write the merged result instead of a blind overwrite:
```python
existing = []
if EXCLUSION_LOG_PATH.exists():
    existing = json.loads(EXCLUSION_LOG_PATH.read_text(encoding="utf-8"))
merged = {(e["code"], e.get("exclusion_reason")): e for e in existing}
merged.update({(e["code"], e.get("exclusion_reason")): e for e in all_excluded})
countries.write_exclusion_log(list(merged.values()), EXCLUSION_LOG_PATH)
```

## Warnings

### WR-01: Critical data-integrity guards rely on bare `assert`, which is silently stripped under `python -O` / `PYTHONOPTIMIZE`

**File:** `src/ingesta/fetch_data.py:101`, `src/db.py:70-74`
**Issue:** `filter_headline_rows`'s "no rows survived the dimension filter" guard (line 101) and `insert_observations`'s pre-insert duplicate-key guard (`src/db.py:70-74`) are both implemented as bare `assert` statements. The module docstrings explicitly frame these as safety nets against real historical incidents (the zero-surviving-rows bug documented in `src/ingesta/countries.py:29-31`, and the "belt-and-suspenders" duplicate check in `src/db.py:3-9`). Both are removed entirely if the code is ever invoked with Python's `-O`/`-OO` flags or `PYTHONOPTIMIZE=1` (a fully standard, supported way to run Python) — at which point `filter_headline_rows` can silently return an empty list instead of raising, and `insert_observations`'s DataFrame-internal duplicate check disappears (the DB-level `UNIQUE` constraint remains as a fallback for `insert_observations`, but `filter_headline_rows` then has no fallback of any kind).
**Fix:** Replace both with explicit `if ...: raise ValueError(...)` (or a custom exception), which cannot be optimized away:
```python
if len(filtered) == 0:
    raise ValueError(f"No rows survived dimension filter for {indicator_code}")
```

### WR-02: `fetch_all_pages`'s `total_pages` is re-read from every page's response, contradicting its own docstring and risking silent premature truncation

**File:** `src/ingesta/client.py:76-104` (specifically line 98)
**Issue:** The docstring states `totalPages` "is read fresh from the FIRST response of THIS indicator and the loop continues until that many pages have been fetched" (lines 68-71), but the implementation reassigns `total_pages = body["totalPages"]` (line 98) on *every* page's response, not just the first. If any page after the first reports a smaller `totalPages` than the initial response (a plausible transient API inconsistency, since nothing in this codebase validates that the value is stable across pages), the `while page <= total_pages` loop (line 80) would terminate early, silently dropping the remaining pages' rows with no error or warning — the exact class of silent data-loss bug (Pitfall 4) this function's docstring says it's designed to avoid.
**Fix:** Capture `total_pages` once, from the first response only, and never overwrite it afterward:
```python
if page == 1:
    total_pages = body["totalPages"]
```

### WR-03: `write_manifest`'s `date` field is derived independently of the raw file's own date, rather than from it

**File:** `src/ingesta/manifest.py:35-55` (specifically line 48)
**Issue:** `write_manifest` populates the manifest's `"date"` field with a fresh `date.today().isoformat()` call (line 48), even though the raw file it is describing already carries its download date encoded in its filename (`data/raw/{indicator}/{date}.json`, per D-06) and is always constructed by the caller from that same `today` value (`src/ingesta/fetch_data.py:152, 174`). The two are only guaranteed consistent because the caller happens to invoke `write_manifest` in the same process, same day, right after building `raw_path` from an already-captured `today` variable. There is no structural guarantee of consistency (e.g. a manifest re-written near a midnight UTC/local boundary, or `write_manifest` called for an older raw file during a backfill/repair script, would silently record the *wrong* date), and the "five exact fields" (D-08) documented as the manifest's contract include `date` as an independent field rather than one derived from — and therefore always consistent with — the artifact it documents.
**Fix:** Derive `date` from `raw_path`'s own filename stem instead of calling `date.today()` again:
```python
manifest_data = {
    "date": raw_path.stem,  # raw_path is always data/raw/{indicator}/{YYYY-MM-DD}.json
    ...
}
```

### WR-04: No loud-failure guard when `filter_to_countries` excludes every row for an indicator

**File:** `src/ingesta/fetch_data.py:188-195`
**Issue:** `filter_headline_rows` has an explicit "raise if zero rows survive" guard (line 101) precisely because a silent all-rows-dropped scenario previously caused a live incident (documented in `src/ingesta/countries.py:29-31`). No equivalent check exists after `countries.filter_to_countries(filtered, country_set, crosswalk)` (line 189): if every row for an indicator fails the country-leaf/crosswalk join (e.g. a `GeoArea/Tree` fetch anomaly, or a crosswalk/tree mismatch affecting this indicator's countries specifically), `kept` is `[]`, `_build_observations_df` builds an empty (but structurally valid) DataFrame, and `db.insert_observations` happily inserts zero rows with no error — the indicator's manifest is (per CR-01) still marked as fetched, so this failure mode is both silent and permanent.
**Fix:** Add a symmetrical guard after the country filter:
```python
kept, row_excluded = countries.filter_to_countries(filtered, country_set, crosswalk)
if len(kept) == 0:
    raise ValueError(f"No rows survived country/crosswalk filter for {indicator_code}")
```

## Info

### IN-01: `timeout=30` duplicated as a magic number across two files

**File:** `src/ingesta/client.py:87`, `src/ingesta/fetch_data.py:134`
**Issue:** The HTTP request timeout (30 seconds) is hardcoded identically in `client.fetch_all_pages` and `fetch_data._fetch_country_reference`, with no shared constant.
**Fix:** Extract a shared `REQUEST_TIMEOUT_SECONDS = 30` constant in `client.py` and import/reuse it in `fetch_data.py`.

---

_Reviewed: 2026-07-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
