import threading
from pathlib import Path

from prometheus_client import generate_latest

import host_metrics_normalizer.worker as worker_module
from host_metrics_normalizer.cache import RawMetricsCache
from host_metrics_normalizer.config import (
    AppConfig,
    AssetConfig,
    CacheConfig,
    NormalizationConfig,
    ServerConfig,
    SourceExporterConfig,
)
from host_metrics_normalizer.metrics import NormalizerMetrics
from host_metrics_normalizer.scraper import ScrapeResult
from host_metrics_normalizer.server import HealthState
from host_metrics_normalizer.worker import ScrapeWorker

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def build_config() -> AppConfig:
    return AppConfig(
        server=ServerConfig(),
        source_exporter=SourceExporterConfig(endpoint="http://127.0.0.1:9182/metrics"),
        cache=CacheConfig(ttl_seconds=60, stale_after_seconds=180),
        asset=AssetConfig(),
        labels={},
        normalization=NormalizationConfig(),
    )


def build_worker(monkeypatch, results):
    """results: list of ScrapeResult to return on successive calls to scrape()."""
    config = build_config()
    cache = RawMetricsCache()
    metrics = NormalizerMetrics(version="0.1.0")
    health = HealthState(version="0.1.0")
    stop_event = threading.Event()
    worker = ScrapeWorker(config, cache, metrics, health, stop_event)

    call_results = iter(results)

    def fake_scrape(endpoint, timeout_seconds):
        return next(call_results)

    monkeypatch.setattr(worker_module, "scrape", fake_scrape)
    return worker, cache, metrics, health


def test_scrape_once_success_updates_cache_metrics_health(monkeypatch):
    raw = _read_fixture("windows_exporter.metrics")
    worker, cache, metrics, health = build_worker(
        monkeypatch,
        [ScrapeResult(success=True, raw_text=raw, duration_seconds=0.05, status_code=200, error_kind=None)],
    )

    worker._scrape_once()

    snapshot = cache.get()
    assert snapshot.last_scrape_success is True
    assert snapshot.detected.type == "windows_exporter"
    assert snapshot.detected.version == "0.31.6"

    health_snapshot = health.snapshot()
    assert health_snapshot["source_exporter_up"] is True
    assert health_snapshot["exporter"] == "windows_exporter"
    assert health_snapshot["os_family"] == "windows"

    output = generate_latest(metrics.registry).decode("utf-8")
    assert 'host_source_exporter_up{exporter="windows_exporter"} 1.0' in output
    assert "host_metrics_stale 0.0" in output


def test_scrape_once_failure_marks_down_and_increments_errors(monkeypatch):
    worker, cache, metrics, health = build_worker(
        monkeypatch,
        [
            ScrapeResult(
                success=False,
                raw_text=None,
                duration_seconds=3.0,
                status_code=None,
                error_kind="timeout",
            )
        ],
    )

    worker._scrape_once()

    snapshot = cache.get()
    assert snapshot.last_scrape_success is False

    health_snapshot = health.snapshot()
    assert health_snapshot["source_exporter_up"] is False

    output = generate_latest(metrics.registry).decode("utf-8")
    # No exporter ever detected -> error must fold into the unlabeled counter.
    assert "host_normalizer_errors_total 1.0" in output


def test_label_stability_across_unknown_then_detected_ticks(monkeypatch):
    """Regression: first tick succeeds but exporter type is unrecognized,
    second tick correctly detects windows_exporter. The final /metrics
    output must never contain a residual exporter="unknown" series."""
    unknown_raw = _read_fixture("unknown.metrics")
    windows_raw = _read_fixture("windows_exporter.metrics")
    worker, cache, metrics, health = build_worker(
        monkeypatch,
        [
            ScrapeResult(
                success=True, raw_text=unknown_raw, duration_seconds=0.02, status_code=200, error_kind=None
            ),
            ScrapeResult(
                success=True, raw_text=windows_raw, duration_seconds=0.03, status_code=200, error_kind=None
            ),
        ],
    )

    worker._scrape_once()
    first_output = generate_latest(metrics.registry).decode("utf-8")
    assert 'exporter="unknown"' in first_output  # genuinely undetected, expected

    worker._scrape_once()
    second_output = generate_latest(metrics.registry).decode("utf-8")

    assert 'exporter="unknown"' not in second_output
    assert 'host_source_exporter_up{exporter="windows_exporter"} 1.0' in second_output
    assert second_output.count("host_source_exporter_up{") == 1

    health_snapshot = health.snapshot()
    assert health_snapshot["exporter"] == "windows_exporter"
