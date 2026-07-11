"""Tests for src/ingesta/client.py: retry/backoff config and automatic pagination.

No live network calls are made (D-03): the retry-integration test spins up a
local loopback HTTP server (stdlib `http.server`) so the real
`urllib3.util.retry.Retry` machinery mounted by `build_session()` is genuinely
exercised end-to-end; the pagination tests mock `session.get` directly since
pagination is this module's own looping logic, not urllib3 internals.
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
from urllib3.util.retry import Retry

from src.ingesta import client

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

with open(FIXTURES_DIR / "mock_500_then_paginated.json", encoding="utf-8") as f:
    FIXTURES = json.load(f)


class _ScriptedHandler(BaseHTTPRequestHandler):
    """Serves one scripted (status, body) response per request, then a default 200."""

    scripted_responses: list[tuple[int, dict]] = []
    request_count = 0

    def do_GET(self):  # noqa: N802 (stdlib method name)
        type(self).request_count += 1
        if type(self).scripted_responses:
            status, body = type(self).scripted_responses.pop(0)
        else:
            status, body = 200, {"totalElements": 0, "totalPages": 1, "pageNumber": 1, "data": []}
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):  # noqa: A002 (stdlib signature)
        pass  # silence default request logging to stderr


@contextmanager
def scripted_server(responses: list[tuple[int, dict]]):
    """Start a local loopback HTTP server that replays `responses` in order."""
    _ScriptedHandler.scripted_responses = list(responses)
    _ScriptedHandler.request_count = 0
    server = HTTPServer(("127.0.0.1", 0), _ScriptedHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", _ScriptedHandler
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def _mock_response(status_code: int, body: dict) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = body
    response.raise_for_status.return_value = None
    return response


# --- build_session() -------------------------------------------------------


def test_build_session_configures_retry_object_with_5xx_status_forcelist():
    session = client.build_session()
    adapter = session.get_adapter("https://unstats.un.org")
    assert isinstance(adapter.max_retries, Retry)
    assert adapter.max_retries.total == 3
    assert adapter.max_retries.backoff_factor == 1
    assert set(adapter.max_retries.status_forcelist) == {429, 500, 502, 503, 504}


def test_build_session_retries_on_500_then_succeeds(monkeypatch):
    """A mocked GET returning one 500 then a 200 succeeds after retry (D-03)."""
    monkeypatch.setattr("time.sleep", MagicMock())  # skip the real 1s backoff wait

    responses = [
        (500, FIXTURES["error_500"]),
        (200, FIXTURES["success_after_retry"]),
    ]
    with scripted_server(responses) as (base_url, handler_cls):
        session = client.build_session()
        resp = session.get(f"{base_url}/Indicator/Data", params={"indicator": "6.4.2"}, timeout=5)

        assert resp.status_code == 200
        assert resp.json() == FIXTURES["success_after_retry"]
        # The 500 was retried transparently by the session, not raised on the first attempt.
        assert handler_cls.request_count == 2


# --- fetch_all_pages() ------------------------------------------------------


def test_fetch_all_pages_single_page_returns_just_that_page(monkeypatch):
    session = MagicMock()
    session.get.return_value = _mock_response(200, FIXTURES["success_after_retry"])
    sleep_mock = MagicMock()
    monkeypatch.setattr(client.time, "sleep", sleep_mock)

    rows = client.fetch_all_pages(session, "6.4.2", page_size=1000)

    assert rows == FIXTURES["success_after_retry"]["data"]
    assert session.get.call_count == 1
    sleep_mock.assert_not_called()  # no delay needed after the only page


def test_fetch_all_pages_multi_page_concatenates_rows_and_sleeps_between_calls(monkeypatch):
    session = MagicMock()
    page1 = _mock_response(200, FIXTURES["page_1_of_2"])
    page2 = _mock_response(200, FIXTURES["page_2_of_2"])
    session.get.side_effect = [page1, page2]
    sleep_mock = MagicMock()
    monkeypatch.setattr(client.time, "sleep", sleep_mock)

    rows = client.fetch_all_pages(session, "6.4.2", page_size=2)

    expected = FIXTURES["page_1_of_2"]["data"] + FIXTURES["page_2_of_2"]["data"]
    assert rows == expected
    assert session.get.call_count == 2
    sleep_mock.assert_called_once_with(client.INTER_PAGE_DELAY_SECONDS)


def test_fetch_all_pages_reads_totalpages_dynamically_never_hardcoded(monkeypatch):
    """A response declaring totalPages=1 must not trigger a second call, even
    though other indicators (e.g. 6.4.1) may have hundreds of pages — the loop
    bound must come from each indicator's own first response (Pitfall 4)."""
    session = MagicMock()
    session.get.return_value = _mock_response(200, FIXTURES["success_after_retry"])
    monkeypatch.setattr(client.time, "sleep", MagicMock())

    client.fetch_all_pages(session, "8.1.1", page_size=1000)

    assert session.get.call_count == 1


def test_fetch_all_pages_raises_on_unexpected_response_shape(monkeypatch):
    session = MagicMock()
    session.get.return_value = _mock_response(200, {"unexpected": "shape"})
    monkeypatch.setattr(client.time, "sleep", MagicMock())

    with pytest.raises(ValueError, match="Unexpected response shape"):
        client.fetch_all_pages(session, "6.4.2", page_size=1000)
