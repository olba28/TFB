---
phase: 1
slug: ingesta-y-almacenamiento-versionado
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (not yet installed — no `.venv` exists in the repo yet) |
| **Config file** | none yet — Wave 0 adds `pyproject.toml` `[tool.pytest.ini_options]` (or `pytest.ini`) with `testpaths = ["tests"]` |
| **Quick run command** | `pytest tests/ingesta -x` |
| **Full suite command** | `pytest --cov=src --cov-report=term-missing` |
| **Estimated runtime** | ~10 seconds (small unit suite, all HTTP calls mocked — no live network calls in tests) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ingesta -x`
- **After every plan wave:** Run `pytest --cov=src --cov-report=term-missing`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

*Task IDs are assigned by the planner (step 8) — rows below key on Requirement ID from RESEARCH.md's Phase Requirements → Test Map until plan/task IDs exist. The planner must fold these into concrete `<verify>`/`must_haves` entries per task.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (planner) | TBD | 0 | INGEST-01 | V5 (input validation on API response shape) | Client retries 3x w/ backoff on transient 500, then succeeds; paginates until `totalElements` reached | unit (mocked) | `pytest tests/ingesta/test_client.py -x` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | 0/1 | INGEST-02 | V5 | Per-indicator dimension filter yields exactly one row per (country, year) for each of the 5 indicators | unit | `pytest tests/ingesta/test_fetch_data.py::test_filters_to_headline_dimension -x` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | 0/1 | INGEST-03 | V5 | `countries.py` excludes all `GeoArea/Tree` nodes of `type != "Country"`; M49→ISO3 crosswalk resolves a known sample correctly | unit | `pytest tests/ingesta/test_countries.py -x` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | 0/1 | INGEST-04 | V5 | Manifest written with required fields (date, URL, params, row count, checksum); second run without `force=True` skips re-fetch | unit | `pytest tests/ingesta/test_manifest.py -x` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | 0/1 | INGEST-05 | T (SQL injection — parameterized queries only) | Duplicate (country, year, indicator) row insert raises (via UNIQUE constraint or the pre-insert assert) | unit | `pytest tests/ingesta/test_db.py::test_unique_constraint_raises -x` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | 0 | REPRO-01 | — | `requirements.lock.txt` exists and is non-empty after `.venv` setup | manual / smoke | `test -s requirements.lock.txt` | ❌ W0 (manual step) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pip install pytest pytest-cov` (into a newly created `.venv`) — no test infrastructure currently exists in the repo
- [ ] `tests/__init__.py`, `tests/conftest.py`, `tests/ingesta/__init__.py` — directory skeleton
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` (or `pytest.ini`) with `testpaths = ["tests"]`
- [ ] `tests/fixtures/` — fixture JSON mirroring the live-verified shapes captured in RESEARCH.md (5-row samples per indicator, one multi-page mock, one 500-then-success mock)
- [ ] Rename `gitignore` → `.gitignore` (RESEARCH.md Pitfall 3) — not a test gap per se, but blocks safe test/data iteration if left unfixed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `requirements.lock.txt` reflects a clean, project-scoped `pip freeze` | REPRO-01 | One-time environment artifact tied to the actual local `.venv` state, not pipeline logic — not meaningfully unit-testable | Create `.venv`, install `requirements.txt`, run `pip freeze > requirements.lock.txt`, confirm file is non-empty and contains no unrelated system packages |
| M49 CSV crosswalk acquisition (source file present with documented provenance) | INGEST-03 | One-time manual download from `unstats.un.org/unsd/methodology/m49/` (no scriptable export exists per RESEARCH.md) | Confirm `src/ingesta/data/m49_countries.csv` (or equivalent) exists, has an `ISO-alpha3 Code` column, and provenance (source URL + download date) is recorded |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
