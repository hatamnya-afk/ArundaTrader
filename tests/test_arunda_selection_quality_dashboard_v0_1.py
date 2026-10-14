from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import arunda_selection_quality_dashboard_v0_1 as dashboard


def request(server: ThreadingHTTPServer, path: str):
    url = f"http://127.0.0.1:{server.server_port}{path}"
    return urllib.request.urlopen(url, timeout=2)


def serve(stream: Path):
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), dashboard.make_handler(stream, min_sample_size=2)
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_dashboard_home_is_local_read_only_html(tmp_path: Path):
    server, thread = serve(tmp_path / "empty.jsonl")
    try:
        with request(server, "/") as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
            assert "آروندا تریدر" in body
            assert "/api/report" in body
            assert "fetch('/api/report'" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_report_endpoint_returns_empty_report_without_fabricating_events(tmp_path: Path):
    stream = tmp_path / "missing.jsonl"
    server, thread = serve(stream)
    try:
        with request(server, "/api/report") as response:
            report = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert report["evidence_basis"] == "REAL_MARKET_OBSERVATIONS_ONLY"
            assert report["selection_count"] == 0
            assert report["rankings_by_horizon"] == {"1h": [], "4h": [], "24h": []}
            assert not stream.exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_report_endpoint_fails_closed_on_corrupt_evidence(tmp_path: Path):
    stream = tmp_path / "corrupt.jsonl"
    stream.write_text("{not-json}\n", encoding="utf-8")
    server, thread = serve(stream)
    try:
        with pytest.raises(urllib.error.HTTPError) as exc:
            request(server, "/api/report")
        assert exc.value.code == 503
        payload = json.loads(exc.value.read().decode("utf-8"))
        assert payload["error"] == "EVIDENCE_READ_FAILED"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_non_loopback_host_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["arunda_selection_quality_dashboard_v0_1.py", "--host", "0.0.0.0"],
    )
    with pytest.raises(SystemExit) as exc:
        dashboard.main()
    assert exc.value.code == 2
