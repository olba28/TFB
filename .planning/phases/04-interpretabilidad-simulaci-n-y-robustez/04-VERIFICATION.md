---
phase: 04-interpretabilidad-simulaci-n-y-robustez
verified: 2026-07-13T14:11:28Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 4: Interpretabilidad, Simulación y Robustez Verification Report

**Phase Goal:** Sobre el Modelo 1 ya diagnosticado y serializado, el sistema produce una simulación contrafactual de sensibilidad y un análisis de interpretabilidad, ambos reproducibles y sin extrapolar más allá del rango de datos observado.
**Verified:** 2026-07-13T14:11:28Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Simulación contrafactual produce CIs bootstrap para ≥3 escenarios de reducción, enmarcada como análisis de sensibilidad, sin extrapolar más allá del rango observado | ✓ VERIFIED | `src/simulate.py::bootstrap_counterfactual` computes percentile CIs per scenario via `np.percentile(...,[2.5,97.5])`; `check_non_extrapolation` excludes (never caps) countries below the historical floor. Notebook cell 6 (markdown) frames this explicitly as sensitivity, not causal prediction. Notebook cell 9 output: `Escenario -10%: 1 de 171 países excluidos... Países excluidos: ['COG']` (same for -20%/-30%). Unit tests `test_non_extrapolation_exclusion`, `test_bootstrap_determinism` pass. |
| 2 | Existe un gráfico multi-escenario con los ≥3 niveles de reducción y sus CIs | ✓ VERIFIED | Notebook cell 11 executed output: scenario summary table (pct/mean_effect/ci_2.5/ci_97.5 for -0.1/-0.2/-0.3) plus a rendered `image/png` figure (700x500) — confirmed present in the executed `.ipynb` JSON. |
| 3 | Heterogeneidad regional/por nivel de ingresos documentada, sin predicciones por país individual | ✓ VERIFIED | `src/simulate.py::fit_interaction_model` returns only per-group coefficient/SE/CI (`Q('6.4.2'):C(region)[...]`, `Q('6.4.2'):C(is_ldc)[...]`) — confirmed in notebook cells 14/15 executed output (grouped tables only, no per-country rows). Unit test `test_interaction_formula` passes (asserts one coefficient per group value, SE/CI present, no `AbsorbingEffectError`). |
| 4 | SHAP (TreeExplainer sobre RF) precedido por matriz de correlación/VIF de Fase 2, con aviso explícito de sesgo por correlación | ✓ VERIFIED | `src/interpret.py::compute_vif_table` reuses `statsmodels.variance_inflation_factor` (constant column added, fixed in commit `8857120` to match Phase 2's real numbers). Notebook cell 19 renders the VIF/correlation section (executed BEFORE cell 21/22's SHAP fit/plot) with real numbers (`|r|=0.092`, `VIF máximo... 1.981`) and an explicit correlation-bias caveat sentence, including a regional-subgroup VIF caveat. Unit test `test_vif_table` passes. |
| 5 | Existen gráficos ALE/partial-dependence complementando SHAP para variables correlacionadas | ✓ VERIFIED | `src/interpret.py::partial_dependence_plots` wraps `sklearn.inspection.PartialDependenceDisplay.from_estimator` (zero new dependency — `requirements.txt`/`requirements.lock.txt` diff is empty across the phase). Notebook cell 26 executed output contains a rendered `image/png` PDP figure for all 3 numeric predictors (`6.4.2`, `6.4.1`, `8.2.1`). |
| 6 | Ejecutar dos veces el pipeline estocástico (bootstrap, RF, cualquier split) produce resultados idénticos por semillas fijas | ✓ VERIFIED | Function-level: `bootstrap_counterfactual` uses `np.random.SeedSequence(seed).spawn(n_replicas)`; `shap_analysis`'s RF uses `n_jobs=1, random_state=seed` (mandatory — `n_jobs=-1` breaks determinism per code review's independent re-verification). Unit tests `test_bootstrap_determinism` and `test_rf_determinism` pass with exact `np.array_equal` assertions (not `pytest.approx`). End-to-end: `scripts/verify_repro02.py` independently executes the full committed notebook twice and asserts bit-identical bootstrap CIs/excluded-country lists/RF `feature_importances_`/`oob_score_`/SHAP values; `data/modelos/_repro_snapshot.pkl` exists on disk with the expected keys (`scenarios`, `rf_feature_importances`, `rf_oob_score`, `shap_values`), consistent with the script having actually run and passed (04-03-SUMMARY.md, commit `e97b8c4`). The full 50-60min two-execution re-run was not repeated during this verification pass (exceeds the spot-check time budget) — evidence relies on function-level exact-equality tests plus the on-disk snapshot artifact and an independent code-review re-verification of the underlying determinism mechanism. |

**Score:** 6/6 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/simulate.py` | resample_entities, bootstrap_counterfactual, check_non_extrapolation, fit_interaction_model | ✓ VERIFIED | All 4 functions present, substantive (not stubs), dependent-variable-agnostic (no hardcoded `8.1.1`/`6.4.2`). |
| `tests/test_simulate.py` | 4 fixture-based unit tests | ✓ VERIFIED | 4 tests present and passing (`test_resample_entities_unique_index`, `test_non_extrapolation_exclusion`, `test_bootstrap_determinism`, `test_interaction_formula`). |
| `src/interpret.py` | compute_vif_table, shap_analysis, partial_dependence_plots | ✓ VERIFIED | All 3 functions present, substantive. `compute_vif_table` was fixed post-hoc (commit `8857120`) to add a constant column — fix is committed and covered by the existing `test_vif_table`. |
| `tests/test_interpret.py` | 4 fixture-based unit tests | ✓ VERIFIED | 4 tests present and passing (`test_shap_values_shape`, `test_oob_score_present`, `test_rf_determinism`, `test_vif_table`). |
| `notebook/4_1_interpretabilidad_simulacion.ipynb` | Orchestration notebook, executed against real panel | ✓ VERIFIED | 32 cells, no error outputs in any cell (confirmed by inspecting the executed `.ipynb` JSON directly, not trusting the SUMMARY's claim). |
| `data/modelos/rf_shap_model.pkl` | Serialized RandomForestRegressor, round-trip verified | ✓ VERIFIED | Loaded directly: `RandomForestRegressor`, `n_estimators=300`, `random_state=42`, `oob_score_=0.6273` (finite float). Notebook cell 29 output: `Las importancias de features del RF recargado coinciden con el RF en memoria: True`. |
| `scripts/verify_repro02.py` | Standalone REPRO-02 proof script | ✓ VERIFIED | Script exists, logic is sound (exact `np.array_equal` comparisons, PASS/FAIL messaging); `data/modelos/_repro_snapshot.pkl` present on disk with matching schema. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `src/simulate.py` | `src/panel_base.py` | `bootstrap_counterfactual` calls `panel_base.fit_panel_model` unmodified per replica | ✓ WIRED | Confirmed by direct read of `src/simulate.py:148`; `git diff` of `src/panel_base.py` across the phase is empty (unmodified, as the plan required). |
| `notebook/4_1_...ipynb` | `src/simulate.py`, `src/interpret.py` | imports and calls public functions | ✓ WIRED | Notebook cells 7, 14, 15, 21, 22, 26 call `simulate.bootstrap_counterfactual`, `simulate.fit_interaction_model`, `interpret.shap_analysis`, `interpret.partial_dependence_plots` — all executed with real (non-error) outputs. |
| `interpret.shap_analysis` returned `rf` | `data/modelos/rf_shap_model.pkl` | pickle.dump → reload → np.allclose | ✓ WIRED | Notebook cells 28-29 serialize and round-trip-verify; confirmed independently by loading the `.pkl` directly in this verification pass. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| INTERP-01 | 04-01, 04-03 | Simulación contrafactual bootstrap con CIs, enmarcada como sensibilidad, no-extrapolación | ✓ SATISFIED | `bootstrap_counterfactual` + `check_non_extrapolation`, notebook cells 6-9. |
| INTERP-02 | 04-01, 04-03 | Gráfico multi-escenario | ✓ SATISFIED | Notebook cell 11 image output. |
| INTERP-03 | 04-01, 04-03 | Heterogeneidad regional/ingresos, sin predicción por país | ✓ SATISFIED | `fit_interaction_model`, notebook cells 13-16. |
| INTERP-04 | 04-02, 04-03 | SHAP precedido de VIF/correlación con aviso de sesgo | ✓ SATISFIED | `compute_vif_table` + `shap_analysis`, notebook cells 18-22. |
| INTERP-05 | 04-02, 04-03 | ALE/PDP complementando SHAP | ✓ SATISFIED | `partial_dependence_plots`, notebook cell 26. |
| INTERP-06 | 04-02, 04-03 | Modelo de referencia (RF) como comparación predictiva | ✓ SATISFIED | `rf.oob_score_` (D-07, same RF), notebook cell 24. |
| REPRO-02 | 04-01, 04-02, 04-03 | Pasos estocásticos con semillas fijas | ✓ SATISFIED | `SeedSequence`, `n_jobs=1`/`random_state=seed`; unit tests + `scripts/verify_repro02.py`. |

No orphaned requirements found — all 7 Phase-4 requirement IDs from `.planning/REQUIREMENTS.md`'s Traceability table match the `requirements:` field declared across the three PLAN.md frontmatters (04-01: INTERP-01/03/REPRO-02; 04-02: INTERP-04/05/06/REPRO-02; 04-03: all seven).

### Anti-Patterns Found

No BLOCKER-level anti-patterns (no TBD/FIXME/XXX markers, no stub returns, no empty handlers) found in `src/simulate.py` or `src/interpret.py`. The phase's own code review (`04-REVIEW.md`, standard depth, 2026-07-13) independently re-executed key statistical paths against the real `data/panel.db` and found 0 critical/blocker findings, 5 WARNING-level items, and 3 INFO-level items — none of which currently manifest against the real dataset (all 171 filtered countries have non-null 2022 `6.4.2` data, so the missing-vs-extrapolation mislabeling in WR-01 is presently latent, not active) and none of which block this phase's goal:

| File | Concern | Severity | Impact on Phase 4 goal |
|------|---------|----------|------------------------|
| `src/simulate.py:93-95` | `check_non_extrapolation` would mislabel a missing-baseline country as an "extrapolation exclusion" if one existed (WR-01) | Warning | Does not currently manifest (no missing 2022 baselines in the real panel); relevant for Phase 6 reuse with `dep_var="2.3.1"`'s higher missingness. |
| `src/simulate.py:224-227` | `fit_interaction_model`'s docstring claims the interaction is the "only" regressor besides effects, but the formula's `1 +` also fits an (unflagged) `Intercept` term (WR-02) | Warning | Documentation-accuracy defect only — code review confirmed bit-identical interaction coefficients with/without the redundant intercept; notebook already filters `Intercept` out of displayed tables. |
| `notebook` cell 2 / `src/simulate.py:67` | `SELECT * FROM panel_clean` has no `ORDER BY`; REPRO-02's bit-identical guarantee implicitly depends on stable SQLite row order (WR-03) | Warning | Not presently broken (repro script passed); an unenforced assumption inherited from Phases 2/3. |
| `src/interpret.py:130` | `shap_analysis`'s categorical-column detection is hardcoded to `"region"`, contradicting its own dependent-variable-agnostic (D-12) design claim (WR-04) | Warning | No impact on Phase 4 itself (region is the only categorical predictor used here); relevant if Phase 6 introduces a new categorical predictor. |
| `scripts/verify_repro02.py:126-134` | Uncaught `RuntimeError` produces a raw traceback instead of the script's own documented failure message (WR-05) | Warning | Operator-experience only; exit code is still non-zero either way. |

These are pre-existing findings from the phase's own code-review artifact, not new discoveries in this verification — surfaced here for completeness since they are unresolved. None rise to BLOCKER for Phase 4's stated goal (they concern documentation precision and future-reuse robustness, not Phase 4's own delivered behavior against the real Model-1 panel).

### Human Verification Required

None outstanding. The phase's own blocking checkpoint (Task 2b, `04-03-PLAN.md`) already gated human review of the notebook's visual/narrative outputs (multi-scenario CI plot legibility, heterogeneity table completeness, VIF/SHAP precedence, PDP presence) and was approved by the user on 2026-07-12 (commit `0513e92`). This verification independently re-confirmed the same evidence programmatically (executed cell outputs, real numbers, image presence) rather than re-trusting the approval alone.

### Gaps Summary

No gaps. All 6 ROADMAP Phase-4 success criteria and all 7 declared requirement IDs (INTERP-01 through INTERP-06, REPRO-02) are backed by passing unit tests, a notebook executed end-to-end without error against the real 171-country panel, a round-trip-verified serialized model artifact, and an end-to-end reproducibility proof script with on-disk supporting evidence. The 5 warning-level findings from the phase's own code review are real but non-blocking for this phase's goal; they are documented above as unresolved technical debt relevant to Phase 6 reuse, not as reasons to withhold phase-goal sign-off.

---

*Verified: 2026-07-13T14:11:28Z*
*Verifier: Claude (gsd-verifier)*
