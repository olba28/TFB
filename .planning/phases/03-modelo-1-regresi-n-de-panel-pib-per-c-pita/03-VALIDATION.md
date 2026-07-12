---
phase: 3
slug: modelo-1-regresi-n-de-panel-pib-per-c-pita
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-12
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`) |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_panel_base.py -q` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/ -q` |
| **Estimated runtime** | ~3-5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/test_panel_base.py -q`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-1 | 01 | 1 | MODEL1-01, PANEL-02 | T-03-01 / — | filter_by_exclusions is a pure function, no side effects on panel_clean/panel_exclusions | unit | `pytest tests/test_panel_base.py -k filter_by_exclusions -q` | ⬜ W0 | ⬜ pending |
| 03-01-2 | 01 | 1 | MODEL1-01, MODEL1-02 | — / N/A | fit_panel_model builds MultiIndex correctly, entity/time effects applied per D-05's signature | unit | `pytest tests/test_panel_base.py -k fit_panel_model -q` | ⬜ W0 | ⬜ pending |
| 03-01-3 | 01 | 1 | MODEL1-03 | — / N/A | hausman_test formula matches the verified textbook computation, pinv fallback on non-PD var_diff | unit | `pytest tests/test_panel_base.py -k hausman -q` | ⬜ W0 | ⬜ pending |
| 03-01-4 | 01 | 1 | MODEL1-04 | — / N/A | pesaran_cd_test + choose_cov_type correctly select clustered vs kernel per the alpha=0.05 rule | unit | `pytest tests/test_panel_base.py -k pesaran -q` | ⬜ W0 | ⬜ pending |
| 03-02-1 | 02 | 2 | MODEL1-02, MODEL1-03, MODEL1-04, MODEL1-06 | — / N/A (notebook, read-only + one .pkl write, no new network/auth surface) | Live fit, pooled/RE/FE comparison, Hausman, SE choice, serialization all execute against real data/panel.db | manual_procedural | notebook executes top-to-bottom without error | ⬜ W0 | ⬜ pending |
| 03-02-2 | 02 | 2 | MODEL1-05, REPRO-03 | — / N/A | Robustness sub-sample fit is qualitatively consistent; limitations section addresses reverse causality/endogeneity | manual_procedural | notebook contains both sections with real computed numbers | ⬜ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_panel_base.py` — stubs for MODEL1-01 (filter_by_exclusions, fit_panel_model), MODEL1-03 (hausman_test), MODEL1-04 (pesaran_cd_test, choose_cov_type)
- [ ] No new test framework install — `pytest` + `pyproject.toml` config already established

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Robustness check qualitative consistency (2000-2019 sub-sample vs. full-sample base model) | MODEL1-05 | "Qualitatively consistent" requires human judgment on sign/magnitude/significance stability, not just successful execution | Open `notebook/3_1_modelo1_pib.ipynb`, confirm the robustness section's coefficient sign and significance match the base model's, with any differences discussed |
| Limitations / Amenazas a la validez section | REPRO-03 | Whether the causal-inference caveats are substantively convincing for a tribunal requires academic judgment | Confirm the notebook (or memoria-facing section) explicitly discusses reverse causality and endogeneity, not just a generic disclaimer |
| Pooled/RE/FE comparison + Hausman justification | Success Criterion #3 | Correctness of the econometric interpretation (not just that the code ran) requires human review | Confirm the comparison table and Hausman test result are present and the FE choice is explicitly justified by the test outcome |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
