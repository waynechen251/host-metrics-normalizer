from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

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
from host_metrics_normalizer.server import HealthState, NormalizerHTTPServer


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
    def _start(debug_enabled: bool = True, cache: RawMetricsCache | None = None):
        config = build_config(debug_enabled=debug_enabled)
        metrics = NormalizerMetrics(version="0.1.0")
        health = HealthState(version="0.1.0")
        cache = cache if cache is not None else RawMetricsCache()
        server = NormalizerHTTPServer(config, metrics, health, cache)
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


def test_metrics_returns_prometheus_exposition(running_server):
    server = running_server()

    status, content_type, body = _get(server, "/metrics")

    assert status == 200
    assert "text/plain" in content_type
    text = body.decode("utf-8")
    assert "host_normalizer_up 1.0" in text
    assert "host_normalizer_info" in text


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


def test_debug_normalized_returns_501(running_server):
    server = running_server(debug_enabled=True)

    status, _, _ = _get(server, "/debug/normalized")

    assert status == 501


def test_debug_endpoint_returns_404_when_disabled(running_server):
    server = running_server(debug_enabled=False)

    status, _, _ = _get(server, "/debug/raw")

    assert status == 404


def test_unknown_path_returns_404(running_server):
    server = running_server()

    status, _, _ = _get(server, "/does-not-exist")

    assert status == 404
