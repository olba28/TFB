from __future__ import annotations

import pandas as pd

INDICATOR_CODES: list[str] = ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"]
YEARS: list[int] = list(range(2000, 2023))


def build_presence_matrix(
    raw_observations: pd.DataFrame,
    countries: list[str],
    indicator_code: str,
    years: list[int] | None = None,
) -> pd.DataFrame:
    years = years if years is not None else YEARS
    subset = raw_observations[raw_observations["indicator_code"] == indicator_code]
    wide = subset.pivot(index="country_code", columns="year", values="value")
    wide = wide.reindex(index=countries, columns=years)
    return wide.notna()


def ordered_countries_with_boundaries(
    country_reference: pd.DataFrame, countries: list[str]
) -> tuple[list[str], list[int]]:
    ref = country_reference[country_reference["country_code"].isin(countries)]
    ref = ref[["country_code", "region", "subregion"]].sort_values(
        ["region", "subregion", "country_code"], na_position="last"
    )
    ordered = ref["country_code"].tolist()

    boundaries: list[int] = []
    prev_region = object()
    for i, region in enumerate(ref["region"]):
        if region != prev_region:
            boundaries.append(i)
            prev_region = region
    return ordered, boundaries
