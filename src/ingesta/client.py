"""HTTP client for the UN SDG API: session-level retry/backoff and automatic pagination.

This module is the sole point of contact with the external UN SDG API
(``unstats.un.org/SDGAPI``). All retry/backoff behavior (D-01) is delegated to
``urllib3.util.retry.Retry`` mounted on the session's ``HTTPAdapter`` — never a
hand-rolled ``try/except`` retry loop. Pagination (D-02) reads ``totalPages`` /
``totalElements`` fresh from each indicator's own first response; it never
assumes a shared or fixed page count across indicators (see Pitfall 4 in
01-RESEARCH.md).
"""

from __future__ import annotations

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Fixed endpoint + year bounds (2000-2022, per PROJECT.md scope). Never derived
# from API response content — Security V5 (path/param-injection safety).
API_BASE_URL = "https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data"
YEAR_START = 2000
YEAR_END = 2022

# D-04: fixed delay between successive page requests (0.5-1.0s), separate from
# the retry backoff itself. Module-level constant so tests can patch `time.sleep`
# without needing to wait out the real delay.
INTER_PAGE_DELAY_SECONDS = 0.5


def build_session() -> requests.Session:
    """Build a requests.Session configured for the D-01 retry/backoff policy.

    Mounts a `urllib3.util.retry.Retry` object on the session's `HTTPAdapter` —
    NOT the integer `max_retries=3` shorthand, which per RESEARCH's "State of
    the Art" section only retries connection errors, not the 5xx/429 status
    codes D-01 actually targets. `backoff_factor=1` produces the 1s/2s/4s
    sequence between the 3 retries.
    """
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True,
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    # Mounted for both schemes: production only ever calls https://, but
    # mounting http:// too lets tests exercise the exact same retry-configured
    # adapter against a local loopback test server (no live network calls).
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_all_pages(
    session: requests.Session,
    indicator_code: str,
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    """Fetch and concatenate all pages of observations for indicator_code.

    Query params are built only from `indicator_code` (a fixed, caller-supplied
    constant) and the hardcoded YEAR_START/YEAR_END bounds — never from
    unvalidated API response content (Security V5). `totalPages` is read fresh
    from the FIRST response of THIS indicator and the loop continues until that
    many pages have been fetched (D-02, Pitfall 4) — never a hardcoded page
    count shared across indicators.

    A fixed `INTER_PAGE_DELAY_SECONDS` delay (D-04) is inserted between
    successive page requests (not before the first, not after the last).
    """
    all_rows: list[dict[str, Any]] = []
    page = 1
    total_pages = 1  # updated from the first response

    while page <= total_pages:
        params = {
            "indicator": indicator_code,
            "timePeriod": list(range(YEAR_START, YEAR_END + 1)),
            "page": page,
            "pageSize": page_size,
        }
        response = session.get(API_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        body = response.json()

        if "data" not in body or "totalPages" not in body:
            raise ValueError(
                f"Unexpected response shape for indicator {indicator_code!r}: "
                "missing 'data' or 'totalPages' key"
            )

        all_rows.extend(body["data"])
        if page == 1:
            # WR-02: capture total_pages only from the FIRST response, per this
            # function's own docstring -- re-reading it on every page risks
            # silent premature truncation if a later page reports a smaller
            # totalPages than the initial response (the exact Pitfall 4 class
            # of silent data loss this function is designed to avoid).
            total_pages = body["totalPages"]

        if page < total_pages:
            time.sleep(INTER_PAGE_DELAY_SECONDS)
        page += 1

    return all_rows
