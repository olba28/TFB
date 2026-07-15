---
phase: 07-mapa-de-calor-de-cobertura
reviewed: 2026-07-15T19:59:05Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/coverage.py
  - tests/test_coverage.py
  - notebook/7_1_mapa_calor_cobertura.ipynb
  - figuras/07_mapa_calor_cobertura.png
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-07-15T19:59:05Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed `src/coverage.py` (the two pure-transform functions `build_presence_matrix` and
`ordered_countries_with_boundaries`), `tests/test_coverage.py`, the orchestrating notebook
`notebook/7_1_mapa_calor_cobertura.ipynb`, and the resulting static figure
`figuras/07_mapa_calor_cobertura.png`.

`build_presence_matrix` is sound: it relies on `raw_observations`'
`UNIQUE(country_code, year, indicator_code)` constraint (verified in `src/db.py`) to
guarantee the post-filter `pivot()` call never sees duplicate `(country_code, year)`
keys, so the "no per-cell branching" claim in the module docstring holds.

`ordered_countries_with_boundaries`, however, has a reproducible logic bug in its
region-boundary detection loop: it compares consecutive `region` values with Python's
`!=` operator, which is NaN-unsafe. `pandas`/`SQLAlchemy` deserialize a SQL `NULL` in a
mixed string/NULL TEXT column to a `float('nan')` (confirmed live against
`data/panel.db`: `country_reference.region` is NaN for `ATA`, dtype `float`), and
`nan != nan` is always `True` in Python/IEEE-754. I reproduced this concretely (see
WR-01) with a `country_reference` DataFrame shaped like production data: two
consecutive countries sharing a missing `region` were incorrectly split into two
separate boundary groups instead of one. This does **not** currently corrupt the
committed `figuras/07_mapa_calor_cobertura.png` only because the one production
country with a NaN region (`ATA`/Antarctica) has zero rows in `raw_observations` and
therefore never reaches this code path in the current dataset — but the function itself
is wrong, untested for this case, and will silently mis-render region separator lines
the moment a second country with a missing/NaN region enters the dataset (e.g. a
re-ingestion, a M49 crosswalk gap, or any `GeoArea/Tree` country not covered by the SDG
region root).

A second, related robustness gap: countries present in `raw_observations` but absent
from `country_reference` are silently dropped from the heatmap's y-axis with no
warning, printed count, or exclusion log — inconsistent with this codebase's own
established "never silently drop, always log" convention (see `src/ingesta/countries.py`
D-16 / `write_exclusion_log`). Currently benign (0 of 215 ingested countries are
missing from `country_reference` today), but nothing guards against a future silent
loss of countries from the figure.

## Warnings

### WR-01: NaN self-inequality bug in region-boundary detection

**File:** `src/coverage.py:76-80`
**Issue:** The boundary-detection loop uses `region != prev_region` to detect the start
of a new SDG region group:

```python
prev_region = object()  # sentinel, never equal to a real region string
for i, region in enumerate(ref["region"]):
    if region != prev_region:
        boundaries.append(i)
        prev_region = region
```

`ref["region"]` is sourced from `country_reference` via `pd.read_sql` (see
`notebook/7_1_mapa_calor_cobertura.ipynb` cell `ca31936e`); a SQL `NULL` in that column
deserializes to Python `float('nan')` (confirmed live: `country_reference.region` for
`ATA` is `nan`, dtype `float`, via `.venv` inspection of `data/panel.db`). Because
`nan != nan` is always `True`, **every** row with a missing region is treated as the
start of a brand-new region group, even when it is the same "no region" group as the
row before it. Reproduced directly against `coverage.ordered_countries_with_boundaries`:

```python
country_reference = pd.DataFrame([
    {"country_code": "ATA", "region": None, "subregion": None},
    {"country_code": "XYZ", "region": None, "subregion": None},
    {"country_code": "FRA", "region": "Europe", "subregion": "Western Europe"},
])
country_reference["region"] = country_reference["region"].astype(object)
country_reference.loc[[0, 1], "region"] = np.nan  # mirrors what read_sql actually returns

ordered, boundaries = coverage.ordered_countries_with_boundaries(
    country_reference, ["ATA", "XYZ", "FRA"]
)
# ordered   == ["FRA", "ATA", "XYZ"]
# boundaries == [0, 1, 2]   <-- WRONG: should be [0, 1] (2 groups: Europe, "no region")
```

`ATA` and `XYZ` are both in the same "no region" group, yet each gets its own boundary
entry, producing a spurious separator line drawn between two countries that belong
together. This does not currently affect the committed `figuras/07_mapa_calor_cobertura.png`
because the only production country with a NaN region (`ATA`) has no rows in
`raw_observations` and so never enters `ordered_countries` today (verified live: 215/215
ingested countries currently resolve to a non-null region) — but the function is
objectively wrong and will silently misdraw region boundaries the moment 2+ countries
with a missing region both appear in a future run's country list. No existing test in
`tests/test_coverage.py` exercises a `region` column containing NaN/None at all.

**Fix:** Use a NaN-safe equality check, e.g.:

```python
def _same_region(a: object, b: object) -> bool:
    if pd.isna(a) and pd.isna(b):
        return True
    return a == b

boundaries: list[int] = []
prev_region = object()
for i, region in enumerate(ref["region"]):
    if not _same_region(region, prev_region):
        boundaries.append(i)
        prev_region = region
```

or normalize NaN to a single fixed sentinel string before the sort/loop (e.g.
`ref["region"] = ref["region"].fillna("__NO_REGION__")`), which also sidesteps needing
a NaN-aware comparison entirely.

### WR-02: Countries missing from `country_reference` are silently dropped from the heatmap

**File:** `src/coverage.py:69-73` (`ordered_countries_with_boundaries`)
**Issue:** `ref = country_reference[country_reference["country_code"].isin(countries)]`
silently excludes any `country_code` in `countries` that has no matching row in
`country_reference` — such countries never appear in `ordered`, so
`build_presence_matrix(raw_observations, ordered_countries, indicator)` (called from
`notebook/7_1_mapa_calor_cobertura.ipynb` cell `35301a2b`) never plots them either, and
no warning, count, or log records that they were dropped. This directly contradicts the
codebase's own established convention elsewhere (see `src/ingesta/countries.py`'s D-16
"every excluded code ... is recorded in a documented exclusion log -- never silently
dropped", and `country_reference` build's own crosswalk-exclusion logging in
`src/ingesta/typology.py`). Currently benign — verified live that all 215 countries
present in `raw_observations` also exist in `country_reference` — but there is no test
or runtime guard preventing a future silent loss of countries from the figure (e.g. if
`country_reference` is rebuilt with a narrower crosswalk, or a new indicator brings in a
country not yet captured by `typology.py`).

**Fix:** Surface the discrepancy instead of dropping it silently, e.g. in the notebook
right after building `ordered_countries`:

```python
missing_from_reference = sorted(set(countries) - set(ordered_countries))
if missing_from_reference:
    print(f"WARNING: {len(missing_from_reference)} countries dropped from the heatmap "
          f"(not in country_reference): {missing_from_reference}")
```

or have `ordered_countries_with_boundaries` itself return/raise on the discrepancy so
callers cannot silently ignore it.

## Info

### IN-01: No test coverage for the NaN-region boundary bug or the missing-country-reference drop

**File:** `tests/test_coverage.py`
**Issue:** `test_ordered_countries_with_boundaries_groups_by_region` (lines 96-105) only
exercises country codes with fully-populated, non-null `region`/`subregion` values. It
does not cover either edge case above (2+ countries sharing a missing region; a country
present in the `countries` argument but absent from `country_reference`), so WR-01 and
WR-02 were not caught by the existing test suite despite the module docstring's explicit
claims about handling the "restricted to members present in it" case correctly.
**Fix:** Add a regression test seeding `country_reference` with two countries whose
`region` is `NaN`/`None` and asserting `len(boundaries)` reflects the correct number of
distinct groups (not one boundary per NaN row), plus a test asserting that a
`countries` entry absent from `country_reference` is either excluded with a documented
signal or causes a clear failure rather than a silent no-op.

### IN-02: `INDICATOR_CODES` duplicated verbatim across two modules

**File:** `src/coverage.py:29` (duplicates `src/panel_build.py:25`)
**Issue:** `INDICATOR_CODES` is a hand-copied literal in both `src/coverage.py` and
`src/panel_build.py` (each module's docstring/comment acknowledges this is deliberate,
to keep the modules standalone). This is a documented, intentional tradeoff, but it is
still a duplication risk: if the indicator list ever changes (a 6th ODS indicator added,
one dropped), both copies must be updated in lockstep or `src/coverage.py`'s heatmap
will silently diverge from `src/panel_build.py`'s panel construction without any error.
**Fix:** No action required for this phase given the explicit standalone-module
constraint already documented; consider a shared `src/indicators.py` constant if a
future phase adds a third consumer of this list.

---

_Reviewed: 2026-07-15T19:59:05Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
