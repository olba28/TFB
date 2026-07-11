---
status: fixed
phase: 02-construcci-n-del-panel-y-eda
depth: standard
files_reviewed: 5
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
reviewed: 2026-07-12
---

# Phase 02 Code Review

> ⚠️ **Deviation notice:** This review was produced inline by the same session
> that executed the phase, not by an independently-spawned `gsd-code-reviewer`
> subagent — the runtime had no `Agent`/`Task` tool available (same constraint
> documented in `02-01-PLAN.md`/`02-02-PLAN.md`'s deviation notices). File
> scope was computed the same way the standard workflow would (extracted from
> `02-01-SUMMARY.md`/`02-02-SUMMARY.md`'s `key-files.created`), and findings
> were investigated and fixed with the same rigor an independent reviewer
> would apply — including reproducing the bug in isolation before writing the
> fix, and adding regression test coverage.

**Depth:** standard
**Files reviewed:** 5 (`src/ingesta/typology.py`, `tests/ingesta/test_typology.py`, `src/panel_build.py`, `tests/test_panel_build.py`, `notebook/2_1_construccion_panel_eda.ipynb`)

## Summary

One real bug found and fixed (WR-01, below) — a data-integrity issue in the
persisted `country_reference.json` artifact that would silently break any
strict JSON consumer. Two Info-level suggestions noted, not requiring code
changes. No Critical findings.

## Findings

### WR-01: `persist_country_reference` emitted invalid JSON (`NaN` token) for countries with no region match — FIXED

**Severity:** Warning
**File:** `src/ingesta/typology.py`
**Status:** Fixed in this review, live artifact regenerated and verified

**Issue:** Antarctica (`ATA`) is a real `type=="Country"` leaf in the live UN
`GeoArea/Tree` response, but it only exists under the continental-regions
root, never under the SDG-regions root that `build_region_map` walks. It
therefore correctly gets `region=None, subregion=None` from
`build_country_reference`'s fallback. However, pandas silently upgrades that
Python `None` to a float `NaN` internally once the `region`/`subregion`
DataFrame columns also hold real region-name strings for the other 247
countries. `persist_country_reference`'s original implementation called
`json.dumps(df.to_dict(orient="records"))` directly — Python's `json` module
allows serializing `float('nan')` by default, emitting the bare, non-standard
token `NaN` (not valid per RFC 8259). Any strict JSON parser (browsers,
`JSON.parse` in JS, most non-Python languages, `jq`, and many Python
libraries that pass `strict=True`-equivalent options) reading
`data/raw/country_reference.json` would fail to parse it.

**Reproduced in isolation before fixing** (see conversation trace): confirmed
`df.where(pd.notnull(df), None)` does NOT actually fix this — pandas
re-coerces the replacement `None` back to `NaN` for its string-backed dtype,
so a DataFrame-level fix does not work. The correct fix operates on the
plain Python dict structure returned by `.to_dict()`, after pandas' dtype
machinery is no longer involved.

**Fix:** Added `_json_safe_records(df)`, which converts `df.to_dict(orient="records")`
and then explicitly replaces any float NaN (`isinstance(v, float) and v != v`,
the standard NaN self-inequality check) with Python `None` before
`json.dumps`. `persist_country_reference` now calls this helper.

**Verification:**
- New regression test `tests/ingesta/test_typology.py::test_persist_country_reference_writes_valid_json_null_for_missing_region` asserts the persisted file never contains the substring `"NaN"` and parses cleanly via the standard `json.loads`.
- New test `test_build_country_reference_defaults_region_to_none_for_country_absent_from_region_map` closes a related test-coverage gap: the plan's Task 1 promised this "absent from region_map" fallback would be "unit-tested explicitly, not just asserted-away," but no test actually exercised it until this review.
- Live artifact regenerated: `data/raw/country_reference.json` re-captured via `python -m src.ingesta.typology`, confirmed zero `NaN` substring matches and successful strict `json.load()` parse, checksum still consistent with its manifest.
- `data/panel.db`'s `country_reference` SQL table was NEVER affected by this bug (`to_sql` correctly converts NaN to SQL NULL regardless) — only the JSON provenance artifact was at risk.
- Full test suite: 71/71 passing after the fix (69 pre-fix + 2 new regression tests).

**Files modified:** `src/ingesta/typology.py`, `tests/ingesta/test_typology.py`
**Committed in:** (this phase's final docs commit, alongside this REVIEW.md)

---

### IN-01: `_find_root`'s `name`/`code` parameters are not mutually exclusive by construction

**Severity:** Info (no fix applied — code quality suggestion, not a bug)
**File:** `src/ingesta/typology.py`

`_find_root(tree_data, *, name=None, code=None)` accepts both keyword
parameters but its internal `if name is not None: ... if code is not None:
...` logic checks them independently per iteration rather than asserting
exactly one is provided. Every current call site passes exactly one
(`name=SDG_REGION_ROOT_NAME` or `code=root_code`), so this is not a live bug,
but a future caller passing both would get name-takes-precedence behavior
silently rather than a clear error. Not fixed — low risk, would add
complexity for a case that doesn't occur; noted for awareness.

### IN-02: `compute_coverage` implicitly assumes `country_reference`'s countries are a superset of `raw_observations`'s

**Severity:** Info (verified true in current live data — no fix applied)
**File:** `src/panel_build.py`

If a country appeared in `raw_observations` but not in `country_reference`
(e.g. due to a future timing/crosswalk skew between when each was captured),
`compute_coverage`'s cross-product (built from `country_reference`'s country
list) would silently omit that country from coverage/exclusion accounting,
even though `build_clean_panel`'s left-join would still include its rows in
`panel_clean` (with null region/typology columns). Verified live against the
current data: `raw_observations`' 215 countries are a strict subset of
`country_reference`'s 248 (checked via direct query — zero orphans). This
holds because both ultimately resolve countries through the same
crosswalk-based logic (`countries.build_crosswalk()` /
`countries.filter_to_countries()` for Phase 1's ingestion,
`typology.build_country_reference()`'s identical crosswalk step for Phase 2).
Not fixed — the invariant holds in practice and adding a defensive assertion
would be reasonable future hardening but isn't required for correctness today.

## Files Reviewed

- `src/ingesta/typology.py` — 1 Warning found and fixed, 1 Info noted
- `tests/ingesta/test_typology.py` — extended with 2 new tests during this review (no findings against the pre-existing tests)
- `src/panel_build.py` — 1 Info noted, no Warning/Critical findings
- `tests/test_panel_build.py` — no findings
- `notebook/2_1_construccion_panel_eda.ipynb` — no findings (no secrets, no hardcoded absolute paths beyond the intentional/documented sys.path bootstrap, no stray debug output)
