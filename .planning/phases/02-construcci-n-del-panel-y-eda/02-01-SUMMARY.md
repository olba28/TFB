---
phase: 02-construcci-n-del-panel-y-eda
plan: 01
subsystem: data
tags: [pandas, sqlite, un-sdg-api, country-typology, panel-construction, idempotency]

# Dependency graph
requires:
  - phase: 01-ingesta-y-almacenamiento-versionado
    provides: raw_observations table, db.get_engine/rebuild_panel, countries.collect_countries/build_crosswalk/_normalize_code, manifest.write_manifest
provides:
  - "src/ingesta/typology.py: country region + LDC/LLDC/SIDS development-status reference data, ISO3-keyed"
  - "src/panel_build.py: 70%-of-years coverage filter (17/23), exclusion table, idempotent clean-panel build"
  - "data/panel.db tables: country_reference, panel_clean (4923 rows), panel_exclusions (529 pairs)"
  - "data/raw/country_reference.json + manifest (gitignored, regenerable) and country_reference_exclusion_log.json"
affects: [phase-02-plan-02-eda-notebook, phase-03-model1-panelols]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "M49-to-ISO3 crosswalk conversion as the single point where GeoArea/Tree-derived reference data joins raw_observations' ISO3 keys (mirrors countries.py's existing pattern, avoids repeating Phase 1's exact M49-vs-ISO3 landmine)"
    - "Full country x indicator cross-product coverage accounting via pandas MultiIndex.reindex(fill_value=0), so zero-row pairs are explicitly documented rather than silently absent"
    - "Exclusion/coverage status documented in a separate table (panel_exclusions), never by nulling real values in the clean panel itself"

key-files:
  created:
    - src/ingesta/typology.py
    - tests/ingesta/test_typology.py
    - src/panel_build.py
    - tests/test_panel_build.py
  modified: []

key-decisions:
  - "Tipología de país operationalized as UN development-status flags (is_ldc, is_lldc, is_sids) sourced from GeoArea/Tree itself, NOT World Bank income groups -- those nodes exist in the API but carry no country membership (verified live during planning)"
  - "panel_clean preserves every real reported value unmodified regardless of 70% coverage status; the exclusion decision lives entirely in the separate panel_exclusions table -- corrected during planning's adversarial self-check (see 02-01-PLAN.md Review Notes, fix #3) from an earlier data-destructive design"
  - "compute_coverage enumerates the full country x indicator cross-product (not just pairs present in raw_observations), so countries with zero rows for an indicator (e.g. most countries for 2.3.1) are explicitly documented as excluded, not silently absent"

patterns-established:
  - "build_region_map's recursive tree walk tolerates variable nesting depth (a country can sit directly under a region with no subregion, or under region->subregion) -- caught and fixed as a bug during implementation, before running any test, when tracing through the shallow-nesting case by hand"

requirements-completed: [PANEL-01, PANEL-02]

coverage:
  - id: D1
    description: "Country region + LDC/LLDC/SIDS development-status reference data captured once from GeoArea/Tree, converted to ISO3, persisted as JSON+manifest and a SQL table"
    requirement: "PANEL-01"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_typology.py (11 tests: shallow-nesting walk, dev-status default/single/multi-flag membership, ISO3 keying, crosswalk-exclusion logging)"
        status: pass
      - kind: integration
        ref: "python -m src.ingesta.typology live run against unstats.un.org/SDGAPI -- 248 countries persisted, checksum-consistent"
        status: pass
    human_judgment: false
  - id: D2
    description: "70%-of-years (17/23) coverage filter per (country, indicator) pair, full cross-product accounting, documented exclusion table"
    requirement: "PANEL-02"
    verification:
      - kind: unit
        ref: "tests/test_panel_build.py (10 tests: coverage counting, 17-year boundary, zero-row pairs, exclusion reasons, real-value preservation, idempotency)"
        status: pass
      - kind: integration
        ref: "python -m src.panel_build live run -- panel_clean=4923 rows (matches Phase 1's panel table exactly), panel_exclusions=529 pairs, >=150 countries excluded on indicator 2.3.1"
        status: pass
    human_judgment: false
  - id: D3
    description: "Panel-cleaning pipeline is idempotent (byte-identical output across two runs)"
    requirement: "PANEL-01"
    verification:
      - kind: unit
        ref: "tests/test_panel_build.py::test_idempotency"
        status: pass
      - kind: integration
        ref: "Live double-run of python -m src.panel_build against data/panel.db -- identical sha256 hash of sorted panel_clean before/after"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-12
status: complete
---

# Phase 02 Plan 01: Country Typology Capture + Idempotent Panel-Cleaning Pipeline Summary

**Captured UN development-status country typology (LDC/LLDC/SIDS, sourced entirely from GeoArea/Tree) and built an idempotent 70%-coverage-filtered clean panel (4,923 rows, matching Phase 1 exactly) that preserves every real observation unmodified while documenting 529 (country, indicator) exclusions separately**

## Performance

- **Duration:** ~25 min (commit span; includes RED/GREEN cycles for both tasks plus the live capture/rebuild run)
- **Completed:** 2026-07-12
- **Tasks:** 3/3 completed
- **Files modified:** 4 created (`src/ingesta/typology.py`, `tests/ingesta/test_typology.py`, `src/panel_build.py`, `tests/test_panel_build.py`) + 1 tracked manifest (`data/raw/country_reference.manifest.json`) + gitignored artifacts (`data/raw/country_reference.json`, `data/raw/country_reference_exclusion_log.json`, `data/panel.db`)

## Accomplishments

- `src/ingesta/typology.py`: recursive `GeoArea/Tree` walk building a region/subregion map (tolerating variable nesting depth) and LDC/LLDC/SIDS development-status flags, merged and converted from M49 to ISO3 via `countries.build_crosswalk()` — the single point where this new reference data joins `raw_observations`' ISO3-keyed schema.
- `src/panel_build.py`: full country × indicator cross-product coverage accounting (17-of-23-years threshold), an exclusion table distinguishing "no data at all" from "some data, still below threshold," and an idempotent `panel_clean` build that never modifies a real reported value based on coverage status.
- Live run: `country_reference` captured for 248 countries (16 excluded for missing M49 crosswalk entries — verified consistent with Phase 1's own already-shipped crosswalk-completeness behavior, not a new bug); `panel_clean` rebuilt with exactly 4,923 rows (matching Phase 1's `panel` table row count precisely — no whole-country drops); `panel_exclusions` documents 529 `(country, indicator)` pairs, including the expected large majority of countries excluded on indicator `2.3.1`.
- Idempotency verified both in an in-memory pytest test and live: re-running `python -m src.panel_build` against the real `data/panel.db` produced a byte-identical `panel_clean` (same sha256 hash of the sorted table).

## Task Commits

1. **Task 1 (RED): failing tests for country typology capture** - `a8ac89a` (test)
2. **Task 1 (GREEN): implement typology.py** - `cfb8eac` (feat)
3. **Task 2 (RED): failing tests for coverage filter + clean-panel build** - `e194041` (test)
4. **Task 2 (GREEN): implement panel_build.py** - `e4c1fe5` (feat)
5. **Task 3: live capture + live clean-panel rebuild** - `a7dbd76` (feat)

**Plan metadata:** committed as part of the final phase docs commit (with Plan 02-02).

## Files Created/Modified

- `src/ingesta/typology.py` - `SDG_REGION_ROOT_NAME`, `DEV_STATUS_ROOT_CODES`, `build_region_map()`, `build_development_status_flags()`, `build_country_reference()`, `capture_country_reference()`, `persist_country_reference()`, `persist_country_reference_to_db()`, `python -m src.ingesta.typology` CLI
- `tests/ingesta/test_typology.py` - 11 tests against an offline, hand-crafted multi-root `GeoArea/Tree` fixture
- `src/panel_build.py` - `INDICATOR_CODES`, `TOTAL_YEARS`, `YEARS_REQUIRED`, `compute_coverage()`, `build_exclusion_table()`, `build_clean_panel()`, `rebuild_clean_panel()`, `python -m src.panel_build` CLI
- `tests/test_panel_build.py` - 10 tests including coverage boundary (17 is NOT excluded), zero-row-pair accounting, and idempotency
- `data/raw/country_reference.manifest.json` - provenance sidecar (tracked; the JSON data file itself is gitignored, regenerable)
- `data/panel.db` - gains `country_reference`, `panel_clean`, `panel_exclusions` tables (gitignored, regenerable)

## Decisions Made

- Country typology = UN development-status flags (LDC/LLDC/SIDS), not World Bank income groups — verified live during planning that income-group nodes in `GeoArea/Tree` carry no country membership, so using them would require a second, non-UN data source (violates the project's single-data-source constraint).
- `panel_clean` never nulls real reported values based on coverage status — a correction made during planning's adversarial self-check (documented in `02-01-PLAN.md`'s Review Notes) from an earlier design that would have destroyed data needed for Phase 3's robustness-check requirement (MODEL1-05).
- `compute_coverage` enumerates the full country × indicator cross-product so zero-data pairs (e.g. most countries for indicator `2.3.1`) are explicitly documented, not silently absent from the exclusion accounting.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect region/subregion assignment in the first draft of `build_region_map`'s recursive walk**
- **Found during:** Task 1 implementation, before running any test (caught by manually tracing the shallow-nesting case)
- **Issue:** The initial implementation set `subregion = ancestors[-1]` unconditionally whenever any ancestors existed, which incorrectly assigned a country's own region name (e.g. "Africa" for Egypt, which has no subregion) to the `subregion` field instead of `None`.
- **Fix:** Reworked the branch logic to explicitly handle 3 cases: 2+ ancestors (`region=ancestors[-2]`, `subregion=ancestors[-1]`), exactly 1 ancestor (`region=ancestors[-1]`, `subregion=None`), and 0 ancestors (`region=None`, `subregion=None`).
- **Files modified:** `src/ingesta/typology.py`
- **Verification:** `tests/ingesta/test_typology.py::test_build_region_map_handles_shallow_nesting_country_directly_under_region` and `::test_build_region_map_records_region_and_subregion_when_both_present` both pass, asserting the exact expected dict for each case (not a permissive either/or).
- **Committed in:** `cfb8eac` (part of Task 1's GREEN commit)

**2. [Rule 1 - Bug] Corrected a test's assumption about `build_development_status_flags`'s contract**
- **Found during:** Task 1 GREEN run (first test execution)
- **Issue:** A test originally asserted that `build_development_status_flags` itself returns an explicit all-`False` record for a country absent from all 3 dev-status roots. The actual (and simpler, correct) design only records countries actually encountered while walking those roots — the "default to `False`, not absence" guarantee is properly enforced one layer up, at `build_country_reference`'s merge point, which has visibility into the full country universe via `collect_countries`.
- **Fix:** Split into two tests: one confirming `build_development_status_flags` legitimately omits an unmatched country (absence, at that layer), and one confirming `build_country_reference`'s merge produces the guaranteed all-`False` record for it.
- **Files modified:** `tests/ingesta/test_typology.py`
- **Verification:** Both tests pass; full suite green.
- **Committed in:** `cfb8eac` (part of Task 1's GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bug fixes caught during implementation/first test run, before any live data was touched). No scope creep — both fixes were necessary for correctness and are exactly the kind of edge case this plan's adversarial planning pass (02-01-PLAN.md Review Notes) had flagged as a risk worth testing for.

## Issues Encountered

None beyond the two deviations documented above.

## TDD Gate Compliance

Both Task 1 and Task 2 (marked `tdd="true"`) followed the RED → GREEN cycle: `test(...)` commits (`a8ac89a`, `e194041`) precede their corresponding `feat(...)` commits (`cfb8eac`, `e4c1fe5`) in git history, and each RED commit's test run was confirmed failing (`ImportError: cannot import name ... from 'src'`) before implementation began.

## User Setup Required

None — no external service configuration required. The live `GeoArea/Tree` capture used the same public, unauthenticated UN SDG API endpoint Phase 1 already depends on.

## Next Phase Readiness

- `panel_clean` (4,923 rows), `panel_exclusions` (529 documented exclusions), and `country_reference` (248 countries with region/typology data) are all in `data/panel.db`, ready for Plan 02-02's EDA notebook to consume.
- **Carried forward for Plan 02-02 and Phase 3:** because `panel_clean` is intentionally unfiltered (preserves all real data), any downstream consumer (the EDA notebook's missingness analysis, Phase 3's `panel_base.py`) that wants to honor the 70% coverage threshold must explicitly join against `panel_exclusions` — this plan makes the exclusion data available but does not pre-filter `panel_clean` itself (see 02-01-PLAN.md Review Notes' "Open items" section).
- No blockers for Plan 02-02.

## Self-Check: PASSED

- FOUND: src/ingesta/typology.py
- FOUND: tests/ingesta/test_typology.py
- FOUND: src/panel_build.py
- FOUND: tests/test_panel_build.py
- FOUND: data/raw/country_reference.manifest.json
- FOUND commit: a8ac89a
- FOUND commit: cfb8eac
- FOUND commit: e194041
- FOUND commit: e4c1fe5
- FOUND commit: a7dbd76

---
*Phase: 02-construcci-n-del-panel-y-eda*
*Completed: 2026-07-12*
