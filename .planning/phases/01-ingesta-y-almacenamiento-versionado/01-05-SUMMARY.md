---
phase: 01-ingesta-y-almacenamiento-versionado
plan: 05
subsystem: ingesta
tags: [requests, pandas, sqlite, un-sdg-api, orchestration]

# Dependency graph
requires:
  - phase: 01-02
    provides: build_session/fetch_all_pages (HTTP client with retry/pagination), write_manifest/manifest_exists (provenance)
  - phase: 01-03
    provides: collect_countries/build_crosswalk/filter_to_countries (M49→ISO3 crosswalk, region exclusion)
  - phase: 01-04
    provides: get_engine/init_db/insert_observations/rebuild_panel (SQLite storage layer)
provides:
  - "src/ingesta/fetch_data.py: HEADLINE_DIMENSIONS, HEADLINE_SERIES, filter_headline_rows(), run_ingestion(force=False), CLI entry"
  - "Live-ingested dataset: data/raw/{6.4.2,6.4.1,8.1.1,8.2.1,2.3.1}/2026-07-11.json + .manifest.json"
  - "Populated data/panel.db: raw_observations (18086 rows) + panel (4923 rows)"
  - "data/raw/exclusion_log.json (D-16 dropped M49 aggregates)"
affects: [phase-02-panel-eda, phase-06-model2-agricultura]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-indicator HEADLINE_DIMENSIONS + HEADLINE_SERIES filter table, never a global dimension rule (Pitfall 1 + multiplexed-series discovery)"
    - "geoAreaCode normalization via _normalize_code() (str(code).zfill(3)) at every join boundary (GeoArea/Tree int, Indicator/Data un-padded string, M49 CSV zero-padded string)"
    - "D-07 idempotency: manifest_exists() short-circuits re-fetch per indicator unless force=True"

key-files:
  created: [src/ingesta/fetch_data.py, tests/ingesta/test_fetch_data.py, tests/fixtures/indicator_dimension_samples.json]
  modified: [src/ingesta/countries.py, tests/ingesta/test_countries.py]

key-decisions:
  - "Adopted PD_AGR_SSFP (small-scale food producers) as indicator 2.3.1's headline series over PD_AGR_LSFP (large-scale) — SDG target 2.3 explicitly names small-scale food producers as its focus; approved by user at Task 3 checkpoint"
  - "geoAreaCode normalized to zero-padded 3-digit string at every source (GeoArea/Tree, Indicator/Data, M49 CSV) via _normalize_code(), discovered live when the unnormalized join zeroed out all 5 indicators on first run"

patterns-established:
  - "Any new indicator dimension/series ambiguity is resolved via an explicit lookup table (HEADLINE_DIMENSIONS / HEADLINE_SERIES) with a loud-failure assert, never silent dropping"

requirements-completed: [INGEST-01, INGEST-02, INGEST-04]

coverage:
  - id: D1
    description: "Per-indicator dimension filter (HEADLINE_DIMENSIONS) yields exactly one row per (country, year) for all 5 indicators; global Activity:TOTAL rule regression-guarded"
    requirement: "INGEST-02"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_fetch_data.py#test_filter_headline_rows (all 5 indicators)"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_fetch_data.py#test_filter_headline_rows_asserts_on_zero_survivors"
        status: pass
    human_judgment: false
  - id: D2
    description: "Value parsing coerces the literal string 'NaN' (2.3.1) to float NaN via pd.to_numeric(errors='coerce') instead of raising"
    requirement: "INGEST-02"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_fetch_data.py#test_value_coercion_handles_nan_string"
        status: pass
    human_judgment: false
  - id: D3
    description: "run_ingestion() orchestrates client -> manifest -> filter -> countries -> db.insert_observations -> db.rebuild_panel end-to-end, skipping re-fetch when manifest exists (D-07)"
    requirement: "INGEST-01"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_fetch_data.py#test_run_ingestion_skips_when_manifest_exists"
        status: pass
    human_judgment: false
  - id: D4
    description: "Live ingestion of all 5 indicators (2000-2022) into versioned raw JSON + manifests and a populated data/panel.db, with plausible country counts, no M49 leakage, and documented 2.3.1 coverage caveat"
    requirement: "INGEST-01"
    verification:
      - kind: manual_procedural
        ref: "Task 3 checkpoint:human-verify — user typed 'approved'"
        status: pass
    human_judgment: true
    rationale: "Live dataset shape/coverage and the 2.3.1 small-scale-vs-large-scale series methodological choice require human sign-off, not just automated assertions"

# Metrics
duration: 45min
completed: 2026-07-11
status: complete
---

# Phase 01 Plan 05: Ingestion Orchestrator + Live Data Load Summary

**`fetch_data.py` orchestrator composing the client/manifest/countries/db modules with a per-indicator dimension+series filter, live-run into `data/panel.db` (18,086 raw_observations rows, 4,923 panel rows, 215 countries, zero M49 leakage), approved by the user at the Task 3 checkpoint.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-11
- **Tasks:** 3/3 completed (Task 3 was a checkpoint:human-verify, now approved)
- **Files modified:** 5 (3 created: `src/ingesta/fetch_data.py`, `tests/ingesta/test_fetch_data.py`, `tests/fixtures/indicator_dimension_samples.json`; 2 modified: `src/ingesta/countries.py`, `tests/ingesta/test_countries.py`)

## Accomplishments

- `fetch_data.py` orchestrates all Wave 2 modules end-to-end: manifest-existence check (D-07 skip) → `fetch_all_pages` → raw JSON + manifest write → per-indicator `filter_headline_rows` (HEADLINE_DIMENSIONS + HEADLINE_SERIES, loud-failure assert on zero survivors) → `pd.to_numeric(errors='coerce')` value parsing (handles 2.3.1's literal `"NaN"` string) → geoAreaCode-normalized country filter → `insert_observations` → `rebuild_panel`
- Live ingestion run against `unstats.un.org/SDGAPI/v1/sdg` completed for all 5 indicators (6.4.2, 6.4.1, 8.1.1, 8.2.1, 2.3.1), 2000–2022: `data/raw/{indicator}/2026-07-11.json` + `.manifest.json` for each, `data/raw/exclusion_log.json` recording dropped M49 aggregates
- `data/panel.db` populated: `raw_observations` = 18,086 rows (unique per country/year/indicator, verified `COUNT == COUNT DISTINCT`), `panel` = 4,923 rows (one per country-year), 215 distinct ISO3 country codes, no M49 region/aggregate leakage
- D-07 idempotency verified live: a second same-day run completed in ~1.4s with no re-fetch and no row-count change
- Per-indicator row counts (raw_observations): 6.4.2=4186 (4041 non-null, 182 countries), 6.4.1=3910 (3530 non-null, 170 countries), 8.1.1=4790 (4790 non-null, 210 countries), 8.2.1=4300 (4300 non-null, 187 countries), 2.3.1=900 (173 non-null, 50 countries)

## Task Commits

1. **Task 1: fetch_data.py orchestrator with per-indicator dimension filter (RED)** - `a564065` (test)
2. **Task 1: fetch_data.py orchestrator with per-indicator dimension filter (GREEN)** - `4c9cca6` (feat)
3. **Task 1 deviation fix: geoAreaCode normalization** - `f55be2d` (fix)
4. **Task 1 deviation fix: 2.3.1 series disambiguation** - `4bca7d6` (fix)
5. **Task 2: Execute the live ingestion run and rebuild the panel** - `5ef9d29` (feat)
6. **Task 3: Confirm the ingested dataset against all 5 success criteria** - checkpoint:human-verify, user responded "approved" (no code commit; verification-only task)

**Plan metadata:** (this commit, docs) — see final commit below.

_Note: the two `fix` commits were discovered live during Task 2's ingestion run and applied before the run could succeed cleanly, so they land chronologically between Task 1's GREEN commit and Task 2's live-run commit._

## Files Created/Modified

- `src/ingesta/fetch_data.py` - `HEADLINE_DIMENSIONS`, `HEADLINE_SERIES`, `filter_headline_rows()`, `run_ingestion(force=False)`, `python -m src.ingesta.fetch_data` CLI entry
- `tests/ingesta/test_fetch_data.py` - 14 tests: per-indicator filter (all 5), Pitfall 1 loud-failure + regression guard, Pitfall 5 NaN-string coercion, D-07 idempotency skip/force-refetch
- `tests/fixtures/indicator_dimension_samples.json` - per-indicator multi-dimension samples matching live-verified API shapes
- `src/ingesta/countries.py` - added `_normalize_code()` (zero-pads geoAreaCode to 3 digits), applied in `collect_countries()` and `filter_to_countries()`
- `tests/ingesta/test_countries.py` - regression tests for int tree codes and un-padded string indicator codes joining against zero-padded M49 keys
- `data/raw/{6.4.2,6.4.1,8.1.1,8.2.1,2.3.1}/2026-07-11.json` + `.manifest.json` - live raw data + provenance (gitignored, regenerable)
- `data/raw/exclusion_log.json` - D-16 dropped M49 aggregates (gitignored, regenerable)
- `data/panel.db` - populated `raw_observations` + `panel` tables (gitignored, regenerable)

## Decisions Made

- **2.3.1 headline series = `PD_AGR_SSFP` (small-scale food producers):** indicator 2.3.1 carries two series (`PD_AGR_SSFP` and `PD_AGR_LSFP`) multiplexed under the identical headline dimension combo (Sex:BOTHSEX, Reporting Type:G), which is not distinguishable by `HEADLINE_DIMENSIONS` alone. Added `HEADLINE_SERIES` as a second per-indicator lookup applied alongside dimension filtering. SDG target 2.3 explicitly names small-scale food producers as its focus, so `PD_AGR_SSFP` was adopted and `PD_AGR_LSFP` dropped. **User-approved** at the Task 3 checkpoint, along with the resulting coverage caveat (50 countries, 173/900 non-null values) — noted for Phase 6 (Model 2) scope planning.
- **geoAreaCode normalization at every join boundary:** `GeoArea/Tree` serializes `geoAreaCode` as a bare JSON integer, `Indicator/Data` as an un-padded numeric string, and the M49 CSV crosswalk uses zero-padded 3-digit strings. `_normalize_code()` (`str(code).zfill(3)`) is applied at both write (`collect_countries()`) and read (`filter_to_countries()`) sides of the country lookup.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed geoAreaCode format mismatch across GeoArea/Tree, Indicator/Data, and the M49 CSV crosswalk**
- **Found during:** Task 2 (first live ingestion run)
- **Issue:** `GeoArea/Tree` returns `geoAreaCode` as a bare JSON integer (e.g. `4`), `Indicator/Data` returns it as an un-padded numeric string (e.g. `"4"`), and the M49 CSV crosswalk (Plan 01-03) uses zero-padded 3-digit strings (e.g. `"004"`). Without normalization, every observation row failed the country-leaf lookup (`not_a_country_leaf`), zeroing out `raw_observations` across all 5 indicators on the first live run — the mocked unit tests in Task 1 did not catch this because their fixtures were already 3-digit strings.
- **Fix:** Added `_normalize_code()` (`str(code).zfill(3)`) in `src/ingesta/countries.py`, applied as the dict key in `collect_countries()` and as the lookup key in `filter_to_countries()`.
- **Files modified:** `src/ingesta/countries.py`, `tests/ingesta/test_countries.py`
- **Verification:** Regression tests added covering int tree codes and un-padded string indicator codes joining against zero-padded keys; full suite green; live re-run populated `raw_observations` correctly.
- **Committed in:** `f55be2d`

**2. [Rule 4 - Architectural/methodological, escalated to user] Disambiguated 2.3.1's two multiplexed producer-size series**
- **Found during:** Task 2 (live run tripped the D-11 duplicate-key assert in `db.insert_observations`)
- **Issue:** Indicator 2.3.1 carries two series (`PD_AGR_SSFP` small-scale food producers, `PD_AGR_LSFP` large-scale food producers) under the identical headline dimension combo, so both survived `filter_headline_rows` and produced duplicate (country, year, indicator) keys.
- **Fix:** Added `HEADLINE_SERIES` (indicator → adopted series code) applied alongside `HEADLINE_DIMENSIONS`; adopted `PD_AGR_SSFP` per SDG target 2.3's explicit focus on small-scale food producers. Per deviation Rule 4 (methodological choice with direct downstream impact on Phase 6's Model 2), this was **not** auto-applied silently — it was flagged for and received explicit human review/approval at this plan's Task 3 checkpoint.
- **Files modified:** `src/ingesta/fetch_data.py`, `tests/ingesta/test_fetch_data.py`, `tests/fixtures/indicator_dimension_samples.json`
- **Verification:** Fixture + regression test added; full suite (46 tests) passed; live re-run resolved the duplicate-key assert; **user typed "approved"** at the Task 3 checkpoint, explicitly accepting `PD_AGR_SSFP` as the headline series and the resulting coverage (50 countries, 173/900 non-null values) as a Phase 6 scope-planning input.
- **Committed in:** `4bca7d6`

---

**Total deviations:** 2 auto-fixed/escalated (1 Rule 1 bug fix, 1 Rule 4 methodological choice escalated to and approved by the user)
**Impact on plan:** Both were necessary for the live run to succeed at all and for `raw_observations` to satisfy its uniqueness invariant. The Rule 4 item is a substantive methodological decision (which of two 2.3.1 series is "the" indicator) with direct bearing on Phase 6's Model 2 scope — correctly escalated rather than silently resolved, and explicitly approved by the user. No scope creep beyond what live data forced.

## Issues Encountered

None beyond the two deviations documented above. The STATE.md blocker "la cobertura real de países/años del indicador 2.3.1 ... no fue verificada en vivo" is now resolved: coverage is 50 countries, 173/900 non-null values (2000–2022, 18 years × 50 countries = 900 possible cells) — a real constraint for Phase 6 to plan around, not a defect.

## User Setup Required

None - no external service configuration required. `data/raw/`, `data/panel.db`, and `data/raw/exclusion_log.json` remain gitignored/regenerable per the project's existing `.gitignore` design; only the provenance manifests (`.manifest.json`) matter for reproducibility and they are versioned alongside the code.

## Next Phase Readiness

- Phase 1 is fully complete: all 5 plans executed, all 5 success criteria met (unique raw_observations, no M49 leakage, per-indicator raw JSON + manifests, client pagination/retry, requirements.lock.txt).
- `data/panel.db`'s `panel` table (4,923 rows, one per country-year, wide by indicator) is ready for Phase 2 (Construcción del Panel y EDA) to consume for cleaning, coverage filtering (70% threshold), and feature engineering.
- **Carried forward for Phase 6 (Model 2 — Productividad Agrícola) scope planning:** indicator 2.3.1 covers only 50 countries with 173/900 non-null (country, year) cells after the `PD_AGR_SSFP` series choice. This is a real, user-approved coverage constraint — Phase 6 must document it explicitly (MODEL2-02) and may need to further restrict the modeling sample.
- No blockers.

---
*Phase: 01-ingesta-y-almacenamiento-versionado*
*Completed: 2026-07-11*

## Self-Check: PASSED

- FOUND: src/ingesta/fetch_data.py
- FOUND: tests/ingesta/test_fetch_data.py
- FOUND: tests/fixtures/indicator_dimension_samples.json
- FOUND: src/ingesta/countries.py
- FOUND: .planning/phases/01-ingesta-y-almacenamiento-versionado/01-05-SUMMARY.md
- FOUND commit: a564065
- FOUND commit: 4c9cca6
- FOUND commit: f55be2d
- FOUND commit: 4bca7d6
- FOUND commit: 5ef9d29
