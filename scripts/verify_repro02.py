"""Standalone reproducibility-proof script for REPRO-02 (04-03-PLAN.md Task 3).

Not a pytest test: executing the full notebook end-to-end costs ~25-30
minutes per run (04-RESEARCH.md Open Questions Q2, live-measured) -- far too
slow for the routine `pytest tests/ -q` suite (10s feedback-latency budget,
04-VALIDATION.md). This script instead runs
`jupyter nbconvert --to notebook --execute` on the committed notebook TWICE,
independently, and asserts the resulting reproducibility snapshot (bootstrap
CIs, excluded-country lists, RF feature importances/oob_score_, SHAP values
array) is bit-identical (`np.array_equal`, never `pytest.approx`) between the
two runs.

Each execution writes its snapshot to the SAME fixed path
(`data/modelos/_repro_snapshot.pkl`, gitignored via `*.pkl`) -- this script
reads that file immediately after each run, before the next run overwrites
it.

Neither throwaway notebook copy executed by this script is committed to git;
only the already-executed `notebook/4_1_interpretabilidad_simulacion.ipynb`
(Task 1/2 output) and this script are checked in.

Usage:
    .venv/Scripts/python.exe scripts/verify_repro02.py
"""

from __future__ import annotations

import pickle
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK_DIR = PROJECT_ROOT / "notebook"
COMMITTED_NOTEBOOK = NOTEBOOK_DIR / "4_1_interpretabilidad_simulacion.ipynb"
SNAPSHOT_PATH = PROJECT_ROOT / "data" / "modelos" / "_repro_snapshot.pkl"
PYTHON = sys.executable


def run_notebook_and_capture_snapshot(run_label: str) -> dict:
    """Copy the committed notebook to a throwaway temp path INSIDE
    ``notebook/`` and execute it there.

    ``nbconvert``'s ``ExecutePreprocessor`` derives the kernel's working
    directory from the INPUT notebook's own directory (live-verified against
    this project's nbconvert install; NOT from ``--output-dir`` or the
    shell's cwd when invoking the command). Keeping the throwaway copy
    inside ``notebook/`` preserves the committed notebook's own
    ``PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebook"
    else Path.cwd()`` bootstrap cell unmodified -- executing the same copy
    from a directory named anything other than ``notebook`` would silently
    break that bootstrap logic.
    """
    temp_notebook = NOTEBOOK_DIR / f"_verify_repro02_{run_label}.ipynb"
    shutil.copy(COMMITTED_NOTEBOOK, temp_notebook)
    print(f"[{run_label}] executing throwaway copy: {temp_notebook.name} ...")
    try:
        result = subprocess.run(
            [
                PYTHON, "-m", "jupyter", "nbconvert",
                "--to", "notebook", "--execute", "--inplace",
                str(temp_notebook),
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            raise RuntimeError(
                f"[{run_label}] nbconvert execution failed (exit {result.returncode})"
            )

        if not SNAPSHOT_PATH.exists():
            raise RuntimeError(
                f"[{run_label}] expected reproducibility snapshot not found at "
                f"{SNAPSHOT_PATH} -- did the notebook's final snapshot cell run?"
            )

        with open(SNAPSHOT_PATH, "rb") as f:
            snapshot = pickle.load(f)
        print(f"[{run_label}] snapshot captured from {SNAPSHOT_PATH}")
        return snapshot
    finally:
        temp_notebook.unlink(missing_ok=True)


def compare_snapshots(run_a: dict, run_b: dict) -> list[str]:
    """Return a list of human-readable mismatch descriptions (empty list if
    bit-identical). Uses ``np.array_equal`` (exact), never
    ``pytest.approx``/``np.allclose`` -- REPRO-02 requires bit-identical
    results, not merely "close"."""
    mismatches: list[str] = []

    scenarios_a, scenarios_b = run_a["scenarios"], run_b["scenarios"]
    if set(scenarios_a) != set(scenarios_b):
        mismatches.append(
            f"scenario keys differ: A={set(scenarios_a)} B={set(scenarios_b)}"
        )
    else:
        for pct in scenarios_a:
            sa, sb = scenarios_a[pct], scenarios_b[pct]
            if not np.array_equal(sa["ci_2.5"], sb["ci_2.5"]):
                mismatches.append(f"scenario {pct}: ci_2.5 differs")
            if not np.array_equal(sa["ci_97.5"], sb["ci_97.5"]):
                mismatches.append(f"scenario {pct}: ci_97.5 differs")
            if sa["excluded_countries"] != sb["excluded_countries"]:
                mismatches.append(f"scenario {pct}: excluded_countries differs")

    if not np.array_equal(run_a["rf_feature_importances"], run_b["rf_feature_importances"]):
        mismatches.append("rf_feature_importances differs")

    if run_a["rf_oob_score"] != run_b["rf_oob_score"]:
        mismatches.append("rf_oob_score differs")

    if not np.array_equal(run_a["shap_values"], run_b["shap_values"]):
        mismatches.append("shap_values differs")

    return mismatches


def main() -> int:
    if not COMMITTED_NOTEBOOK.exists():
        print(f"FAIL: committed notebook not found at {COMMITTED_NOTEBOOK}")
        return 1

    run_a = run_notebook_and_capture_snapshot("runA")
    run_b = run_notebook_and_capture_snapshot("runB")

    mismatches = compare_snapshots(run_a, run_b)

    print()
    if mismatches:
        print(
            "FAIL: REPRO-02 -- two full top-to-bottom executions produced "
            "DIFFERENT results:"
        )
        for m in mismatches:
            print(f"  - {m}")
        print()
        print(
            "Root cause is almost certainly a missed n_jobs=1/unseeded step "
            "(04-RESEARCH.md Pitfall #2) -- fix src/simulate.py or "
            "src/interpret.py (not the notebook), then re-run this script."
        )
        return 1

    print(
        "PASS: REPRO-02 -- two independent full top-to-bottom executions of "
        "notebook/4_1_interpretabilidad_simulacion.ipynb produced bit-identical "
        "bootstrap CIs, excluded-country lists, RF feature importances/"
        "oob_score_, and SHAP values."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
