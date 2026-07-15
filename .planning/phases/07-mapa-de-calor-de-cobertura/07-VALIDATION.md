---
phase: 7
slug: mapa-de-calor-de-cobertura
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-15
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (repo-wide convention: `tests/test_panel_build.py`, `tests/test_interpret.py`) |
| **Config file** | none — no `pytest.ini` / `pyproject.toml [tool.pytest]` detected; tests run via bare `pytest` from repo root |
| **Quick run command** | `pytest tests/test_coverage.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~seconds (matches this repo's existing suite velocity from prior phases) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_coverage.py -x`
- **After every plan wave:** Run `pytest` (full suite)
- **Before `/gsd-verify-work`:** Full suite green, plus a manual `Kernel → Restart & Run All` execution of `notebook/7_1_mapa_calor_cobertura.ipynb` confirming the PNG regenerates and visually satisfies the 4 Roadmap Success Criteria
- **Max feedback latency:** ~seconds (unit-test-only phase, no slow integration suite)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-T2 | 07-01 | 1 | COVER-01 | — | `build_presence_matrix` treats a wholly-absent (country, year) row as missing | unit | `pytest tests/test_coverage.py::test_build_presence_matrix_absent_row_is_missing -x` | ❌ Wave 0 | ⬜ pending |
| 07-01-T2 | 07-01 | 1 | COVER-01 | — | `build_presence_matrix` treats a present row with `value IS NULL` as missing (same state as absent-row, D-04) | unit | `pytest tests/test_coverage.py::test_build_presence_matrix_null_value_is_missing -x` | ❌ Wave 0 | ⬜ pending |
| 07-01-T2 | 07-01 | 1 | COVER-01 | — | `build_presence_matrix` treats a present row with a non-null value as present | unit | `pytest tests/test_coverage.py::test_build_presence_matrix_non_null_value_is_present -x` | ❌ Wave 0 | ⬜ pending |
| 07-01-T2 | 07-01 | 1 | COVER-01 | — | `ordered_countries_with_boundaries` groups countries by region and returns correct boundary indices | unit | `pytest tests/test_coverage.py::test_ordered_countries_with_boundaries_groups_by_region -x` | ❌ Wave 0 | ⬜ pending |
| 07-01-T2 | 07-01 | 1 | COVER-01 | — | Coverage computation reads `raw_observations`/`country_reference` only, never `panel_clean` | unit (behavioral/import check) | `pytest tests/test_coverage.py::test_coverage_module_never_reads_panel_clean -x` | ❌ Wave 0 | ⬜ pending |
| 07-02-T1 | 07-02 | 2 | COVER-02 | — | Notebook produces exactly one PNG file at `figuras/07_mapa_calor_cobertura.png` | manual (nbconvert execution + file-existence check) | `jupyter nbconvert --to notebook --execute notebook/7_1_mapa_calor_cobertura.ipynb` then verify PNG exists | ❌ Wave 0 | ⬜ pending |
| 07-02-T2 | 07-02 | 2 | COVER-02 | — | The 5 ODS indicator codes are visually identifiable in the figure (e.g. as subplot titles) | manual (visual inspection) | N/A — inherently a visual/manual check | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/coverage.py` — does not exist yet; must be created before any test in `tests/test_coverage.py` can pass
- [ ] `tests/test_coverage.py` — stubs for COVER-01 (mirror `tests/test_panel_build.py`'s fixture style: `tmp_path`-backed SQLite engine, synthetic `raw_observations`/`country_reference` covering absent row, present-with-NULL, present-with-value, multiple regions)
- [ ] `notebook/7_1_mapa_calor_cobertura.ipynb` — does not exist yet (COVER-02's manual/visual checks depend on it)

Framework install: none — pytest already installed and used project-wide.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Exactly one PNG produced at `figuras/07_mapa_calor_cobertura.png` | COVER-02 | One-shot notebook artifact, not a repeatedly-invoked function — Nyquist-appropriate to verify by execution + file check rather than a unit test | Run `jupyter nbconvert --to notebook --execute notebook/7_1_mapa_calor_cobertura.ipynb`, then confirm the PNG file exists at the expected path |
| The 5 SDG indicator codes are visually identifiable in the figure | COVER-02 | Inherently a visual/perceptual check — cannot be asserted from pixel data alone | Open the generated PNG and confirm each of the 5 sub-heatmaps is labeled with its indicator code (6.4.2, 6.4.1, 8.1.1, 8.2.1, 2.3.1) |
| Figure satisfies all 4 Roadmap Success Criteria end-to-end | COVER-01, COVER-02 | Requires human judgment of visual correctness (country×year axes, region grouping, missing/present legend) that no automated test can fully capture | `Kernel → Restart & Run All` on the notebook, then visually check against `.planning/ROADMAP.md` §"Phase 7" Success Criteria |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < seconds
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
