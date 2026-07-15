"""Coverage/presence signal for the Phase 7 heatmap (COVER-01).

This module computes, from raw ingested data ONLY, whether a
(country_code, year, indicator_code) combination has a non-null reported
value. Per D-04, a wholly-absent row and a present row with ``value IS
NULL`` are unified into the SAME missing state -- pandas already collapses
both into ``NaN`` through the ``pivot()`` + ``.reindex()`` mechanics (no
row at all -> reindex fills NaN; a stored SQL ``NULL`` -> deserializes to
NaN via ``pd.read_sql``), so a single ``.notna()`` call is the entire
missing/present decision with no per-cell branching.

Region grouping (D-03) is resolved purely against ``country_reference`` (a
reference/lookup table, unaffected by Phase 2's 70%-coverage filter) -- this
module never reads, imports, or references Phase 2's derived clean-panel or
exclusion tables in any way (COVER-01, Pitfall 3): the coverage signal must
reflect raw data, not the post-filter clean panel.

All callers pass DataFrames already read via fixed-literal SQL table names
(mirrors ``src/db.py``'s and ``src/panel_build.py``'s established Security
V5 discipline) -- this module itself performs no SQL reads at all.
"""

from __future__ import annotations

import pandas as pd

# Same fixed indicator list `src/panel_build.py` establishes -- copied as a
# literal constant (not imported) to keep this module standalone.
INDICATOR_CODES: list[str] = ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"]
YEARS: list[int] = list(range(2000, 2023))


def build_presence_matrix(
    raw_observations: pd.DataFrame,
    countries: list[str],
    indicator_code: str,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """Country x year boolean presence grid for a single indicator.

    True where a non-null value exists for (country, year, indicator_code).
    False covers BOTH "no row at all" and "row exists but value IS NULL"
    (D-04) -- pivot+reindex already produce NaN for both, so a single
    ``.notna()`` unifies them without per-cell existence/nullity logic.

    Returned frame is indexed by ``countries`` (in the given order) with
    columns = ``years`` (default: module-level YEARS, 2000-2022).
    """
    years = years if years is not None else YEARS
    subset = raw_observations[raw_observations["indicator_code"] == indicator_code]
    wide = subset.pivot(index="country_code", columns="year", values="value")
    wide = wide.reindex(index=countries, columns=years)
    return wide.notna()


def ordered_countries_with_boundaries(
    country_reference: pd.DataFrame, countries: list[str]
) -> tuple[list[str], list[int]]:
    """Region-grouped country order + region-group boundary row indices (D-03).

    Restricts ``country_reference`` to the members of ``countries`` present
    in it, sorted by (region, subregion, country_code). ``boundaries`` are
    the 0-based row positions where a new region group starts (index 0 is
    always the first boundary). Join/selection uses only
    ["country_code", "region", "subregion"], on country_code, mirroring
    ``build_clean_panel``'s how="left" merge shape -- never touches Phase 2's
    derived clean-panel table.
    """
    ref = country_reference[country_reference["country_code"].isin(countries)]
    ref = ref[["country_code", "region", "subregion"]].sort_values(
        ["region", "subregion", "country_code"], na_position="last"
    )
    ordered = ref["country_code"].tolist()

    boundaries: list[int] = []
    prev_region = object()  # sentinel, never equal to a real region string
    for i, region in enumerate(ref["region"]):
        if region != prev_region:
            boundaries.append(i)
            prev_region = region
    return ordered, boundaries
