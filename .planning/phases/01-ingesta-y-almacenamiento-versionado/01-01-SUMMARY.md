---
phase: 01-ingesta-y-almacenamiento-versionado
plan: 01
subsystem: infra
tags: [venv, pytest, pytest-cov, pip-freeze, gitignore, reproducibility]

# Dependency graph
requires: []
provides:
  - "Isolated project-scoped .venv with runtime + dev deps installed"
  - "requirements.lock.txt frozen from the .venv interpreter (REPRO-01)"
  - "requirements-dev.txt pinning pytest>=8, pytest-cov>=5"
  - "pyproject.toml with [tool.pytest.ini_options] testpaths=['tests']"
  - "src/ingesta and tests/ package skeletons for Plans 02-05"
  - "Active .gitignore correctly ignoring raw JSON + data/panel.db while tracking manifests"
affects: [01-02, 01-03, 01-04, 01-05]

# Tech tracking
tech-stack:
  added: [pytest, pytest-cov]
  patterns:
    - "Dev-only test tooling pinned separately in requirements-dev.txt, never merged into requirements.txt"
    - "Lockfile always generated via .venv/Scripts/python.exe -m pip freeze, never the global interpreter"

key-files:
  created:
    - .gitignore
    - requirements-dev.txt
    - requirements.lock.txt
    - pyproject.toml
    - src/ingesta/__init__.py
    - tests/__init__.py
    - tests/ingesta/__init__.py
    - tests/conftest.py
    - tests/fixtures/.gitkeep
  modified: []

key-decisions:
  - "pytest/pytest-cov legitimacy confirmed by human before install (Task 1 checkpoint) — RESEARCH's [SUS] flag was a release-recency heuristic false positive, not a real risk"
  - "requirements.lock.txt frozen strictly from .venv/Scripts/python.exe -m pip freeze to avoid polluting the lockfile with global-interpreter packages"

patterns-established:
  - "Test scaffolding (tests/__init__.py, tests/ingesta/__init__.py, tests/conftest.py, tests/fixtures/) exists empty and ready — downstream plans add fixtures/tests without re-authoring package structure"

requirements-completed: [REPRO-01]

coverage:
  - id: D1
    description: "Isolated .venv created and requirements.lock.txt reflects its pip freeze (REPRO-01)"
    requirement: "REPRO-01"
    verification:
      - kind: other
        ref: ".venv/Scripts/python.exe -m pip freeze > requirements.lock.txt (152 lines, non-empty)"
        status: pass
    human_judgment: false
  - id: D2
    description: "pytest scaffolding stands up cleanly (pyproject.toml testpaths, package __init__.py files, conftest.py, fixtures dir)"
    verification:
      - kind: other
        ref: ".venv/Scripts/python.exe -m pytest --collect-only -q (0 tests collected, no errors)"
        status: pass
    human_judgment: false
  - id: D3
    description: ".gitignore activated (renamed from gitignore) and correctly ignores data/raw JSON + data/panel.db while tracking {fecha}.manifest.json files"
    verification:
      - kind: other
        ref: "git check-ignore -q data/raw/6.4.2/2026-07-10.json && git check-ignore -q data/panel.db && ! git check-ignore -q data/raw/6.4.2/2026-07-10.manifest.json"
        status: pass
    human_judgment: false

duration: ~20min (across two sessions; checkpoint pause in between)
completed: 2026-07-11
status: complete
---

# Phase 01 Plan 01: Reproducibility & Test Foundation Summary

**Project-scoped .venv with pinned requirements.lock.txt (REPRO-01), pytest/pytest-cov dev tooling, pyproject.toml pytest config, and empty src/ingesta + tests/ package skeletons; .gitignore activated and corrected for manifest tracking.**

## Performance

- **Duration:** ~20 min (spanned two sessions due to Task 1's blocking human-verify checkpoint)
- **Tasks:** 3 (1 checkpoint, 2 auto)
- **Files modified/created:** 9 (`.gitignore` renamed + 8 new files)

## Accomplishments
- Human-verified pytest/pytest-cov legitimacy before any install (blocking checkpoint, approved)
- `.gitignore` activated (git mv from plain `gitignore`), added `data/panel.db` ignore rule, fixed the manifest re-include pattern (`!data/**/*.manifest.json`) to match the real `{fecha}.manifest.json` filenames
- Isolated `.venv` created; runtime deps from `requirements.txt` plus new dev deps (`pytest>=8`, `pytest-cov>=5` in `requirements-dev.txt`) installed into it
- `requirements.lock.txt` frozen from the `.venv` interpreter (152 packages, REPRO-01 satisfied)
- `pyproject.toml` with `[tool.pytest.ini_options]` (`testpaths = ["tests"]`) plus `src/ingesta/__init__.py`, `tests/__init__.py`, `tests/ingesta/__init__.py`, `tests/conftest.py`, `tests/fixtures/.gitkeep` created
- `pytest --collect-only -q` runs clean against the `.venv` interpreter (0 tests collected, no import/config errors)

## Task Commits

Each task was committed atomically:

1. **Task 1: Verify pytest/pytest-cov legitimacy before install** - checkpoint, no commit (human approval only)
2. **Task 2: Fix repo hygiene — activate and extend .gitignore** - `61f617d` (fix)
3. **Task 3: Create .venv, freeze lockfile, and stand up pytest scaffolding** - `5ef98fc` (feat)

**Plan metadata:** (this commit) `docs(01-01): complete reproducibility and test foundation plan`

## Files Created/Modified
- `.gitignore` - renamed from `gitignore`; added `data/panel.db` ignore, fixed manifest negation to `!data/**/*.manifest.json`
- `requirements-dev.txt` - pins `pytest>=8`, `pytest-cov>=5` (dev-only, kept separate from `requirements.txt`)
- `requirements.lock.txt` - frozen via `.venv/Scripts/python.exe -m pip freeze` (152 packages)
- `pyproject.toml` - `[tool.pytest.ini_options]` with `testpaths = ["tests"]`
- `src/ingesta/__init__.py` - empty package init, consumed by Plans 02-05
- `tests/__init__.py`, `tests/ingesta/__init__.py` - empty test package inits
- `tests/conftest.py` - empty, ready for shared fixtures
- `tests/fixtures/.gitkeep` - placeholder; actual fixture JSON added by consuming plans

## Decisions Made
- pytest/pytest-cov confirmed legitimate by human (pypi.org project pages, pytest-dev GitHub org) before install — RESEARCH's `[SUS]` flag traced to a release-recency heuristic, not a real supply-chain risk
- Lockfile generation strictly scoped to the `.venv` interpreter (`.venv/Scripts/python.exe -m pip freeze`), never the global Python, to avoid capturing unrelated system packages

## Deviations from Plan

None - plan executed exactly as written. Task 3 was split across two sessions only because Task 1's blocking checkpoint required a fresh continuation agent; no task content deviated from `01-01-PLAN.md`.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Test infrastructure (`tests/`, `pyproject.toml` pytest config) ready for Plans 02-05 to add fixtures and tests
- `.venv` + `requirements.lock.txt` established as the canonical reproducible environment for the rest of Phase 1
- `.gitignore` correctly scoped: raw JSON and `data/panel.db` will be ignored once ingestion code starts writing to `data/`; manifests will be tracked

---
*Phase: 01-ingesta-y-almacenamiento-versionado*
*Completed: 2026-07-11*

## Self-Check: PASSED

All 9 created files verified present on disk. Both task commits (`61f617d`, `5ef98fc`) verified in git log.
