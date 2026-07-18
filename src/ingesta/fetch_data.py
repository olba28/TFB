from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src import db
from src.ingesta import client, countries, manifest

INDICATOR_CODES: list[str] = ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"]

GEOAREA_TREE_URL = "https://unstats.un.org/SDGAPI/v1/sdg/GeoArea/Tree"

EXCLUSION_LOG_PATH = Path("data/raw/exclusion_log.json")

HEADLINE_DIMENSIONS: dict[str, dict[str, str]] = {
    "6.4.2": {"Activity": "TOTAL"},
    "6.4.1": {"Activity": "TOTAL"},
    "8.1.1": {},
    "8.2.1": {},
    "2.3.1": {"Sex": "BOTHSEX"},
}

HEADLINE_SERIES: dict[str, str] = {
    "2.3.1": "PD_AGR_SSFP",
}


def filter_headline_rows(rows: list[dict[str, Any]], indicator_code: str) -> list[dict[str, Any]]:
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
    response = session.get(GEOAREA_TREE_URL, timeout=30)
    response.raise_for_status()
    tree_nodes = response.json()

    excluded: list[dict[str, Any]] = []
    country_set = countries.collect_countries(tree_nodes, excluded=excluded)
    crosswalk = countries.build_crosswalk()
    return country_set, crosswalk, excluded


def run_ingestion(force: bool = False) -> None:
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
            continue

        rows = client.fetch_all_pages(session, indicator_code)

        raw_path = manifest.RAW_DATA_ROOT / indicator_code / f"{today}.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps({"data": rows}, ensure_ascii=False), encoding="utf-8")

        filtered = filter_headline_rows(rows, indicator_code)
        kept, row_excluded = countries.filter_to_countries(filtered, country_set, crosswalk)
        all_excluded.extend(row_excluded)
        if len(kept) == 0:
            raise ValueError(f"No rows survived country/crosswalk filter for {indicator_code}")

        df = _build_observations_df(
            kept, indicator_code, source_manifest_id=f"{indicator_code}:{today}"
        )
        db.insert_observations(engine, df)

        manifest.write_manifest(
            raw_path,
            url=client.API_BASE_URL,
            params={
                "indicator": indicator_code,
                "timePeriod": f"{client.YEAR_START}-{client.YEAR_END}",
            },
            row_count=len(rows),
        )

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
