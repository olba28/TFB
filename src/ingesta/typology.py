from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from sqlalchemy import Engine

from src.ingesta import manifest as manifest_module
from src.ingesta.countries import _normalize_code, build_crosswalk, collect_countries

GEOAREA_TREE_URL = "https://unstats.un.org/SDGAPI/v1/sdg/GeoArea/Tree"

SDG_REGION_ROOT_NAME = "World (total) by SDG regions"

DEV_STATUS_ROOT_CODES: dict[str, int] = {
    "is_ldc": 199,
    "is_lldc": 432,
    "is_sids": 722,
}

DEFAULT_COUNTRY_REFERENCE_PATH = Path("data/raw/country_reference.json")
DEFAULT_EXCLUSION_LOG_PATH = Path("data/raw/country_reference_exclusion_log.json")


def _find_root(tree_data: list[dict[str, Any]], *, name: str | None = None, code: int | None = None) -> dict[str, Any] | None:
    for root in tree_data:
        if name is not None and root.get("geoAreaName") == name:
            return root
        if code is not None:
            try:
                if int(root.get("geoAreaCode")) == code:
                    return root
            except (TypeError, ValueError):
                continue
    return None


def build_region_map(tree_data: list[dict[str, Any]]) -> dict[str, dict[str, str | None]]:
    root = _find_root(tree_data, name=SDG_REGION_ROOT_NAME)
    result: dict[str, dict[str, str | None]] = {}
    if root is None:
        return result

    def walk(node: dict[str, Any], ancestors: list[str]) -> None:
        if node.get("type") == "Country":
            code = _normalize_code(node.get("geoAreaCode"))
            if len(ancestors) >= 2:
                region, subregion = ancestors[-2], ancestors[-1]
            elif len(ancestors) == 1:
                region, subregion = ancestors[-1], None
            else:
                region, subregion = None, None
            result[code] = {"region": region, "subregion": subregion}
            return
        for child in node.get("children") or []:
            walk(child, ancestors + [node.get("geoAreaName")])

    for child in root.get("children") or []:
        walk(child, [])

    return result


def build_development_status_flags(tree_data: list[dict[str, Any]]) -> dict[str, dict[str, bool]]:
    flags: dict[str, dict[str, bool]] = {}

    def walk(node: dict[str, Any], flag_name: str) -> None:
        if node.get("type") == "Country":
            code = _normalize_code(node.get("geoAreaCode"))
            flags.setdefault(code, {"is_ldc": False, "is_lldc": False, "is_sids": False})
            flags[code][flag_name] = True
            return
        for child in node.get("children") or []:
            walk(child, flag_name)

    for flag_name, root_code in DEV_STATUS_ROOT_CODES.items():
        root = _find_root(tree_data, code=root_code)
        if root is None:
            continue
        for child in root.get("children") or []:
            walk(child, flag_name)

    return flags


def build_country_reference(
    tree_data: list[dict[str, Any]], crosswalk: dict[str, str]
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    region_map = build_region_map(tree_data)
    dev_status_map = build_development_status_flags(tree_data)
    country_set = collect_countries(tree_data)

    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for m49_code, name in country_set.items():
        iso3 = crosswalk.get(m49_code)
        if iso3 is None:
            excluded.append(
                {"code": m49_code, "name": name, "reason": "missing_from_m49_crosswalk"}
            )
            continue

        region_info = region_map.get(m49_code, {"region": None, "subregion": None})
        dev_status = dev_status_map.get(
            m49_code, {"is_ldc": False, "is_lldc": False, "is_sids": False}
        )
        rows.append(
            {
                "country_code": iso3,
                "region": region_info.get("region"),
                "subregion": region_info.get("subregion"),
                "is_ldc": dev_status["is_ldc"],
                "is_lldc": dev_status["is_lldc"],
                "is_sids": dev_status["is_sids"],
            }
        )

    df = pd.DataFrame(
        rows, columns=["country_code", "region", "subregion", "is_ldc", "is_lldc", "is_sids"]
    )
    return df, excluded


def capture_country_reference(
    session: requests.Session,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    response = session.get(GEOAREA_TREE_URL, timeout=30)
    response.raise_for_status()
    tree_data = response.json()
    crosswalk = build_crosswalk()
    return build_country_reference(tree_data, crosswalk)


def _json_safe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    records = df.to_dict(orient="records")
    return [
        {k: (None if isinstance(v, float) and v != v else v) for k, v in row.items()}
        for row in records
    ]


def persist_country_reference(
    df: pd.DataFrame, path: Path = DEFAULT_COUNTRY_REFERENCE_PATH
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe_records(df), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    manifest_module.write_manifest(
        raw_path=path,
        url=GEOAREA_TREE_URL,
        params={},
        row_count=len(df),
    )
    return path


def persist_country_reference_to_db(df: pd.DataFrame, engine: Engine) -> None:
    df.to_sql("country_reference", engine, if_exists="replace", index=False)


def _write_exclusion_log(excluded: list[dict[str, Any]], path: Path = DEFAULT_EXCLUSION_LOG_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(excluded, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _main() -> None:
    from src import db
    from src.ingesta import client

    session = client.build_session()
    df, excluded = capture_country_reference(session)
    persist_country_reference(df)
    _write_exclusion_log(excluded)

    engine = db.get_engine()
    persist_country_reference_to_db(df, engine)

    print(f"country_reference: {len(df)} countries persisted (JSON + manifest + SQL table)")
    if excluded:
        print(f"country_reference_exclusion_log: {len(excluded)} codes excluded (missing_from_m49_crosswalk)")


if __name__ == "__main__":
    _main()
