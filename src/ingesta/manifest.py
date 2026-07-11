"""Provenance manifest reader/writer for raw indicator downloads (D-05, D-08).

Pure file-I/O: this module never calls the network (client.py owns that) and
never inspects the API's response schema beyond the row count it is handed.
All paths are built only from a fixed indicator code and an ISO date string —
never from API response content (Security V5, path-construction safety).

Manifest schema (D-08): date de descarga, URL, parametros de consulta, numero
de filas, checksum del fichero descargado.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

# D-06: data/raw/{indicador}/{fecha}.json folder structure.
RAW_DATA_ROOT = Path("data/raw")


def sha256_of(path: Path) -> str:
    """Return the sha256 hex digest of the file at `path` (D-08 checksum)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _manifest_path_for(raw_path: Path) -> Path:
    """Sidecar manifest path for a raw JSON path: {fecha}.json -> {fecha}.manifest.json."""
    raw_path = Path(raw_path)
    return raw_path.with_name(f"{raw_path.stem}.manifest.json")


def write_manifest(
    raw_path: Path,
    url: str,
    params: dict[str, Any],
    row_count: int,
) -> Path:
    """Write the provenance sidecar manifest next to `raw_path`.

    Fields (D-08, exactly these five): date, url, params, row_count, checksum.
    """
    raw_path = Path(raw_path)
    manifest_path = _manifest_path_for(raw_path)
    manifest_data = {
        "date": date.today().isoformat(),
        "url": url,
        "params": params,
        "row_count": row_count,
        "checksum": sha256_of(raw_path),
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    return manifest_path


def load_manifest(path: Path) -> dict[str, Any]:
    """Load and return the manifest dict stored at `path`."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def manifest_exists(indicator_code: str, day: str) -> bool:
    """True only when both the raw JSON and its manifest exist for indicator_code+day.

    The orchestrator (Plan 05's fetch_data.py) owns the `if exists and not
    force: skip` control flow (D-07) — this function only reports existence.
    Paths are built only from `indicator_code` (fixed constant list) and `day`
    (an ISO date string, typically `date.today().isoformat()`) — never from
    API response content.
    """
    raw_path = RAW_DATA_ROOT / indicator_code / f"{day}.json"
    manifest_path = _manifest_path_for(raw_path)
    return raw_path.exists() and manifest_path.exists()
