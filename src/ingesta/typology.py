"""Country region and UN development-status (LDC/LLDC/SIDS) reference data.

Sourced ENTIRELY from the UN SDG API's own `GeoArea/Tree` endpoint -- no
external/non-UN data source (World Bank income groups were investigated and
rejected: `GeoArea/Tree` carries World Bank income-group node *labels* but no
country membership for them; see 02-RESEARCH.md Finding 1). "Tipología de
país" is therefore operationalized as three UN-native development-status
flags: LDC (Least Developed Countries), LLDC (Land Locked Developing
Countries), and SIDS (Small Island Developing States) -- each a country can
belong to zero, one, or more than one.

Pure-transform module, mirroring `countries.py`'s existing pattern: no network
call inside any of `build_region_map`/`build_development_status_flags`/
`build_country_reference` -- only `capture_country_reference` performs the
live HTTP GET (fixed URL, never derived from response content -- Security
V5, matching Phase 1's precedent).

Country reference data (region, subregion, LDC/LLDC/SIDS) is captured ONCE
and persisted (both as a JSON+manifest artifact and as a `country_reference`
SQL table) rather than re-fetched live at every panel-rebuild -- required for
PANEL-01's idempotency/reconstructibility guarantee (a rebuild must not
depend on a live network call; see 02-RESEARCH.md Finding 2).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from sqlalchemy import Engine

from src.ingesta import manifest as manifest_module
from src.ingesta.countries import _normalize_code, build_crosswalk, collect_countries

# Same endpoint Phase 1's fetch_data.py already trusts -- copied as a literal
# string constant (not imported from fetch_data.py) to avoid coupling this
# standalone Phase 2 module to Phase 1's orchestrator module.
GEOAREA_TREE_URL = "https://unstats.un.org/SDGAPI/v1/sdg/GeoArea/Tree"

# The exact root name (of the 7 roots GeoArea/Tree returns) that carries SDG
# region/subregion groupings -- verified live in 02-RESEARCH.md Finding 1.
SDG_REGION_ROOT_NAME = "World (total) by SDG regions"

# Development-status flag name -> the geoAreaCode of its root in GeoArea/Tree
# (verified live in 02-RESEARCH.md Finding 1). Each root's descendants resolve
# to real Country leaves (unlike the World Bank income-group nodes, which
# carry no country membership at all).
DEV_STATUS_ROOT_CODES: dict[str, int] = {
    "is_ldc": 199,
    "is_lldc": 432,
    "is_sids": 722,
}

DEFAULT_COUNTRY_REFERENCE_PATH = Path("data/raw/country_reference.json")
DEFAULT_EXCLUSION_LOG_PATH = Path("data/raw/country_reference_exclusion_log.json")


def _find_root(tree_data: list[dict[str, Any]], *, name: str | None = None, code: int | None = None) -> dict[str, Any] | None:
    """Return the first root dict matching `name` (geoAreaName) or `code`
    (geoAreaCode, compared numerically so both int- and string-typed codes
    match), or None if no root matches."""
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
    """Walk the SDG-region root recursively, returning
    `{m49_code: {"region": ..., "subregion": ...}}` for every Country leaf.

    Does NOT assume a fixed region->subregion->country depth: a country found
    directly under a top-level region (no subregion in between) gets
    `subregion=None` and `region=<the one ancestor name available>`, rather
    than being dropped or raising.
    """
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
    """Walk each root in DEV_STATUS_ROOT_CODES to every Country leaf, returning
    `{m49_code: {"is_ldc": bool, "is_lldc": bool, "is_sids": bool}}`.

    A country not found under a given root defaults to `False` for that flag
    (default, not absence) -- every country that appears under ANY of the
    three roots ends up with a complete 3-flag record.
    """
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
    """Merge region + development-status maps into one ISO3-keyed DataFrame.

    Both `build_region_map` and `build_development_status_flags` key their
    output by the raw M49 code (what `GeoArea/Tree` walks naturally produce).
    This function is the SINGLE point where M49 is converted to ISO3 via
    `crosswalk` -- matching `raw_observations.country_code`'s schema exactly.
    An M49 code with no crosswalk entry is EXCLUDED from the returned
    DataFrame and recorded in the second return value (never silently
    dropped or inserted with a null `country_code`), mirroring
    `countries.filter_to_countries`'s existing exclusion-logging pattern.
    """
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
    """Fetch GeoArea/Tree once (single GET, no retry-policy reuse -- see this
    plan's threat model T-02-01-03) and build the country reference DataFrame.

    The crosswalk is built via `build_crosswalk()`, a pure file read from the
    fixed, versioned M49 CSV path -- no additional network call.
    """
    response = session.get(GEOAREA_TREE_URL, timeout=30)
    response.raise_for_status()
    tree_data = response.json()
    crosswalk = build_crosswalk()
    return build_country_reference(tree_data, crosswalk)


def persist_country_reference(
    df: pd.DataFrame, path: Path = DEFAULT_COUNTRY_REFERENCE_PATH
) -> Path:
    """Write `df` as JSON records to `path` and a provenance manifest sidecar
    via `manifest.write_manifest` (same date/url/params/row_count/checksum
    schema Phase 1 established for indicator raw files)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(df.to_dict(orient="records"), indent=2, ensure_ascii=False),
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
    """Write `df` to a `country_reference` SQL table, always fully
    regenerated (`if_exists="replace"`) -- mirrors `db.rebuild_panel`'s
    established "never hand-edit, always rebuild from source" convention."""
    df.to_sql("country_reference", engine, if_exists="replace", index=False)


def _write_exclusion_log(excluded: list[dict[str, Any]], path: Path = DEFAULT_EXCLUSION_LOG_PATH) -> Path:
    """Persist crosswalk-exclusions as a documented artifact -- mirrors D-16's
    `exclusion_log.json` precedent (never silently drop an unmapped code)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(excluded, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _main() -> None:
    """CLI entry: `python -m src.ingesta.typology`.

    Runs capture_country_reference, then BOTH persist_country_reference
    (JSON + manifest) AND persist_country_reference_to_db (SQL table) end to
    end, plus writes any crosswalk-exclusions to a documented log.
    """
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
