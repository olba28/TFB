---
phase: 01-ingesta-y-almacenamiento-versionado
plan: 03
subsystem: data-ingestion
tags: [m49, iso3, un-sdg-api, crosswalk, country-classification, csv]

# Dependency graph
requires:
  - phase: 01-ingesta-y-almacenamiento-versionado (plan 01-01)
    provides: .venv, requirements-dev.txt, pytest infrastructure, tests/fixtures/ convention
provides:
  - "src/ingesta/countries.py: collect_countries(), build_crosswalk(), filter_to_countries(), write_exclusion_log()"
  - "src/ingesta/data/m49_countries.csv + m49_countries.provenance.json (versioned, checksummed reference data)"
  - "Documented exclusion-log pattern reused by Phase 2's PANEL-02 exclusions table"
affects: [01-04, 01-05, phase-02-panel-eda]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-transform module (no network I/O) receiving pre-fetched tree JSON, mirroring manifest.py's file-I/O-only boundary"
    - "Exclusion-not-drop: every rejected code/row is logged with a reason, never silently discarded (D-16)"
    - "Objective type=='Country' inclusion rule with zero hardcoded exception lists (D-14)"

key-files:
  created:
    - src/ingesta/countries.py
    - src/ingesta/data/m49_countries.csv
    - src/ingesta/data/m49_countries.provenance.json
    - tests/ingesta/test_countries.py
    - tests/fixtures/geoarea_tree_sample.json
  modified:
    - .gitignore

key-decisions:
  - "M49 CSV crosswalk keyed on the CSV's 'M49 Code' column (per-country code), not 'Global Code' (always '001'/World) -- verified against the actual acquired file"
  - "filter_to_countries() takes (rows, countries, crosswalk) rather than (rows) alone -- the join requires both the GeoArea/Tree-derived country set and the CSV crosswalk, which the plan's artifact line abbreviated"
  - "collect_countries() accepts an optional excluded: list mutated in place, keeping the -> dict[str,str] return type while still exposing the D-16 exclusion log to callers/tests"
  - "Renamed src/ingesta/Data/ (capital D, created by the acquisition step) to lowercase src/ingesta/data/ to match the plan path and repo naming convention"

patterns-established:
  - "Reference/static data files live under src/ingesta/data/ with a *.provenance.json sidecar (source URL, download date, checksum) for one-time manual acquisitions -- distinct from manifest.py's per-fetch API manifest schema"

requirements-completed: [INGEST-03]

coverage:
  - id: D1
    description: "collect_countries() keeps only GeoArea/Tree type=='Country' leaves and logs every excluded aggregate with its parent name"
    requirement: "INGEST-03"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_collect_countries_returns_only_country_leaves"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_collect_countries_logs_all_aggregates_with_parent_names"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_collect_countries_dedupes_same_country_under_two_parents"
        status: pass
    human_judgment: false
  - id: D2
    description: "build_crosswalk() resolves the M49->ISO3 crosswalk from the acquired official M49 CSV (UN's own classification, not pycountry/World Bank)"
    requirement: "INGEST-03"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_build_crosswalk_resolves_known_sample_spain"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_build_crosswalk_resolves_multiple_known_samples"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_module_does_not_import_pycountry_or_world_bank_lists"
        status: pass
    human_judgment: false
  - id: D3
    description: "filter_to_countries() joins observation rows to the canonical set + crosswalk, tags ISO3, and logs (not silently drops) rows that fail either the country-leaf test or the crosswalk lookup, including the D-14 disputed-territory case"
    requirement: "INGEST-03"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_filter_to_countries_keeps_rows_that_resolve_to_country_leaf"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_filter_to_countries_drops_rows_not_a_country_leaf"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_filter_to_countries_logs_country_leaf_missing_from_crosswalk"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_filter_to_countries_disputed_territory_kept_iff_type_country"
        status: pass
    human_judgment: false
  - id: D4
    description: "write_exclusion_log() persists the exclusion log to a real file, never stdout"
    requirement: "INGEST-03"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_countries.py#test_write_exclusion_log_persists_to_file"
        status: pass
    human_judgment: false
  - id: D5
    description: "Official M49 classification CSV acquired (human-verified, one-time manual download) and versioned with a provenance sidecar (source URL, download date, checksum)"
    requirement: "INGEST-03"
    verification:
      - kind: manual_procedural
        ref: "src/ingesta/data/m49_countries.csv (248 rows) + src/ingesta/data/m49_countries.provenance.json"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-07-11
status: complete
---

# Phase 1 Plan 3: M49 Country Classification & ISO3 Crosswalk Summary

**Reusable `countries.py` module (M49 canonical country list, M49-to-ISO3 crosswalk, documented exclusion log) built against the human-acquired official UN M49 CSV, satisfying INGEST-03's "no regional aggregate leaks into the panel" requirement.**

## Performance

- **Duration:** ~30 min (continuation run; prior executor session had already reached and stopped at the Task 1 checkpoint)
- **Completed:** 2026-07-11
- **Tasks:** 2 (Task 1: acquire M49 CSV [human-action checkpoint, completed by user before this session]; Task 2: countries.py + tests)
- **Files modified:** 6 (2 created in Task 1's commit, 4 in Task 2's commit -- see Task Commits)

## Accomplishments
- Generated `src/ingesta/data/m49_countries.provenance.json` from the CSV the user placed on disk (real sha256 checksum, source URL, download date, delimiter/encoding metadata), mirroring `manifest.py`'s D-08 pattern adapted for a one-time static file
- `collect_countries()`: walks a `GeoArea/Tree`-shaped node list, keeps only `type=='Country'` leaves, dedupes repeated countries across multiple parent groupings, and logs every excluded aggregate (region/other) with its parent name via an optional mutable `excluded` list
- `build_crosswalk()`: loads the real acquired M49 CSV (semicolon-delimited, UTF-8 BOM) into `{m49_code: iso3}`, keyed on the CSV's per-country `M49 Code` column (not the always-`001` `Global Code` column)
- `filter_to_countries()`: joins observation rows against the canonical country set + crosswalk, tags kept rows with `iso3`, and logs excluded rows with an explicit reason (`not_a_country_leaf` or `missing_from_m49_crosswalk`) instead of silently dropping them
- `write_exclusion_log()`: persists the exclusion log to a real file (D-16)
- D-14 (disputed territories) operationalized as an objective `type=='Country'` rule with zero hardcoded exception list -- verified with a synthetic Kosovo fixture case
- 13 new unit tests, 100% statement coverage of `countries.py`; crosswalk tests resolve against the real acquired CSV (Spain 724→ESP, Egypt 818→EGY, Kenya 404→KEN)

## Task Commits

Each task was committed atomically:

1. **Task 1: Acquire the official M49 classification CSV (one-time)** - `991ad2a` (feat) -- CSV + generated provenance.json, plus the `Data/`→`data/` case-fix deviation
2. **Task 2: countries.py — canonical list, ISO3 crosswalk, exclusion log** - `c2e0151` (feat) -- module, tests, fixture, plus the `.gitignore` `.coverage` fix deviation

**Plan metadata:** (pending -- final commit below)

## Files Created/Modified
- `src/ingesta/data/m49_countries.csv` - Official UN M49 classification table (248 country rows), human-acquired
- `src/ingesta/data/m49_countries.provenance.json` - Source URL, download date, checksum, row count for the CSV above
- `src/ingesta/countries.py` - `collect_countries()`, `build_crosswalk()`, `filter_to_countries()`, `write_exclusion_log()`
- `tests/ingesta/test_countries.py` - 13 tests covering leaf-only collection, exclusion logging, dedup, crosswalk resolution, D-14 disputed-territory rule, and the D-13 pycountry/World-Bank anti-pattern guard
- `tests/fixtures/geoarea_tree_sample.json` - Synthetic `GeoArea/Tree`-shaped tree (mixed Country/Region/Other nodes, a country duplicated under two parents, a disputed-territory leaf)
- `.gitignore` - Added `.coverage`/`.coverage.*`/`htmlcov/`/`.pytest_cache/` (generated by the `pytest --cov` verification run, was left untracked)

## Decisions Made
- **M49 CSV column choice:** crosswalk keys off the CSV's `M49 Code` column (the country's own numeric code), not `Global Code` (always `001`/"World" -- a grouping column, not a country code). Verified directly against the acquired file before writing `build_crosswalk()`.
- **`filter_to_countries()` signature:** implemented as `(rows, countries, crosswalk)` rather than `(rows)` alone as abbreviated in the plan's artifact line -- the join is impossible without both the `GeoArea/Tree`-derived country set and the M49 crosswalk dict, and the module is explicitly a pure transform with no network access to derive them internally. `filter_to_countries` and `write_exclusion_log`'s other signatures match the plan exactly.
- **Exclusion-log exposure from `collect_countries()`:** kept the plan's literal `-> dict[str,str]` return type by adding an optional `excluded: list[dict] | None` parameter that the function mutates in place when provided, rather than changing the return type to a tuple.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed `src/ingesta/Data/` → `src/ingesta/data/` directory case mismatch**
- **Found during:** Task 1 (continuation start, before writing provenance.json)
- **Issue:** The download/save step the user performed created the folder as `Data` (capital D) on Windows' case-insensitive filesystem. `git status`/`git ls-files` confirmed the tracked path would have been `src/ingesta/Data/m49_countries.csv`, not the plan's specified lowercase `src/ingesta/data/m49_countries.csv` -- a mismatch that reads fine on Windows but would break `import` paths and file lookups on case-sensitive systems (Linux CI, grading environment) and doesn't match the project's `lowercase_with_underscores` naming convention.
- **Fix:** Renamed via a safe two-step move (`Data` → temp name → `data`) to work around case-insensitive-filesystem rename semantics; no file content changed.
- **Files modified:** `src/ingesta/data/m49_countries.csv` (path only)
- **Verification:** `ls src/ingesta/` shows lowercase `data/`; `find -iname` confirms a single copy of the CSV at the correct path.
- **Committed in:** `991ad2a` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Generated `m49_countries.provenance.json`**
- **Found during:** Task 1 (continuation start)
- **Issue:** The plan's Task 1 required the user to create this file by hand, but per the "if Claude can automate it, Claude does it" rule (and the orchestrator's explicit instruction for this continuation), computing a real sha256 checksum and recording metadata is exactly the kind of thing that should not be hand-written.
- **Fix:** Computed the real sha256 of the acquired CSV, counted its data rows via `csv.DictReader`, and wrote `m49_countries.provenance.json` mirroring `manifest.py`'s D-08 field shape (adapted: `source_url`/`download_date`/`file`/`delimiter`/`encoding`/`row_count`/`checksum`/`notes` instead of the per-indicator API schema).
- **Files modified:** `src/ingesta/data/m49_countries.provenance.json`
- **Verification:** JSON is valid; `checksum` field matches `hashlib.sha256(...).hexdigest()` recomputed independently during this session.
- **Committed in:** `991ad2a` (Task 1 commit)

**3. [Rule 3 - Blocking] Added `.coverage`/`.pytest_cache/`/`htmlcov/` to `.gitignore`**
- **Found during:** Task 2, after running `pytest --cov=src --cov-report=term-missing` per the plan's verification step
- **Issue:** Running the coverage command left a `.coverage` file untracked in `git status`; per the executor's task-commit protocol, generated files must never be left untracked (either committed if intentional, or gitignored if generated/runtime output).
- **Fix:** Added the standard coverage/pytest-cache ignore patterns to `.gitignore` and removed the generated `.coverage` file from the working tree.
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` shows no untracked coverage artifacts after the fix.
- **Committed in:** `c2e0151` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking path-case fix, 1 missing-critical-functionality automation, 1 blocking repo-hygiene fix)
**Impact on plan:** All three were necessary for correctness/reproducibility (case-sensitive path portability, a required provenance artifact that would otherwise not exist, and clean repo state). No scope creep -- `countries.py`'s public API matches the plan's four named functions (with the noted, functionally-necessary signature expansion on `filter_to_countries`).

## Issues Encountered

The CSV column layout was confirmed to be **semicolon-delimited**, UTF-8 with a BOM (not comma-delimited as a naive reading of the plan's prose might suggest, though the plan itself did not assert a specific delimiter). `build_crosswalk()` was written directly against the verified real layout (`csv.DictReader(f, delimiter=";")`, `encoding="utf-8-sig"`) from the start, so no rework was needed -- flagged here per the orchestrator's instruction to note the actual column layout, but this was not a deviation since the plan left the exact CSV shape for verification during implementation rather than asserting comma-delimiting.

## User Setup Required

None - the one manual step (Task 1's M49 CSV download) was already completed by the user before this session started; this session only generated the provenance sidecar and implemented Task 2.

## Next Phase Readiness

- `src/ingesta/countries.py` is ready for Phase 1 Plan 5 (`fetch_data.py` orchestrator) to import and call `collect_countries()` / `build_crosswalk()` / `filter_to_countries()` / `write_exclusion_log()` against the live `GeoArea/Tree` response and real indicator rows.
- The exclusion-log pattern established here (log-with-reason, never silently drop) is the documented precedent Phase 2's PANEL-02 exclusions table is expected to reuse.
- No blockers. One open follow-up for Plan 05 (not a blocker for this plan): confirm the real `GeoArea/Tree` API's `geoAreaCode` string format (zero-padded vs not) matches the M49 CSV's zero-padded 3-digit `M49 Code` format exactly -- if they differ, `filter_to_countries()` will correctly route affected rows to the `missing_from_m49_crosswalk` exclusion reason rather than fail silently, but the crosswalk's effective coverage should be spot-checked against a live tree fetch once `client.py`'s `GeoArea/Tree` call exists.

---
*Phase: 01-ingesta-y-almacenamiento-versionado*
*Completed: 2026-07-11*
