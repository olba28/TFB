# Phase 1: Ingesta y Almacenamiento Versionado - Pattern Map

**Mapped:** 2026-07-10
**Files analyzed:** 11 (5 src modules, 1 config fix, 5 test files) + 1 repro artifact
**Analogs found:** 0 / 11 in-repo — this is the first phase to write any `src/` code.

**Repo state verified:** `src/ingesta/` is an empty skeleton directory (no files). `tests/` does not exist at all. No `.venv`. The file `gitignore` exists but is misnamed (missing leading dot — confirmed via `ls`, not active). There is **no existing codebase code to copy patterns from** for this phase. All pattern assignments below are therefore anchored on the concrete, live-verified code examples already produced in `01-RESEARCH.md` (Code Examples / Pattern 1-4 sections), not on in-repo analogs. Every file in this phase falls in the "No Analog Found" table; the "Pattern Assignments" section below substitutes RESEARCH.md's validated snippets as the canonical source to copy from, since the planner still needs concrete code, not just "figure it out."

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `src/ingesta/__init__.py` | config/package-init | — | none | no-analog |
| `src/ingesta/client.py` | service (HTTP client) | request-response + pagination | none in-repo | no-analog (use RESEARCH.md Pattern 1) |
| `src/ingesta/countries.py` | utility/model (crosswalk + filter) | transform | none in-repo | no-analog (use RESEARCH.md Code Examples: `collect_countries`) |
| `src/ingesta/manifest.py` | model/service (provenance record) | file-I/O | none in-repo | no-analog (use RESEARCH.md Pattern 3) |
| `src/ingesta/fetch_data.py` | service (orchestrator) | batch, file-I/O, CRUD | none in-repo | no-analog (use RESEARCH.md architecture diagram + Patterns 2-4) |
| `src/db.py` | model/config (SQLite DDL + connection) | CRUD | none in-repo | no-analog (use RESEARCH.md Pattern 4) |
| `gitignore` → `.gitignore` (rename) | config | — | none | no-analog (bug fix, not a pattern) |
| `requirements-dev.txt` | config | — | `requirements.txt` (existing, root) | partial — same format (pinned floors), different purpose (dev-only) |
| `requirements.lock.txt` | config | — | none | no-analog (generated via `pip freeze`, not authored) |
| `tests/conftest.py` | test (fixtures) | — | none in-repo | no-analog (use TESTING.md conventions + RESEARCH.md fixture list) |
| `tests/ingesta/test_client.py` | test | request-response (mocked) | none in-repo | no-analog (use RESEARCH.md Pattern 1 + D-03 mock spec) |
| `tests/ingesta/test_countries.py` | test | transform | none in-repo | no-analog |
| `tests/ingesta/test_manifest.py` | test | file-I/O | none in-repo | no-analog |
| `tests/ingesta/test_db.py` | test | CRUD | none in-repo | no-analog (use RESEARCH.md Pattern 4 assert) |

## Pattern Assignments

Since there are no in-repo analogs, each assignment below points to the exact RESEARCH.md section/snippet the planner should treat as the copy-from source, plus the concrete decision IDs (D-xx) it must satisfy.

### `src/ingesta/client.py` (service, request-response + pagination)

**Source:** `01-RESEARCH.md` → "Pattern 1: Session-level retry via `urllib3.Retry` + `HTTPAdapter`" (lines ~215-236 of RESEARCH.md)

**Session/retry pattern to copy verbatim (adapt import location only):**
```python
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

**Pagination requirement (D-02, Pitfall 4):** loop until `page >= totalPages` (or accumulated rows == `totalElements`) read fresh from each indicator's *own* first response — never assume a shared/fixed page count across indicators (6.4.2 ≈ 201 pages @ 100/page differs hugely from others).

**Delay requirement (D-04):** insert `time.sleep(0.5–1.0)` between successive page/indicator calls — not inside the retry backoff itself, a separate fixed delay per successful call.

**Error handling:** rely on `Retry`'s `status_forcelist` for retryable HTTP codes — do not hand-roll a `try/except` retry loop (explicit anti-pattern in RESEARCH.md "Don't Hand-Roll" table).

---

### `src/ingesta/countries.py` (utility/model, transform)

**Source:** `01-RESEARCH.md` → "Code Examples: M49 canonical list from `GeoArea/Tree`" (lines ~355-379) and "M49 → ISO3 crosswalk" section (lines ~381-387)

**Core tree-walk pattern to copy:**
```python
def collect_countries(tree_nodes: list[dict]) -> dict[str, str]:
    """Walk the GeoArea/Tree response; return {geoAreaCode: geoAreaName} for type=='Country' leaves."""
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

**Required additions per CONTEXT.md decisions (not in the snippet above, planner must add):**
- D-13/D-15: load `src/ingesta/data/m49_countries.csv` (one-time manual acquisition, versioned) to build `{m49_code: iso3}` crosswalk, cross-checked against `collect_countries()`'s tree walk output.
- D-14: objective criterion — a code counts as an included country iff it resolves to a `type == "Country"` leaf in `GeoArea/Tree`, regardless of disputed-territory status (no manual exception list).
- D-16: the `excluded` list above (or an expanded version) is exactly the exclusion log required — must be persisted (e.g., CSV/JSON) as a documented artifact, not just logged to stdout.

**Data flow note:** this module is a pure transform (tree in → filtered dict + exclusion log out); no network calls belong here — the tree JSON itself is fetched via `client.py`.

---

### `src/ingesta/manifest.py` (model/service, file-I/O)

**Source:** `01-RESEARCH.md` → "Pattern 3: Idempotent fetch guarded by manifest existence" (lines ~257-274)

```python
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

**Manifest schema (D-08, per-indicator per D-05):** date de descarga, URL, parámetros de consulta, número de filas, checksum (`hashlib.sha256(path.read_bytes()).hexdigest()` — stdlib, per RESEARCH.md "Don't Hand-Roll" table).

**Note:** this file's idempotency check (`fetch_indicator`) is actually the orchestration entry point — RESEARCH.md's recommended module split places the manifest *read/write* logic in `manifest.py` and the *orchestration* (calling client → filter → countries → manifest) in `fetch_data.py`. Keep the function above as the template but split concerns: `manifest.py` exposes `write_manifest(...)` / `manifest_exists(...)` / `load_manifest(...)`; `fetch_data.py` owns the `if exists and not force: skip` control flow.

---

### `src/ingesta/fetch_data.py` (service, orchestrator — batch, file-I/O, CRUD)

**Source:** `01-RESEARCH.md` → architecture diagram (lines ~144-188) + "Pattern 2: Per-indicator dimension filter" (lines ~238-255)

**Per-indicator dimension filter — critical, do not hardcode a single rule:**
```python
HEADLINE_DIMENSIONS = {
    "6.4.2": {"Activity": "TOTAL"},          # + always require Reporting Type == "G"
    "6.4.1": {"Activity": "TOTAL"},
    "8.1.1": {},                              # only Reporting Type == "G"
    "8.2.1": {},                              # also has "Age": "15+" — verify no alt-age rows (A3)
    "2.3.1": {"Sex": "BOTHSEX"},
}

def filter_headline_rows(rows: list[dict], indicator_code: str) -> list[dict]:
    required = {"Reporting Type": "G", **HEADLINE_DIMENSIONS[indicator_code]}
    return [r for r in rows if all(r["dimensions"].get(k) == v for k, v in required.items())]
```

**Orchestration sequence (from RESEARCH.md architecture diagram):**
1. check manifest → skip if exists and not `force` (D-07)
2. write `data/raw/{indicador}/{fecha}.json`
3. write manifest (D-08)
4. filter to per-indicator headline dims (Pattern 2 above)
5. join `geoAreaCode` → `countries.py` filter (M49/ISO3, exclusion log)
6. `assert` (country, year) unique per indicator before insert (D-11) — see `src/db.py` below
7. insert into `raw_observations`

**Value parsing (Pitfall 5):** use `pd.to_numeric(series, errors="coerce")`, never bare `float(row["value"])` — indicator 2.3.1 can return the literal string `"NaN"`.

**Error handling:** post-filter assertion `assert len(filtered) > 0, f"No rows survived dimension filter for {indicator_code}"` (Pitfall 1) — fail loudly rather than silently proceeding with zero rows.

---

### `src/db.py` (model/config, CRUD)

**Source:** `01-RESEARCH.md` → "Pattern 4: UNIQUE constraint + explicit assert" (lines ~276-301)

```python
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

**Connection pattern (per RESEARCH.md Standard Stack):** prefer SQLAlchemy `Engine` (`create_engine("sqlite:///data/panel.db")`) over raw `sqlite3.Connection` for `to_sql`/`read_sql` bulk operations — pandas docs treat raw-connection as legacy for this path.

**`panel` table (D-12):** must be a regenerable pivot — implement as a function that drops/recreates from `raw_observations` (indicator→columns pivot), never hand-edited. No code example exists yet for the pivot itself in RESEARCH.md; planner should derive via `df.pivot(index=["country_code","year"], columns="indicator_code", values="value")` then `to_sql("panel", conn, if_exists="replace")`.

**Security note (V5, SQL injection):** parameterized queries only — never f-string values into SQL; this project's scale/threat model is single-user/local but the convention should still be followed per RESEARCH.md Security Domain.

---

### Test files (`tests/ingesta/test_*.py`)

**Source:** `01-RESEARCH.md` → "Validation Architecture" (Phase Requirements → Test Map) + "Wave 0 Gaps"

No existing test files or `tests/` directory exist in this repo to copy structure from — this phase also establishes the test scaffolding itself. Use `unittest.mock` (stdlib, RESEARCH.md-preferred over `responses`) to:
- `test_client.py`: mock a `Session.get` sequence returning one `500` then a paginated `200` — assert exactly 3 total attempts and exponential 1s/2s/4s backoff triggered (D-03).
- `test_countries.py`: feed a small synthetic `GeoArea/Tree`-shaped fixture with mixed `Country`/`Region` nodes; assert `collect_countries()` returns only `Country` leaves and the exclusion log captures the rest.
- `test_manifest.py`: assert manifest schema fields present (date, URL, params, row count, checksum) and that a second call with `force=False` is a no-op (idempotency, D-07).
- `test_db.py`: assert duplicate (country, year, indicator) rows raise via the `assert` in `insert_observations` before ever reaching SQLite's `UNIQUE` constraint (D-11 belt-and-suspenders).

**Fixture strategy:** RESEARCH.md recommends `tests/fixtures/` with 5-row samples per indicator matching the live-verified dimension shapes (6.4.2/6.4.1 need `Activity`, 2.3.1 needs `Sex`, 8.1.1/8.2.1 have none) plus one multi-page mock and one 500-then-success mock.

---

## Shared Patterns

### Retry/Backoff (applies to `client.py` only, but is the single most safety-critical shared pattern)
**Source:** RESEARCH.md Pattern 1 (see above). Do not reimplement per-call — configure once on the `Session`.

### Idempotency-by-manifest-check (applies to `manifest.py` + `fetch_data.py`)
**Source:** RESEARCH.md Pattern 3. Every ingestion entry point must check-before-fetch; never re-download blindly.

### UNIQUE + assert double-check (applies to `db.py` + `fetch_data.py`'s pre-insert step)
**Source:** RESEARCH.md Pattern 4. Two independent enforcement layers per D-11: schema `UNIQUE` constraint and a Python-level `assert` raised before the insert is attempted.

### Value coercion (applies to `fetch_data.py` and any module touching the API's raw `value` field)
**Source:** RESEARCH.md Pitfall 5. Always `pd.to_numeric(series, errors="coerce")`.

### Path construction safety (applies to `client.py`, `manifest.py`, `fetch_data.py`)
**Source:** RESEARCH.md Security Domain V5. File paths under `data/raw/{indicador}/{fecha}.json` must be built only from the fixed 5-indicator-code constant list and `date.today()` — never from unvalidated API response content.

## No Analog Found

All files in this phase have no in-repo analog (first phase writing `src/` code). Listed here per required format; see Pattern Assignments above for the RESEARCH.md-anchored substitute pattern for each.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/ingesta/client.py` | service | request-response | No HTTP client code exists anywhere in repo yet |
| `src/ingesta/countries.py` | utility | transform | No data-transform modules exist in `src/` yet |
| `src/ingesta/manifest.py` | model | file-I/O | No provenance/manifest code exists yet (only mentioned conceptually in ARCHITECTURE.md) |
| `src/ingesta/fetch_data.py` | service | batch | No orchestration code exists yet |
| `src/db.py` | model | CRUD | No database code exists yet (SQLite chosen but unimplemented) |
| `tests/ingesta/*.py` (all 4) | test | varies | No `tests/` directory exists in the repo at all |
| `requirements.lock.txt` | config | — | No lockfile exists; no `.venv` exists yet either |

## Metadata

**Analog search scope:** `src/` (all subdirectories), `tests/` (does not exist), repo root config files (`requirements.txt`, `gitignore`)
**Files scanned:** entire repo tree via `find`/`ls` (src/, tests/, root) — confirmed empty/non-existent for all target roles
**Pattern extraction date:** 2026-07-10
**Substitute source used in lieu of in-repo analogs:** `.planning/phases/01-ingesta-y-almacenamiento-versionado/01-RESEARCH.md` (Code Examples, Patterns 1-4, Pitfalls 1/4/5, Security Domain V5) — all snippets there are live-verified against the production UN SDG API in the same research session, not hypothetical.
