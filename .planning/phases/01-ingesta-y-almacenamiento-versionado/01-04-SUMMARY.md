---
phase: 01-ingesta-y-almacenamiento-versionado
plan: 04
subsystem: database
tags: [sqlite, sqlalchemy, pandas, panel-data, storage]

# Dependency graph
requires:
  - phase: 01-01
    provides: project skeleton, .venv, requirements.txt/requirements.lock.txt conventions
provides:
  - "src/db.py: get_engine(), init_db(), insert_observations(), rebuild_panel()"
  - "raw_observations table (immutable long table, UNIQUE(country_code, year, indicator_code))"
  - "panel table (derived wide pivot, regenerated via rebuild_panel())"
affects: [01-05, phase-02-panel-eda]

# Tech tracking
tech-stack:
  added: ["sqlalchemy>=2.0 (Engine for pandas to_sql/read_sql)"]
  patterns:
    - "UNIQUE constraint + pre-insert assert double-guard against duplicate keys (D-11)"
    - "Derived table regenerated via pivot + if_exists='replace', never hand-edited (D-12)"

key-files:
  created: [src/db.py, tests/ingesta/test_db.py]
  modified: [requirements.txt, requirements.lock.txt]

key-decisions:
  - "Added sqlalchemy>=2.0 to requirements.txt: required for the Engine-based to_sql/read_sql path the plan and RESEARCH.md's Standard Stack section explicitly call for; installed and refroze requirements.lock.txt"
  - "pandas.to_sql wraps the underlying sqlalchemy.exc.IntegrityError in pandas.errors.DatabaseError -- tests assert on the wrapper, not the raw sqlalchemy exception"

patterns-established:
  - "Storage layer: raw_observations is the only writable/insert target; panel is always derived, never inserted into directly"

requirements-completed: [INGEST-05]

coverage:
  - id: D1
    description: "raw_observations schema (D-10 columns) with UNIQUE(country_code, year, indicator_code) + pre-insert assert guard (D-11)"
    requirement: "INGEST-05"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_db.py#test_insert_observations_raises_on_duplicate_keys_in_df"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_db.py#test_unique_constraint_raises"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_db.py#test_insert_observations_persists_null_value"
        status: pass
    human_judgment: false
  - id: D2
    description: "rebuild_panel() regenerates the wide panel table via pivot, idempotently, from raw_observations (D-12)"
    requirement: "INGEST-05"
    verification:
      - kind: unit
        ref: "tests/ingesta/test_db.py#test_rebuild_panel_is_idempotent"
        status: pass
      - kind: unit
        ref: "tests/ingesta/test_db.py#test_rebuild_panel_shape_one_row_per_country_year_one_column_per_indicator"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-11
status: complete
---

# Phase 01 Plan 04: SQLite Storage Layer (raw_observations + panel) Summary

**`src/db.py` storage layer: raw_observations enforces one row per (country, year, indicator) via UNIQUE + pre-insert assert; panel is a regenerable pivot rebuilt with `if_exists='replace'`, never hand-edited.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-07-11
- **Tasks:** 2/2 completed
- **Files modified:** 4 (2 created: `src/db.py`, `tests/ingesta/test_db.py`; 2 modified: `requirements.txt`, `requirements.lock.txt`)

## Accomplishments
- `init_db(engine)` creates `raw_observations` (D-10 columns, `UNIQUE(country_code, year, indicator_code)`) idempotently via `CREATE TABLE IF NOT EXISTS`
- `insert_observations(engine, df)` asserts no duplicate (country, year, indicator) keys within the incoming df before any row reaches SQLite (D-11, first guard); the schema `UNIQUE` constraint rejects duplicates across separate calls (second guard)
- NULL/NaN values are stored as NULL in `raw_observations`, never dropped or silently coerced (2.3.1's `"NaN"`-string case is Phase 2's filtering concern, not this layer's)
- `rebuild_panel(engine)` regenerates the wide `panel` table via `pivot(index=['country_code','year'], columns='indicator_code', values='value')` + `to_sql(..., if_exists='replace')`; two consecutive rebuilds over the same `raw_observations` are byte-identical (idempotent)
- All SQL is parameterized (via SQLAlchemy `text()`/pandas `to_sql`/`read_sql`) or built from fixed constants — no API-sourced value is ever f-string-interpolated into SQL text (Security V5, T-01-SQLi mitigated)

## Task Commits

Each task followed RED → GREEN (TDD):

1. **Task 1 + Task 2 tests (RED):** `123e60c` - test(01-04): add failing tests for raw_observations schema, insert guard, and panel pivot
2. **Task 1 + Task 2 implementation (GREEN):** `bbde99e` - feat(01-04): implement raw_observations storage layer and derived panel pivot

_Note: both plan tasks (schema/insert and panel pivot) were implemented together since their tests were authored in a single RED commit against the single `src/db.py` module; each still has its own dedicated test coverage per the plan's acceptance criteria._

**Plan metadata:** (this commit, docs) — see final commit below.

## Files Created/Modified
- `src/db.py` - `CREATE_RAW_OBSERVATIONS` DDL, `get_engine()`, `init_db()`, `insert_observations()`, `rebuild_panel()`
- `tests/ingesta/test_db.py` - 5 tests: duplicate-in-df assert, schema UNIQUE second guard, NULL persistence, panel idempotency, panel shape
- `requirements.txt` - added `sqlalchemy>=2.0`
- `requirements.lock.txt` - refrozen via `pip freeze` to include `SQLAlchemy==2.0.51` and its `greenlet` dependency

## Decisions Made
- **SQLAlchemy Engine over raw `sqlite3.Connection`:** per RESEARCH.md's Standard Stack recommendation and the plan's explicit action text (`get_engine()` returns `create_engine('sqlite:///...')`), used for the `to_sql`/`read_sql` path throughout.
- **`pandas.errors.DatabaseError` vs `sqlalchemy.exc.IntegrityError`:** discovered during GREEN that `pandas.to_sql` wraps the underlying `sqlalchemy.exc.IntegrityError` in its own `pandas.errors.DatabaseError`. Adjusted the schema-UNIQUE test to assert on the wrapper exception with a message match, since that's what callers of `insert_observations()` actually see.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added `sqlalchemy` to `requirements.txt`**
- **Found during:** Task 1 (before implementing `get_engine()`)
- **Issue:** The plan's action explicitly directs `get_engine()` to return a SQLAlchemy `Engine` (per RESEARCH.md's Standard Stack section), but `sqlalchemy` was not in `requirements.txt` and not installed in `.venv`. Without it, `src/db.py` cannot be implemented as specified.
- **Fix:** Installed `sqlalchemy>=2.0` in `.venv` (a foundational, extremely well-established PyPI package — no legitimacy concern; installed cleanly with only `greenlet` as a transitive dependency), added it to `requirements.txt` under a new "Almacenamiento" section, and refroze `requirements.lock.txt` via `pip freeze`.
- **Files modified:** `requirements.txt`, `requirements.lock.txt`
- **Verification:** `import sqlalchemy` succeeds in `.venv`; full test suite (29 tests) passes.
- **Committed in:** `bbde99e` (Task 1+2 GREEN commit)

**2. [Rule 1 - Bug] Fixed incorrect exception type in schema-UNIQUE test**
- **Found during:** Task 1 GREEN (first test run)
- **Issue:** Test initially asserted `sqlalchemy.exc.IntegrityError` is raised directly by `insert_observations()` on a duplicate key. In practice `pandas.to_sql` catches the underlying `SQLAlchemyError` and re-raises it wrapped as `pandas.errors.DatabaseError`.
- **Fix:** Changed the test import/assertion to expect `pandas.errors.DatabaseError` with a message match on `"UNIQUE constraint failed"`.
- **Files modified:** `tests/ingesta/test_db.py`
- **Verification:** `test_unique_constraint_raises` passes; full suite green.
- **Committed in:** `bbde99e` (Task 1+2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical dependency, 1 test-assumption bug)
**Impact on plan:** Both necessary for the plan's own explicit design (SQLAlchemy Engine) and for correctness of the test suite. No scope creep — no functionality was added beyond what the plan specified.

## Issues Encountered
None beyond the two deviations documented above.

## User Setup Required
None - no external service configuration required. `data/panel.db` remains gitignored (already covered by the existing `.gitignore` entry); no manual step needed.

## Next Phase Readiness
- `src/db.py` is ready to be wired into `fetch_data.py`'s orchestration (Plan 01-05): after per-indicator dimension filtering and country filtering, rows flow into `insert_observations()`, then `rebuild_panel()` regenerates the wide table.
- Phase 2 (panel/EDA) can rely on `panel` always being a fresh, gap-free (indicator-wise) pivot of `raw_observations` — no coverage filtering or feature engineering has been applied yet, by design (that is explicitly Phase 2's responsibility).
- No blockers.

---
*Phase: 01-ingesta-y-almacenamiento-versionado*
*Completed: 2026-07-11*

## Self-Check: PASSED

- FOUND: src/db.py
- FOUND: tests/ingesta/test_db.py
- FOUND: .planning/phases/01-ingesta-y-almacenamiento-versionado/01-04-SUMMARY.md
- FOUND commit: 123e60c
- FOUND commit: bbde99e
