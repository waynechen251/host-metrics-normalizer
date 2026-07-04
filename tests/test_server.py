from __future__ import annotations

import http.client
import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

import host_metrics_normalizer.refresher as refresher_module
from host_metrics_normalizer.cache import RawMetricsCache
from host_metrics_normalizer.config import (
    AppConfig,
    AssetConfig,
    CacheConfig,
    NormalizationConfig,
    ServerConfig,
    SourceExporterConfig,
)
from host_metrics_normalizer.detect import DetectedExporter
from host_metrics_normalizer.metrics import NormalizerMetrics
from host_metrics_normalizer.normalized import NormalizedSeries, NormalizedSnapshot
from host_metrics_normalizer.refresher import MetricsRefresher
from host_metrics_normalizer.scraper import ScrapeResult
from host_metrics_normalizer.server import HealthState, NormalizerHTTPServer

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def build_config(debug_enabled: bool = True) -> AppConfig:
    return AppConfig(
        server=ServerConfig(listen_address="127.0.0.1", listen_port=0, debug_enabled=debug_enabled),
        source_exporter=SourceExporterConfig(endpoint="http://127.0.0.1:9100/metrics"),
        cache=CacheConfig(),
        asset=AssetConfig(),
        labels={},
        normalization=NormalizationConfig(),
    )


@pytest.fixture
def running_server():
    def _start(
        debug_enabled: bool = True,
        cache: RawMetricsCache | None = None,
        config: AppConfig | None = None,
        metrics: NormalizerMetrics | None = None,
    ):
        config = config if config is not None else build_config(debug_enabled=debug_enabled)
        metrics = metrics if metrics is not None else NormalizerMetrics(version="0.1.0")
        health = HealthState(version="0.1.0")
        cache = cache if cache is not None else RawMetricsCache()
        refresher = MetricsRefresher(config, cache, metrics, health)
        server = NormalizerHTTPServer(config, metrics, health, cache, refresher)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    servers = []

    def factory(debug_enabled: bool = True, cache: RawMetricsCache | None = None):
        server = _start(debug_enabled=debug_enabled, cache=cache)
        servers.append(server)
        return server

    yield factory

    for server in servers:
        server.shutdown()


def _get(server: NormalizerHTTPServer, path: str):
    host, port = server.server_address
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.headers.get("Content-Type"), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type"), exc.read()


def _get_no_redirect(server: NormalizerHTTPServer, path: str):
    host, port = server.server_address
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        response.read()
        return response.status, response.getheader("Location")
    finally:
        conn.close()


def test_healthz_returns_expected_json(running_server):
    server = running_server()

    status, content_type, body = _get(server, "/healthz")

    assert status == 200
    assert content_type == "application/json"
    payload = json.loads(body)
    assert payload["status"] == "ok"
    assert payload["version"] == "0.1.0"
    assert payload["source_exporter_up"] is False
    assert payload["last_scrape_success"] is False
    assert payload["last_scrape_timestamp"] == 0


def _fail_fast_scrape(endpoint, timeout_seconds):
    return ScrapeResult(
        success=False, raw_text=None, duration_seconds=0.0, status_code=None, error_kind="connection_error"
    )


def test_metrics_returns_prometheus_exposition(running_server, monkeypatch):
    monkeypatch.setattr(refresher_module, "scrape", _fail_fast_scrape)
    server = running_server()

    status, content_type, body = _get(server, "/metrics")

    assert status == 200
    assert "text/plain" in content_type
    text = body.decode("utf-8")
    assert "host_normalizer_up 1.0" in text
    assert "host_normalizer_info" in text


def test_metrics_triggers_a_fresh_scrape_on_every_request(running_server, monkeypatch):
    windows_raw = _read_fixture("windows_exporter.metrics")
    node_raw = _read_fixture("node_exporter.metrics")
    responses = iter([windows_raw, node_raw])
    call_count = {"n": 0}

    def fake_scrape(endpoint, timeout_seconds):
        call_count["n"] += 1
        return ScrapeResult(
            success=True, raw_text=next(responses), duration_seconds=0.01, status_code=200, error_kind=None
        )

    monkeypatch.setattr(refresher_module, "scrape", fake_scrape)
    server = running_server()

    _, _, first_body = _get(server, "/metrics")
    assert 'exporter="windows_exporter"' in first_body.decode("utf-8")

    _, _, second_body = _get(server, "/metrics")
    second_text = second_body.decode("utf-8")
    assert 'exporter="node_exporter"' in second_text
    assert 'exporter="windows_exporter"' not in second_text

    assert call_count["n"] == 2


def test_metrics_end_to_end_hits_a_real_local_exporter_every_request():
    """No monkeypatching of scrape(): a stdlib HTTPServer stands in for the
    local source exporter, proving /metrics makes a genuine new TCP connection
    and HTTP GET on every request instead of replaying a cached result."""
    responses = [_read_fixture("windows_exporter.metrics"), _read_fixture("node_exporter.metrics")]
    call_count = {"n": 0}

    class FakeExporterHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            index = min(call_count["n"], len(responses) - 1)
            call_count["n"] += 1
            body = responses[index].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    fake_exporter = HTTPServer(("127.0.0.1", 0), FakeExporterHandler)
    fake_thread = threading.Thread(target=fake_exporter.serve_forever, daemon=True)
    fake_thread.start()

    host, port = fake_exporter.server_address
    config = AppConfig(
        server=ServerConfig(listen_address="127.0.0.1", listen_port=0, debug_enabled=True),
        source_exporter=SourceExporterConfig(endpoint=f"http://{host}:{port}/metrics"),
        cache=CacheConfig(),
        asset=AssetConfig(),
        labels={},
        normalization=NormalizationConfig(),
    )
    cache = RawMetricsCache()
    metrics = NormalizerMetrics(version="0.1.0", config=config, cache=cache)
    health = HealthState(version="0.1.0")
    refresher = MetricsRefresher(config, cache, metrics, health)
    server = NormalizerHTTPServer(config, metrics, health, cache, refresher)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        first_body = _get(server, "/metrics")[2]
        assert 'exporter="windows_exporter"' in first_body.decode("utf-8")

        second_body = _get(server, "/metrics")[2]
        second_text = second_body.decode("utf-8")
        assert 'exporter="node_exporter"' in second_text
        assert 'exporter="windows_exporter"' not in second_text

        assert call_count["n"] == 2
    finally:
        server.shutdown()
        server_thread.join(timeout=5)
        fake_exporter.shutdown()
        fake_thread.join(timeout=5)


def test_debug_raw_returns_503_when_no_cache_yet(running_server):
    server = running_server(debug_enabled=True)

    status, _, _ = _get(server, "/debug/raw")

    assert status == 503


def test_debug_raw_returns_cached_text_when_available(running_server):
    cache = RawMetricsCache()
    cache.update_success(
        raw_text="windows_exporter_build_info 1\n",
        detected=DetectedExporter(type="windows_exporter", os_family="windows", version="0.31.6"),
        duration=0.02,
        monotonic_now=1.0,
        wall_now=1.0,
    )
    server = running_server(debug_enabled=True, cache=cache)

    status, content_type, body = _get(server, "/debug/raw")

    assert status == 200
    assert "text/plain" in content_type
    assert body.decode("utf-8") == "windows_exporter_build_info 1\n"


def test_debug_normalized_returns_503(running_server):
    server = running_server(debug_enabled=True)

    status, _, _ = _get(server, "/debug/normalized")

    assert status == 503


def test_debug_normalized_returns_cached_json():
    config = build_config(debug_enabled=True)
    cache = RawMetricsCache()
    normalized = NormalizedSnapshot(
        status="ok",
        supported=True,
        exporter="windows_exporter",
        version="0.31.6",
        os_family="windows",
        host="srv-app-01",
        series=(
            NormalizedSeries.from_mapping(
                "host_os_info",
                1.0,
                {
                    "host": "srv-app-01",
                    "os_family": "windows",
                    "os_name": "Windows 10 Pro",
                    "os_version": "10.0.19045",
                    "kernel_version": "10.0.19045",
                    "architecture": "x86_64",
                },
            ),
        ),
    )
    cache.update_success(
        raw_text="windows_exporter_build_info 1\n",
        detected=DetectedExporter(type="windows_exporter", os_family="windows", version="0.31.6"),
        duration=0.02,
        monotonic_now=1.0,
        wall_now=1.0,
        normalized=normalized,
    )
    metrics = NormalizerMetrics(version="0.1.0", config=config, cache=cache)
    health = HealthState(version="0.1.0")
    refresher = MetricsRefresher(config, cache, metrics, health)
    server = NormalizerHTTPServer(config, metrics, health, cache, refresher)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        status, content_type, body = _get(server, "/debug/normalized")

        assert status == 200
        assert content_type == "application/json"
        payload = json.loads(body)
        assert payload["status"] == "ok"
        assert payload["supported"] is True
        assert payload["exporter"] == "windows_exporter"
        assert payload["host"] == "srv-app-01"
        assert payload["last_scrape_timestamp"] == 1
        assert payload["series"][0]["name"] == "host_os_info"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_debug_endpoint_returns_404_when_disabled(running_server):
    server = running_server(debug_enabled=False)

    status, _, _ = _get(server, "/debug/raw")

    assert status == 404


def test_unknown_path_returns_404(running_server):
    server = running_server()

    status, _, _ = _get(server, "/does-not-exist")

    assert status == 404


def test_root_path_redirects_to_metrics_path(running_server):
    server = running_server()

    status, location = _get_no_redirect(server, "/")

    assert status == 302
    assert location == "/metrics"


def test_root_path_follow_redirect_returns_prometheus_exposition(running_server, monkeypatch):
    monkeypatch.setattr(refresher_module, "scrape", _fail_fast_scrape)
    server = running_server()

    status, content_type, body = _get(server, "/")

    assert status == 200
    assert "text/plain" in content_type
    assert "host_normalizer_up 1.0" in body.decode("utf-8")
