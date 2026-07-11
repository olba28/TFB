"""SQLite storage layer for the water-stress / economic-impact panel.

``raw_observations`` is the immutable, append-only single source of truth for
every observation ingested from the UN SDG API: one row per
(country_code, year, indicator_code), enforced twice (D-11, belt-and-suspenders)
-- a Python-level assert in :func:`insert_observations` catches duplicates
*within* the incoming DataFrame before any row reaches SQLite, and the table's
own ``UNIQUE`` constraint catches duplicates that slip past that check across
separate insert calls.

``panel`` is a derived wide table (D-12): always fully regenerated from
``raw_observations`` via :func:`rebuild_panel` (pivot indicator_code -> columns),
never hand-edited. Phase 2 owns cleaning, coverage filtering, and feature
engineering on top of this thin pivot.

All SQL here uses parameterized statements or pandas ``to_sql``/``read_sql`` --
API-sourced values are never interpolated into SQL text (Security V5, SQL
injection; see 01-RESEARCH.md Security Domain).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine, text

CREATE_RAW_OBSERVATIONS = """
CREATE TABLE IF NOT EXISTS raw_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL,       -- ISO3
    indicator_code TEXT NOT NULL,     -- e.g. '6.4.2'
    year INTEGER NOT NULL,
    value REAL,                       -- nullable: missing observations stored as NULL, never dropped
    dimension TEXT NOT NULL,          -- original API dimension combo, e.g. 'Activity=TOTAL'
    source_manifest_id TEXT NOT NULL, -- reference to the manifest file/id this row came from
    UNIQUE(country_code, year, indicator_code)
);
"""

KEY_COLS = ["country_code", "year", "indicator_code"]


def get_engine(db_path: str = "data/panel.db") -> Engine:
    """Return a SQLAlchemy Engine bound to the panel SQLite file.

    Creates the parent directory if it does not yet exist (skipped for the
    special SQLAlchemy in-memory DSN ``":memory:"``).
    """
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine: Engine) -> None:
    """Create ``raw_observations`` if it does not already exist (idempotent)."""
    with engine.begin() as conn:
        conn.execute(text(CREATE_RAW_OBSERVATIONS))


def insert_observations(engine: Engine, df: pd.DataFrame) -> None:
    """Append ``df`` to ``raw_observations``, guarded by a pre-insert duplicate assert (D-11).

    Raises ``AssertionError`` naming the offending (country_code, year,
    indicator_code) keys if ``df`` itself contains duplicates on those columns --
    before any row reaches SQLite. The schema's ``UNIQUE`` constraint is the
    second, independent guard for duplicates that span separate calls (e.g. the
    same row inserted twice).
    """
    duplicated_mask = df.duplicated(subset=KEY_COLS, keep=False)
    assert not duplicated_mask.any(), (
        "Duplicate (country_code, year, indicator_code) rows before insert: "
        f"{df.loc[duplicated_mask, KEY_COLS].to_dict('records')}"
    )
    df.to_sql("raw_observations", engine, if_exists="append", index=False)


def rebuild_panel(engine: Engine) -> None:
    """Regenerate the derived wide ``panel`` table from ``raw_observations`` (D-12).

    Always drops and recreates ``panel`` (``if_exists='replace'``) -- it is a
    pure pivot (indicator_code -> columns) indexed by (country_code, year) and
    must never be hand-edited or treated as an independent source of truth.
    """
    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    wide = raw.pivot(index=["country_code", "year"], columns="indicator_code", values="value")
    wide = wide.reset_index()
    wide.to_sql("panel", engine, if_exists="replace", index=False)
