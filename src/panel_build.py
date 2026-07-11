"""Coverage filter, exclusion table, and idempotent clean-panel build (PANEL-01, PANEL-02).

``panel_clean`` is a faithful, unmodified pivot of ``raw_observations`` (plus
``country_reference`` columns joined in) -- it is always fully regenerated
from source, never hand-edited, mirroring ``db.rebuild_panel``'s established
convention. Coverage/exclusion status against the 70%-of-years threshold is
computed and documented ENTIRELY in the separate ``panel_exclusions`` table;
``panel_clean`` never nulls or otherwise alters a real, already-reported
value based on that status (see 02-01-PLAN.md's Review Notes, fix #3, for
the rationale -- destroying real data would make Phase 3's robustness-check
requirement, MODEL1-05, impossible on the excluded subsample).

All reads/writes use ``pandas.read_sql``/``to_sql`` with fixed table names --
no table or column name is ever built from external input (Security V5,
mirrors ``src/db.py``'s existing pattern).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine

# Same fixed indicator list `fetch_data.py` already establishes -- copied as a
# literal constant (not imported) to keep this module standalone.
INDICATOR_CODES: list[str] = ["6.4.2", "6.4.1", "8.1.1", "8.2.1", "2.3.1"]

TOTAL_YEARS = 23  # 2000-2022 inclusive
YEARS_REQUIRED = 17  # 23 * 0.70 = 16.1 -> 17 (02-RESEARCH.md Finding 4)

REFERENCE_COLUMNS = ["region", "subregion", "is_ldc", "is_lldc", "is_sids"]


def compute_coverage(
    raw_observations: pd.DataFrame,
    country_reference: pd.DataFrame,
    indicator_codes: list[str] | None = None,
) -> pd.DataFrame:
    """Return one row for EVERY (country_code, indicator_code) pair in the
    full cross-product of country_reference's countries x indicator_codes --
    including pairs with ZERO rows in raw_observations at all (years_available=0).
    """
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
    """Filter compute_coverage's output to excluded==True rows, with a
    `reason` column distinguishing "no data at all" from "some data, still
    below the 70% threshold" -- both are the same underlying rule, the
    finer-grained string is purely for documentation clarity (PANEL-02)."""
    excluded = coverage[coverage["excluded"]].copy()
    excluded["reason"] = excluded["years_available"].apply(
        lambda n: "no_data_reported" if n == 0 else "coverage_below_70pct_threshold"
    )
    return excluded


def build_clean_panel(
    raw_observations: pd.DataFrame, country_reference: pd.DataFrame
) -> pd.DataFrame:
    """Pivot raw_observations exactly as db.rebuild_panel does, join
    country_reference columns in, and NEVER modify a value based on coverage
    status. Sorted by (country_code, year) with a fixed column order so
    rebuild_clean_panel is idempotent regardless of run-to-run row order.
    """
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
    """Read raw_observations + country_reference fresh from `engine`, compute
    coverage/exclusions/clean-panel, and write panel_clean + panel_exclusions
    back (`if_exists="replace"` -- always fully regenerated, never appended).
    """
    raw_observations = pd.read_sql("SELECT * FROM raw_observations", engine)
    country_reference = pd.read_sql("SELECT * FROM country_reference", engine)

    coverage = compute_coverage(raw_observations, country_reference, INDICATOR_CODES)
    exclusions = build_exclusion_table(coverage)
    clean_panel = build_clean_panel(raw_observations, country_reference)

    clean_panel.to_sql("panel_clean", engine, if_exists="replace", index=False)
    exclusions.to_sql("panel_exclusions", engine, if_exists="replace", index=False)


def _main() -> None:
    """CLI entry: `python -m src.panel_build`."""
    from src import db

    engine = db.get_engine()
    rebuild_clean_panel(engine)
    clean = pd.read_sql("SELECT COUNT(*) AS n FROM panel_clean", engine)
    exclusions = pd.read_sql("SELECT COUNT(*) AS n FROM panel_exclusions", engine)
    print(f"panel_clean: {clean['n'].iloc[0]} rows")
    print(f"panel_exclusions: {exclusions['n'].iloc[0]} (country, indicator) pairs excluded")


if __name__ == "__main__":
    _main()
