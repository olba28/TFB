# Phase 7: Mapa de Calor de Cobertura - Research

**Researched:** 2026-07-15
**Domain:** Data-coverage visualization (pandas pivot/reindex + matplotlib/seaborn multi-panel heatmap) over an existing SQLite panel-data pipeline
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Layout de la figura**
- **D-01:** Grid de 5 sub-heatmaps (uno por cada uno de los 5 indicadores ODS), cada uno país × año, en lugar de colapsar a un único panel agregado. Justificación del usuario: más fiel a COVER-01 ("los 5 indicadores ODS... aparecen identificados en la figura") que un heatmap único con color agregado.
- **D-02:** El resultado final es UN solo fichero PNG (per COVER-02, "un fichero PNG") — los 5 sub-heatmaps se combinan en una sola figura (p.ej. matplotlib subplots grid), no 5 PNGs separados.

**Orden de países (eje Y de cada sub-heatmap)**
- **D-03:** Países agrupados por región SDG (con separadores visuales entre grupos), no alfabético ni ordenado por cobertura. Usa el campo `region` ya calculado en Fase 2 (`src/ingesta/typology.py::build_region_map`, expuesto en la tabla `panel`/`panel_clean` vía `panel_build.py::REFERENCE_COLUMNS`). Nota: `raw_observations` no tiene columna `region` — requiere join con la tabla `panel` (o con el mapa de región derivado directamente de `GeoArea/Tree`) para obtener el agrupamiento, sin usar `panel_clean` como fuente de la cobertura en sí (eso violaría COVER-01: debe calcularse sobre datos crudos).

**Definición de "dato ausente"**
- **D-04:** Una celda país-año-indicador cuenta como "sin dato" (missing) si NO existe fila en `raw_observations` para esa combinación, O si existe la fila pero `value IS NULL`. Ambos casos se tratan como el mismo estado visual (missing), sin distinguir en la leyenda entre "nunca reportado" y "reportado como NULL".

**Entry point / reproducibilidad**
- **D-05:** Nuevo notebook `notebook/7_1_mapa_calor_cobertura.ipynb`, siguiendo la convención numérica ya establecida (`2_1_construccion_panel_eda.ipynb`, `3_1_modelo1_pib.ipynb`, `4_1_interpretabilidad_simulacion.ipynb`) — no un script standalone en `scripts/`. Debe ser re-ejecutable de principio a fin (Kernel → Restart & Run All) para cumplir con "figura reproducible" (Success Criteria #4 del roadmap).

### Claude's Discretion
- Nombre exacto del fichero PNG dentro de `figuras/` (p.ej. `figuras/07_mapa_calor_cobertura.png`), DPI/tamaño para impresión en la memoria, paleta de colores exacta para el estado binario missing/presente (puede reutilizar el estilo `cmap="Reds"` ya usado en la Fase 2 para el heatmap de missingness por región, o un esquema binario de 2 colores más apropiado para presencia/ausencia — a discreción), orientación de etiquetas de eje (rotación de años en el eje X), tamaño de figura exacto dado que cada sub-panel tiene ~40-45 países (215 países / 5-7 regiones SDG).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COVER-01 | El sistema genera un mapa de calor país × indicador × año que visualiza la cobertura de datos (presencia/ausencia) para los 5 indicadores ODS ya ingeridos, calculado sobre los datos crudos (antes del filtro de cobertura del 70% de Fase 2) | See "Don't Hand-Roll" (pivot+reindex pattern collapses both missing states for free), "Code Examples" (`src/coverage.py` design), and live DB verification below (215 países, 18086 filas, 1252 `value IS NULL`) confirming `raw_observations` is the correct, sufficient source — no `panel_clean` dependency needed |
| COVER-02 | La figura se exporta en formato estático (PNG) al directorio `figuras/` para su inclusión directa en el anexo de la memoria, sin cambios al dashboard Streamlit | See "Architecture Patterns" (savefig convention — this is the FIRST matplotlib-generated PNG in the repo; `figuras/plan_b/*.png` are manual browser screenshots, not `savefig` output) and "Environment Availability" (matplotlib/seaborn/pandas already installed, no new deps) |
</phase_requirements>

## Summary

Phase 7 is a small, self-contained, read-only visualization phase. All required data already exists in `data/panel.db`: `raw_observations` (18,086 rows, 215 countries, 5 indicators, years 2000-2022, 1,252 `value IS NULL` rows) and `country_reference` (248 rows, region/subregion/LDC-LLDC-SIDS flags, already persisted by Phase 2's `src/ingesta/typology.py` — **no live GeoArea/Tree fetch is needed**, a simple SQL join suffices). All 215 countries in `raw_observations` have a matching row in `country_reference` (verified live: zero orphans), so the region join is a straightforward `country_code` merge, not a fragile crosswalk problem.

The core technical trick that satisfies D-04 "for free": build a country×year matrix per indicator via `raw_observations[raw_observations.indicator_code == X].pivot(index="country_code", columns="year", values="value")`, then `.reindex(index=all_countries, columns=all_years)`. `pivot`/`reindex` already produce `NaN` for combinations with no row at all, and a stored `NULL` already deserializes to `NaN` in pandas — so `matrix.isna()` gives the unified "missing" boolean D-04 asks for, with **zero per-cell Python looping** over the ~24,725-cell space (215 × 23 × 5). This exact reindex-to-complete-grid pattern is already established in this codebase (`src/panel_build.py::compute_coverage`, using `pd.MultiIndex.from_product` + `.reindex(fill_value=0)`) — Phase 7 should mirror it, not invent a new idiom.

Architecturally, this codebase's convention for every prior phase (2-6) is "logic lives in a testable `src/*.py` pure-transform module; the notebook imports it and only orchestrates + plots" (see `src/panel_build.py`, `src/interpret.py`, `src/simulate.py`, `src/model2_agri.py`, each with a matching `tests/test_*.py`). Phase 7 should follow the same shape: a new `src/coverage.py` holding `build_presence_matrix()` and a region-ordering/boundary helper (both pure, unit-testable against a tiny synthetic engine, mirroring `tests/test_panel_build.py`'s fixture style), with `notebook/7_1_mapa_calor_cobertura.ipynb` doing only `pd.read_sql` + calling `src.coverage` + matplotlib/seaborn plotting + `savefig`. This is a **recommendation, not a re-litigation of D-05** — D-05 only fixes the entry point (the notebook), it does not forbid a supporting `src/` module, and every existing precedent phase uses one.

One discrepancy versus CONTEXT.md's Claude's-Discretion note worth flagging to the planner: the note estimates "~40-45 países" per region across "5-7 regiones SDG". Live query against `country_reference` joined to `raw_observations`'s 215 ingested countries shows **8 regions** with sizes ranging from **4** (Europe and Northern America) to **49** (Sub-Saharan Africa) — not a uniform ~40-45. This affects figure-sizing decisions (see Common Pitfalls) and the planner should size the figure/labels around the real distribution, not the estimate.

**Primary recommendation:** Add `src/coverage.py` (pure, tested pivot/reindex + region-ordering functions reading `raw_observations` + `country_reference`) and `notebook/7_1_mapa_calor_cobertura.ipynb` (thin orchestrator: load, call `src.coverage`, build a 1×5 (or 5×1, see Architecture Patterns) matplotlib grid with a binary 2-color "status" palette and axhline region separators, single shared legend, `savefig(dpi=300, bbox_inches="tight")` to `figuras/07_mapa_calor_cobertura.png`). No new dependencies, no changes to `src/db.py`, `src/panel_build.py`, or `src/dashboard/`.

## Architectural Responsibility Map

This project has no web/client tiers (see `.claude/CLAUDE.md` Architecture section) — tiers below are adapted to the project's own established layers (Storage / Processing-src / Notebook-orchestration-and-visualization), not a generic browser/API/CDN stack.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Read `raw_observations` + `country_reference` from SQLite | Storage (`data/panel.db`, via `src/db.py::get_engine`) | — | Already the single source of truth; no new tables, no writes in this phase |
| Build country×year presence/absence matrix per indicator (D-04 logic) | Processing (`src/coverage.py`, new pure-transform module) | — | Matches the project's established pattern: pure, unit-testable transforms live in `src/*.py`, never inline in a notebook cell (mirrors `src/panel_build.py::compute_coverage`) |
| Region-based row ordering + group-boundary computation (D-03) | Processing (`src/coverage.py`) | — | Same reasoning; a pure function is trivially unit-testable against a tiny synthetic `country_reference`, unlike notebook-inline logic |
| 5-panel matplotlib/seaborn grid rendering + legend + savefig | Notebook orchestration (`notebook/7_1_mapa_calor_cobertura.ipynb`) | — | D-05 fixes the entry point here explicitly; matches every prior phase's notebook-as-visualization-layer convention |
| PNG artifact for the thesis annex | Output (`figuras/07_mapa_calor_cobertura.png`, committed to git) | — | `figuras/` PNGs are NOT gitignored (verified: `figuras/plan_b/*.png` are tracked) — this new PNG should be committed alongside the notebook |
| Dashboard (`src/dashboard/`) | N/A — explicitly out of scope | — | REQUIREMENTS.md Out-of-Scope table; no capability in this phase touches it |

## Standard Stack

### Core
| Library | Version (verified in `.venv`) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 3.0.3 [VERIFIED: `.venv/Scripts/python.exe -c "import pandas"`] | Read SQL tables, pivot/reindex to build the presence matrix | Already the project's sole tabular-data library; `pivot`+`reindex` is the idiomatic pandas pattern for long→wide gap-filling |
| matplotlib | 3.11.0 [VERIFIED: same] | Subplot grid, `savefig` to PNG | Already the project's base plotting library; only library in `requirements.txt` capable of `savefig` to a static PNG file |
| seaborn | 0.13.2 [VERIFIED: same] | `sns.heatmap` per sub-panel (annotation, tick handling) | Already used for the Phase 2 missingness heatmap precedent (`notebook/2_1...ipynb` cell 9); consistent style with existing EDA figures |
| sqlalchemy | 2.0.51 [VERIFIED: same] | `src.db.get_engine` connection reused as-is | Already the project's DB engine layer; no schema change needed |

**No new packages are required for this phase.** All four libraries above are already pinned in `requirements.txt`/`requirements.lock.txt` and confirmed importable in the project's `.venv`.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `matplotlib.colors.ListedColormap` | (part of matplotlib, no separate install) | Define the binary missing/present 2-color palette | When `sns.heatmap`'s default continuous colormap (e.g. `cmap="Reds"`) would misleadingly imply a magnitude gradient over what is actually a binary state |
| `matplotlib.patches.Patch` | (part of matplotlib) | Build a manual 2-entry legend (not a colorbar) | Binary/status data should use a legend with swatches + labels, not a continuous colorbar (see dataviz guidance below) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sns.heatmap` per sub-panel | raw `ax.imshow()` + manual tick/annotation code | `imshow` is slightly faster for 215×23 grids and used in matplotlib's own annotated-heatmap gallery example, but `sns.heatmap` already matches this project's Phase 2 precedent and needs less boilerplate — no reason to diverge |
| Reusing `cmap="Reds"` (Phase 2 precedent, per Claude's Discretion) | A dedicated 2-color binary palette | `Reds` is a *sequential* colormap (implies magnitude); the underlying signal here is *binary state* (present/absent), which is a "status" encoding job, not "sequential" — see Architecture Patterns/Anti-Patterns below. Recommend the 2-color binary scheme, not reusing `Reds`, despite it being explicitly offered as an option in CONTEXT.md's discretion note |

**Installation:** none — all dependencies already present.

## Package Legitimacy Audit

**Not applicable.** This phase introduces zero new external packages (see Standard Stack — all four libraries used are already in `requirements.txt`/`requirements.lock.txt` and verified importable in `.venv`). No `gsd-tools query package-legitimacy check` run was needed.

## Architecture Patterns

### System Architecture Diagram

```
data/panel.db (SQLite, existing, unmodified by this phase)
  ├── raw_observations  ── country_code, indicator_code, year, value (nullable) ──┐
  └── country_reference ── country_code, region, subregion, is_ldc/lldc/sids ─────┤
                                                                                    │
                                                                                    ▼
                                                            src/coverage.py (NEW, pure transform)
                                                            ├── build_presence_matrix(raw_obs, countries, indicator)
                                                            │     -> per-indicator country×year boolean grid
                                                            │        (pivot + reindex; D-04 collapses for free)
                                                            └── ordered_countries_with_boundaries(country_reference, countries)
                                                                  -> region-sorted country list + group-boundary indices
                                                                    (D-03)
                                                                                    │
                                                                                    ▼
                                                notebook/7_1_mapa_calor_cobertura.ipynb (D-05 entry point)
                                                ├── load engine, read raw_observations + country_reference
                                                ├── call src.coverage for each of the 5 indicators (D-01)
                                                ├── build 1×5 (or 5×1) matplotlib subplot grid, shared binary
                                                │     cmap, axhline region separators, single shared legend
                                                └── plt.savefig(...) -> ONE PNG (D-02)
                                                                                    │
                                                                                    ▼
                                                    figuras/07_mapa_calor_cobertura.png (committed, thesis annex)
```

### Recommended Project Structure
```
src/
├── coverage.py                              # NEW: pure presence-matrix + region-ordering functions
notebook/
├── 7_1_mapa_calor_cobertura.ipynb           # NEW: D-05 entry point, orchestration + plotting only
tests/
├── test_coverage.py                          # NEW: unit tests mirroring test_panel_build.py's fixture style
figuras/
├── 07_mapa_calor_cobertura.png              # NEW: generated output, committed (figuras/ PNGs are NOT gitignored)
```

### Pattern 1: Long-to-wide gap-filling via pivot + reindex (not a per-cell loop)
**What:** For each indicator, pivot `raw_observations` to a country×year matrix, then `.reindex()` against the FULL country list and FULL year range. Both "row never existed" and "row exists but `value IS NULL`" collapse to `NaN` automatically — `matrix.isna()` is D-04's unified missing-state check with no explicit case-splitting.
**When to use:** Any long-format-to-grid completeness check over a small-to-medium cross product (here: 215 × 23 × 5 = 24,725 cells — trivial for pandas, no chunking needed).
**Example:**
```python
# Source: mirrors src/panel_build.py::compute_coverage's established
# MultiIndex.from_product + reindex(fill_value=...) pattern in this codebase
# [VERIFIED: src/panel_build.py, this repository]
def build_presence_matrix(raw_observations, countries, indicator_code, years):
    subset = raw_observations[raw_observations["indicator_code"] == indicator_code]
    wide = subset.pivot(index="country_code", columns="year", values="value")
    wide = wide.reindex(index=countries, columns=years)  # NaN for absent rows too
    return wide.notna()  # True = present; False = missing (row-absent OR value IS NULL, unified per D-04)
```

### Pattern 2: Region-group separator lines via `axhline` at boundary indices (not minor-tick grid on every row)
**What:** Sort the country axis by `(region, subregion, country_code)`, compute the row indices where the region changes, and draw a horizontal line only at those boundaries.
**When to use:** D-03's grouped-not-alphabetical y-axis with "separadores visuales entre grupos" — a separator is needed only between groups, not between every row (the minor-tick-grid-on-every-row technique from matplotlib's own gallery is the wrong tool here; it is meant for a small uniform grid, not for marking a handful of group boundaries among 215 rows).
**Example:**
```python
# Source: matplotlib official annotated-heatmap gallery pattern, adapted to
# boundary-only lines instead of every-row lines
# [CITED: matplotlib.org/stable/gallery/images_contours_and_fields/image_annotated_heatmap.html]
for boundary_row in region_boundaries:
    ax.axhline(y=boundary_row, color="black", linewidth=0.8)
```

### Pattern 3: Shared legend for a grid of heatmaps sharing one binary scale
**What:** Since all 5 sub-panels share the exact same 2-value domain (missing/present), draw `cbar=False` on every `sns.heatmap` call and add ONE manual legend (`matplotlib.patches.Patch` swatches) to the figure, rather than a colorbar per panel or a shared continuous colorbar.
**When to use:** Whenever the underlying value is a binary/categorical state rather than a magnitude — a continuous colorbar over a 2-value domain is misleading (implies interpolated values that don't exist) and wastes space five times over.
**Example:**
```python
# Source: seaborn.heatmap's documented cbar/cbar_ax params confirm a colorbar
# can be suppressed per-axis; adapted here to a status/binary legend instead
# of a shared continuous colorbar, per the binary-domain reasoning above
# [CITED: seaborn.pydata.org/generated/seaborn.heatmap.html]
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

cmap = ListedColormap(["#e8e8e8", "#2b6cb0"])  # 0=missing (light gray), 1=present (blue)
for ax, indicator in zip(axes, INDICATOR_CODES):
    sns.heatmap(matrix.astype(int), cmap=cmap, cbar=False, ax=ax, yticklabels=False)
fig.legend(
    handles=[Patch(color="#e8e8e8", label="Sin dato"), Patch(color="#2b6cb0", label="Dato presente")],
    loc="lower center", ncol=2,
)
```

### Anti-Patterns to Avoid
- **Reusing a continuous/sequential colormap (e.g. `cmap="Reds"`) for a binary missing/present state:** This is a "status" encoding job (present/absent = a state, not a magnitude), not a "sequential" one. A sequential ramp on a 2-value domain implies a gradient that doesn't exist and forces an unnecessary colorbar legend where a simple 2-entry legend would be clearer. Recommend a 2-color `ListedColormap` with a `Patch`-based legend instead, even though CONTEXT.md offers `Reds` reuse as an in-scope discretion option.
- **A per-cell Python loop to determine "row missing OR value IS NULL":** Unnecessary and slow. `pivot()` + `.reindex()` already produces `NaN` for both cases; explicit case-splitting logic (e.g. `if (country, year) not in raw.index: missing=True elif raw.loc[...].isna(): missing=True`) would be redundant, slower, and a likely source of off-by-one/index bugs at 24,725 cells.
- **Uniform minor-tick gridlines between every row as the D-03 "separator":** matplotlib's own gallery example applies this between every row of a small grid; with 215 rows it would produce visual noise, not clarity. Use `axhline` only at region-boundary indices.
- **Re-fetching `GeoArea/Tree` live inside the notebook to get region data:** `country_reference` is already a persisted SQL table (`src/ingesta/typology.py::persist_country_reference_to_db`), populated once in Phase 2 and verified live to contain all 215 countries `raw_observations` needs. A live HTTP call here would be redundant network I/O and violate PANEL-01's precedent of "a rebuild must not depend on a live network call" (02-RESEARCH.md Finding 2).
- **Reading from `panel_clean` for the coverage signal itself:** Explicitly forbidden by D-03/COVER-01 — `panel_clean` is post-70%-filter; only `country_reference` (a reference/lookup table, not filtered data) may be joined from Phase 2's tables.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Determining "row absent OR value NULL" per cell | A custom per-cell existence+nullity check (nested loops or `.apply`) | `raw.pivot(...).reindex(countries, years).isna()` | pandas already unifies both missing states into `NaN` through the pivot+reindex mechanics — this is the exact pattern `src/panel_build.py::compute_coverage` already established in this codebase for an analogous "count as missing" computation |
| Region-based row grouping | A manual JSON/dict mapping country→region hardcoded in the notebook | `country_reference` SQL table (already built by `src/ingesta/typology.py`, already joined in `panel_clean` via `src/panel_build.py::REFERENCE_COLUMNS`) | The mapping already exists, verified live (0 orphaned country codes between `raw_observations` and `country_reference`); hardcoding it again would duplicate a source of truth and risk drift |
| Full country×year×indicator cross product | Manually enumerating `for country in countries: for year in years: ...` | `pd.MultiIndex.from_product` (as used in `panel_build.py::compute_coverage`) or the simpler per-indicator `pivot`+`reindex` shown above | Vectorized pandas operations over ~25k cells are near-instant; a Python-level triple loop is both slower and a common source of off-by-one errors in axis alignment |

**Key insight:** every piece of machinery this phase needs — the raw data, the region reference data, and the reindex-to-complete-grid idiom — already exists in this codebase from Phases 1-2. Phase 7's actual net-new work is almost entirely the plotting/layout logic, not data engineering.

## Runtime State Inventory

Not applicable — this is a greenfield, read-only visualization phase (no rename/refactor/migration). No existing runtime state (databases, live service configs, OS registrations, secrets, or build artifacts) is touched or renamed.

## Common Pitfalls

### Pitfall 1: Assuming region-group sizes are roughly uniform (~40-45 countries) when sizing the figure/labels
**What goes wrong:** A figure/font size chosen assuming 5-7 roughly-equal-sized regional groups will look badly unbalanced once rendered, because the real distribution is far from uniform.
**Why it happens:** CONTEXT.md's Claude's-Discretion note estimates "~40-45 países" per region across "5-7 regiones SDG" as a rough sizing heuristic during discussion — but it wasn't verified against the live database at discussion time.
**How to avoid:** Live query against `country_reference` joined to the 215 `raw_observations` countries shows **8 regions**, sizes: Sub-Saharan Africa 49, Latin America and the Caribbean 44, Europe 43, Northern Africa and Western Asia 25, Oceania 18, Eastern and South-Eastern Asia 18, Central and Southern Asia 14, Europe and Northern America 4. Size the figure height and any per-region visual weight (e.g. minimum band height so a 4-country region is still visible) around these real numbers, not the ~40-45 estimate.
**Warning signs:** A generated figure where the "Europe and Northern America" band (4 countries) is visually indistinguishable from a rounding artifact, or where "Sub-Saharan Africa" (49 countries) dominates disproportionately without any labeling to orient the reader.

### Pitfall 2: 215 individual country y-tick labels rendered illegibly (or omitted entirely, losing information)
**What goes wrong:** With 215 rows per sub-panel, per-country tick labels at any print-legible font size (≥ 6pt) would require an implausibly tall figure (215 rows × ~0.08in/row minimum ≈ 17in+ just for label spacing) — but omitting labels entirely loses the ability to identify individual countries, which a thesis reviewer may want to check.
**Why it happens:** Country-level heatmaps at this row count are a well-known readability tension between "show every category" and "keep the figure a sane physical size."
**How to avoid:** Since the final artifact is a PNG (typically viewed digitally / embedded in a PDF the reader can zoom), it's reasonable to render country labels at a small font (e.g. 3.5-4pt) on ONLY the leftmost of the 5 subplots (they're identical to the shared y-axis on all 5, `sharey=True`), at 300 DPI so they remain legible when zoomed digitally, rather than omitting them. If the planner decides legibility at physical print size (not digital zoom) is the actual requirement, omitting per-country labels and relying on region-band annotations (region name once per group, e.g. via a text label at each `axhline` boundary) is the fallback — this tradeoff should be made explicit in the plan, not left implicit.
**Warning signs:** A generated PNG where zooming in on country labels shows illegible smearing even at 300 DPI (indicates DPI needs to increase, e.g. to 400-600, or labels need to be dropped in favor of region-band annotations only).

### Pitfall 3: Reusing `panel_clean` (or its 70%-filtered exclusions) anywhere in the coverage computation
**What goes wrong:** If the notebook reads `panel_clean` instead of `raw_observations` for the coverage signal itself (even by copy-paste convenience from the Phase 2 notebook's style), the resulting figure would show the *filtered* coverage, silently violating COVER-01 and Success Criteria #2 ("verificable porque incluye países/pares que `panel_clean` excluye").
**Why it happens:** `notebook/2_1_construccion_panel_eda.ipynb` (the explicit style precedent for this phase, cell 9) reads exclusively from `panel_clean` — it's easy to habitually reach for the same table.
**How to avoid:** Only `raw_observations` (for the coverage signal) and `country_reference` (for the region join only, a reference/lookup table not affected by the 70% filter) should ever be read in this notebook. `panel_clean`/`panel_exclusions` should not appear at all.
**Warning signs:** If the resulting figure's total missing-cell count exactly matches `panel_exclusions`'s exclusion count rather than the true `raw_observations`-derived count (24,725 - 18,086 + 1,252 = 7,891 missing cells among the 215×23×5 grid), the wrong table was used.

## Code Examples

### Presence matrix + region ordering (`src/coverage.py`, proposed)
```python
# Source: adapted from src/panel_build.py's established reindex-to-complete-grid
# convention in this repository [VERIFIED: src/panel_build.py::compute_coverage]
from __future__ import annotations

import pandas as pd

INDICATOR_CODES: list[str] = ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"]
YEARS: list[int] = list(range(2000, 2023))


def build_presence_matrix(
    raw_observations: pd.DataFrame,
    countries: list[str],
    indicator_code: str,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """country x year boolean grid: True where a non-null value exists for
    (country, year, indicator_code). False covers BOTH 'no row at all' and
    'row exists but value IS NULL' (D-04) -- pivot+reindex already produce
    NaN for both, so a single .notna() unifies them without per-cell logic."""
    years = years or YEARS
    subset = raw_observations[raw_observations["indicator_code"] == indicator_code]
    wide = subset.pivot(index="country_code", columns="year", values="value")
    wide = wide.reindex(index=countries, columns=years)
    return wide.notna()


def ordered_countries_with_boundaries(
    country_reference: pd.DataFrame, countries: list[str]
) -> tuple[list[str], list[int]]:
    """Countries restricted to `countries` (raw_observations' universe),
    sorted by (region, subregion, country_code) for D-03's grouped y-axis,
    plus the row-index positions where a new region group starts (for
    axhline separators)."""
    ref = country_reference[country_reference["country_code"].isin(countries)].copy()
    ref = ref.sort_values(["region", "subregion", "country_code"], na_position="last")
    ordered = ref["country_code"].tolist()
    boundaries: list[int] = []
    prev_region = object()  # sentinel, never equal to a real region string
    for i, region in enumerate(ref["region"]):
        if region != prev_region:
            boundaries.append(i)
            prev_region = region
    return ordered, boundaries
```

### Notebook orchestration sketch (`notebook/7_1_mapa_calor_cobertura.ipynb`, proposed)
```python
# Source: adapted from notebook/2_1_construccion_panel_eda.ipynb's established
# PROJECT_ROOT/sys.path bootstrap + db.get_engine pattern [VERIFIED: this repository]
import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebook" else Path.cwd()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from src import db, coverage

engine = db.get_engine(str(PROJECT_ROOT / "data" / "panel.db"))
raw_observations = pd.read_sql("SELECT * FROM raw_observations", engine)
country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

countries = sorted(raw_observations["country_code"].unique())
ordered_countries, boundaries = coverage.ordered_countries_with_boundaries(country_reference, countries)

fig, axes = plt.subplots(1, 5, figsize=(24, 14), sharey=True)
cmap = ListedColormap(["#e8e8e8", "#2b6cb0"])
for ax, indicator in zip(axes, coverage.INDICATOR_CODES):
    matrix = coverage.build_presence_matrix(raw_observations, ordered_countries, indicator)
    sns.heatmap(matrix.astype(int), cmap=cmap, cbar=False, ax=ax, yticklabels=False)
    for b in boundaries:
        ax.axhline(y=b, color="black", linewidth=0.8)
    ax.set_title(indicator)
    ax.set_xlabel("Año")

axes[0].set_yticks([i + 0.5 for i in range(len(ordered_countries))])
axes[0].set_yticklabels(ordered_countries, fontsize=3.5)

fig.legend(
    handles=[Patch(color="#e8e8e8", label="Sin dato"), Patch(color="#2b6cb0", label="Dato presente")],
    loc="lower center", ncol=2,
)
fig.suptitle("Cobertura de datos crudos por indicador ODS, país y año (2000-2022)")
plt.tight_layout(rect=(0, 0.03, 1, 0.97))
plt.savefig(PROJECT_ROOT / "figuras" / "07_mapa_calor_cobertura.png", dpi=300, bbox_inches="tight")
plt.show()
```

## State of the Art

Not applicable in the "old vs new library API" sense — this phase uses no library feature that has meaningfully changed across versions relevant here. One note: matplotlib's `layout='constrained'` (stable since ~3.6, confirmed available at the pinned 3.11.0) is the modern replacement for manual `fig.subplots_adjust`/`tight_layout` tuning when arranging a multi-panel figure with a shared legend below it — worth considering over `plt.tight_layout()` for finer control of the legend's reserved space, though either works for this figure's modest complexity.

**Deprecated/outdated:** None identified as relevant to this phase's scope.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 300 DPI is an adequate resolution for this PNG's use in a printed/PDF thesis annex | Common Pitfalls (Pitfall 2), Code Examples | Low — DPI/size is explicitly Claude's Discretion per CONTEXT.md; if 300 DPI proves too coarse for legible zoomed country labels, bumping to 400-600 DPI is a one-line change with no architectural impact |
| A2 | A 1×5 horizontal subplot layout (vs. e.g. 5×1 vertical or 2×3 grid) best serves the thesis annex, assuming a landscape-oriented page for this figure | Architecture Patterns | Low-Medium — purely a layout choice (Claude's Discretion); if the memoria's page format can't accommodate a wide landscape figure, planner should pick a taller/narrower grid (e.g. 5 stacked rows) instead — same underlying `src/coverage.py` functions still apply |
| A3 | Small-font (3.5-4pt) per-country y-tick labels on the leftmost subplot are an acceptable resolution to the 215-country-label density problem, rather than omitting labels entirely | Common Pitfalls (Pitfall 2) | Medium — if the actual annex requirement is strict physical-print legibility (not digital zoom), this choice would need revisiting in favor of region-band-only labeling; flagged explicitly as an open question below |

## Open Questions

1. **Should `src/coverage.py` be introduced as a new module, or should all logic live inline in the notebook?**
   - What we know: D-05 only fixes the *entry point* (the notebook must be the reproducible driver); every other analytical phase (2-6) in this codebase extracts pure logic into a `src/*.py` module with matching `tests/test_*.py`, and the notebook only orchestrates + plots.
   - What's unclear: CONTEXT.md doesn't explicitly discuss whether Phase 7 should introduce a new `src/` module or keep everything notebook-inline (the phase's `code_context` section only lists reusable existing assets, not a decision about new modules).
   - Recommendation: Follow the established precedent (introduce `src/coverage.py` + `tests/test_coverage.py`) for consistency and testability — this is a research recommendation, not a locked decision; the planner should confirm this shape explicitly in the plan rather than assume it silently.

2. **Is per-country y-tick legibility at print size a hard requirement, or is digital-zoom legibility (at 300 DPI) sufficient?**
   - What we know: 215 countries cannot fit at a physically-print-legible font size in a reasonably-sized figure; CONTEXT.md's Claude's-Discretion section allows Claude to choose "orientación de etiquetas" and "tamaño de figura exacto" but doesn't address this specific tension.
   - What's unclear: Whether the tribunal/reviewer is expected to read individual country rows directly off a printed page, or whether digital-PDF zoom is the assumed reading mode for this specific figure (unlike, say, a results table).
   - Recommendation: Default to small-font (3.5-4pt) labels on the leftmost subplot at 300 DPI (assumes digital-PDF zoom is acceptable, consistent with how dense country-level figures are typically handled in econometrics theses). If this proves insufficient during Task/UAT review, the fallback is region-band-only annotation (label each region once at its `axhline` boundary, drop individual country labels).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pandas | Read raw_observations/country_reference, pivot/reindex | ✓ | 3.0.3 (`.venv`) | — |
| matplotlib | Subplot grid, savefig | ✓ | 3.11.0 (`.venv`) | — |
| seaborn | `sns.heatmap` per sub-panel | ✓ | 0.13.2 (`.venv`) | — |
| sqlalchemy | `src.db.get_engine` | ✓ | 2.0.51 (`.venv`) | — |
| `data/panel.db` (with `raw_observations` + `country_reference` populated) | Data source | ✓ (verified live: 18,086 raw rows, 215 countries, 248 country_reference rows, 0 orphaned country codes) | — | — |
| Jupyter / nbconvert (to verify "Kernel -> Restart & Run All" reproducibility, D-05) | Reproducibility check | ✓ (`jupyter` already in `requirements.txt`) | — | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None — everything this phase needs is already installed and populated.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already used repo-wide: `tests/test_panel_build.py`, `tests/test_interpret.py`, etc.) |
| Config file | none detected (no `pytest.ini`/`pyproject.toml [tool.pytest]` found) — tests run via bare `pytest` from repo root, matching existing precedent |
| Quick run command | `pytest tests/test_coverage.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COVER-01 | `build_presence_matrix` treats a wholly-absent (country, year) row as missing | unit | `pytest tests/test_coverage.py::test_build_presence_matrix_absent_row_is_missing -x` | ❌ Wave 0 |
| COVER-01 | `build_presence_matrix` treats a present row with `value IS NULL` as missing (same state as absent-row, D-04) | unit | `pytest tests/test_coverage.py::test_build_presence_matrix_null_value_is_missing -x` | ❌ Wave 0 |
| COVER-01 | `build_presence_matrix` treats a present row with a non-null value as present | unit | `pytest tests/test_coverage.py::test_build_presence_matrix_non_null_value_is_present -x` | ❌ Wave 0 |
| COVER-01 | `ordered_countries_with_boundaries` groups countries by region and returns correct boundary indices | unit | `pytest tests/test_coverage.py::test_ordered_countries_with_boundaries_groups_by_region -x` | ❌ Wave 0 |
| COVER-01 | Coverage computation reads `raw_observations`/`country_reference` only, never `panel_clean` (guards against Pitfall 3) | unit (static/import check, mirroring `tests/test_panel_build.py`'s style of asserting on function behavior, not just output) | `pytest tests/test_coverage.py::test_coverage_module_never_reads_panel_clean -x` | ❌ Wave 0 |
| COVER-02 | Notebook produces exactly one PNG file at `figuras/07_mapa_calor_cobertura.png` | manual (nbconvert execution + file-existence check) — Nyquist-appropriate since this is a one-shot notebook artifact, not a repeatedly-invoked function | `jupyter nbconvert --to notebook --execute notebook/7_1_mapa_calor_cobertura.ipynb` then verify the PNG exists | ❌ Wave 0 (notebook doesn't exist yet) |
| COVER-02 | The 5 ODS indicator codes are visually identifiable in the figure (e.g. as subplot titles) | manual (visual inspection of the generated PNG, human-verify checkpoint) | N/A — inherently a visual/manual check | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_coverage.py -x`
- **Per wave merge:** `pytest` (full suite — fast, this repo's existing suite runs in seconds per prior phases' velocity data)
- **Phase gate:** Full suite green, plus a manual `Kernel -> Restart & Run All` execution of `notebook/7_1_mapa_calor_cobertura.ipynb` confirming the PNG regenerates and the figure visually satisfies the 4 Roadmap Success Criteria, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `src/coverage.py` — does not exist yet; must be created before any test in `tests/test_coverage.py` can pass
- [ ] `tests/test_coverage.py` — covers COVER-01 (all rows above); mirror `tests/test_panel_build.py`'s fixture style (`tmp_path`-backed SQLite engine, a small synthetic `raw_observations`/`country_reference` pair covering: absent row, present-with-NULL row, present-with-value row, multiple regions)
- [ ] `notebook/7_1_mapa_calor_cobertura.ipynb` — does not exist yet (COVER-02's manual/visual checks depend on it)
- Framework install: none — pytest already installed and used project-wide

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase has no auth surface — local notebook/script reading a local SQLite file, no network-facing component |
| V3 Session Management | No | No sessions involved |
| V4 Access Control | No | No access-control boundary; single-user local analysis |
| V5 Input Validation | Marginal — no untrusted external input | All SQL reads use fixed, hardcoded table names (`raw_observations`, `country_reference`) via `pandas.read_sql`, no string interpolation of external input into SQL text — mirrors `src/db.py`/`src/panel_build.py`'s existing established pattern (Security V5, SQL injection avoidance already documented in `src/db.py`'s own module docstring) |
| V6 Cryptography | No | No secrets, no crypto operations in this phase |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via dynamically-built table/column names | Tampering | Not applicable here in practice (no external input reaches SQL text), but as a defensive habit: keep `pd.read_sql("SELECT * FROM raw_observations", engine)` with the fixed literal table name, never build the query string from a variable — mirrors `src/db.py`'s and `src/panel_build.py`'s existing pattern |
| Path traversal via a user-controlled output filename | Tampering | Not applicable — the PNG output path (`figuras/07_mapa_calor_cobertura.png`) is a fixed literal in the notebook, never derived from external/untrusted input |

**Overall assessment:** This phase's security surface is negligible — it is a local, read-only, no-network, single-file-output data visualization task with no untrusted input at any boundary. ASVS Level 1 controls are effectively satisfied by inheriting `src/db.py`'s existing parameterized-query discipline; no new controls are needed.

## Sources

### Primary (HIGH confidence)
- `src/db.py`, `src/panel_build.py`, `src/ingesta/typology.py` — read directly, this repository [VERIFIED: Read tool]
- Live query against `data/panel.db` via `sqlite3`/pandas — 18,086 `raw_observations` rows, 215 distinct countries, 1,252 `value IS NULL` rows, 248 `country_reference` rows, 8 distinct regions among the 215 ingested countries (sizes 4-49), 0 orphaned country codes between the two tables [VERIFIED: live query, this session]
- `.venv/Scripts/python.exe` import check — pandas 3.0.3, matplotlib 3.11.0, seaborn 0.13.2, sqlalchemy 2.0.51 all importable [VERIFIED: live shell check, this session]
- `notebook/2_1_construccion_panel_eda.ipynb` (style precedent, cell 9's `sns.heatmap(..., cmap="Reds", annot=True)`) [VERIFIED: Read tool]
- `tests/test_panel_build.py` (test-style precedent for `src/coverage.py`'s planned tests) [VERIFIED: Read tool]
- `.gitignore`, `git ls-files figuras/` — confirms `figuras/*.png` files are tracked/committed, not gitignored [VERIFIED: live shell check, this session]

### Secondary (MEDIUM confidence)
- seaborn.heatmap's `cbar`/`cbar_ax` parameters for shared-colorbar patterns [CITED: seaborn.pydata.org/generated/seaborn.heatmap.html]
- matplotlib's official annotated-heatmap gallery example for grid-separator-line techniques (adapted from every-row minor-tick-grid to boundary-only `axhline`) [CITED: matplotlib.org/stable/gallery/images_contours_and_fields/image_annotated_heatmap.html]

### Tertiary (LOW confidence)
- 300 DPI as a common rule-of-thumb for publication/thesis figures (various blog sources, not an official style guide; this is a Claude's-Discretion parameter per CONTEXT.md, so LOW confidence here is an acceptable risk level, logged as Assumption A1) [WebSearch, multiple non-official sources — not officially cited]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, all versions verified live in `.venv`
- Data/architecture (pivot+reindex, region join, table shapes): HIGH — verified live against the actual `data/panel.db`, not assumed
- Visualization layout/color specifics (DPI, exact figsize, exact palette hex): MEDIUM/LOW — these are explicitly Claude's Discretion per CONTEXT.md; guidance here is a well-reasoned recommendation (grounded in the dataviz skill's status-encoding rule and matplotlib's own documented APIs), not a locked fact

**Research date:** 2026-07-15
**Valid until:** No expiry pressure — this phase depends only on already-ingested, static historical data (2000-2022) and already-pinned library versions; safe to treat as valid through the rest of this milestone's execution.
