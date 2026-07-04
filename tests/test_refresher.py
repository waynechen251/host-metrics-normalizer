import threading
from pathlib import Path

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
from host_metrics_normalizer.metrics import NormalizerMetrics
from host_metrics_normalizer.refresher import MetricsRefresher
from host_metrics_normalizer.scraper import ScrapeResult
from host_metrics_normalizer.server import HealthState

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def build_config() -> AppConfig:
    return AppConfig(
        server=ServerConfig(),
        source_exporter=SourceExporterConfig(endpoint="http://127.0.0.1:9182/metrics"),
        cache=CacheConfig(stale_after_seconds=180),
        asset=AssetConfig(),
        labels={},
        normalization=NormalizationConfig(),
    )


def build_refresher(monkeypatch, results):
    """results: list of ScrapeResult to return on successive calls to scrape()."""
    config = build_config()
    cache = RawMetricsCache()
    metrics = NormalizerMetrics(version="0.1.0")
    health = HealthState(version="0.1.0")
    refresher = MetricsRefresher(config, cache, metrics, health)

    call_results = iter(results)

    def fake_scrape(endpoint, timeout_seconds):
        return next(call_results)

    monkeypatch.setattr(refresher_module, "scrape", fake_scrape)
    return refresher, cache, metrics, health


def test_refresh_success_updates_cache_metrics_health(monkeypatch):
    raw = _read_fixture("windows_exporter.metrics")
    refresher, cache, metrics, health = build_refresher(
        monkeypatch,
        [ScrapeResult(success=True, raw_text=raw, duration_seconds=0.05, status_code=200, error_kind=None)],
    )

    output = refresher.refresh_and_render().decode("utf-8")

    snapshot = cache.get()
    assert snapshot.last_scrape_success is True
    assert snapshot.detected.type == "windows_exporter"
    assert snapshot.detected.version == "0.31.6"
    assert snapshot.normalized is not None
    assert snapshot.normalized.status == "ok"
    assert {
        "host_os_info",
        "host_cpu_usage_percent",
        "host_memory_bytes_total",
        "host_uptime_seconds",
    }.issubset({series.name for series in snapshot.normalized.series})

    health_snapshot = health.snapshot()
    assert health_snapshot["source_exporter_up"] is True
    assert health_snapshot["exporter"] == "windows_exporter"
    assert health_snapshot["os_family"] == "windows"

    assert 'host_source_exporter_up{exporter="windows_exporter"} 1.0' in output
    assert "host_metrics_stale 0.0" in output


def test_refresh_failure_marks_down_and_increments_errors(monkeypatch):
    refresher, cache, metrics, health = build_refresher(
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

    output = refresher.refresh_and_render().decode("utf-8")

    snapshot = cache.get()
    assert snapshot.last_scrape_success is False

    health_snapshot = health.snapshot()
    assert health_snapshot["source_exporter_up"] is False

    # No exporter ever detected -> error must fold into the unlabeled counter.
    assert "host_normalizer_errors_total 1.0" in output


def test_label_stability_across_unknown_then_detected_calls(monkeypatch):
    """Regression: first call succeeds but exporter type is unrecognized,
    second call correctly detects windows_exporter. The final /metrics
    output must never contain a residual exporter="unknown" series."""
    unknown_raw = _read_fixture("unknown.metrics")
    windows_raw = _read_fixture("windows_exporter.metrics")
    refresher, cache, metrics, health = build_refresher(
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

    first_output = refresher.refresh_and_render().decode("utf-8")
    assert 'exporter="unknown"' in first_output  # genuinely undetected, expected

    second_output = refresher.refresh_and_render().decode("utf-8")

    assert 'exporter="unknown"' not in second_output
    assert 'host_source_exporter_up{exporter="windows_exporter"} 1.0' in second_output
    assert second_output.count("host_source_exporter_up{") == 1

    health_snapshot = health.snapshot()
    assert health_snapshot["exporter"] == "windows_exporter"


def test_concurrent_refresh_calls_do_not_raise_and_stay_consistent(monkeypatch):
    """Regression: NormalizerMetrics.update_source_exporter mutates an unlocked
    _current_exporter_label via a clear()-then-relabel sequence. Once every
    /metrics request triggers its own refresh (instead of a single background
    thread), refresh_and_render's lock must serialize the whole scrape+render
    cycle or this tears under concurrent callers."""
    windows_raw = _read_fixture("windows_exporter.metrics")
    unknown_raw = _read_fixture("unknown.metrics")
    results = [
        ScrapeResult(
            success=True,
            raw_text=windows_raw if i % 2 == 0 else unknown_raw,
            duration_seconds=0.01,
            status_code=200,
            error_kind=None,
        )
        for i in range(200)
    ]
    refresher, cache, metrics, health = build_refresher(monkeypatch, results)

    outputs = []
    errors = []
    outputs_lock = threading.Lock()

    def call_repeatedly():
        try:
            for _ in range(25):
                output = refresher.refresh_and_render().decode("utf-8")
                with outputs_lock:
                    outputs.append(output)
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=call_repeatedly) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert errors == []
    assert len(outputs) == 200
    for output in outputs:
        assert output.count("host_source_exporter_up{") == 1
