---
phase: 01-ingesta-y-almacenamiento-versionado
plan: 02
subsystem: ingesta
tags: [requests, urllib3, retry, pagination, provenance, hashlib, pytest]

# Dependency graph
requires:
  - phase: 01-ingesta-y-almacenamiento-versionado (Plan 01)
    provides: "Isolated .venv, pytest/pytest-cov scaffolding, tests/ package skeletons, active .gitignore"
provides:
  - "src/ingesta/client.py: build_session() with urllib3.Retry-backed backoff, fetch_all_pages() with dynamic per-indicator pagination"
  - "src/ingesta/manifest.py: write_manifest()/load_manifest()/manifest_exists()/sha256_of() provenance sidecar API"
  - "tests/fixtures/mock_500_then_paginated.json shared fixture for retry + pagination scenarios"
affects: [01-03, 01-04, 01-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Retry/backoff configured once on requests.Session via urllib3.util.retry.Retry mounted on HTTPAdapter — never a hand-rolled retry loop"
    - "Retry-integration tests use a local loopback http.server (stdlib only) so the real urllib3 Retry state machine is exercised end-to-end, instead of mocking session.get (which would bypass the transport layer the retry logic actually lives in)"
    - "Pagination loop reads totalPages fresh from each indicator's own first response — no shared/hardcoded page count across indicators"
    - "manifest.py is pure file-I/O: no network calls, no API schema knowledge beyond row_count; orchestration (skip-if-exists) deferred to Plan 05's fetch_data.py"

key-files:
  created:
    - src/ingesta/client.py
    - src/ingesta/manifest.py
    - tests/ingesta/test_client.py
    - tests/ingesta/test_manifest.py
    - tests/fixtures/mock_500_then_paginated.json
  modified: []

key-decisions:
  - "Retry test uses a local loopback HTTP server (stdlib http.server) rather than mocking session.get directly — mocking session.get would bypass urllib3's Retry machinery entirely (retries happen transparently below Session.get), so a session.get-level mock could not actually prove retry-on-500 behavior works"
  - "fetch_all_pages() queries the UN SDG API with a repeated timePeriod query param for years 2000-2022 (requests expands a list value into repeated params) — exact param name/format not pinned down in RESEARCH.md, resolved via Claude's Discretion"
  - "HTTPAdapter with the Retry object mounted on both http:// and https:// (not just https://) so the same production-configured adapter can be exercised against the loopback test server without a separate test-only session builder"

patterns-established:
  - "src/ingesta/ modules are self-contained I/O units: client.py owns all network calls, manifest.py owns all provenance file-I/O, neither imports the other"

requirements-completed: [INGEST-01, INGEST-04]

coverage:
  - id: D1
    description: "build_session() carries a urllib3.Retry object (not integer shorthand) with the D-01 5xx/429 status_forcelist and 1s/2s/4s backoff"
    requirement: "INGEST-01"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_client.py#test_build_session_configures_retry_object_with_5xx_status_forcelist"
        status: pass
    human_judgment: false
  - id: D2
    description: "A mocked 500-then-200 sequence succeeds transparently after retry (no exception raised on the first 500)"
    requirement: "INGEST-01"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_client.py#test_build_session_retries_on_500_then_succeeds"
        status: pass
    human_judgment: false
  - id: D3
    description: "fetch_all_pages() paginates dynamically from totalPages read per-indicator and concatenates all page rows; inserts D-04 delay only between pages"
    requirement: "INGEST-01"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_client.py#test_fetch_all_pages_multi_page_concatenates_rows_and_sleeps_between_calls"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_client.py#test_fetch_all_pages_reads_totalpages_dynamically_never_hardcoded"
        status: pass
    human_judgment: false
  - id: D4
    description: "write_manifest() produces a per-indicator sidecar with date/url/params/row_count/sha256 checksum matching the raw file; load_manifest round-trips all fields"
    requirement: "INGEST-04"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_manifest.py#test_write_manifest_creates_sidecar_with_all_five_required_fields"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_manifest.py#test_sha256_of_matches_stdlib_hashlib"
        status: pass
    human_judgment: false
  - id: D5
    description: "manifest_exists() reflects presence correctly (false before write, true after, false with only the raw file, false for a different date) — the idempotency signal Plan 05 will build on"
    requirement: "INGEST-04"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_manifest.py#test_manifest_exists_false_before_write_true_after"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_manifest.py#test_manifest_exists_false_when_only_raw_json_present_no_manifest"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-07-11
status: complete
---

# Phase 01 Plan 02: HTTP Client & Provenance Manifest Summary

**UN SDG API client with urllib3.Retry-backed retry/backoff and dynamic per-indicator pagination, plus a pure file-I/O provenance manifest module (write/load/exists) — both fully unit-tested with zero live network calls.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 (both auto, TDD)
- **Files modified:** 5 (all new)

## Accomplishments
- `build_session()` mounts a `urllib3.util.retry.Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504])` on the session's `HTTPAdapter` (both `http://` and `https://`) — the correct object-based configuration, not the integer `max_retries=3` shorthand that RESEARCH.md flags as only retrying connection errors
- `fetch_all_pages()` reads `totalPages` fresh from each indicator's own first response and loops until complete, concatenating rows across pages, with a fixed `INTER_PAGE_DELAY_SECONDS` (0.5s) sleep only between successive page calls (never before the first or after the last)
- Retry-on-500 behavior verified genuinely end-to-end: a local loopback `http.server` (stdlib only, no live network) replays a scripted 500-then-200 sequence, letting the real urllib3 Retry state machine execute — a `session.get`-level mock could not have proven this, since retries happen transparently beneath `Session.get`
- `manifest.py` provides `sha256_of()`, `write_manifest()`, `load_manifest()`, `manifest_exists()` — a pure file-I/O module with exactly the D-08 five-field schema (date, url, params, row_count, checksum), no network calls, no API schema coupling beyond the row count it's handed
- 11 tests total (6 client, 5 manifest), all green, 0.7s runtime

## Task Commits

Each task was committed atomically:

1. **Task 1: HTTP client with retry/backoff and automatic pagination** - `567f5f7` (feat)
2. **Task 2: Provenance manifest reader/writer with idempotency guard** - `dee63c8` (feat)

**Plan metadata:** (this commit) `docs(01-02): complete HTTP client & manifest plan`

## Files Created/Modified
- `src/ingesta/client.py` - `build_session()`, `fetch_all_pages()`; owns all network calls to the UN SDG API
- `src/ingesta/manifest.py` - `sha256_of()`, `write_manifest()`, `load_manifest()`, `manifest_exists()`; pure file-I/O provenance layer
- `tests/ingesta/test_client.py` - retry config assertion, real retry-on-500 via local server, pagination/delay/error-shape tests
- `tests/ingesta/test_manifest.py` - checksum correctness, schema round-trip, existence-check transitions
- `tests/fixtures/mock_500_then_paginated.json` - shared mock response bodies (500 error, single success, 2-page pair)

## Decisions Made
- Chose a local loopback `http.server` (stdlib, no live network) over mocking `session.get` for the retry-integration test, because mocking `session.get` directly would bypass the transport layer where urllib3's Retry logic actually lives — it would only prove the test's own mock sequence works, not that `build_session()`'s retry configuration is effective
- `fetch_all_pages()` uses a repeated `timePeriod` query param (list of years 2000-2022) since RESEARCH.md didn't pin down the exact year-range parameter name/format for the `Indicator/Data` endpoint (left to Claude's Discretion); `D-02` (dynamic `totalPages`) is independent of this choice and is satisfied regardless
- Mounted the Retry-configured `HTTPAdapter` on both `http://` and `https://` schemes so the identical production adapter configuration is exercised against the loopback test server, rather than maintaining a separate test-only session builder

## Deviations from Plan

None - plan executed exactly as written. The retry test implementation approach (local HTTP server vs. a plain `session.get` mock) was a Claude's-Discretion test-design choice within the plan's explicit allowance for either `unittest.mock` or an equivalent stdlib-only mocking technique (D-03 permits `unittest.mock` or `responses`; a stdlib loopback server was chosen instead of adding the `responses` dependency, consistent with RESEARCH's "do NOT add the responses package" instruction while still avoiding a session.get-level mock that wouldn't actually test retry behavior).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `client.py` and `manifest.py` are both self-contained and ready for Plan 03/04's `countries.py` and `fetch_data.py` orchestrator to import
- No live network calls anywhere in the test suite; `pytest tests/ingesta -x` runs in under 1 second
- `manifest_exists()`'s existence-check contract (raw + manifest both present) is now available for Plan 05's `if exists and not force: skip` idempotency control flow

---
*Phase: 01-ingesta-y-almacenamiento-versionado*
*Completed: 2026-07-11*

## Self-Check: PASSED

All 5 created files verified present on disk. Both task commits (`567f5f7`, `dee63c8`) verified in git log.
