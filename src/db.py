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
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(CREATE_RAW_OBSERVATIONS))


def insert_observations(engine: Engine, df: pd.DataFrame) -> None:
    duplicated_mask = df.duplicated(subset=KEY_COLS, keep=False)
    if duplicated_mask.any():
        raise ValueError(
            "Duplicate (country_code, year, indicator_code) rows before insert: "
            f"{df.loc[duplicated_mask, KEY_COLS].to_dict('records')}"
        )
    df.to_sql("raw_observations", engine, if_exists="append", index=False)


def rebuild_panel(engine: Engine) -> None:
    raw = pd.read_sql("SELECT * FROM raw_observations", engine)
    wide = raw.pivot(index=["country_code", "year"], columns="indicator_code", values="value")
    wide = wide.reset_index()
    wide.to_sql("panel", engine, if_exists="replace", index=False)
