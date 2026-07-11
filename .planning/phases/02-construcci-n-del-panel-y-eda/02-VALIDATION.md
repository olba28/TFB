---
phase: 2
slug: construcci-n-del-panel-y-eda
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`) |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_panel_build.py tests/ingesta/test_typology.py -q` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/ -q` |
| **Estimated runtime** | ~2-4 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/test_panel_build.py tests/ingesta/test_typology.py -q`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-1 | 01 | 1 | PANEL-01 | T-02-01 / path-construction-from-fixed-list-only | country_reference capture uses only fixed GeoArea/Tree endpoint + persisted output, no dynamic path from response content | unit | `pytest tests/ingesta/test_typology.py -q` | ⬜ W0 | ⬜ pending |
| 02-01-2 | 01 | 1 | PANEL-01, PANEL-02 | T-02-02 / — | Coverage filter (17/23-year threshold per country×indicator) is a pure function, no side effects on raw_observations | unit | `pytest tests/test_panel_build.py -q` | ⬜ W0 | ⬜ pending |
| 02-01-3 | 01 | 1 | PANEL-01 | T-02-03 / — | Idempotency: running the build twice against the same data/panel.db produces byte-identical output | unit | `pytest tests/test_panel_build.py::test_idempotency -q` | ⬜ W0 | ⬜ pending |
| 02-02-1 | 02 | 2 | PANEL-03, PANEL-04 | — / N/A (notebook, no new network/auth surface) | N/A — descriptive/EDA notebook, not security-relevant | manual_procedural | notebook opens and executes top-to-bottom without error | ⬜ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_panel_build.py` — stubs for PANEL-01 (idempotency), PANEL-02 (coverage filter/exclusion table)
- [ ] `tests/ingesta/test_typology.py` — stubs for PANEL-04 (region/LDC/LLDC/SIDS extraction), mocked `GeoArea/Tree` fixture (no live network call in tests, mirrors `tests/ingesta/test_countries.py`'s existing pattern)
- [ ] No new test framework install — `pytest` + `pyproject.toml` config already established in Phase 1

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| MNAR missing-data discussion (prose + table, possible heatmap figure) | PANEL-03 | Discussion quality/completeness cannot be asserted by pytest — human judgment on whether the bias argument is convincing | Open `notebook/2_1_construccion_panel_eda.ipynb`, confirm a dedicated markdown section discusses missingness pattern and reporting-capacity bias with supporting numbers |
| Correlation/VIF matrix at global/regional/typology levels | PANEL-04 | Correctness of the statistical output and whether the 3-level breakdown is genuinely useful for Phase 3 requires human review, not just "did the cell execute" | Open the notebook, confirm 3 VIF/correlation outputs (global, per-region, per-typology) render without error and values are plausible (no VIF of infinity/NaN without explanation) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
