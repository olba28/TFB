---
phase: 4
slug: interpretabilidad-simulaci-n-y-robustez
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-12
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already used: `tests/test_panel_base.py`, `tests/test_panel_build.py`, `tests/ingesta/`) |
| **Config file** | none found (no `pytest.ini`/`pyproject.toml [tool.pytest]` section) — defaults apply |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_simulate.py tests/test_interpret.py -q` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/ -q` |
| **Estimated runtime** | ~5-10 seconds (fast fixture-based unit tests only — NOT the 1000-replica bootstrap or the real-data SHAP run, which belong in the notebook's own top-to-bottom execution, ≈25-30 min) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/test_simulate.py tests/test_interpret.py -q`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green, plus one full top-to-bottom `notebook/4_1_interpretabilidad_simulacion.ipynb` re-execution (matching Phase 2/3's verification pattern)
- **Max feedback latency:** 10 seconds (unit tests); notebook re-execution is a separate, slower, end-of-phase gate

---

## Per-Task Verification Map

*Task IDs are assigned by the planner (Step 8) and not yet known at research/validation-strategy time. Rows below map each phase requirement to its automated test — the planner must attach a real `{phase}-{plan}-{task}` ID to whichever task implements each behavior.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | INTERP-01 | — / N/A | `resample_entities()` relabels every draw to a unique synthetic entity id — produces exactly N recognized entities for N draws (no silent collision) | unit | `pytest tests/test_simulate.py::test_resample_entities_unique_index -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | INTERP-01 | — / N/A | Non-extrapolation check (D-04) excludes a country from a scenario — never caps — when its simulated value falls below the historical global minimum | unit | `pytest tests/test_simulate.py::test_non_extrapolation_exclusion -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1+ | INTERP-02 | — / N/A | Multi-scenario sensitivity plot renders ≥3 scenarios (-10/-20/-30%) with percentile CI bands | manual/notebook | `nbconvert --execute` + visual check (no automated pixel test) | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | INTERP-03 | — / N/A | Interaction formula uses `water_stress : C(group)` (colon) — fits without `AbsorbingEffectError` and returns one coefficient per group (region, is_ldc), never a per-country prediction | unit | `pytest tests/test_panel_base.py::test_interaction_formula -x` (or a small new test module) | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | INTERP-04 | — / N/A | `shap_analysis()` returns a SHAP values array of shape `(n_samples, n_features)` for a small fixture RF; VIF/correlation table is computed and reported before SHAP output | unit | `pytest tests/test_interpret.py::test_shap_values_shape -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1+ | INTERP-05 | — / N/A | ALE/partial-dependence plots render for the correlated Phase-2 predictors, complementing the SHAP output | manual/notebook | `nbconvert --execute` + visual check | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | INTERP-06 | — / N/A | `rf.oob_score_` (or equivalent held-out metric) is computed and is a real float, not NaN/None | unit | `pytest tests/test_interpret.py::test_oob_score_present -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REPRO-02 | — / N/A | Two calls to `bootstrap_counterfactual()` with the same seed produce identical coefficient draws (`n_jobs=1` enforced for the RF step) | unit (determinism) | `pytest tests/test_simulate.py::test_bootstrap_determinism -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REPRO-02 | — / N/A | Two calls to `shap_analysis()`/RF training with the same seed produce identical `feature_importances_`/`oob_score_`/SHAP values | unit (determinism) | `pytest tests/test_interpret.py::test_rf_determinism -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_simulate.py` — stubs for INTERP-01/02, REPRO-02 (bootstrap determinism, entity-relabeling correctness, non-extrapolation exclusion)
- [ ] `tests/test_interpret.py` — stubs for INTERP-04/05/06, REPRO-02 (RF determinism with `n_jobs=1`, SHAP values shape, OOB score presence)
- [ ] A small pytest fixture RF (tiny synthetic data, not the full 3473-row real panel) shared by both test files for fast unit tests of `shap_analysis`/`ale_plots` — the real-data run belongs only in the notebook, not the fast per-commit test loop
- [ ] Framework install: none needed — `pytest` already installed and used by Phases 1-3

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Multi-scenario sensitivity plot legibility (≥3 scenarios with CI bands) | INTERP-02 | Visual quality/clarity of a chart cannot be asserted by an automated pixel test | Open `notebook/4_1_interpretabilidad_simulacion.ipynb`, confirm the plot shows all simulated reduction scenarios with visibly distinct CI bands and axis/legend labeling |
| Heterogeneity coefficient table presentation (region, is_ldc) never surfaces a per-country prediction | INTERP-03 | Confirming the *absence* of a forbidden output shape (per-country prediction) requires reading the notebook's rendered output, not just that the code executed | Confirm the notebook's heterogeneity section renders only grouped coefficient/SE/CI tables — no per-country predicted value anywhere in that section |
| SHAP correlation-bias caveat is honest, not templated | INTERP-04 | Whether the reported VIF/correlation numbers are the real Phase-2 numbers (not a generic disclaimer) requires human review against `notebook/2_1_construccion_panel_eda.ipynb` | Confirm the VIF/correlation table preceding SHAP matches Phase 2's actual committed numbers, and the caveat text references those numbers rather than a boilerplate warning |
| ALE/PDP plot choice and correlated-variable selection | INTERP-05 | Which Phase-2-correlated variables warrant an ALE/PDP plot is a judgment call left to Claude's Discretion in CONTEXT.md | Confirm at least one ALE/PDP plot exists per RF predictor flagged as correlated in Phase 2, with a brief rationale in the notebook |
| Full-notebook reproducibility (REPRO-02) | REPRO-02 | Unit tests cover function-level determinism on fixtures; full notebook re-execution against real data is the end-to-end proof | Re-execute `notebook/4_1_interpretabilidad_simulacion.ipynb` top-to-bottom twice; confirm bootstrap CIs, RF feature importances, and SHAP values are bit-identical between runs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
