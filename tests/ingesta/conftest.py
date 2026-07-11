"""Ingesta-suite-scoped test isolation guard (INGEST-04 gap closure).

Root cause: `test_run_ingestion_force_true_refetches_even_when_manifest_exists`
called the real `run_ingestion(force=True)` without sandboxing
`manifest.RAW_DATA_ROOT`, so its un-mocked `raw_path.write_text()` call
clobbered the real, live-ingested `data/raw/{indicator}/{date}.json` files
with an empty stub for all 5 indicators every time the test suite ran on the
same calendar day as a live ingestion.

This module provides an autouse guard that fails the ingesta test session if
any test creates, modifies, or removes a file under the real `data/raw/`
tree, plus the snapshot/diff helpers it is built on (also exercised directly
by `test_isolation_guard.py`).

Deliberately scoped to `tests/ingesta/` (not the top-level `tests/conftest.py`)
since this is the suite that produced the bug.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.ingesta import manifest

# Resolved once at import time: the real, on-disk production raw-data root.
REAL_RAW_DATA_ROOT = manifest.RAW_DATA_ROOT.resolve()


def snapshot_tree(root: Path) -> dict[str, str]:
    """Map each regular file under `root` (recursively) to a fast change-token.

    Token is `"{st_size}:{st_mtime_ns}"` -- cheap enough to compute before and
    after every ingesta test, deliberately NOT a content hash. Returns `{}` if
    `root` does not exist (so a suite run before any raw data has ever been
    fetched does not error out).
    """
    root = Path(root)
    if not root.exists():
        return {}
    tokens: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_file():
            st = os.stat(path)
            tokens[str(path)] = f"{st.st_size}:{st.st_mtime_ns}"
    return tokens


def diff_snapshots(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Return the sorted list of paths added, removed, or changed between two snapshots."""
    changed = {
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    }
    return sorted(changed)


@pytest.fixture(autouse=True)
def forbid_writes_to_real_raw_data():
    """Fail the test at teardown if it wrote under the real data/raw/ tree.

    This is the regression guard for the exact class of bug that corrupted
    all 5 raw JSON artifacts: a test calling production ingestion code
    without redirecting `manifest.RAW_DATA_ROOT` into a tmp_path sandbox.
    """
    before = snapshot_tree(REAL_RAW_DATA_ROOT)
    yield
    after = snapshot_tree(REAL_RAW_DATA_ROOT)
    offending = diff_snapshots(before, after)
    assert offending == [], (
        "Test wrote to the real data/raw/ tree instead of a tmp_path sandbox. "
        f"Offending path(s): {offending}"
    )
