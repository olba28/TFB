---
phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita
plan: 02
subsystem: modeling
tags: [linearmodels, panel-data, fixed-effects, hausman-test, pesaran-cd-test, jupyter, robustness-check]

# Dependency graph
requires:
  - phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita
    plan: "03-01"
    provides: "src/panel_base.py: filter_by_exclusions, fit_panel_model, compare_specifications, hausman_test, pesaran_cd_test, choose_cov_type"
provides:
  - "notebook/3_1_modelo1_pib.ipynb: live base FE fit, pooled/RE/FE comparison, Hausman result, Pesaran-CD-driven SE choice, COVID-excluded robustness check, limitations section"
  - "data/modelos/model1_gdp.pkl: the fitted base FE model, reloadable without refitting"
affects: ["04 (Interpretabilidad/Simulación -- consumes model1_gdp.pkl directly)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Notebook-embedded computed-value narrative via IPython.display.Markdown(f\"...\") for cells that must cite real fitted numbers (Pesaran p-value, Hausman statistic, robustness comparison) rather than static placeholder prose -- keeps the acceptance criteria's 'actual computed value, not a placeholder' requirement true by construction"
    - "Hausman-test RE fit built directly via linearmodels.panel.RandomEffects(...).fit(cov_type=..., **cov_config) inline in the notebook, deliberately reusing the SAME cov_type/cov_config variables as the base model's final refit -- not panel_base.py's compare_specifications (which always uses unadjusted SEs for the point-estimate table) and not a third, independently-chosen SE type"

key-files:
  created:
    - notebook/3_1_modelo1_pib.ipynb
  modified: []

key-decisions:
  - "Two atomic task commits both touch the same single notebook file -- Task 1 built and executed cells 1-11 (bootstrap through pkl reload-verification) and committed first; Task 2 appended cells 12-15 (robustness check + limitations) to the already-committed file and was executed/committed second, per the plan's explicit 'append cells, do not create a second notebook file' instruction"
  - "Jupyter kernel spec set to the project's already-registered 'tfb-venv' kernel (matching notebook/2_1_construccion_panel_eda.ipynb's precedent) -- the default 'python3' kernelspec nbformat generates by default pointed at the system Python, which lacks linearmodels, and would have failed nbconvert --execute"
  - "Live Pesaran CD test on the real two-way-effects residuals rejects H0 (p=0.0014) at N=171 countries -- selecting Driscoll-Kraay (kernel/bartlett) SEs via choose_cov_type. Per Plan 03-01's forwarded nuance, this is documented in the notebook as consistent with (not necessarily caused by) the known De Hoyos & Sarafidis 2006 two-way-FE time-demeaning artifact, rather than presented as unambiguous evidence of true cross-sectional dependence"
  - "Hausman test (both sides fit with the same chosen cov_type=\"kernel\") fails to reject H0 (p=0.6125) -- FE remains the specification regardless, per D-03's already-locked base-spec decision; the Hausman result is reported as documented justification, not a live branch point"
  - "COVID-excluded (2000-2019) robustness sub-sample: coefficient sign unchanged, significance conclusion unchanged (not significant at 5% in either sample) -- explicit 'cualitativamente consistente' verdict"

requirements-completed: [MODEL1-02, MODEL1-05, MODEL1-06, REPRO-03]

coverage:
  - id: D1
    description: "Base two-way FE model (8.1.1 ~ 6.4.2) fit against the real, D-01/D-02-filtered panel_clean/panel_exclusions data (171 countries, 3933 observations -- within 10% of 03-RESEARCH.md Finding 4's ~171/~3879 expectation)"
    requirement: "MODEL1-02"
    verification:
      - kind: manual
        ref: "notebook/3_1_modelo1_pib.ipynb -- executed top-to-bottom twice in a row via jupyter nbconvert --execute --inplace, no exceptions"
        status: pass
    human_judgment: true
  - id: D2
    description: "Pooled/RE/FE comparison table (compare_specifications) and Hausman test (hausman_test, both sides fit with the same Pesaran-selected cov_type) documented with real computed statistics"
    requirement: "MODEL1-02"
    verification:
      - kind: manual
        ref: "notebook/3_1_modelo1_pib.ipynb cells 7-8 (Model Comparison table, Hausman H=0.2566, p=0.6125)"
        status: pass
    human_judgment: true
  - id: D3
    description: "COVID-excluded (2000-2019) robustness sub-sample fit and its qualitative consistency with the base model explicitly assessed with real computed coefficients"
    requirement: "MODEL1-05"
    verification:
      - kind: manual
        ref: "notebook/3_1_modelo1_pib.ipynb Task 2 cells -- base coef -0.00014 (p=0.8238) vs robustness coef -0.00044 (p=0.4694), same sign, same significance conclusion, verdict 'cualitativamente consistente'"
        status: pass
    human_judgment: true
  - id: D4
    description: "data/modelos/model1_gdp.pkl exists and is proven, in-notebook, to reload and produce identical parameters without refitting"
    requirement: "MODEL1-06"
    verification:
      - kind: automated
        ref: "notebook/3_1_modelo1_pib.ipynb reload-verification cell -- np.allclose(reloaded.params, final_fe_results.params) printed True, asserted"
        status: pass
    human_judgment: false
  - id: D5
    description: "'Limitaciones / Amenazas a la validez' section explicitly discusses reverse causality (causalidad inversa) and endogeneity (endogeneidad), connecting both to Phase 4's counterfactual simulation being framed as sensitivity analysis"
    requirement: "REPRO-03"
    verification:
      - kind: manual
        ref: "notebook/3_1_modelo1_pib.ipynb final markdown cell -- grep -c Limitaciones == 1, both required substrings present"
        status: pass
    human_judgment: true

duration: 45min
completed: 2026-07-12
status: complete
---

# Phase 3 Plan 2: Live Model 1 Fit, Diagnostics, Robustness Check, and Limitations Summary

**`notebook/3_1_modelo1_pib.ipynb` -- the real-data application of Plan 03-01's `panel_base.py`: a two-way fixed-effects fit of GDP-per-capita growth (8.1.1) on water stress (6.4.2) across 171 countries/3,933 observations, with a Pesaran-CD-driven Driscoll-Kraay SE choice, a Hausman-justified FE-vs-RE comparison, a COVID-excluded robustness check, and a reverse-causality/endogeneity limitations section, plus the serialized `data/modelos/model1_gdp.pkl` model.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-12
- **Tasks:** 2
- **Files modified:** 1 (notebook, appended across both tasks) + 1 gitignored artifact (`data/modelos/model1_gdp.pkl`)

## Accomplishments

- Loaded the full `panel_clean`/`panel_exclusions` tables (no `LIMIT`) and applied `panel_base.filter_by_exclusions` -- confirmed 171 countries / 3,933 observations survive the D-01/D-02 coverage filter, within 10% of 03-RESEARCH.md Finding 4's ~171/~3,879 expectation (1.4% obs drift, 0% country drift)
- Ran the Pesaran CD test on a provisional clustered-SE fit's residuals (CD=3.2042, p=0.0014 -- rejects H0), selected Driscoll-Kraay SEs (`cov_type="kernel"`, `kernel="bartlett"`) via `choose_cov_type`, and documented the known De Hoyos & Sarafidis time-demeaning-artifact nuance (forwarded from Plan 03-01) rather than treating the rejection as unambiguous evidence of true cross-sectional dependence
- Refit the base FE model with the chosen SE type, produced the pooled/RE/FE comparison table (`compare_specifications`), and ran the Hausman test with the RE side fit using the *identical* `cov_type`/`cov_config` as the base model (H=0.2566, p=0.6125 -- fails to reject H0; FE remains the specification per D-03 regardless)
- Serialized `final_fe_results` to `data/modelos/model1_gdp.pkl` and proved, in the same notebook run, that reloading it reproduces identical `.params` (`np.allclose` == `True`, asserted)
- Ran the D-04 COVID-excluded (2000-2019) robustness sub-sample with the same SE type, confirmed the coefficient sign and significance conclusion are unchanged relative to the base model, and stated an explicit "cualitativamente consistente" verdict with the real computed coefficients
- Wrote a "Limitaciones / Amenazas a la validez" section explicitly covering reverse causality and omitted-variable endogeneity, connecting both to why Phase 4's counterfactual simulation is framed (per `PROJECT.md`) as a sensitivity analysis rather than a causal prediction

## Task Commits

1. **Task 1: Live base fit, pooled/RE/FE comparison, Hausman, SE choice, and serialization** - `01570a3` (feat) -- built and executed notebook cells 1-11 (bootstrap through pkl reload-verification proof)
2. **Task 2: Robustness check (COVID-excluded sub-sample) and limitations section** - `5635f9d` (feat) -- appended and executed notebook cells 12-15 on top of Task 1's committed notebook

**Plan metadata:** (this commit, made after this SUMMARY)

## Files Created/Modified

- `notebook/3_1_modelo1_pib.ipynb` (new) -- the primary artifact: sys.path bootstrap (mirrors `2_1_construccion_panel_eda.ipynb`'s pattern) + imports, full-table load of `panel_clean`/`panel_exclusions`, `filter_by_exclusions` + Finding-4 sanity check, provisional clustered fit + Pesaran CD test + `choose_cov_type` + narrative markdown citing the real p-value, final refit with the chosen SE type, `compare_specifications` table, a separate same-cov_type `RandomEffects` fit + `hausman_test` + narrative markdown, `pickle.dump`/reload-verification, the D-04 2000-2019 robustness refit + comparison narrative, and the "Limitaciones / Amenazas a la validez" section.
- `data/modelos/model1_gdp.pkl` (new, gitignored via the existing bare `*.pkl` rule) -- the serialized fitted base FE model, reloadable without refitting; not committed to git per the plan's threat model (T-03-02-01: fixed hardcoded path, no external-input path construction) and CLAUDE.md's "Model persistence: not versioned" constraint.

## Decisions Made

- Split the plan's single-notebook output into two staged builds so each task's commit is atomic and contains only that task's cells: Task 1 built/executed cells 1-11 and committed; Task 2's script then read the already-committed notebook, appended cells 12-15, re-executed the full notebook top-to-bottom, and committed the diff. This satisfies both the plan's "append cells, do not create a second notebook file" instruction and the executor's one-commit-per-task requirement.
- Used `display(Markdown(f"..."))` code cells (rather than static markdown cells with placeholder text) everywhere the acceptance criteria required citing "the actual computed value, not a placeholder" (Pesaran p-value + SE-choice justification, Hausman statistic + conclusion, robustness coefficient comparison + qualitative-consistency verdict) -- these render as narrative markdown in the executed notebook but are generated from live fitted-model values, so the claims are provably non-placeholder by construction, not just by convention.
- Set the notebook's `kernelspec` to the project's already-registered `tfb-venv` kernel (matching `2_1_construccion_panel_eda.ipynb`) rather than nbformat's default `python3` kernelspec, which points at the system Python (lacks `linearmodels` and would fail `nbconvert --execute`).
- Built the Hausman-specific `RandomEffects` fit directly via `linearmodels.panel.RandomEffects(...).fit(cov_type=chosen_cov_type, **chosen_cov_config)` in the notebook (per the plan's explicit "or directly via `RandomEffects(...).fit(...)`" allowance) rather than adding a new public function to `panel_base.py` -- keeps `panel_base.py` unmodified from Plan 03-01, satisfying D-05's "Phase 6 reuses it unmodified" intent.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Default `python3` kernelspec lacked `linearmodels`, causing `ModuleNotFoundError` on first execution attempt**
- **Found during:** Task 1, first `jupyter nbconvert --execute --inplace` attempt
- **Issue:** `nbformat.v4.new_notebook()`'s default metadata pointed at the `python3` kernelspec (system Python), which does not have the project's dependencies (`linearmodels`, `pandas`, etc.) installed -- the notebook failed at the very first import cell with `ModuleNotFoundError: No module named 'linearmodels'`.
- **Fix:** Set the notebook's `kernelspec` metadata to `{"display_name": "TFB (.venv)", "name": "tfb-venv"}`, matching the already-registered project kernel `2_1_construccion_panel_eda.ipynb` uses (confirmed via `jupyter kernelspec list`).
- **Files modified:** `notebook/3_1_modelo1_pib.ipynb` (metadata only, before any commit)
- **Verification:** re-ran `nbconvert --execute --inplace` -- completed with no exceptions, twice in a row
- **Committed in:** `01570a3` (Task 1 commit) -- the fix was applied before the first commit, not as a separate correction commit

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking issue, resolved before any commit)
**Impact on plan:** None on the plan's substance -- purely a notebook-execution-environment fix; all statistical logic, SE choice, Hausman comparison, robustness check, and limitations content match the plan's `<behavior>`/`<action>` specifications exactly.

## Issues Encountered

None beyond the deviation documented above. One non-issue investigated during execution: an initial `grep`/`print`-based check of notebook output appeared to show corrupted accented characters (`�` in place of `í`/`ó`/`ñ`) when displayed through this session's Windows terminal (cp1252 codepage, confirmed via `chcp`). Direct inspection of the notebook file's raw bytes (`\xc3\xad`, `\xc3\xb1`, etc.) confirmed the actual file content is correctly UTF-8 encoded -- the apparent corruption was a terminal-display artifact only, not real data loss, and no fix was needed to the notebook itself.

## User Setup Required

None - no external service configuration required. The `tfb-venv` Jupyter kernel used to execute this notebook was already registered from Phase 2's setup.

## Next Phase Readiness

- `data/modelos/model1_gdp.pkl` is ready for Phase 4 (Interpretabilidad/Simulación) to load directly without refitting, per the plan's integration point.
- MODEL1-02, MODEL1-05, MODEL1-06, and REPRO-03 are all satisfied; Phase 3's remaining requirements (MODEL1-01, MODEL1-03, MODEL1-04) were already completed by Plan 03-01.
- The Pesaran-CD/two-way-FE time-demeaning-artifact nuance is now documented twice (Plan 03-01's SUMMARY and this notebook's own narrative) -- future phases interpreting this model's SE methodology should read the notebook's own markdown cell directly rather than re-deriving the caveat.

---
*Phase: 03-modelo-1-regresi-n-de-panel-pib-per-c-pita*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: notebook/3_1_modelo1_pib.ipynb
- FOUND: data/modelos/model1_gdp.pkl (gitignored, confirmed present on disk)
- FOUND commit: 01570a3 (Task 1)
- FOUND commit: 5635f9d (Task 2)
