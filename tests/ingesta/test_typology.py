"""Tests for src/ingesta/typology.py: country region + UN development-status
(LDC/LLDC/SIDS) reference data, built entirely from the UN SDG API's own
`GeoArea/Tree` (no external/non-UN data source, per 02-RESEARCH.md Finding 1).

All tests operate on an offline, hand-crafted `GeoArea/Tree`-shaped fixture --
no live network call is made anywhere in this file.
"""

from __future__ import annotations

from src.ingesta import typology

# --- Synthetic GeoArea/Tree fixture ------------------------------------------
#
# Mirrors the real live shape verified in 02-RESEARCH.md:
# - The SDG-region root is named exactly typology.SDG_REGION_ROOT_NAME.
# - Egypt sits DIRECTLY under "Africa" (region, no subregion) -- proves the
#   recursive walk tolerates shallow nesting (mirrors the real
#   tests/fixtures/geoarea_tree_sample.json shape, where Egypt is likewise a
#   direct child of "Africa" with no subregion level).
# - Kenya sits under "Africa" -> "Sub-Saharan Africa" (region + subregion).
# - Spain sits under "Europe" -> "Southern Europe" (region + subregion).
# - Kosovo sits under "Other areas" and is deliberately OMITTED from the test
#   crosswalk below, to exercise the crosswalk-missing exclusion path.
# - Dev-status roots use bare int geoAreaCodes (matches the live-verified
#   GeoArea/Tree shape for these nodes, e.g. `"geoAreaCode": 199`).

SDG_REGION_TREE = {
    "geoAreaCode": "1",
    "geoAreaName": typology.SDG_REGION_ROOT_NAME,
    "type": "Region",
    "children": [
        {
            "geoAreaCode": "002",
            "geoAreaName": "Africa",
            "type": "Region",
            "children": [
                {"geoAreaCode": "818", "geoAreaName": "Egypt", "type": "Country", "children": None},
                {
                    "geoAreaCode": "202",
                    "geoAreaName": "Sub-Saharan Africa",
                    "type": "Region",
                    "children": [
                        {"geoAreaCode": "404", "geoAreaName": "Kenya", "type": "Country", "children": None},
                        {"geoAreaCode": "262", "geoAreaName": "Djibouti", "type": "Country", "children": None},
                    ],
                },
            ],
        },
        {
            "geoAreaCode": "150",
            "geoAreaName": "Europe",
            "type": "Region",
            "children": [
                {
                    "geoAreaCode": "039",
                    "geoAreaName": "Southern Europe",
                    "type": "Region",
                    "children": [
                        {"geoAreaCode": "724", "geoAreaName": "Spain", "type": "Country", "children": None},
                    ],
                },
            ],
        },
        {
            "geoAreaCode": "900",
            "geoAreaName": "Other areas",
            "type": "Other areas",
            "children": [
                {"geoAreaCode": "901", "geoAreaName": "Kosovo", "type": "Country", "children": None},
            ],
        },
    ],
}

# Unrelated root that must be ignored (mirrors the real "World by continental
# regions" root -- same shape family, different geoAreaName, must NOT be
# selected as the region source).
CONTINENTAL_REGION_TREE = {
    "geoAreaCode": "1",
    "geoAreaName": "World (total) by continental regions",
    "type": "Region",
    "children": [
        {"geoAreaCode": "10", "geoAreaName": "Antarctica", "type": "Country", "children": None},
    ],
}

LDC_TREE = {
    "geoAreaCode": 199,
    "geoAreaName": "Least Developed Countries (LDC)",
    "type": "Region",
    "children": [
        {
            "geoAreaCode": 927,
            "geoAreaName": "LDC Africa",
            "type": "Region",
            "children": [
                {"geoAreaCode": 404, "geoAreaName": "Kenya", "type": "Country", "children": None},
                {"geoAreaCode": 262, "geoAreaName": "Djibouti", "type": "Country", "children": None},
            ],
        },
    ],
}

LLDC_TREE = {
    "geoAreaCode": 432,
    "geoAreaName": "Land Locked Developing Countries (LLDC)",
    "type": "Region",
    "children": [
        {
            "geoAreaCode": 923,
            "geoAreaName": "LLDC Africa",
            "type": "Region",
            "children": [
                {"geoAreaCode": 404, "geoAreaName": "Kenya", "type": "Country", "children": None},
            ],
        },
    ],
}

SIDS_TREE = {
    "geoAreaCode": 722,
    "geoAreaName": "Small Island Developing States (SIDS)",
    "type": "Region",
    "children": [
        {
            "geoAreaCode": 928,
            "geoAreaName": "SIDS Other",
            "type": "Region",
            "children": [],
        },
    ],
}

TREE_DATA = [SDG_REGION_TREE, CONTINENTAL_REGION_TREE, LDC_TREE, LLDC_TREE, SIDS_TREE]

# Deliberately omits "901" (Kosovo) so it lands in `excluded`, not the
# returned DataFrame.
CROSSWALK = {
    "818": "EGY",  # Egypt
    "404": "KEN",  # Kenya
    "262": "DJI",  # Djibouti
    "724": "ESP",  # Spain
}


# --- build_region_map() -------------------------------------------------------


def test_build_region_map_handles_shallow_nesting_country_directly_under_region():
    """Egypt sits directly under 'Africa' with no subregion in between --
    proves the walk does not assume a fixed region->subregion->country depth."""
    result = typology.build_region_map(TREE_DATA)

    assert result["818"] == {"region": "Africa", "subregion": None}


def test_build_region_map_records_region_and_subregion_when_both_present():
    """Kenya's path is Africa (region) -> Sub-Saharan Africa (subregion) ->
    Kenya (country leaf): the immediate parent is the subregion, the parent's
    parent is the region."""
    result = typology.build_region_map(TREE_DATA)

    assert result["404"] == {"region": "Africa", "subregion": "Sub-Saharan Africa"}


def test_build_region_map_ignores_the_continental_regions_root():
    """Antarctica (10) only exists under the continental-regions root, which
    must NOT be selected as the region source (only SDG_REGION_ROOT_NAME is)."""
    result = typology.build_region_map(TREE_DATA)

    assert "010" not in result


# --- build_development_status_flags() ---------------------------------------


def test_dev_status_flags_map_omits_countries_absent_from_all_roots():
    """build_development_status_flags itself only records countries actually
    encountered while walking the 3 dev-status trees -- Egypt appears in
    neither LDC, LLDC, nor SIDS in this fixture, so it is legitimately ABSENT
    here (not an explicit all-False entry). The "default to False, not
    absence" guarantee is enforced one layer up, by build_country_reference's
    merge (see test_build_country_reference_defaults_dev_status_to_false_for_absent_country)."""
    result = typology.build_development_status_flags(TREE_DATA)

    assert "818" not in result


def test_dev_status_single_flag_membership():
    """Djibouti (262) is present under LDC only, not LLDC/SIDS."""
    result = typology.build_development_status_flags(TREE_DATA)

    assert result["262"] == {"is_ldc": True, "is_lldc": False, "is_sids": False}


def test_dev_status_multi_flag_membership():
    """Kenya (404) is present under BOTH LDC and LLDC in this fixture."""
    result = typology.build_development_status_flags(TREE_DATA)

    assert result["404"] == {"is_ldc": True, "is_lldc": True, "is_sids": False}


# --- build_country_reference() ------------------------------------------------


def test_build_country_reference_keys_output_by_iso3_not_m49():
    """Critical regression guard: the returned DataFrame's country_code column
    must be ISO3 (matching raw_observations.country_code's schema), NOT the
    raw M49 code used internally by build_region_map/build_development_status_flags."""
    df, excluded = typology.build_country_reference(TREE_DATA, CROSSWALK)

    codes = set(df["country_code"])
    assert "EGY" in codes
    assert "KEN" in codes
    assert "818" not in codes  # M49 code must not leak into the final output
    assert "404" not in codes


def test_build_country_reference_defaults_dev_status_to_false_for_absent_country():
    """Egypt is absent from build_development_status_flags' map entirely (not
    found under LDC/LLDC/SIDS) -- build_country_reference's merge must still
    produce an explicit all-False record for it, not a missing/null value."""
    df, _ = typology.build_country_reference(TREE_DATA, CROSSWALK)

    egypt = df[df["country_code"] == "EGY"].iloc[0]
    assert bool(egypt["is_ldc"]) is False
    assert bool(egypt["is_lldc"]) is False
    assert bool(egypt["is_sids"]) is False


def test_build_country_reference_merges_region_and_dev_status_columns():
    df, _ = typology.build_country_reference(TREE_DATA, CROSSWALK)

    kenya = df[df["country_code"] == "KEN"].iloc[0]
    assert bool(kenya["is_ldc"]) is True
    assert bool(kenya["is_lldc"]) is True
    assert bool(kenya["is_sids"]) is False


def test_build_country_reference_excludes_codes_missing_from_crosswalk():
    """Kosovo (901) is a valid Country leaf in the tree but absent from
    CROSSWALK -- must be excluded and logged, never silently dropped or
    inserted with a null country_code."""
    df, excluded = typology.build_country_reference(TREE_DATA, CROSSWALK)

    assert "XKX" not in set(df["country_code"])
    assert not any(row.get("country_code") == "" for _, row in df.iterrows())
    excluded_codes = {e["code"] for e in excluded}
    assert "901" in excluded_codes
    kosovo_entry = next(e for e in excluded if e["code"] == "901")
    assert kosovo_entry["reason"] == "missing_from_m49_crosswalk"


def test_build_country_reference_columns_shape():
    df, _ = typology.build_country_reference(TREE_DATA, CROSSWALK)

    expected_columns = {"country_code", "region", "subregion", "is_ldc", "is_lldc", "is_sids"}
    assert expected_columns <= set(df.columns)
