"""M49 canonical country list, ISO3 crosswalk, and exclusion log (D-13-D-16).

Pure transform module: no network calls. The `GeoArea/Tree` JSON is fetched
by `client.py` and passed in here; the M49 CSV crosswalk is loaded from a
fixed, versioned repo path (Security V5 -- path never derived from external
input, mirrors `manifest.py`'s `RAW_DATA_ROOT` convention).

Per D-13, the canonical country-list source is the UN's own M49
classification (`GeoArea/Tree`'s `type` field + the official M49 CSV) --
never `pycountry`, never a World Bank list.

Per D-14 (operationalized exactly per 01-RESEARCH.md's "Research flag on
D-14"): a `geoAreaCode` counts as an included country iff it resolves to a
`type == 'Country'` leaf in `GeoArea/Tree`. This objective rule is applied
uniformly -- no hardcoded exception list for Kosovo/Taiwan/Palestine/Hong
Kong or any other disputed territory.

Per D-16, every excluded code (any node with `type != 'Country'`, or a
country-leaf code with no matching M49 CSV crosswalk entry) is recorded in a
documented exclusion log -- never silently dropped.

Code normalization: the live `GeoArea/Tree` endpoint serializes `geoAreaCode`
as a bare JSON integer (e.g. ``4``, not ``"004"``), the `Indicator/Data`
endpoint serializes it as an un-padded numeric string (e.g. ``"4"``), and the
official M49 CSV's `M49 Code` column is a zero-padded 3-digit string (e.g.
``"004"``). All three must be joined on the same key -- every code is
normalized via :func:`_normalize_code` (`str(code).zfill(3)`) before being
used as a dict key or looked up, both here and in :func:`filter_to_countries`.
Without this, every observation row fails the country-leaf lookup silently
(live-verified: a live run without normalization produced zero surviving
rows across all 5 indicators -- see Phase 1 Plan 5 SUMMARY).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

# D-15: fixed, repo-relative path -- never derived from API response content
# (Security V5, path-construction safety).
M49_CSV_PATH = Path(__file__).resolve().parent / "data" / "m49_countries.csv"


def _normalize_code(code: Any) -> str:
    """Normalize a geoAreaCode/M49 code to a zero-padded 3-digit string.

    `GeoArea/Tree` returns bare JSON integers, `Indicator/Data` returns
    un-padded numeric strings, and the M49 CSV uses zero-padded 3-digit
    strings -- this is the single normalization point all three are joined
    through.
    """
    return str(code).strip().zfill(3)


def collect_countries(
    tree_nodes: list[dict[str, Any]],
    excluded: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Walk the `GeoArea/Tree` response; return `{geoAreaCode: geoAreaName}`
    for `type == 'Country'` leaves only.

    Every non-'Country' node encountered (regions, aggregates, or any other
    type) is appended to `excluded` (when a list is provided) with its code,
    name, type, and the name of its parent aggregate -- the documented
    exclusion log required by D-16. The same country can appear under
    multiple top-level groupings (e.g. by SDG region and by continental
    region); dict keys naturally dedupe by `geoAreaCode`.
    """
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
    """Load the official M49 CSV and return `{m49_code: iso3_code}`.

    The CSV (semicolon-delimited, UTF-8 with BOM -- confirmed against the
    file acquired for this repo) carries the country's own M49 numeric code
    in the `M49 Code` column and its ISO-alpha3 in `ISO-alpha3 Code`. This is
    the UN's own classification (D-13) -- no `pycountry`, no World Bank list.
    """
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
    """Tag each observation row with its ISO3 code and split kept/excluded.

    A row is KEPT iff its `geoAreaCode` resolves to a `type == 'Country'`
    leaf, i.e. is present in `countries` (the `GeoArea/Tree`-derived
    canonical set) -- this is the D-14 objective rule, applied uniformly
    with no manual exception list for disputed territories. Rows whose
    `geoAreaCode` is not in `countries` are excluded and logged with a
    reason. A `geoAreaCode` present in `countries` but missing from
    `crosswalk` (a CSV/tree mismatch) is also excluded and logged rather
    than silently dropped or inserted without an ISO3 code.
    """
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
    """Persist the exclusion log as a documented artifact (D-16) -- never stdout."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(excluded, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
