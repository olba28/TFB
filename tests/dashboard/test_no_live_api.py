"""Static no-live-API guard for src/dashboard/*.py (DASH-01, T-5-05).

The dashboard must NEVER call the UN SDG API at runtime -- it consumes only
local artifacts (``data/panel.db`` via ``src.db``, ``data/modelos/*.pkl``)
through ``src/dashboard/data.py``'s cached loaders. This test reads every
``src/dashboard/*.py`` source file as plain text (no network, no import of
the modules under test needed beyond a static scan) and asserts none of them
contain an import of the UN SDG API client (``src.ingesta``), an HTTP client
import (``requests``/``httpx``/``urllib.request``), or the UN SDG API base
host (``unstats.un.org``) anywhere in the source text.

Mirrors tests/dashboard/test_plots.py's
test_plots_module_has_no_streamlit_import (exact-substring checks, not
bare-word checks, to avoid false positives against prose in docstrings).
"""

from __future__ import annotations

from pathlib import Path

FORBIDDEN_IMPORT_SUBSTRINGS: tuple[str, ...] = (
    "import requests",
    "from requests",
    "import httpx",
    "from httpx",
    "import urllib.request",
    "from urllib.request",
    "from src.ingesta",
    "import src.ingesta",
    "from src import ingesta",
)

FORBIDDEN_HOST_SUBSTRING = "unstats.un.org"


def _dashboard_source_files() -> list[Path]:
    dashboard_dir = Path(__file__).resolve().parents[2] / "src" / "dashboard"
    return sorted(dashboard_dir.glob("*.py"))


def test_no_dashboard_module_imports_a_live_http_client_or_ingesta():
    """DASH-01: no src/dashboard/*.py file imports requests/httpx/
    urllib.request or src.ingesta (the UN SDG API client module)."""
    source_files = _dashboard_source_files()
    assert source_files, "expected at least one src/dashboard/*.py file to scan"

    offenders: dict[str, list[str]] = {}
    for path in source_files:
        source = path.read_text(encoding="utf-8")
        hits = [needle for needle in FORBIDDEN_IMPORT_SUBSTRINGS if needle in source]
        if hits:
            offenders[path.name] = hits

    assert not offenders, f"Forbidden live-API/HTTP imports found: {offenders}"


def test_no_dashboard_module_references_the_un_sdg_api_host():
    """DASH-01: the UN SDG API base host never appears anywhere in
    src/dashboard/*.py -- not just as an import, but as any literal
    reference (e.g. a hardcoded URL string)."""
    source_files = _dashboard_source_files()
    assert source_files, "expected at least one src/dashboard/*.py file to scan"

    offenders = [
        path.name
        for path in source_files
        if FORBIDDEN_HOST_SUBSTRING in path.read_text(encoding="utf-8")
    ]

    assert not offenders, f"UN SDG API host referenced in: {offenders}"
