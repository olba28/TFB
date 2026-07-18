from __future__ import annotations

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_BASE_URL = "https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data"
YEAR_START = 2000
YEAR_END = 2022

INTER_PAGE_DELAY_SECONDS = 0.5


def build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True,
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_all_pages(
    session: requests.Session,
    indicator_code: str,
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    page = 1
    total_pages = 1

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
            total_pages = body["totalPages"]

        if page < total_pages:
            time.sleep(INTER_PAGE_DELAY_SECONDS)
        page += 1

    return all_rows
