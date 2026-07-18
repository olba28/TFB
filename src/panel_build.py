from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine

INDICATOR_CODES: list[str] = ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"]

TOTAL_YEARS = 23
YEARS_REQUIRED = 17

REFERENCE_COLUMNS = ["region", "subregion", "is_ldc", "is_lldc", "is_sids"]


def compute_coverage(
    raw_observations: pd.DataFrame,
    country_reference: pd.DataFrame,
    indicator_codes: list[str] | None = None,
) -> pd.DataFrame:
    if indicator_codes is None:
        indicator_codes = INDICATOR_CODES

    countries = country_reference["country_code"].drop_duplicates().tolist()
    full_index = pd.MultiIndex.from_product(
        [countries, indicator_codes], names=["country_code", "indicator_code"]
    )

    non_null = raw_observations[raw_observations["value"].notna()]
    years_available = (
        non_null.groupby(["country_code", "indicator_code"])["year"]
        .nunique()
        .rename("years_available")
    )

    coverage = years_available.reindex(full_index, fill_value=0).reset_index()
    coverage["years_required"] = YEARS_REQUIRED
    coverage["coverage_pct"] = coverage["years_available"] / TOTAL_YEARS
    coverage["excluded"] = coverage["years_available"] < YEARS_REQUIRED
    return coverage


def build_exclusion_table(coverage: pd.DataFrame) -> pd.DataFrame:
    excluded = coverage[coverage["excluded"]].copy()
    excluded["reason"] = excluded["years_available"].apply(
        lambda n: "no_data_reported" if n == 0 else "coverage_below_70pct_threshold"
    )
    return excluded


def build_clean_panel(
    raw_observations: pd.DataFrame, country_reference: pd.DataFrame
) -> pd.DataFrame:
    wide = raw_observations.pivot(
        index=["country_code", "year"], columns="indicator_code", values="value"
    )
    wide = wide.reset_index()

    merged = wide.merge(
        country_reference[["country_code", *REFERENCE_COLUMNS]],
        on="country_code",
        how="left",
    )

    indicator_columns = sorted(c for c in wide.columns if c not in ("country_code", "year"))
    ordered_columns = ["country_code", "year", *REFERENCE_COLUMNS, *indicator_columns]
    merged = merged[ordered_columns]
    merged = merged.sort_values(["country_code", "year"]).reset_index(drop=True)
    return merged


def rebuild_clean_panel(engine: Engine) -> None:
    raw_observations = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

    coverage = compute_coverage(raw_observations, country_reference, INDICATOR_CODES)
    exclusions = build_exclusion_table(coverage)
    clean_panel = build_clean_panel(raw_observations, country_reference)

    clean_panel.to_sql("panel_clean", engine, if_exists="replace", index=False)
    exclusions.to_sql("panel_exclusions", engine, if_exists="replace", index=False)


def _main() -> None:
    from src import db

    engine = db.get_engine()
    rebuild_clean_panel(engine)
    clean = pd.read_sql("SELECT COUNT(*) AS n FROM panel_clean", engine)
    exclusions = pd.read_sql("SELECT COUNT(*) AS n FROM panel_exclusions", engine)
    print(f"panel_clean: {clean['n'].iloc[0]} rows")
    print(f"panel_exclusions: {exclusions['n'].iloc[0]} (country, indicator) pairs excluded")


if __name__ == "__main__":
    _main()
