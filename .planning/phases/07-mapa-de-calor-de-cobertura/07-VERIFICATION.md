---
phase: 07-mapa-de-calor-de-cobertura
verified: 2026-07-15T22:15:00Z
status: passed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 7: Mapa de Calor de Cobertura Verification Report

**Phase Goal:** Producir una figura estática (PNG) de cobertura/missingness que visualiza la presencia/ausencia de datos país × indicador × año para los 5 indicadores ODS ya ingeridos, calculada sobre los datos crudos (`raw_observations`, antes del filtro del 70% de la Fase 2), lista para el anexo de la memoria.
**Verified:** 2026-07-15T22:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `figuras/07_mapa_calor_cobertura.png` exists and shows a 5-indicator grid of country×year coverage sub-heatmaps (Roadmap SC1) | ✓ VERIFIED | File exists (566,566 bytes, tracked in git). Read/rendered the PNG directly — confirmed 5 subplots titled `6.4.2`, `6.4.1`, `8.1.1`, `8.2.1`, `2.3.1`, y-axis = country codes, x-axis = years 2000-2022, black horizontal separator lines between SDG-region groups, shared legend "Sin dato"/"Dato presente". |
| 2 | Coverage is computed from `raw_observations` (pre-filter), verifiably including country/indicator pairs `panel_clean` excludes (Roadmap SC2) | ✓ VERIFIED | Queried `data/panel.db` directly: `panel_exclusions` records ETH/2.3.1 as `excluded=1, reason=coverage_below_70pct_threshold, coverage_pct=0.174`. `raw_observations` for ETH/2.3.1 shows 4 non-null values across 2000-2022 (years 2014, 2016, 2019, 2021) — exactly the sparse pattern visible in the rendered heatmap's 2.3.1 column, proving the figure surfaces raw presence for pairs the 70% filter drops from `panel_clean`. |
| 3 | The 5 ODS indicator codes (6.4.2, 6.4.1, 8.1.1, 8.2.1, 2.3.1) are identifiable in the figure (Roadmap SC3) | ✓ VERIFIED | Confirmed visually — each subplot has an `ax.set_title(indicator)` matching `coverage.INDICATOR_CODES`. |
| 4 | The figure regenerates reproducibly from a re-executable notebook, with no modification to `src/dashboard/` (Roadmap SC4) | ✓ VERIFIED | Independently re-ran `jupyter nbconvert --to notebook --execute notebook/7_1_mapa_calor_cobertura.ipynb` — completed with no cell error, regenerated `figuras/07_mapa_calor_cobertura.png` byte-identical in size (566,566 bytes) to the committed version. `git log --oneline` for `src/dashboard/`, `src/db.py`, `src/panel_build.py` shows no commits from Phase 7 (`b525880`, `76adf03`, `e95f296`); `git status --porcelain` on those paths is clean. |
| 5 | `build_presence_matrix` unifies "row wholly absent" and "row present with value IS NULL" into the same missing state (D-04) | ✓ VERIFIED | `pytest tests/test_coverage.py::test_build_presence_matrix_absent_row_is_missing` and `::test_build_presence_matrix_null_value_is_missing` both pass (re-ran independently, 5/5 green). Source (`src/coverage.py:33-53`) implements via `pivot()`+`reindex()`+`.notna()`, no per-cell branching. |
| 6 | `ordered_countries_with_boundaries` groups countries by SDG region and returns correct boundary indices (D-03) | ✓ VERIFIED (with a known non-blocking edge-case gap — see Anti-Patterns) | `pytest tests/test_coverage.py::test_ordered_countries_with_boundaries_groups_by_region` passes. Correct for the actual production dataset (215/215 ingested countries resolve to a non-null `region`; confirmed live against `data/panel.db`). `07-REVIEW.md` (WR-01) documents a NaN-unsafe `!=` comparison that would mis-render separators if 2+ countries with a missing region both entered the dataset — not currently triggered, not fixed. |
| 7 | The coverage signal is computed from `raw_observations` + `country_reference` only, never from `panel_clean`/`panel_exclusions` (COVER-01, Pitfall 3) | ✓ VERIFIED | `grep -n "panel_clean\|panel_exclusions" src/coverage.py` → 0 matches. `grep -c "panel_clean\|panel_exclusions" notebook/7_1_mapa_calor_cobertura.ipynb` → 0 matches. `pytest tests/test_coverage.py::test_coverage_module_never_reads_panel_clean` passes (asserts both functions succeed against an engine with no `panel_clean` table present). |

**Score:** 7/7 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/coverage.py` | Pure module: `build_presence_matrix`, `ordered_countries_with_boundaries`, `INDICATOR_CODES`, `YEARS` | ✓ VERIFIED | Exists, imports cleanly, exposes exactly the required symbols with correct values (`INDICATOR_CODES == ["6.4.2","6.4.1","8.1.1","8.2.1","2.3.1"]`, `YEARS == list(range(2000,2023))`). No `_main`/`__main__` CLI entry (D-05 compliant). |
| `tests/test_coverage.py` | Five named COVER-01 unit tests | ✓ VERIFIED | All 5 contract-named tests present and passing (re-run independently: `5 passed in 1.96s`). Full test suite unaffected (no regression check needed beyond this file per scope, but nothing in `src/coverage.py` touches shared modules). |
| `notebook/7_1_mapa_calor_cobertura.ipynb` | Thin orchestrator loading raw data, calling `src.coverage`, rendering + saving the PNG | ✓ VERIFIED | 7 cells, imports `from src import db, coverage`, calls `coverage.build_presence_matrix` 5x (once per indicator) and `coverage.ordered_countries_with_boundaries` 1x, exactly one `fig.savefig(...)` call (dpi=300) to `figuras/07_mapa_calor_cobertura.png`. Re-executed end-to-end with nbconvert — no errors. |
| `figuras/07_mapa_calor_cobertura.png` | The single static PNG deliverable | ✓ VERIFIED | Exists, tracked in git, visually confirmed to match all 4 roadmap success criteria. Regenerates byte-identical on independent re-execution. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `src/coverage.py::build_presence_matrix` | `raw_observations` (DataFrame arg) | pure-function pivot/reindex/notna on a caller-supplied DataFrame | ✓ WIRED | Function signature takes `raw_observations: pd.DataFrame` directly; notebook Cell 2 reads it via `pd.read_sql("SELECT * FROM raw_observations", engine)` (fixed-literal SQL) and passes it into Cell 4's loop. |
| `src/coverage.py::ordered_countries_with_boundaries` | `country_reference` (DataFrame arg) | left-restrict + sort on `country_code`, mirroring `build_clean_panel`'s join shape | ✓ WIRED | Notebook Cell 3 reads `country_reference` via fixed-literal SQL and calls the function once; output (`ordered_countries`, `boundaries`) consumed in Cell 4's plotting loop. |
| `notebook Cell 6 (fig.savefig)` | `figuras/07_mapa_calor_cobertura.png` | direct filesystem write, fixed literal path | ✓ WIRED | Confirmed via independent nbconvert re-execution: `Saved: ...figuras\07_mapa_calor_cobertura.png` printed, file present after execution, byte-identical to the committed artifact. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `figuras/07_mapa_calor_cobertura.png` | `matrix` (per-indicator presence grid) | `pd.read_sql("SELECT * FROM raw_observations", engine)` → `coverage.build_presence_matrix` | Yes — live DB query, 18,086 raw rows, 215 countries, 24,725 total heatmap cells (215×23×5), 16,834 present / 7,891 missing (verified via independent notebook re-execution output) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Five COVER-01 unit tests pass | `.venv/Scripts/python.exe -m pytest tests/test_coverage.py -v` | `5 passed in 1.96s` | ✓ PASS |
| Notebook runs end-to-end and regenerates the PNG | `.venv/Scripts/python.exe -m jupyter nbconvert --to notebook --execute notebook/7_1_mapa_calor_cobertura.ipynb` | Completed with no cell error; `figuras/07_mapa_calor_cobertura.png` regenerated, identical size to committed version (566,566 bytes) | ✓ PASS |
| Raw-coverage sanity check reflects pre-filter data (SC2) | Notebook Cell 6 output + direct DB query on `panel_exclusions`/`raw_observations` for ETH/2.3.1 | `Total: 24725, Present: 16834, Missing: 7891`; ETH/2.3.1 shows 4 non-null raw values despite being `excluded=1 (coverage_below_70pct_threshold)` in `panel_exclusions` | ✓ PASS |
| `coverage.py` never references `panel_clean`/`panel_exclusions` | `grep -n "panel_clean\|panel_exclusions" src/coverage.py` | No matches | ✓ PASS |
| No modifications to dashboard/pipeline modules | `git status --porcelain src/dashboard/ src/db.py src/panel_build.py` + `git log` on Phase 7 commits | Clean; no Phase 7 commit touches these paths | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| COVER-01 | 07-01-PLAN.md | Genera un mapa de calor país×indicador×año sobre datos crudos, antes del filtro del 70% | ✓ SATISFIED | `src/coverage.py` + 5 passing unit tests; PNG visually confirms raw-data coverage (Truth 2, ETH/2.3.1 evidence) |
| COVER-02 | 07-02-PLAN.md | Exporta la figura como PNG estático en `figuras/` sin cambios al dashboard Streamlit | ✓ SATISFIED | `figuras/07_mapa_calor_cobertura.png` exists, reproducible via notebook, no `src/dashboard/` modifications |

No orphaned requirements — `REQUIREMENTS.md` maps exactly COVER-01 and COVER-02 to Phase 7, both claimed in plan frontmatter (`requirements: [COVER-01]` in 07-01, `requirements: [COVER-02]` in 07-02).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/coverage.py` | 76-80 | NaN-unsafe `region != prev_region` comparison in `ordered_countries_with_boundaries` (documented in `07-REVIEW.md` WR-01) | ⚠️ Warning | Latent bug: would mis-draw region separator lines if 2+ countries with a missing/NaN `region` both entered the dataset. Not triggered today (215/215 ingested countries have a non-null region; `ATA`, the one NaN-region country in `country_reference`, has zero rows in `raw_observations`). Does not affect the current committed PNG. Not fixed as of this verification — no follow-up commit or override recorded. |
| `src/coverage.py` | 69-73 | Countries in `countries` but absent from `country_reference` are silently dropped with no log/warning (documented in `07-REVIEW.md` WR-02) | ⚠️ Warning | Inconsistent with the codebase's established "never silently drop" convention (`src/ingesta/countries.py` D-16). Not triggered today (all 215 raw-data countries exist in `country_reference`). Not fixed. |

No debt markers (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) found in `src/coverage.py`, `tests/test_coverage.py`, or `notebook/7_1_mapa_calor_cobertura.ipynb`.

Both warnings are pre-existing, documented, currently-inert edge-case robustness gaps identified by the phase's own code review (`07-REVIEW.md`, status `issues_found`, 2 warnings). Neither affects any of the 4 Roadmap Success Criteria for the actual delivered dataset — verified live against `data/panel.db` that the triggering conditions (2+ countries sharing a missing region; a `raw_observations` country absent from `country_reference`) do not currently occur. They are flagged here as recommended follow-up work, not phase-blocking gaps.

### Human Verification Required

None. All roadmap Success Criteria were independently verified programmatically and visually (the PNG was read and inspected directly as part of this verification) — no items require human judgment beyond what has already occurred (the phase's own `checkpoint:human-verify` gate in 07-02-PLAN.md Task 2, approved by the user).

### Gaps Summary

No gaps blocking phase goal achievement. All 4 Roadmap Success Criteria are met and independently verified (not merely SUMMARY-claimed): the PNG exists with the correct 5-indicator/country/year structure, the raw-data (pre-filter) nature of the coverage signal is concretely proven against `panel_exclusions` data, the 5 ODS indicators are identifiable, and the notebook reproduces the PNG byte-identically on independent re-execution with zero modification to dashboard/pipeline files.

Two non-blocking, pre-existing code-review warnings (WR-01 NaN-unsafe region comparison, WR-02 silent country drop) remain unresolved in `src/coverage.py`. They do not affect the current deliverable but are latent correctness risks for future re-ingestion/crosswalk changes. Recommended as a small follow-up fix (not required to close Phase 7, since the roadmap's Success Criteria are about the delivered figure, which is correct for the current dataset).

---

_Verified: 2026-07-15T22:15:00Z_
_Verifier: Claude (gsd-verifier)_
