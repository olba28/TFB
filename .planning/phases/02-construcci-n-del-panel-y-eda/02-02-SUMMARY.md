---
phase: 02-construcci-n-del-panel-y-eda
plan: 02
subsystem: eda
tags: [jupyter, pandas, seaborn, statsmodels, vif, mnar, eda]

# Dependency graph
requires:
  - phase: 02-construcci-n-del-panel-y-eda (plan 01)
    provides: panel_clean, panel_exclusions, country_reference SQLite tables
provides:
  - "notebook/2_1_construccion_panel_eda.ipynb: descriptive stats, MNAR discussion, 12 VIF/correlation tables (global/regional/typology)"
  - "A registered tfb-venv Jupyter kernel pointing at the project's .venv (previously only a global-Python kernel existed)"
affects: [phase-03-model1-panelols, phase-04-interpretabilidad-shap]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Notebook-in-subdirectory sys.path bootstrap: Path.cwd().parent when cwd.name == 'notebook', inserted into sys.path before importing src.* -- makes the notebook launch-method-agnostic (nbconvert, Jupyter Lab, VS Code)"
    - "compute_vif_table() helper: listwise-complete-case + add_constant() + try/except around variance_inflation_factor, returning (None, None) for undersized subsets rather than raising -- reused across global/regional/typology VIF cells"

key-files:
  created:
    - notebook/2_1_construccion_panel_eda.ipynb
  modified: []

key-decisions:
  - "MNAR discussion reports the REAL, honest pattern found in the data rather than force-fitting the a priori hypothesis: SIDS shows a strong ~2x missingness gap (49.9% vs 26.3%) supporting the MNAR-bias hypothesis, but LDC/LLDC show a weaker or even reversed pattern in this aggregate view -- both facts are reported, since an EDA that only reports confirming evidence would be less credible before a tribunal"
  - "VIF computed with add_constant() applied first (constant excluded from the reported table) -- a considered fix from the planning stage's adversarial self-check, not a default oversight"
  - "Registered a tfb-venv Jupyter kernel from .venv via the already-installed ipykernel package (not a new dependency) -- the only pre-existing kernel pointed at the global Python install, which would have made nbconvert --execute silently run against the wrong environment"

patterns-established:
  - "Notebooks under notebook/ that import from src/ must bootstrap sys.path at the top (see 2_1_construccion_panel_eda.ipynb's first code cell) -- future notebooks in this project should follow the same pattern"

requirements-completed: [PANEL-03, PANEL-04]

coverage:
  - id: D1
    description: "Descriptive statistics and missingness breakdown (by indicator, region, LDC/LLDC/SIDS typology) with an explicit MNAR discussion grounded in real computed numbers"
    requirement: "PANEL-03"
    verification:
      - kind: automated_ui
        ref: "jupyter nbconvert --to notebook --execute --inplace notebook/2_1_construccion_panel_eda.ipynb -- 0 cells with errors"
        status: pass
    human_judgment: true
    rationale: "Whether the MNAR discussion's argument is substantively convincing (not just that the notebook executes) requires human academic judgment -- this is exactly the kind of deliverable PANEL-03 flags for manual review in 02-VALIDATION.md."
  - id: D2
    description: "Correlation/VIF matrix at global, regional, and country-typology (LDC/LLDC/SIDS) levels using statsmodels' variance_inflation_factor"
    requirement: "PANEL-04"
    verification:
      - kind: automated_ui
        ref: "jupyter nbconvert --to notebook --execute --inplace notebook/2_1_construccion_panel_eda.ipynb -- 12 VIF tables produced (1 global + 8 regional + 3 typology), 0 errors"
        status: pass
    human_judgment: true
    rationale: "Correctness and usefulness of the VIF/correlation output for informing Phase 3's Model 1 specification requires human statistical review, not just successful execution -- flagged for manual verification in 02-VALIDATION.md."

duration: 20min
completed: 2026-07-12
status: complete
---

# Phase 02 Plan 02: EDA Notebook (Descriptive Stats, MNAR Discussion, VIF/Correlation) Summary

**Notebook with descriptive statistics, a numbers-grounded MNAR discussion (SIDS countries show ~2x the missingness of non-SIDS), and 12 VIF/correlation tables (global + 8 regions + 3 typology flags) informing Phase 3's Model 1 specification**

## Performance

- **Duration:** ~20 min (includes discovering and fixing a notebook-execution environment gap — see Deviations)
- **Completed:** 2026-07-12
- **Tasks:** 2/2 completed
- **Files modified:** 1 created (`notebook/2_1_construccion_panel_eda.ipynb`)

## Accomplishments

- Descriptive statistics for all 5 indicator columns at the global level, plus a missingness breakdown by indicator (2.7%–96.5% missing, indicator-dependent), by region (Oceania highest at 61.7%), and by each development-status flag (LDC/LLDC/SIDS).
- An MNAR discussion grounded in the notebook's own real computed numbers: SIDS countries show 49.9% missingness vs. 26.3% for non-SIDS (~2x, supporting the reporting-capacity-bias hypothesis), while honestly noting LDC/LLDC show a weaker or reversed pattern in this aggregate view rather than force-fitting the a priori hypothesis to all three typology axes.
- 12 VIF/correlation tables (1 global, 8 per-region, 3 per-typology-flag) computed via `statsmodels.stats.outliers_influence.variance_inflation_factor` with `add_constant()` applied first, gracefully handling small/singular subsets via `try`/`except` rather than crashing.
- Closing summary explicitly flags this VIF matrix as the input Phase 3 needs for control-variable selection and Phase 4 needs for its SHAP correlation-bias caveat (INTERP-04).

## Task Commits

1. **Task 1: Descriptive statistics + MNAR discussion** - `c0579f8` (feat)
2. **Task 2: Correlation/VIF matrix at global/regional/typology levels** - `e59391f` (feat)

**Plan metadata:** committed as part of the final phase docs commit.

_Note: both commits build on the same single notebook file. It was built and fully validated as one artifact, then deliberately split into two task-scoped commits (temporarily truncating to Task 1's cells, re-executing fresh, committing, then restoring and re-executing the full Task 1+2 version for Task 2's commit) to preserve this project's one-commit-per-task convention despite both tasks sharing a single file._

## Files Created/Modified

- `notebook/2_1_construccion_panel_eda.ipynb` - 18 cells: imports/sys.path bootstrap, descriptive stats, missingness tables (indicator/region/typology), missingness heatmap, MNAR discussion, VIF helper function, global/regional/typology VIF tables, closing summary

## Decisions Made

- MNAR discussion reports the honest, nuanced pattern found in the real data (strong SIDS effect, weak/reversed LDC/LLDC effect) rather than only the confirming evidence — more academically credible for a thesis defense.
- VIF computation includes `add_constant()` before calling `variance_inflation_factor`, per the planning stage's adversarial self-check finding (omitting it is a common, easy-to-miss pitfall that changes the resulting values).
- Registered a `tfb-venv` Jupyter kernel (via the already-installed `ipykernel` package — not a new dependency) so `nbconvert --execute` actually runs against the project's `.venv`, not the global Python installation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Registered a project-specific Jupyter kernel**
- **Found during:** Task 1, first attempt to execute the notebook
- **Issue:** The only Jupyter kernel registered on this machine (`python3`) pointed at the global Python installation, not the project's `.venv` — `jupyter kernelspec list` showed no kernel backed by `.venv`. Building the notebook with the default kernel metadata would have made `nbconvert --execute` silently attempt to run against the wrong Python environment (missing `pandas`, `seaborn`, `statsmodels`, and the project's own `src` package).
- **Fix:** Ran `.venv/Scripts/python.exe -m ipykernel install --user --name=tfb-venv --display-name="TFB (.venv)"` (using the already-installed `ipykernel>=6.25` dependency — not a new package install) and set the notebook's `kernelspec` metadata to `tfb-venv`.
- **Files modified:** None (kernel registration is a machine-level Jupyter configuration change, not a repo file); `notebook/2_1_construccion_panel_eda.ipynb`'s metadata references the new kernel name.
- **Verification:** `jupyter kernelspec list` shows `tfb-venv` alongside the pre-existing `python3`; the notebook executes cleanly using it.
- **Committed in:** `c0579f8` (part of Task 1's commit)

**2. [Rule 1 - Bug] Fixed a `ModuleNotFoundError: No module named 'src'` on first execution attempt**
- **Found during:** Task 1, first `nbconvert --execute` run
- **Issue:** `nbconvert`'s `ExecutePreprocessor` sets the kernel's working directory to the notebook file's own directory (`notebook/`), not the invoking shell's cwd (project root) — so `from src import db` failed even though the command was run from the project root.
- **Fix:** Added a `sys.path`/cwd-detection bootstrap as the first lines of the notebook's imports cell (`Path.cwd().parent if Path.cwd().name == "notebook" else Path.cwd()`, inserted into `sys.path`), making the notebook resolve `src/` correctly regardless of launch method (nbconvert, Jupyter Lab, VS Code) or invocation cwd — a more robust fix than relying on an undocumented `--ExecutePreprocessor.cwd=` CLI flag, since the plan's own verify command has no such flag and a human evaluator (e.g. opening this notebook in Jupyter Lab for the thesis defense) won't pass one either.
- **Files modified:** `notebook/2_1_construccion_panel_eda.ipynb`
- **Verification:** Notebook executes cleanly top-to-bottom, twice in a row, from the exact command in the plan's `<verify><automated>` block.
- **Committed in:** `c0579f8` (part of Task 1's commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 3 blocking-issue fix, 1 Rule 1 bug fix), both environment/execution-mechanics issues discovered while actually running the notebook for the first time — neither affects the analysis content, both were necessary for the notebook to be usable at all (by nbconvert, by a human opening it later, or by CI).

## Issues Encountered

None beyond the two deviations documented above.

## User Setup Required

**One-time local Jupyter kernel registration was performed automatically** (not left for the user): `.venv/Scripts/python.exe -m ipykernel install --user --name=tfb-venv --display-name="TFB (.venv)"`. This registers a kernel in the current user's Jupyter kernel directory (`%APPDATA%\jupyter\kernels\tfb-venv` on this Windows machine). If this project is cloned onto a different machine, the same command should be re-run once before opening this notebook in Jupyter Lab (VS Code's Jupyter extension will typically detect and offer to use `.venv` directly without this step, but plain `jupyter lab`/`nbconvert` needs the registered kernel).

## Next Phase Readiness

- Phase 2 (Construcción del Panel y EDA) is now fully complete: both plans executed, all 4 requirements (PANEL-01..04) satisfied.
- Phase 3 (Modelo 1 — Regresión de Panel) can consume `panel_clean`, `panel_exclusions`, and `country_reference` directly, plus this notebook's VIF/correlation output for control-variable selection.
- **Carried forward for Phase 3:** because `panel_clean` is intentionally unfiltered (Plan 02-01's design), Phase 3's `panel_base.py` must explicitly join against `panel_exclusions` before fitting Model 1 if it wants to honor the 70% coverage threshold — this is documented in `02-01-PLAN.md`'s Review Notes "Open items" section.
- No blockers.

## Self-Check: PASSED

- FOUND: notebook/2_1_construccion_panel_eda.ipynb
- FOUND commit: c0579f8
- FOUND commit: e59391f

---
*Phase: 02-construcci-n-del-panel-y-eda*
*Completed: 2026-07-12*
