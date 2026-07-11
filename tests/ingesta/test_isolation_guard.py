"""Self-tests proving tests/ingesta/conftest.py's snapshot_tree/diff_snapshots
detect writes under a directory (INGEST-04 gap closure regression guard).

Both tests operate ONLY on a tmp_path directory -- never the real data/raw/
tree -- so they cannot themselves corrupt production data while demonstrating
the guard's detection logic.
"""

from __future__ import annotations

from tests.ingesta.conftest import diff_snapshots, snapshot_tree


def test_snapshot_detects_new_file(tmp_path):
    (tmp_path / "existing.txt").write_text("hello", encoding="utf-8")

    before = snapshot_tree(tmp_path)
    new_file = tmp_path / "new.txt"
    new_file.write_text("world", encoding="utf-8")
    after = snapshot_tree(tmp_path)

    assert diff_snapshots(before, after) == [str(new_file)]


def test_snapshot_detects_content_change(tmp_path):
    target = tmp_path / "existing.txt"
    target.write_text("hello", encoding="utf-8")

    before = snapshot_tree(tmp_path)
    target.write_text("a completely different, longer payload", encoding="utf-8")
    after = snapshot_tree(tmp_path)

    assert diff_snapshots(before, after) == [str(target)]
