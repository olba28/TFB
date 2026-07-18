from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

RAW_DATA_ROOT = Path("data/raw")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _manifest_path_for(raw_path: Path) -> Path:
    raw_path = Path(raw_path)
    return raw_path.with_name(f"{raw_path.stem}.manifest.json")


def write_manifest(
    raw_path: Path,
    url: str,
    params: dict[str, Any],
    row_count: int,
) -> Path:
    raw_path = Path(raw_path)
    manifest_path = _manifest_path_for(raw_path)
    manifest_data = {
        "date": raw_path.stem,
        "url": url,
        "params": params,
        "row_count": row_count,
        "checksum": sha256_of(raw_path),
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    return manifest_path


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def manifest_exists(indicator_code: str, day: str) -> bool:
    raw_path = RAW_DATA_ROOT / indicator_code / f"{day}.json"
    manifest_path = _manifest_path_for(raw_path)
    return raw_path.exists() and manifest_path.exists()
