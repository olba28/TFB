"""Ingestion orchestrator: composes client.py, manifest.py, countries.py, and
src/db.py end-to-end for the 5 fixed UN SDG indicator codes (INGEST-01,
INGEST-02, INGEST-04).

Orchestration sequence (per indicator, RESEARCH.md architecture diagram):
1. Check the manifest -> skip re-fetch unless `force=True` (D-07).
2. Fetch all pages via `client.fetch_all_pages`.
3. Write raw JSON to disk (D-05, D-06).
4. Filter to the indicator's headline dimension combo (Pitfall 1) -- this is
   NEVER a single global `Activity: TOTAL` rule; see `HEADLINE_DIMENSIONS`.
5. Join `geoAreaCode` -> ISO3 and drop non-country rows via `countries.py`
   (M49 exclusion, D-13-D-16).
6. Coerce `value` via `pd.to_numeric(errors='coerce')` (Pitfall 5 -- 2.3.1 can
   return the literal string "NaN").
7. Insert into `raw_observations` (duplicate-key check lives in
   `db.insert_observations`, D-11).
8. Only once steps 4-7 have all succeeded, write the provenance manifest
   (D-08) -- writing it any earlier would let a mid-pipeline failure
   permanently and silently skip that indicator on every future run, since
   `manifest_exists()` (step 1) only checks for the manifest's presence, not
   whether the rows actually reached `raw_observations` (CR-01).

After all indicators, `db.rebuild_panel` regenerates the derived wide pivot
(D-12). All file paths are built only from the fixed `INDICATOR_CODES` list
and `date.today()` -- never from unvalidated API response content (Security
V5).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src import db
from src.ingesta import client, countries, manifest

# Fixed indicator-code list (Security V5: paths built only from this + date.today()).
INDICATOR_CODES: list[str] = ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"]

# GeoArea/Tree endpoint (D-13): fetched once per run, shared across all 5
# indicators -- never per-indicator.
GEOAREA_TREE_URL = "https://unstats.un.org/SDGAPI/v1/sdg/GeoArea/Tree"

# Documented exclusion log (D-16): every M49 region/aggregate dropped from
# GeoArea/Tree, plus every observation row that failed the country-leaf/
# crosswalk join, in one place for the memoria.
EXCLUSION_LOG_PATH = Path("data/raw/exclusion_log.json")

# Per-indicator headline dimension filter (Pitfall 1) -- NEVER a single global
# rule. 6.4.2/6.4.1 need Activity:TOTAL; 2.3.1 needs Sex:BOTHSEX; 8.1.1/8.2.1
# have no extra dimension beyond Reporting Type == 'G' (Assumption A3: 8.2.1's
# Age:"15+" is confirmed the only age bucket by the live run -- no alternate
# buckets found, no "Age" entry needed here).
HEADLINE_DIMENSIONS: dict[str, dict[str, str]] = {
    "6.4.2": {"Activity": "TOTAL"},
    "6.4.1": {"Activity": "TOTAL"},
    "8.1.1": {},
    "8.2.1": {},
    "2.3.1": {"Sex": "BOTHSEX"},
}

# Live-run finding (Task 2): indicator 2.3.1 multiplexes TWO distinct series
# under the identical headline dimension combo (Sex: BOTHSEX, Reporting Type:
# G) -- "PD_AGR_SSFP" (productivity of small-scale food producers) and
# "PD_AGR_LSFP" (large-scale food producers). Neither `dimensions` key
# distinguishes them; the API's separate `series` field does. This was not
# anticipated by RESEARCH.md's Assumptions Log (which only flagged 8.2.1's
# Age bucket, A3) -- it surfaced via the same per-indicator uniqueness assert
# (D-11) that A3 was meant to guard, just on a different field.
#
# SDG target 2.3 explicitly names "small-scale food producers" as its focus
# ("double the agricultural productivity and incomes of small-scale food
# producers"); PD_AGR_SSFP is adopted here as 2.3.1's headline series for
# that reason -- PD_AGR_LSFP is dropped from raw_observations, not averaged
# or combined. This is a methodological choice with direct downstream impact
# on Phase 6's Model 2 (agricultural productivity) and is flagged for human
# review at this plan's Task 3 checkpoint.
HEADLINE_SERIES: dict[str, str] = {
    "2.3.1": "PD_AGR_SSFP",
}


def filter_headline_rows(rows: list[dict[str, Any]], indicator_code: str) -> list[dict[str, Any]]:
    """Keep only rows matching `indicator_code`'s headline dimension combo,
    always additionally requiring `Reporting Type == 'G'`, and (for
    indicators listed in `HEADLINE_SERIES`) matching the chosen headline
    `series` code.

    Raises `ValueError` if zero rows survive (Pitfall 1 loud-failure guard) --
    a hardcoded global filter would silently zero out 3 of the 5 indicators
    instead of failing loudly. An explicit `raise` is used instead of a bare
    `assert` (WR-01) so this guard cannot be silently stripped when Python is
    run with `-O`/`-OO`/`PYTHONOPTIMIZE=1`.
    """
    required = {"Reporting Type": "G", **HEADLINE_DIMENSIONS[indicator_code]}
    headline_series = HEADLINE_SERIES.get(indicator_code)
    filtered = [
        row
        for row in rows
        if all(row.get("dimensions", {}).get(k) == v for k, v in required.items())
        and (headline_series is None or row.get("series") == headline_series)
    ]
    if len(filtered) == 0:
        raise ValueError(f"No rows survived dimension filter for {indicator_code}")
    return filtered


def _build_observations_df(
    rows: list[dict[str, Any]], indicator_code: str, source_manifest_id: str
) -> pd.DataFrame:
    """Convert filtered, ISO3-tagged rows into the `raw_observations` column shape.

    Value parsing uses `pd.to_numeric(errors='coerce')` (Pitfall 5) -- 2.3.1
    can return the literal string "NaN"; it is stored as NULL, never dropped.
    """
    return pd.DataFrame(
        {
            "country_code": [row["iso3"] for row in rows],
            "indicator_code": indicator_code,
            "year": [int(row["timePeriodStart"]) for row in rows],
            "value": pd.to_numeric([row.get("value") for row in rows], errors="coerce"),
            "dimension": [
                ";".join(f"{k}={v}" for k, v in sorted(row.get("dimensions", {}).items()))
                for row in rows
            ],
            "source_manifest_id": source_manifest_id,
        }
    )


def _fetch_country_reference(
    session: requests.Session,
) -> tuple[dict[str, str], dict[str, str], list[dict[str, Any]]]:
    """Fetch `GeoArea/Tree` once and build the canonical country set, the
    M49->ISO3 crosswalk, and the exclusion log for every non-country node.
    """
    response = session.get(GEOAREA_TREE_URL, timeout=30)
    response.raise_for_status()
    tree_nodes = response.json()

    excluded: list[dict[str, Any]] = []
    country_set = countries.collect_countries(tree_nodes, excluded=excluded)
    crosswalk = countries.build_crosswalk()
    return country_set, crosswalk, excluded


def run_ingestion(force: bool = False) -> None:
    """Orchestrate the full ingestion pipeline for all 5 indicators (D-07, D-11, D-12).

    Idempotent (D-07): if every indicator already has today's manifest and
    `force` is False, no session is opened and no network call is made at
    all -- only `rebuild_panel` runs, to keep `panel` in sync with whatever is
    already on disk.
    """
    today = date.today().isoformat()

    engine = db.get_engine()
    db.init_db(engine)

    needs_fetch = force or any(
        not manifest.manifest_exists(code, today) for code in INDICATOR_CODES
    )
    if not needs_fetch:
        db.rebuild_panel(engine)
        return

    session = client.build_session()
    country_set, crosswalk, tree_excluded = _fetch_country_reference(session)
    all_excluded: list[dict[str, Any]] = list(tree_excluded)

    for indicator_code in INDICATOR_CODES:
        if manifest.manifest_exists(indicator_code, today) and not force:
            continue  # D-07 idempotent per-indicator skip

        rows = client.fetch_all_pages(session, indicator_code)

        raw_path = manifest.RAW_DATA_ROOT / indicator_code / f"{today}.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps({"data": rows}, ensure_ascii=False), encoding="utf-8")

        # CR-01: everything that can raise (dimension filter, country filter,
        # DB insert) must run BEFORE the manifest is written -- the manifest's
        # existence is what manifest_exists() uses to decide whether to skip
        # re-fetching on a future run (D-07). Writing it before validating and
        # inserting the rows would let a mid-pipeline failure permanently and
        # silently skip that indicator on every subsequent run.
        filtered = filter_headline_rows(rows, indicator_code)
        kept, row_excluded = countries.filter_to_countries(filtered, country_set, crosswalk)
        all_excluded.extend(row_excluded)
        # WR-04: symmetrical loud-failure guard to filter_headline_rows' own
        # zero-rows check -- if every row fails the country-leaf/crosswalk
        # join (e.g. a GeoArea/Tree fetch anomaly), inserting zero rows must
        # not look identical to a clean, fully-processed indicator.
        if len(kept) == 0:
            raise ValueError(f"No rows survived country/crosswalk filter for {indicator_code}")

        df = _build_observations_df(
            kept, indicator_code, source_manifest_id=f"{indicator_code}:{today}"
        )
        db.insert_observations(engine, df)

        # Only now, once the data has actually landed in raw_observations, record
        # success by writing the manifest that gates future idempotent skips.
        manifest.write_manifest(
            raw_path,
            url=client.API_BASE_URL,
            params={
                "indicator": indicator_code,
                "timePeriod": f"{client.YEAR_START}-{client.YEAR_END}",
            },
            row_count=len(rows),
        )

    # CR-02: `all_excluded` only carries entries for indicators actually
    # processed THIS run -- indicators skipped via the per-indicator
    # `continue` above (already fetched today) never contribute their row
    # exclusions here. Merge with whatever is already on disk (keyed by
    # code + exclusion_reason) instead of blindly overwriting, so a partial
    # re-run never destroys previously-documented exclusions (D-16).
    merged_excluded = all_excluded
    if EXCLUSION_LOG_PATH.exists():
        existing_excluded = json.loads(EXCLUSION_LOG_PATH.read_text(encoding="utf-8"))
        merged_by_key = {
            (e.get("code"), e.get("exclusion_reason")): e for e in existing_excluded
        }
        merged_by_key.update(
            {(e.get("code"), e.get("exclusion_reason")): e for e in all_excluded}
        )
        merged_excluded = list(merged_by_key.values())

    countries.write_exclusion_log(merged_excluded, EXCLUSION_LOG_PATH)
    db.rebuild_panel(engine)


if __name__ == "__main__":
    run_ingestion()
