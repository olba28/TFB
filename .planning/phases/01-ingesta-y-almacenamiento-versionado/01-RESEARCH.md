# Phase 1: Ingesta y Almacenamiento Versionado - Research

**Researched:** 2026-07-10
**Domain:** UN SDG API batch ingestion → immutable raw/manifest storage → SQLite panel storage (long + derived wide table) for a solo academic econometrics thesis
**Confidence:** HIGH (UN SDG API behavior live-verified against production endpoints in this session; stack/library choices already empirically verified in project-wide research; M49/country-classification approach is MEDIUM — the exact scriptable source for the ISO3 crosswalk required one-time manual acquisition, documented below)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Paginación y reintentos**
- **D-01:** 3 reintentos con backoff exponencial (1s, 2s, 4s) ante fallos transitorios de la API.
- **D-02:** El cliente itera automáticamente por páginas usando el campo `totalElements`/`pageSize` de la respuesta de la API, sin asumir un tamaño de página fijo.
- **D-03:** El comportamiento de reintento/paginación (Success Criteria #4 del roadmap) se verifica con un test unitario que mockea `requests` (`unittest.mock` o `responses`) simulando un fallo 500 y una respuesta paginada — no una prueba manual ni un test de integración real contra la API.
- **D-04:** Se introduce un delay fijo pequeño (0.5–1s) entre llamadas a la API para evitar bloqueos, dado el volumen (5 indicadores × 150+ países).

**Manifiesto y almacenamiento crudo**
- **D-05:** Un manifiesto de procedencia por indicador (no uno global ni uno por ejecución).
- **D-06:** Estructura de carpetas `data/raw/{indicador}/{fecha}.json` — permite comparar versiones del mismo indicador a lo largo del tiempo.
- **D-07:** La descarga es idempotente: el script comprueba el manifiesto antes de llamar a la API y solo descarga si no existe una copia o si se fuerza explícitamente.
- **D-08:** El manifiesto registra: fecha de descarga, URL, parámetros de consulta, número de filas y checksum del fichero descargado.

**Esquema SQLite**
- **D-09:** El fichero de base de datos vive en `data/panel.db`.
- **D-10:** `raw_observations` incluye las columnas: `country_code` (ISO3), `indicator_code`, `year`, `value`, `dimension` (valor original de la dimensión de la API, p. ej. `Activity`), `source_manifest_id` (referencia al manifiesto de origen).
- **D-11:** La unicidad (país, año, indicador) — Success Criteria #1 del roadmap — se aplica con un `UNIQUE constraint` en SQLite **y** un `assert` explícito en el pipeline de carga antes de insertar (doble verificación: esquema + código).
- **D-12:** `panel` (tabla ancha) es una vista/tabla derivada, regenerable siempre desde `raw_observations` mediante pivot indicador→columnas. Nunca se edita a mano — coherente con el pipeline idempotente que construirá la Fase 2.

**Lista canónica de países y crosswalk M49↔ISO3**
- **D-13:** La lista canónica de países sale de la clasificación oficial M49 de la ONU (distinción "country/area" vs. agregados regionales), no de pycountry ni de la lista del Banco Mundial — alineada con la propia fuente de datos (API SDG).
- **D-14:** Territorios/casos disputados o no soberanos (Kosovo, Taiwán, Palestina, Hong Kong) se incluyen si la API los reporta con código país (ISO3) y no como agregado regional M49 — criterio objetivo aplicado uniformemente, sin lista de excepciones manual.
- **D-15:** La lista canónica y el crosswalk M49↔ISO3 viven en `src/ingesta/countries.py` (constante + función de filtrado) — módulo reutilizable por la Fase 2 sin duplicar lógica.
- **D-16:** El pipeline de ingesta genera un log/tabla de exclusiones (qué códigos M49/regiones se descartaron y por qué) como insumo documentado para la memoria — no un filtrado silencioso.

> **Research flag on D-14:** live-verified, the API's `Indicator/Data` endpoint never returns an ISO3 code at all (only `geoAreaCode`, an M49 numeric string, and `geoAreaName`). D-14's phrasing ("si la API los reporta con código país (ISO3)") should be operationalized as: *"si el `geoAreaCode` del indicador resuelve a una entrada de tipo `Country` en la clasificación M49 (ver hallazgo GeoArea/Tree más abajo), y no aparece únicamente como hijo de un agregado regional."* This is a clarification of mechanism, not a change of intent — flagged here for the planner/discuss-phase to confirm, not silently resolved.

### Claude's Discretion
- Nombre exacto de la función/módulo del cliente API, organización interna de `src/ingesta/` (p. ej. `fetch.py`, `client.py`, `manifest.py` como ficheros separados vs. un solo módulo).
- Formato exacto del checksum (sha256 vs md5) — cualquiera es válido mientras sea determinista y verificable.
- Mecanismo concreto para generar `requirements.lock.txt` (script dedicado vs. instrucción en README) — REPRO-01 solo exige que el fichero exista y refleje `pip freeze`.

### Deferred Ideas (OUT OF SCOPE)
None — la discusión se mantuvo dentro del alcance de la Fase 1.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INGEST-01 | Obtener vía API SDG los 5 indicadores (6.4.2, 6.4.1, 8.1.1, 8.2.1, 2.3.1) para 150+ países 2000–2022, con paginación y reintentos | Live-verified endpoint, query params, pagination fields, and all 5 series codes/dimension shapes documented below (UN SDG API section). Retry/backoff pattern (`urllib3.Retry` + `HTTPAdapter`) documented in Code Examples. |
| INGEST-02 | Filtrar por dimensión (p. ej. `Activity: TOTAL`) para evitar filas duplicadas país-año | **Critical finding:** each indicator has a *different* dimension key set (see table below) — filtering cannot hardcode `Activity: TOTAL` globally. Per-indicator filter spec documented in Common Pitfalls Pitfall 1 and Code Examples. |
| INGEST-03 | Excluir agregados regionales M49 del panel, con crosswalk M49↔ISO3 y lista canónica | `GeoArea/Tree` endpoint (live-verified) provides an API-native `type` field (`Country`/`Region`/other) to build the canonical list — see "M49 Canonical List" section. ISO3 crosswalk requires a one-time acquisition from the official M49 table (documented, with provenance). |
| INGEST-04 | Copia local versionada del JSON crudo + manifiesto de procedencia | Manifest schema, folder structure (`data/raw/{indicador}/{fecha}.json`), and idempotency check pattern documented below. **Critical repo finding:** the project's `.gitignore` is currently a plain `gitignore` file (no leading dot) and is NOT active — raw JSON would currently be committed to git. Flagged as a required fix task. |
| INGEST-05 | Almacenar el panel en SQLite (`raw_observations` larga + `panel` ancha derivada) | DDL, UNIQUE constraint + assert double-check pattern, and derived-table regeneration pattern documented in SQLite Schema section and Code Examples. |
| REPRO-01 | `requirements.lock.txt` vía `pip freeze` | Documented in Standard Stack / Environment Availability — no venv currently exists; must be created before this requirement can be satisfied. |

</phase_requirements>

## Summary

Phase 1 is a batch, single-run ingestion pipeline against the UN SDG public API (`unstats.un.org/SDGAPI/v1/sdg/`), landing data into an immutable raw-JSON + manifest layer and a `raw_observations` SQLite table, with a `panel` table as a thin derived pivot. Everything needed to implement CONTEXT.md's 16 locked decisions was live-verified against the production API in this session (not just documentation): the exact endpoint, query parameters, pagination fields, and — critically — the **exact series code and dimension-key set for all 5 indicators**, not just 6.4.2 (which is all the prior project-wide research had tested). This surfaces the single most important new finding of this phase-specific research: **dimension filtering is not one universal rule** — `Activity: TOTAL` applies to the two water indicators (6.4.2, 6.4.1), but 2.3.1 needs `Sex: BOTHSEX` and 8.1.1/8.2.1 have no extra dimension beyond `Reporting Type: G` at all. A hardcoded `Activity: TOTAL` filter would silently produce zero rows for 3 of the 5 indicators.

The second major finding concerns the country/region crosswalk (D-13, which explicitly rejects `pycountry` and the World Bank list in favor of "la clasificación oficial M49"). The official M49 table (`unstats.un.org/unsd/methodology/m49/`) has no scriptable export — it's a JS-triggered download only. Two complementary, code-native sources close this gap: (1) the SDG API's own `GeoArea/Tree` endpoint, live-verified to return a `type` field (`Country`/`Region`/`Other areas`/etc.) with `children: null` on leaf countries — an API-native way to build the canonical exclusion list without any browser step; and (2) a one-time manual acquisition of the official M49 CSV (with its `ISO-alpha3 Code` column) to get the M49-numeric↔ISO3 crosswalk `raw_observations.country_code` requires, versioned in the repo with documented provenance. This satisfies D-13's "not pycountry, not World Bank" constraint since both sources are the UN's own classification, not a third-party library.

A third, purely repo-hygiene finding directly threatens INGEST-04 and the reproducibility goal: the file meant to be `.gitignore` is currently checked in as a plain file named `gitignore` (no leading dot) and is **not active** — `git check-ignore` confirms `data/raw/**/*.json` is not currently ignored. Without fixing this, every downloaded indicator JSON will be committed to git history, bloating the repo and contradicting the project's own stated intent (visible in the file's own comments) to keep only manifests versioned.

**Primary recommendation:** Build `src/ingesta/` as a `client.py` (HTTP + pagination + retry), `countries.py` (M49 canonical list + ISO3 crosswalk + exclusion log, per D-15), `manifest.py` (provenance JSON per indicator, per D-05/D-08), and `fetch_data.py` (orchestrator: client → per-indicator dimension filter → raw JSON + manifest → `raw_observations` insert with UNIQUE + assert). Fix the `.gitignore` naming bug and extend it to cover `data/panel.db` before any data is fetched. Install `pytest`/`pytest-cov` (dev-only) and use `unittest.mock` (already the codebase's documented convention, zero new runtime dependency) for the D-03 mocked retry/pagination test.

## Architectural Responsibility Map

> This project is a solo-author batch data pipeline, not a client/server web app — the standard browser/API/CDN tier taxonomy doesn't apply directly. Tiers below use this project's own five-layer pipeline vocabulary (already established in `.planning/research/ARCHITECTURE.md` and `.planning/codebase/ARCHITECTURE.md`).

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTTP client, pagination, retry/backoff | Ingestion (`src/ingesta/client.py`) | — | Sole point of contact with the external API; must own all pagination/retry logic so nothing downstream re-implements it |
| Dimension filtering (per-indicator headline row selection) | Ingestion (`src/ingesta/fetch_data.py`) | Storage (UNIQUE constraint as backstop) | Filtering must happen before any row reaches SQLite (D-11's assert requires already-filtered input); the DB constraint is a second, independent line of defense, not the primary filter |
| M49 canonical country list + ISO3 crosswalk + exclusion log | Ingestion (`src/ingesta/countries.py`) | Storage (Phase 2 reuses as-is) | D-15 explicitly designates this as a shared, reusable module — it is ingestion-time logic but its output (exclusion log) is also a Storage/documentation artifact |
| Provenance manifest (date, URL, params, checksum, row count) | Ingestion (`src/ingesta/manifest.py`) | Filesystem (`data/raw/`) | Manifest is generated at ingestion time but its permanent home is the versioned raw-data folder tree |
| Raw JSON versioned snapshot | Filesystem (`data/raw/{indicador}/{fecha}.json`) | — | Immutable, never edited; the audit trail requirement (INGEST-04) lives here, not in the database |
| `raw_observations` (long, immutable) | Storage (SQLite, `data/panel.db`) | — | Single source of truth for all downstream phases; UNIQUE constraint is schema-level enforcement |
| `panel` (wide, derived pivot) | Storage (SQLite, `data/panel.db`) | ETL (regeneration logic in Phase 2) | Phase 1 only builds the basic indicator→columns pivot (per CONTEXT.md's Phase Boundary); full cleaning/feature engineering is explicitly Phase 2's job |
| `requirements.lock.txt` generation | Reproducibility tooling (repo root) | — | Not a pipeline stage — a one-time-per-environment snapshot step, but REPRO-01 requires it exist and be current |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.32.3 (currently installed globally; `>=2.31` already pinned) | HTTP client for the UN SDG API | Zero-controversy choice for an unauthenticated batch REST/JSON API at this scale (~150 countries × 5 indicators, not high-concurrency) `[VERIFIED: pip show, local environment]` |
| urllib3 (bundled with requests) | — | `Retry` + `HTTPAdapter` for automatic exponential backoff | Standard library-level retry mechanism; avoids hand-rolling a retry loop and matches D-01's exact 1s/2s/4s sequence when configured `total=3, backoff_factor=1` `[CITED: urllib3.readthedocs.io/en/stable/reference/urllib3.util.html]` |
| pandas | 2.2.2 (currently installed globally; `>=2.0` already pinned) | Parse API JSON into DataFrames, dimension filtering, `to_sql`/`read_sql` for the SQLite round-trip | Already the project's core data structure; project-wide `research/STACK.md` recommends pairing with a SQLAlchemy `Engine` rather than a raw `sqlite3.Connection` for `to_sql`/`read_sql` (pandas docs describe raw-connection support as legacy-only) `[CITED: research/STACK.md, pandas.pydata.org docs]` |
| sqlite3 (Python stdlib) | 3.45.3 (bundled with Python 3.12.4) | Underlying SQLite engine for `data/panel.db` | No install needed; zero-configuration per PROJECT.md's own storage decision `[VERIFIED: local `python -c "import sqlite3"`]` |
| hashlib (Python stdlib) | — | Checksum computation for the manifest (D-08) | `hashlib.sha256(...).hexdigest()` is deterministic, stdlib, no new dependency — satisfies "Claude's Discretion" on checksum format; prefer sha256 over md5 (md5 has no cryptographic value here but sha256 costs nothing extra and is the more defensible default for a submitted thesis) `[ASSUMED: standard practice, not independently benchmarked this session]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | not yet installed (`.planning/codebase/TESTING.md` already recommends it) | Test runner for the D-03 mocked retry/pagination test and the D-11 uniqueness-assert test | Needed the moment any `tests/` file is written — currently zero test infrastructure in the repo (`no venv found`, `pytest` import fails) |
| pytest-cov | not yet installed | Coverage reporting | `.planning/codebase/TESTING.md` already recommends ≥80% overall, 100% for ingestion specifically |
| unittest.mock (Python stdlib) | — | Mock `requests.get`/`Session.get` for D-03's simulated 500 + paginated response test | Already the codebase's documented convention (`TESTING.md`) — zero new dependency, sufficient for the required test scope. Prefer this over the `responses` package unless pagination-mock boilerplate becomes unwieldy. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `unittest.mock` for HTTP mocking | `responses` library (`getsentry/responses`) | More declarative for multi-call/pagination sequences (`responses.add()` per call), but is an added dependency; D-03 explicitly permits either. Only switch if the mocked-pagination test becomes hard to read with plain `unittest.mock`. |
| Manual M49 CSV acquisition + `GeoArea/Tree` cross-check | `pycountry` | **Explicitly rejected by D-13** — not an option for this phase regardless of convenience. |
| SQLAlchemy `Engine` for `to_sql`/`read_sql` | Raw `sqlite3.Connection` + manual `INSERT` with `?` placeholders | Acceptable for the D-11 assert-before-insert pattern (arguably clearer to reason about transaction/assert ordering with raw `sqlite3` + explicit `cursor.execute`), but pandas' own docs treat the raw-connection path as legacy for bulk `to_sql`. Either is fine for this phase's scale; pick one, document it, and keep it consistent with what Phase 2 will need for `panel` table regeneration. |

**Installation:**
```bash
# No new runtime dependencies beyond what's already in requirements.txt (requests, pandas, numpy).
# Dev-only additions for testing (not in requirements.txt — separate requirements-dev.txt per TESTING.md convention):
pip install pytest pytest-cov

# After finalizing the environment (REPRO-01):
pip freeze > requirements.lock.txt
```

**Version verification:** `requests` and `pandas` were checked against the locally installed global Python 3.12.4 environment in this session (`pip show`-equivalent via `import X; print(X.__version__)`) — versions above are directly observed, not assumed. No `.venv` currently exists in the repo (see Environment Availability below); this must be created before REPRO-01 can be satisfied, since a global-interpreter `pip freeze` would capture unrelated system packages.

## Package Legitimacy Audit

| Package | Registry | Age (of latest release checked) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----------|-----------|-------------|---------|-------------|
| pytest | PyPI | Latest release 2026-06-19 | Not resolvable by the legitimacy tool | github.com/pytest-dev/pytest | `[SUS]` (heuristic: "too-new" + "unknown-downloads") | **Approved with note** — pytest is the de facto standard Python test framework (in wide use since the mid-2000s); the SUS verdict is a tool heuristic false-positive triggered by checking the most recent release timestamp rather than the package's actual first-publish date. Per protocol, the planner should still add a lightweight `checkpoint:human-verify` before `pip install pytest`, but this can be a one-line sanity check, not a deep investigation. |
| pytest-cov | PyPI | Latest release 2026-03-21 | Not resolvable | Not resolved by the tool (repo exists at github.com/pytest-dev/pytest-cov) | `[SUS]` ("unknown-downloads", "no-repository") | **Approved with note** — same heuristic limitation; pytest-cov is the standard coverage plugin for pytest. `checkpoint:human-verify` recommended before install, same rationale as above. |
| responses | PyPI | Latest release 2026-07-03 | Not resolvable | github.com/getsentry/responses | `[SUS]` ("too-new", "unknown-downloads") | **Not needed this phase** — D-03 is satisfied by `unittest.mock` (stdlib, already the codebase convention per TESTING.md), so `responses` is not part of the recommended installation. Listed here only because it was evaluated as an alternative; do not install unless the planner deliberately chooses it over `unittest.mock`. |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** pytest, pytest-cov (approved with a lightweight human-verify checkpoint — see notes above; both are extremely well-established, ubiquitous packages, and the SUS signal traces to the legitimacy tool's release-recency heuristic, not any actual red flag like a missing repo, deprecation, or suspicious postinstall script). `responses` evaluated but not recommended for installation this phase.

*No `postinstall` scripts were found for any of the three packages checked (`npm view`-equivalent check via the legitimacy seam returned `postinstall: null` for all).*

## Architecture Patterns

### System Architecture Diagram

```text
                 ┌─────────────────────────────────────────────┐
                 │   UN SDG API (unstats.un.org/SDGAPI/v1/sdg/) │
                 │   GET /Indicator/Data   GET /GeoArea/Tree    │
                 └───────────────────┬───────────────────────────┘
                                     │  paginated GET, 1 per (indicator, page)
                                     ▼
                 ┌─────────────────────────────────────────────┐
                 │  src/ingesta/client.py                       │
                 │  - Session + HTTPAdapter(Retry(3, backoff=1))│
                 │  - loop page=1..N until len(rows)==totalElem.│
                 │  - 0.5-1s delay between calls (D-04)         │
                 └───────────────────┬───────────────────────────┘
                                     │ raw JSON pages (all dimensions, unfiltered)
                                     ▼
                 ┌─────────────────────────────────────────────┐
                 │  src/ingesta/fetch_data.py (orchestrator)     │
                 │  1. check manifest -> skip if exists (D-07)  │
                 │  2. write data/raw/{indicador}/{fecha}.json  │
                 │  3. write manifest.py -> manifest.json (D-08)│
                 │  4. filter to per-indicator headline dims    │
                 │  5. join geoAreaCode -> countries.py filter  │
                 │  6. assert (country,year) unique per indic.  │
                 └──────┬──────────────────────────┬─────────────┘
                        │                          │
                        ▼                          ▼
        ┌───────────────────────────┐   ┌───────────────────────────┐
        │ src/ingesta/countries.py  │   │ data/raw/<ind>/<date>.json │
        │ - M49 canonical list      │   │ (immutable, versioned,     │
        │   (GeoArea/Tree + M49 CSV)│   │  git-ignored except        │
        │ - M49->ISO3 crosswalk     │   │  manifest.json)            │
        │ - exclusion log (D-16)    │   └───────────────────────────┘
        └──────────────┬────────────┘
                       │ filtered, ISO3-tagged rows
                       ▼
        ┌───────────────────────────────────────────────┐
        │  data/panel.db (SQLite)                        │
        │  ┌─────────────────────┐  ┌──────────────────┐│
        │  │ raw_observations     │  │ panel (derived,  ││
        │  │ (long, immutable,    │─▶│ wide pivot,      ││
        │  │ UNIQUE constraint +  │  │ regenerated from ││
        │  │ assert before insert)│  │ raw_observations)││
        │  └─────────────────────┘  └──────────────────┘│
        └───────────────────────────────────────────────┘
```

### Recommended Project Structure
```
src/ingesta/
├── __init__.py
├── client.py        # HTTP session, pagination loop, retry/backoff (D-01, D-02, D-04)
├── countries.py     # M49 canonical list, M49<->ISO3 crosswalk, exclusion log (D-13-D-16)
├── manifest.py       # Provenance manifest read/write (D-05, D-08)
└── fetch_data.py     # Orchestrator: client -> filter -> countries -> raw file -> manifest -> SQLite (D-07, D-11)

src/db.py             # SQLite connection/engine + DDL for raw_observations, panel (D-09-D-12)

data/
├── raw/
│   └── {indicador}/{fecha}.json      # e.g. data/raw/6.4.2/2026-07-10.json
└── panel.db                          # SQLite, single file (D-09)

tests/
├── conftest.py
└── ingesta/
    ├── test_client.py        # D-03: mocked 500 + paginated response
    ├── test_countries.py     # M49 exclusion / crosswalk correctness
    ├── test_manifest.py      # manifest schema + idempotency check
    └── test_db.py            # UNIQUE constraint + assert dedup (D-11)
```

### Pattern 1: Session-level retry via `urllib3.Retry` + `HTTPAdapter`
**What:** Configure retry/backoff once on a `requests.Session`, not per-call.
**When to use:** Any code path that calls the UN SDG API — never construct a bare `requests.get()` outside `client.py`.
**Example:**
```python
# Source: urllib3.readthedocs.io/en/stable/reference/urllib3.util.html (CITED)
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,                     # D-01: 3 reintentos
        backoff_factor=1,            # produces 1s, 2s, 4s delays
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True,
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session
```

### Pattern 2: Per-indicator dimension filter, not a global "Activity: TOTAL" rule
**What:** Each indicator's `dimensions` dict has a different key set — a config table maps indicator code to its headline dimension combination.
**When to use:** Immediately after fetching each indicator's raw pages, before any row reaches `countries.py` or SQLite.
**Example:**
```python
# Source: live-verified against unstats.un.org/SDGAPI/v1/sdg/Indicator/Data (VERIFIED: SDGAPI live query, 2026-07-10)
HEADLINE_DIMENSIONS = {
    "6.4.2": {"Activity": "TOTAL"},          # + always require Reporting Type == "G"
    "6.4.1": {"Activity": "TOTAL"},
    "8.1.1": {},                              # only Reporting Type == "G", no extra dimension
    "8.2.1": {},                              # dimensions also include "Age": "15+" — treat as headline default, verify no alt-age rows exist
    "2.3.1": {"Sex": "BOTHSEX"},
}

def filter_headline_rows(rows: list[dict], indicator_code: str) -> list[dict]:
    required = {"Reporting Type": "G", **HEADLINE_DIMENSIONS[indicator_code]}
    return [r for r in rows if all(r["dimensions"].get(k) == v for k, v in required.items())]
```

### Pattern 3: Idempotent fetch guarded by manifest existence
**What:** Before calling the API, check whether `data/raw/{indicador}/{fecha}.json` + its manifest already exist for today's date; skip unless `force=True`.
**When to use:** Every ingestion run (D-07).
**Example:**
```python
# Source: derived from CONTEXT.md D-07 + D-08 (project decision, not external doc)
from pathlib import Path
from datetime import date

def fetch_indicator(indicator_code: str, force: bool = False) -> Path:
    today = date.today().isoformat()
    raw_path = Path(f"data/raw/{indicator_code}/{today}.json")
    manifest_path = raw_path.with_name(f"{today}.manifest.json")
    if raw_path.exists() and manifest_path.exists() and not force:
        return raw_path  # idempotent skip
    # ... fetch, write raw_path, write manifest_path ...
    return raw_path
```

### Pattern 4: UNIQUE constraint + explicit assert (belt and suspenders, per D-11)
**What:** Schema-level `UNIQUE(country_code, year, indicator_code, dimension)` catches genuine duplicate inserts; a Python-level `assert` catches logic errors *before* the insert is even attempted, giving a clearer error message during development.
**Example:**
```python
# Source: SQLite DDL — standard pattern, not an external citation (well-established RDBMS practice)
CREATE_RAW_OBSERVATIONS = """
CREATE TABLE IF NOT EXISTS raw_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL,       -- ISO3
    indicator_code TEXT NOT NULL,     -- e.g. '6.4.2'
    year INTEGER NOT NULL,
    value REAL,
    dimension TEXT NOT NULL,          -- original API dimension combo, e.g. 'Activity=TOTAL'
    source_manifest_id TEXT NOT NULL, -- FK-like reference to a manifest file/id
    UNIQUE(country_code, year, indicator_code)
);
"""

def insert_observations(conn, df):
    key_cols = ["country_code", "year", "indicator_code"]
    assert not df.duplicated(subset=key_cols).any(), (
        f"Duplicate (country, year, indicator) rows before insert: "
        f"{df[df.duplicated(subset=key_cols, keep=False)][key_cols].to_dict('records')}"
    )
    df.to_sql("raw_observations", conn, if_exists="append", index=False)
```

### Anti-Patterns to Avoid
- **Hardcoding `Activity: TOTAL` as the universal dimension filter:** breaks silently for 8.1.1, 8.2.1, and 2.3.1 (different or absent dimension keys) — see Pitfall 1 below.
- **Using `pycountry` or the World Bank country list for the canonical country list:** explicitly rejected by D-13 regardless of convenience — use the M49 classification (`GeoArea/Tree` + the official M49 CSV) instead.
- **Editing `panel` by hand:** per D-12 it must always be regenerated from `raw_observations` via pivot; never patch it directly.
- **Treating a `200 OK` as "data is correct":** the SDG API is explicitly published as a test/development service (per project-wide `research/PITFALLS.md`); this phase should log enough (manifest, checksum) to support the spot-check step Phase 2's EDA will need, even though the spot-check itself is out of this phase's scope.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry with exponential backoff | A manual `for attempt in range(3): try/except/time.sleep(...)` loop | `urllib3.util.Retry` + `requests.adapters.HTTPAdapter` mounted on a `Session` | Handles edge cases (which status codes to retry, `Retry-After` header, method allowlist) that a hand-rolled loop tends to miss or get subtly wrong; also directly produces the exact 1s/2s/4s sequence D-01 specifies with one line of config |
| Checksum computation | Custom hashing scheme | `hashlib.sha256(path.read_bytes()).hexdigest()` | Stdlib, deterministic, zero new dependency, and the industry-default choice for this exact provenance use case |
| SQLite connection pooling / transaction handling for the `to_sql`/`read_sql` path | Manual `sqlite3.Connection` juggling with manual commit/rollback | SQLAlchemy `Engine` (`create_engine("sqlite:///data/panel.db")`) if pandas' bulk I/O is the primary access pattern | pandas' own docs mark raw `sqlite3.Connection` as legacy-only for `to_sql`/`read_sql`; avoids reinventing transaction safety `[CITED: research/STACK.md, pandas.pydata.org]` |

**Key insight:** Every "don't hand-roll" item above already has a stdlib or already-pinned-dependency solution — this phase introduces zero new mandatory runtime dependencies beyond what `requirements.txt` already lists.

## Common Pitfalls

### Pitfall 1: Hardcoding a single dimension filter across all 5 indicators
**What goes wrong:** A filter written for 6.4.2 (`Activity: TOTAL`) silently returns zero rows for 8.1.1 and 8.2.1 (no `Activity` key at all in their `dimensions` dict) and wrong/duplicate rows for 2.3.1 (needs `Sex: BOTHSEX`, not `Activity`).
**Why it happens:** Prior project-wide research (`research/STACK.md`) only live-tested 6.4.2 in depth; it's easy to generalize one indicator's shape to all five.
**How to avoid:** Use the per-indicator `HEADLINE_DIMENSIONS` config table (Code Examples, Pattern 2), and add an assertion after filtering: `assert len(filtered) > 0, f"No rows survived dimension filter for {indicator_code}"`.
**Warning signs:** Zero rows (or an unexpectedly small count) for 8.1.1/8.2.1/2.3.1 after filtering; a filter that only ever checks `dimensions.get("Activity")`.
`[VERIFIED: SDGAPI live query, 2026-07-10]`

### Pitfall 2: Regional aggregates leaking in because M49 codes for regions and countries look identical
**What goes wrong:** `GeoArea/List` (the flat endpoint) returns countries and aggregates ("World", "Sub-Saharan Africa", "LLDC", etc.) with no distinguishing field — a naive "pull every geoAreaCode seen in Indicator/Data" approach will include these.
**How to avoid:** Cross-reference every `geoAreaCode` seen in `Indicator/Data` against `GeoArea/Tree`'s `type == "Country"` leaf nodes (live-verified: leaves have `children: null`; aggregates have `type: "Region"` and non-null `children`). Log every excluded code + its containing aggregate name for D-16's exclusion table.
**Warning signs:** Country count in the raw panel exceeding ~200; entries named "World", "Africa", "High income" surviving into `raw_observations`.
`[VERIFIED: SDGAPI GeoArea/Tree live query, 2026-07-10]`

### Pitfall 3: `.gitignore` is not actually active in this repo
**What goes wrong:** The repo's ignore rules live in a file literally named `gitignore` (no leading dot), which git does not recognize — confirmed via `git check-ignore -v` returning no match for a `data/raw/**/*.json` test path. Every downloaded indicator JSON would currently be committed to git history the moment ingestion runs.
**Why it happens:** A one-character naming slip that's easy to miss since the file's *contents* already correctly describe the intended ignore rules (including the exact `data/**/*.json` / `!data/**/manifest.json` pattern this phase needs).
**How to avoid:** Rename `gitignore` → `.gitignore` as an early task in this phase's plan (before the first fetch is run), and add a pattern for `data/panel.db` (currently not covered by the existing rules at all — see Open Questions).
**Warning signs:** `git status` showing untracked/modified files under `data/raw/` after running ingestion once.
`[VERIFIED: local repo inspection — git ls-files, git check-ignore, 2026-07-10]`

### Pitfall 4: Unbalanced page counts across indicators lead to very different total row counts
**What goes wrong:** Live-verified total row counts before filtering: 6.4.2 ≈ 20,016 rows (201 pages @ 100/page), 6.4.1 ≈ 19,656 rows (3,932 pages @ 5/page in the sampled call — actual production `pageSize` should be 500–2000 per project-wide research), 8.1.1 ≈ 6,178, 2.3.1 ≈ 5,441, 8.2.1 ≈ 5,888. A pagination loop that assumes a fixed page count across indicators (rather than reading `totalPages`/`totalElements` fresh per indicator, per D-02) will under- or over-fetch.
**How to avoid:** Always loop until `page >= totalPages` (or accumulated rows == `totalElements`) read from *that indicator's* first response — never assume a shared page count across indicators.
**Warning signs:** Row count for one indicator suspiciously close to another's total, or a loop that exits after a hardcoded number of pages.
`[VERIFIED: SDGAPI live queries for all 5 indicators, 2026-07-10]`

### Pitfall 5: Values arriving as non-numeric strings (including the literal string `"NaN"`)
**What goes wrong:** Live-verified: indicator 2.3.1's `value` field can be the literal JSON string `"NaN"` (not a JSON null, not a number) when `attributes.Observation Status` indicates missing/no-data. A naive `float(row["value"])` will raise, or `pd.to_numeric` needs `errors="coerce"` to avoid crashing the whole batch.
**How to avoid:** Parse `value` with `pd.to_numeric(series, errors="coerce")` so `"NaN"` strings become proper `NaN` floats rather than crashing ingestion; do not silently drop these rows at this phase (that's Phase 2's coverage-filter job) — store them as `NULL`/`NaN` in `raw_observations`.
**Warning signs:** `ValueError: could not convert string to float: 'NaN'` during ingestion; row counts dropping unexpectedly if a naive `try/except: continue` swallows these.
`[VERIFIED: SDGAPI live query for indicator 2.3.1, 2026-07-10]`

## Code Examples

### M49 canonical list from `GeoArea/Tree` (API-native, satisfies D-13's "align with the data source itself")
```python
# Source: live-verified structure of GET https://unstats.un.org/SDGAPI/v1/sdg/GeoArea/Tree
# (VERIFIED: SDGAPI live query, 2026-07-10)
def collect_countries(tree_nodes: list[dict]) -> dict[str, str]:
    """Walk the GeoArea/Tree response; return {geoAreaCode: geoAreaName} for type=='Country' leaves.
    Note: the same country can appear under multiple top-level groupings (e.g. 'by SDG regions'
    and 'by continental regions') — dict keys naturally dedupe by geoAreaCode.
    """
    countries: dict[str, str] = {}
    excluded: list[dict] = []

    def walk(node: dict, parent_name: str) -> None:
        if node["type"] == "Country":
            countries[node["geoAreaCode"]] = node["geoAreaName"]
        else:
            excluded.append({"code": node["geoAreaCode"], "name": node["geoAreaName"],
                              "type": node["type"], "parent": parent_name})
        for child in (node.get("children") or []):
            walk(child, node["geoAreaName"])

    for root in tree_nodes:
        walk(root, parent_name="ROOT")
    return countries  # exclusion log (D-16) built from `excluded`, deduped by code
```

### M49 → ISO3 crosswalk (one-time acquisition, per D-13/D-15)
The official M49 standard table (`unstats.un.org/unsd/methodology/m49/`) includes an `ISO-alpha3 Code` column but has no scriptable export endpoint — only JS-triggered CSV/Excel download buttons `[CITED: unstats.un.org/unsd/methodology/m49/overview/, WebFetch inspection 2026-07-10]`. Recommended approach:
1. One-time manual step: download the official CSV/Excel export from the methodology page, save as a versioned reference file in the repo (e.g. `src/ingesta/data/m49_countries.csv`), and record the download date + source URL in a comment at the top of the file (or a small sidecar `.manifest.json` next to it, mirroring D-08's pattern).
2. `countries.py` loads this file at import time and builds the `{m49_code: iso3}` dict.
3. Cross-check every code against `GeoArea/Tree`'s `type == "Country"` set (previous example) — if a code appears in the M49 CSV but not in the live API tree (or vice versa), log it explicitly rather than silently dropping it (relevant to D-14's disputed-territory criterion).

This is a defensible, reproducible pattern for a thesis: the source is the UN's own classification (not `pycountry`, not World Bank), the acquisition step is documented and one-time (not a runtime dependency), and the file is version-controlled so grading is fully reproducible from the repo alone.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requests.adapters.HTTPAdapter(max_retries=3)` (integer shorthand) | `HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[...]))` | Long-standing (`urllib3` `Retry` object has been the documented approach for years) | The integer shorthand only retries connection errors, not HTTP 5xx/429 status codes — using a bare int silently fails to retry on the exact transient-failure scenario D-01 targets |

**Deprecated/outdated:** None specific to this phase's tooling beyond the retry-shorthand note above.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The official M49 CSV export (with `ISO-alpha3 Code` column) has no scriptable/API download and requires a one-time manual acquisition step | Standard Stack, Code Examples | If a scriptable source is later found, the manual-acquisition task in the plan becomes unnecessary busywork — low risk, easy to simplify later |
| A2 | `hashlib.sha256` is an acceptable checksum choice (vs md5) | Standard Stack | None — explicitly left to Claude's Discretion in CONTEXT.md; either satisfies D-08 |
| A3 | 8.2.1's `Age: "15+"` dimension value is the only age bucket returned (i.e., no alternate age-group rows exist that would need filtering like 2.3.1's `Sex`) | Common Pitfalls / Code Examples Pattern 2 | If wrong, 8.2.1 could have the same multi-row-per-country-year duplication as 2.3.1/6.4.2/6.4.1 — the per-indicator filter table would need an `"Age": "15+"` entry added. **Recommend the planner add a verification task**: inspect distinct `dimensions` combinations for 8.2.1 across a larger sample before finalizing the filter, not just the 5-row sample fetched during this research. |
| A4 | Antarctica appearing with `type: "Country"` in `GeoArea/Tree` is a genuine edge case that will simply produce no economic-indicator rows (rather than needing special exclusion logic) | Common Pitfalls Pitfall 2 | Low risk — if Antarctica somehow has indicator rows, D-16's exclusion log will surface it for manual review; no silent failure mode |

## Open Questions

1. **Should `data/panel.db` itself be committed to git?**
   - What we know: The existing (currently-inactive) `gitignore` file only covers `data/**/*.json` and `data/**/*.csv`, not `.db` files. D-09 fixes the DB path but CONTEXT.md doesn't say whether the binary file should be versioned.
   - What's unclear: Committing a growing SQLite binary has real repo-hygiene costs (matches `research/PITFALLS.md`'s "Committing raw SQLite database file" security/hygiene note); not committing it means a fresh clone can't inspect the panel without re-running ingestion.
   - Recommendation: Gitignore `data/panel.db` (consistent with "regenerable from raw + `src/`" being the reproducibility contract), and instead ensure `data/raw/` + manifests + `src/` alone are sufficient to rebuild it — flag for the plan to make an explicit choice and document it in the README.

2. **Exact `pageSize` to use in production ingestion.**
   - What we know: project-wide `research/STACK.md` found `pageSize=50000` timed out and recommended 500–2000; this session's live spot-checks used small `pageSize` values (5–100) purely for inspection, not representative of production throughput.
   - What's unclear: The exact sweet spot within 500–2000 for this specific set of 5 indicators wasn't re-benchmarked in this session.
   - Recommendation: Start at `pageSize=1000`; D-02 already requires reading `totalElements`/`pageSize` dynamically rather than assuming a fixed value, so this is a tunable default, not a hard requirement.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything | ✓ | 3.12.4 | — |
| pip | Everything | ✓ | 26.0.1 | — |
| `.venv` virtual environment | REPRO-01 (clean `pip freeze`) | ✗ | — | **Blocking for REPRO-01** — must be created (`python -m venv .venv`) and `requirements.txt` installed into it before `pip freeze > requirements.lock.txt` can produce a clean, project-scoped lockfile. A `pip freeze` against the global interpreter would capture unrelated system packages. |
| requests | INGEST-01 | ✓ (global interpreter only) | 2.32.3 | Reinstall into `.venv` once created |
| pandas | INGEST-05 | ✓ (global interpreter only) | 2.2.2 | Reinstall into `.venv` once created |
| pytest / pytest-cov | D-03's required unit test | ✗ | — | Install as dev dependency (`pip install pytest pytest-cov`) — no fallback needed, these are the recommended tools with no blocking alternative |
| Network access to `unstats.un.org` | INGEST-01 | ✓ (live-verified in this research session) | — | — |
| sqlite3 (stdlib) | INGEST-05 | ✓ | 3.45.3 (bundled with Python 3.12.4) | — |

**Missing dependencies with no fallback:**
- `.venv` must be created before REPRO-01 can be satisfied cleanly — this should be an early task in the plan (Wave 0), not an afterthought.
- `pytest`/`pytest-cov` must be installed before D-03's required test can be written — flag as a Wave 0 dependency.

**Missing dependencies with fallback:**
- None beyond the above — everything else needed is either already installed globally or is a stdlib module.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (not yet installed — recommended per `.planning/codebase/TESTING.md`) |
| Config file | none yet — Wave 0 should add `pyproject.toml`'s `[tool.pytest.ini_options]` or a `pytest.ini` with `testpaths = ["tests"]` |
| Quick run command | `pytest tests/ingesta -x` |
| Full suite command | `pytest --cov=src --cov-report=term-missing` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INGEST-01 | Client retries 3x with backoff on transient 500, then succeeds; paginates until `totalElements` reached | unit (mocked) | `pytest tests/ingesta/test_client.py -x` | ❌ Wave 0 |
| INGEST-02 | Per-indicator dimension filter yields exactly one row per (country, year) for each of the 5 indicators | unit | `pytest tests/ingesta/test_fetch_data.py::test_filters_to_headline_dimension -x` | ❌ Wave 0 |
| INGEST-03 | `countries.py` excludes all `GeoArea/Tree` nodes of `type != "Country"`; M49→ISO3 crosswalk resolves a known sample correctly | unit | `pytest tests/ingesta/test_countries.py -x` | ❌ Wave 0 |
| INGEST-04 | Manifest written with required fields (date, URL, params, row count, checksum); second run without `force=True` skips re-fetch | unit | `pytest tests/ingesta/test_manifest.py -x` | ❌ Wave 0 |
| INGEST-05 | Duplicate (country, year, indicator) row insert raises (via UNIQUE constraint or the pre-insert assert) | unit | `pytest tests/ingesta/test_db.py::test_unique_constraint_raises -x` | ❌ Wave 0 |
| REPRO-01 | `requirements.lock.txt` exists and is non-empty after `.venv` setup | manual / smoke | `test -s requirements.lock.txt` (shell check, not a pytest case — this is a one-time environment artifact, not pipeline logic) | ❌ Wave 0 (manual step) |

### Sampling Rate
- **Per task commit:** `pytest tests/ingesta -x`
- **Per wave merge:** `pytest --cov=src --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `pip install pytest pytest-cov` (into a newly created `.venv`) — no test infrastructure currently exists in the repo
- [ ] `tests/__init__.py`, `tests/conftest.py`, `tests/ingesta/__init__.py` — directory skeleton
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` (or `pytest.ini`) with `testpaths = ["tests"]`
- [ ] `tests/fixtures/` — fixture JSON mirroring the exact live-verified shapes captured in this research (5-row samples per indicator, one multi-page mock, one 500-then-success mock)
- [ ] Rename `gitignore` → `.gitignore` (Pitfall 3) — not a test gap, but blocks safe test/data iteration if left unfixed

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | UN SDG API is public, unauthenticated; no credentials handled in this phase |
| V3 Session Management | No | No user sessions — this is a batch script, not a request-serving app |
| V4 Access Control | No | Single local user (the student), no multi-user access model |
| V5 Input Validation | Yes | Validate API response shape before use: check `dimensions` dict has expected keys before indexing; use `pd.to_numeric(..., errors="coerce")` rather than a bare `float()` cast (Pitfall 5); construct file paths (`data/raw/{indicador}/{fecha}.json`) only from a fixed, hardcoded list of 5 indicator codes and `date.today()` — never from unvalidated API response content, to avoid any path-construction surprises |
| V6 Cryptography | Minor | SHA256 checksum for manifest integrity (data-integrity control, not secrecy — no secrets exist in this phase since the API requires no auth) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via string-formatted `INSERT`/`SELECT` statements | Tampering | Use parameterized queries exclusively (`?` placeholders in raw `sqlite3`, or pandas `to_sql`/SQLAlchemy `text()` with bound params) — never f-string API values into SQL |
| Path traversal / unexpected file writes via indicator code or date used in file paths | Tampering | Indicator codes are a fixed, hardcoded constant list (never derived from API response content); dates come from `date.today().isoformat()` or an explicit ISO-format CLI argument — never from unsanitized external input |
| Unbounded retry/pagination loop (resource exhaustion / hung process) | Denial of Service (against the student's own machine/time budget, not a multi-tenant system) | `Retry(total=3, ...)` caps retries per D-01; pagination loop must terminate on `page >= totalPages` (never an unconditional `while True`) |
| Committing secrets or personal absolute paths (e.g., the `G:\Mi unidad\...` path referenced in PROJECT.md) into ingestion scripts | Information Disclosure | Keep all paths relative to the repo root in `src/ingesta/`; the `.gitignore` fix (Pitfall 3) also prevents accidentally committing large raw data dumps that could embed local environment details |

## Sources

### Primary (HIGH confidence)
- `https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data` — live queries for indicators 6.4.1, 6.4.2 (from prior project research), 8.1.1, 8.2.1, 2.3.1 — series codes, dimension key sets, pagination fields, the `"NaN"`-string value gotcha — directly observed, 2026-07-10
- `https://unstats.un.org/SDGAPI/v1/sdg/GeoArea/Tree` and `/GeoArea/List` — live queries — `type` field values, `children: null` on leaf countries, absence of `type`/ISO3 on the flat list — directly observed, 2026-07-10
- `https://unstats.un.org/SDGAPI/swagger/v1/swagger.json` — official OpenAPI spec — endpoint/parameter inventory for `GeoArea/List`, `GeoArea/Tree`, `GeoArea/{code}/List` — directly observed, 2026-07-10
- Local repo inspection (`git ls-files`, `git check-ignore -v`, `python -c "import X"`) — `.gitignore` naming bug, installed package versions, absence of `.venv` — directly observed, 2026-07-10
- `.planning/research/STACK.md`, `.planning/research/PITFALLS.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/SUMMARY.md` — project-wide research already empirically verified (installed + executed the full stack) in a prior session, 2026-07-10

### Secondary (MEDIUM confidence)
- `https://unstats.un.org/unsd/methodology/m49/` and `/overview/` — official M49 classification table structure and columns (WebFetch inspection — confirmed no scriptable export exists)
- `https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html` — `Retry` object parameters and backoff formula (WebSearch, cross-checked against multiple independent tutorials)
- `.planning/codebase/TESTING.md` — pytest/unittest.mock conventions already established for this repo (direct repo inspection, pre-existing document)

### Tertiary (LOW confidence)
- General WebSearch results comparing `responses` vs `unittest.mock` (multiple blog/tutorial sources, no single authoritative doc) — used only to confirm `unittest.mock` remains a fully valid choice, not to override the codebase's existing TESTING.md recommendation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new runtime dependencies; versions directly observed on the local machine; retry pattern is a well-documented urllib3 feature
- Architecture: HIGH — directly extends the already-established, previously-researched project architecture (`research/ARCHITECTURE.md`), no new structural decisions needed beyond what CONTEXT.md already locked
- Pitfalls: HIGH — the two most important findings (per-indicator dimension key differences, `.gitignore` naming bug) were both directly observed against live systems in this session, not inferred
- M49/ISO3 crosswalk approach: MEDIUM — the recommended one-time-manual-acquisition pattern is sound and defensible for a thesis but wasn't literally executed (no CSV was downloaded in this research session — flagged as A1 in Assumptions Log)

**Research date:** 2026-07-10
**Valid until:** 30 days for the retry/pytest/SQLite patterns (stable); the UN SDG API's exact series codes and dimension shapes should be considered stable but worth a quick re-spot-check if ingestion is not implemented within a few weeks, since the API is explicitly published as a test/development service and its metadata does occasionally shift.
