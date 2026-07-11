---
phase: 02-construcci-n-del-panel-y-eda
status: complete
completed: 2026-07-11
---

# Phase 02 Research: Construcción del Panel y EDA

> ⚠️ **Deviation notice:** This research was produced in a single-context inline flow
> (no independent subagent). The environment used for this planning session did not
> expose an `Agent`/`Task` tool, so the research → plan → self-check passes that would
> normally run as three independently-spawned agents (`gsd-phase-researcher`,
> `gsd-planner`, `gsd-plan-checker`) instead ran sequentially in one session, with
> deliberate context separation between passes (this file is the sole input to the
> planning pass; the plan is the sole input to the self-check pass). User-approved
> deviation — see conversation record.

## Objective

Answer: "What do I need to know to PLAN Phase 2 well?"

Phase 2 goal (ROADMAP.md): *"A partir de los datos crudos versionados, el sistema
produce un panel país×año limpio, filtrado por cobertura y documentado, junto con un
análisis exploratorio que informa la especificación del Modelo 1."*

Requirements to satisfy: PANEL-01 (idempotencia), PANEL-02 (filtro de cobertura 70%),
PANEL-03 (discusión MNAR), PANEL-04 (EDA global/regional/tipología + VIF).

No CONTEXT.md exists for this phase (user chose to proceed with ROADMAP + REQUIREMENTS
only, skipping a dedicated `/gsd-discuss-phase` round).

## Inputs Read

- `.planning/PROJECT.md` — indicator semantics, constraints, out-of-scope list
- `.planning/ROADMAP.md` — Phase 2 goal/success criteria, Phase 3/4/6 downstream needs
- `.planning/REQUIREMENTS.md` — PANEL-01..04 exact wording
- `.planning/STATE.md` — accumulated decisions from Phase 1
- `src/db.py` — `raw_observations` / `panel` schema, `rebuild_panel()` pivot logic
- `src/ingesta/countries.py` — M49/GeoArea country-leaf resolution, `_normalize_code()`
- `src/ingesta/manifest.py` — provenance manifest pattern (date/url/params/row_count/checksum)
- `src/ingesta/client.py` — session/retry pattern (no GeoArea/Tree caching here)
- `.planning/phases/01-ingesta-y-almacenamiento-versionado/01-05-SUMMARY.md` — live dataset shape (18,086 raw_observations, 4,923 panel rows, 215 countries; 2.3.1 coverage caveat: 50 countries, 173/900 non-null)
- `CLAUDE.md` — naming/testing/module conventions
- **Live verification call** to `https://unstats.un.org/SDGAPI/v1/sdg/GeoArea/Tree` (same endpoint Phase 1 already depends on) to resolve the "país por tipología" ambiguity — see Finding 1 below.

## Key Findings

### Finding 1 — "Tipología de país" must come from the UN SDG API itself, and World Bank income groups are NOT retrievable that way (verified live)

PROJECT.md's constraint is explicit: *"Fuente de datos: Exclusivamente la API pública
ODS de la ONU — ninguna otra fuente de datos."* The ROADMAP success criterion says the
EDA must break down variables "a nivel global, regional y por tipología de país" —
three distinct levels. "Regional" is trivially available (SDG regions / continental
regions, both root trees in `GeoArea/Tree`). "Tipología" needed a concrete, in-scope
definition.

I live-queried `GeoArea/Tree` (the same endpoint `fetch_data.py` already calls) and
found **7 root groupings**:

| Root | geoAreaCode | Has real country membership? |
|---|---|---|
| World by SDG regions | 1 | Yes (used for "regional") |
| World by continental regions | 1 | Yes |
| Land Locked Developing Countries (LLDC) | 432 | **Yes** — walked to real Country leaves |
| Least Developed Countries (LDC) | 199 | **Yes** — walked to real Country leaves |
| Small Island Developing States (SIDS) | 722 | **Yes** — walked to real Country leaves |
| World by MDG regions | 1 | Not inspected (legacy MDG scheme, superseded by SDG) |
| Custom groupings of data providers | 922 | **Mixed** — see below |

Under "Custom groupings of data providers" (922) I found nodes literally named `Low
income economies (WB)` (911), `Lower middle economies (WB)` (912), `Low and middle
income economies (WB)` (913), `Upper middle economies (WB)` (914) — i.e. World Bank
income groups DO appear as named nodes in this API. **However**, fetching node 911's
full JSON shows `"children": null`  — these income-group nodes carry **no country
membership** in this endpoint (they are bare labels, `"type": "Other areas"`). So income
group is NOT usable as a typology axis without a second, non-UN data source (which
would violate the single-source constraint).

By contrast, LDC (199), LLDC (432), and SIDS (722) **do** resolve to real `"type":
"Country"` leaves when walked (verified: LDC → LDC Africa → Angola/Benin/Burkina
Faso/... with real `geoAreaCode`s matching the same country codes Phase 1 already
uses).

**Recommendation:** operationalize "tipología de país" as **UN development-status
classification** — three boolean flags per country: `is_ldc`, `is_lldc`, `is_sids`
(a country can be in zero, one, or more than one group; e.g. many LDCs are also LLDC
or SIDS). This is a real, citable, UN-native typology (distinct from geographic
region) that stays entirely within the "exclusively UN SDG API" constraint, and is
academically well-precedented for exactly this kind of vulnerability/water-stress
economics study (LDC/LLDC/SIDS status correlates with both statistical reporting
capacity and economic vulnerability — directly relevant to the MNAR discussion in
PANEL-03).

This is a **methodological decision with no explicit prior lock in CONTEXT.md**
(none exists) — flag it in the plan as an explicit, documented choice (mirroring how
Phase 1 handled the 2.3.1 series ambiguity) so it is visible and can be revisited if
the user disagrees.

### Finding 2 — Country reference data (region + typology) is not currently persisted; it must be captured once, not re-fetched live on every panel rebuild

`fetch_data.py`'s `_fetch_country_reference()` calls `GeoArea/Tree` fresh every run and
only keeps the resulting `{code: name}` dict in memory — it is never written to
`data/raw/` or SQLite. For PANEL-01's idempotency requirement ("Reconstruir la tabla
`panel` desde cero a partir de `raw_observations` produce un resultado idéntico"), the
panel-build step must be a **pure function of already-persisted data** — it should not
depend on a live network call at rebuild time (flaky, slow, and technically breaks the
"desde `raw_observations`" framing of the success criterion).

**Recommendation:** add a small reference-data capture step (own module, e.g.
`src/ingesta/typology.py`, following `countries.py`'s existing pure-transform pattern)
that walks `GeoArea/Tree` **once** and persists a `country_reference` table (or a
`data/raw/country_reference.json` + manifest sidecar, mirroring the existing
manifest pattern) with columns: `country_code (ISO3), country_name, region,
subregion, is_ldc, is_lldc, is_sids`. The panel-build pipeline then joins
`raw_observations`/`panel` against this persisted reference table — no network call
needed for the idempotency check itself. This keeps the existing `manifest.py`
provenance pattern consistent (date/url/params/row_count/checksum) even though this
is reference/classification data rather than a time-series indicator.

### Finding 3 — `panel` (Phase 1's `db.rebuild_panel()`) is a *raw* pivot; Phase 2 owns everything downstream

Confirmed from `src/db.py` docstring and code: `panel` is `indicator_code` pivoted to
columns, indexed by `(country_code, year)`, **always fully regenerated** — no cleaning,
no coverage filter, no feature engineering. Phase 2's job starts from this raw wide
table (or equivalently from `raw_observations` directly) and must itself be
idempotent and reconstructible. This means Phase 2's own build step should follow the
same "always fully regenerate, never hand-edit" pattern Phase 1 established for
`panel` — i.e., a `panel_clean` (or similarly named) derived table/artifact that is
always dropped and rebuilt from `raw_observations` + `country_reference`, never
patched in place.

**Naming collision risk:** ROADMAP/REQUIREMENTS (Phase 3, MODEL1-01) already reserve
the name `panel_base.py` for a *different* artifact — Phase 3's shared
fit/diagnose-panel function. Phase 2's own module must use a different name (e.g.
`src/panel_build.py` or `src/panel/build.py`) to avoid confusion with Phase 3's
`panel_base.py`.

### Finding 4 — 70% coverage threshold: per-(country, indicator), not per-country-overall

REQUIREMENTS.md's exact wording: *"El sistema filtra países con cobertura mínima del
70% de años disponibles **por indicador**"* — the "por indicador" qualifier means the
threshold check must be evaluated **per (country, indicator) pair**, not "does this
country have 70% coverage across all 5 indicators combined." This is consistent with
Phase 1's already-known finding that indicator 2.3.1 has much lower coverage (50
countries, 173/900 non-null cells) than the other 4 indicators — a single "70% across
everything" rule would force 2.3.1's poor coverage to exclude countries from the
*entire* panel, which would then also starve Model 1 (which doesn't need 2.3.1 at
all — 2.3.1 is Model 2's target variable, Phase 6). 23 possible years (2000–2022
inclusive) × 0.70 = 16.1 → **a country needs data in at least 17 of the 23 years for
a given indicator to count as "covered" for that indicator.**

**Recommendation:** produce one exclusion-table row per `(country, indicator)` pair
that fails the 17/23-year threshold, with columns `country_code, indicator_code,
years_available, years_required(=17), coverage_pct, excluded(bool)`. The final
"clean panel" used for EDA/modeling should retain a country-year row as long as the
country clears the threshold for the indicators actually in use downstream — do NOT
drop a country from the whole panel merely because indicator 2.3.1 (a Model 2-only
target) fails its threshold. This must be an explicit, visible plan decision (not
silently resolved) since it directly affects Phase 3 and Phase 6 sample sizes.

### Finding 5 — MNAR discussion is a documentation deliverable inside the Phase 2 notebook, NOT the deferred EXTRA-01 tool

`.planning/STATE.md`'s Deferred Items table explicitly defers **EXTRA-01** ("Informe
automatizado y visual de cobertura/missingness (mapa de calor país × indicador ×
año)") to v2. PANEL-03 only requires that *"la memoria documenta explícitamente el
patrón de datos faltantes (riesgo MNAR) y su posible sesgo hacia países con mejor
reporting."* This is satisfiable with a one-off missingness summary (a table of
% missing by indicator × region × typology, plus a short prose discussion, and
optionally one simple heatmap figure using existing `seaborn`/`matplotlib`) produced
inside the Phase 2 notebook — it must NOT be scoped as building a reusable
"automated visual missingness report" tool (that would silently pull EXTRA-01 out of
its deferred status and inflate Phase 2's scope). Plan tasks should explicitly note
this boundary.

### Finding 6 — VIF/correlation matrix: `statsmodels` already in `requirements.txt`, no new dependency

`statsmodels.stats.outliers_influence.variance_inflation_factor` is the standard
tool and is already available (`statsmodels>=0.14` in `requirements.txt`, installed
per Phase 1). No new dependency required. The 5 numeric indicator columns
(6.4.2, 6.4.1, 8.1.1, 8.2.1, 2.3.1) are the VIF input; PANEL-04 requires this matrix
computed at 3 levels: global, per-region, and per-typology (LDC/LLDC/SIDS, per
Finding 1). `scipy`/`numpy` linear algebra needed for VIF ships as a `statsmodels`
transitive dependency already present.

### Finding 7 — Deliverable split: testable `src/` module for the build pipeline (idempotency is a code-testable property), notebook for EDA (inherently exploratory, per CLAUDE.md's "Notebook-driven exploratory workflow" convention)

CLAUDE.md: *"Notebook-driven exploratory workflow (Jupyter for prototyping) ...
Transition to modular `src/` structure for reproducible pipeline stages."* PANEL-01's
idempotency claim ("verificable por comparación/hash entre ejecuciones") is only
practically testable via pytest if the build logic lives in an importable module, not
notebook cells. PANEL-03/PANEL-04 explicitly reference "el documento/notebook" and
"el EDA produce..." — these are naturally notebook deliverables. Recommended split:

- **`src/panel_build.py`** (or `src/panel/build.py`) — pure functions: coverage
  filter + exclusion table, clean/merge, feature engineering. Idempotent,
  pytest-testable (mirrors `tests/ingesta/` → new `tests/panel/` or
  `tests/test_panel_build.py`, following the existing `tests/` layout).
- **`src/ingesta/typology.py`** — country reference capture (region + LDC/LLDC/SIDS),
  reusing `countries.py`'s pure-transform pattern (no network call inside the
  transform function itself — pass in the already-fetched tree nodes, same shape as
  `collect_countries()`).
- **`notebook/2_1_construccion_panel_eda.ipynb`** (naming per CLAUDE.md's `[number]_
  [descriptive_name].ipynb` convention) — imports the above modules, produces
  descriptive stats, correlation/VIF matrices (global/regional/typology), and the
  MNAR missingness discussion (prose + table + optional simple heatmap figure).

### Finding 8 — Idempotency verification method

Since `raw_observations` is immutable/append-only (Phase 1 invariant, D-11) and
`country_reference` (Finding 2) is captured once and persisted, the panel-build
function is a pure function of two on-disk inputs. Verify idempotency by: running the
build twice against the same `data/panel.db` snapshot, sorting the output
deterministically by `(country_code, year)` with a fixed column order, and asserting
byte-for-byte or `pandas.testing.assert_frame_equal` equality between the two runs
(mirrors the "hash comparison between executions" language in the ROADMAP success
criterion). This is a straightforward pytest assertion, no special tooling needed.

## Architecture Recommendation Summary

```
src/
  ingesta/
    typology.py          # NEW — walk GeoArea/Tree once, extract region + LDC/LLDC/SIDS per country
  panel_build.py          # NEW — coverage filter (17/23-year threshold per country×indicator),
                           #        exclusion table, clean/merge, feature engineering; pure + idempotent
notebook/
  2_1_construccion_panel_eda.ipynb   # NEW — descriptive stats, correlation/VIF (global/regional/tipología),
                                       #        explicit MNAR discussion
tests/
  test_panel_build.py      # NEW — idempotency test (run twice, compare), coverage-filter unit tests
  ingesta/
    test_typology.py        # NEW — region/LDC/LLDC/SIDS extraction unit tests (mocked GeoArea/Tree fixture)
data/
  raw/
    country_reference.json + .manifest.json   # NEW — persisted country_code/region/typology reference
  panel.db                  # existing — gains a `country_reference` table + a clean/filtered panel artifact
```

## Open Questions Flagged for the Plan (not silently resolved)

1. **Country typology definition** (Finding 1): LDC/LLDC/SIDS boolean flags, NOT World
   Bank income group (unavailable with country membership from this API). Flag as an
   explicit plan decision.
2. **70% threshold scope** (Finding 4): per-(country, indicator), not per-country-overall.
   A country can be excluded from Model 1's core variables while still contributing
   rows for other indicators — flag as an explicit plan decision affecting Phase 3/6
   sample sizes.
3. **Where the "clean panel" artifact lives**: a new SQLite table (e.g. `panel_clean`)
   vs. an in-notebook DataFrame recomputed each run vs. a persisted parquet/CSV. Given
   PANEL-01's idempotency/reconstructibility requirement and Phase 3's need to consume
   this output, recommend a new SQLite table via the same `db.py`
   `if_exists='replace'` pattern `rebuild_panel()` already established — plan should
   decide the exact table name and confirm with the user only if ambiguous.
4. **Naming**: confirm `panel_build.py` (not `panel_base.py`, reserved for Phase 3) to
   avoid collision.

## Validation Architecture

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`) |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_panel_build.py tests/ingesta/test_typology.py -q` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/ -q` |
| **Estimated runtime** | ~2-4 seconds (Phase 1's 48-test suite ran in 2.34s; Phase 2 adds a modest number of pure-function unit tests, no network calls in tests) |

**Sampling rate:** run the quick command after every task commit; run the full suite
after each plan/wave; full suite must be green before any `/gsd-verify-work` pass.

**Manual-only verifications:** the MNAR prose discussion (PANEL-03) and the VIF/
correlation-matrix EDA output (PANEL-04) are inherently human-judgment deliverables
(a notebook's descriptive-stats/discussion quality cannot be asserted by pytest) —
these route to `human_judgment: true` in the plan's SUMMARY coverage block, not
automated `pass/fail`.

## Wave 0 / Test Infrastructure Notes

No new test framework needed — `pytest` + `pyproject.toml` config already established
in Phase 1. New test files: `tests/test_panel_build.py`, `tests/ingesta/test_typology.py`
(mirrors `tests/ingesta/` layout already used by `test_countries.py`, `test_manifest.py`,
etc.).
