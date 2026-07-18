from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

M49_CSV_PATH = Path(__file__).resolve().parent / "data" / "m49_countries.csv"


def _normalize_code(code: Any) -> str:
    return str(code).strip().zfill(3)


def collect_countries(
    tree_nodes: list[dict[str, Any]],
    excluded: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    countries: dict[str, str] = {}

    def walk(node: dict[str, Any], parent_name: str) -> None:
        code = _normalize_code(node.get("geoAreaCode"))
        name = node.get("geoAreaName")
        node_type = node.get("type")
        if node_type == "Country":
            countries[code] = name
        elif excluded is not None:
            excluded.append(
                {"code": code, "name": name, "type": node_type, "parent": parent_name}
            )
        for child in node.get("children") or []:
            walk(child, parent_name=name)

    for root in tree_nodes:
        walk(root, parent_name="ROOT")

    return countries


def build_crosswalk(csv_path: Path | str = M49_CSV_PATH) -> dict[str, str]:
    csv_path = Path(csv_path)
    crosswalk: dict[str, str] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            m49_code = (row.get("M49 Code") or "").strip()
            iso3 = (row.get("ISO-alpha3 Code") or "").strip()
            if m49_code and iso3:
                crosswalk[m49_code] = iso3
    return crosswalk


def filter_to_countries(
    rows: list[dict[str, Any]],
    countries: dict[str, str],
    crosswalk: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for row in rows:
        code = _normalize_code(row.get("geoAreaCode"))
        if code not in countries:
            excluded.append({**row, "exclusion_reason": "not_a_country_leaf"})
            continue
        iso3 = crosswalk.get(code)
        if iso3 is None:
            excluded.append({**row, "exclusion_reason": "missing_from_m49_crosswalk"})
            continue
        kept.append({**row, "iso3": iso3})

    return kept, excluded


def write_exclusion_log(excluded: list[dict[str, Any]], path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(excluded, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
