from pathlib import Path

from prometheus_client import generate_latest

from host_metrics_normalizer.cache import RawMetricsCache
from host_metrics_normalizer.config import (
    AppConfig,
    AssetConfig,
    CacheConfig,
    GpuConfig,
    NormalizationConfig,
    ServerConfig,
    SourceExporterConfig,
)
from host_metrics_normalizer.detect import DetectedExporter
from host_metrics_normalizer.metrics import NormalizerMetrics
from host_metrics_normalizer.normalization import normalize_exporter_metrics

FIXTURES_DIR = Path(__file__).parent / "fixtures"
WINDOWS_0316 = DetectedExporter(type="windows_exporter", os_family="windows", version="0.31.6")
WINDOWS_UNSUPPORTED = DetectedExporter(type="windows_exporter", os_family="windows", version="0.31.5")
UNKNOWN_EXPORTER = DetectedExporter(type="unknown_exporter", os_family="linux", version="1.0.0")


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def build_config() -> AppConfig:
    return AppConfig(
        server=ServerConfig(),
        source_exporter=SourceExporterConfig(endpoint="http://127.0.0.1:9182/metrics"),
        cache=CacheConfig(),
        asset=AssetConfig(
            asset_id="ASSET-001",
            hostname="srv-app-01",
            display_name="App Server 01",
            owner="infra",
            environment="prod",
            location="office-3f",
            role="app-server",
            criticality="medium",
            managed_by="wayne",
        ),
        labels={},
        normalization=NormalizationConfig(),
        gpu=GpuConfig(enabled=False),
    )


def test_wrong_exporter_type_returns_unsupported_snapshot():
    config = build_config()
    raw = _read_fixture("windows_exporter_0316_full.metrics")

    snapshot = normalize_exporter_metrics(config, UNKNOWN_EXPORTER, raw, now=1784049820.304)

    assert snapshot.status == "unsupported_exporter"
    assert snapshot.supported is False
    assert snapshot.series == ()


def test_unsupported_windows_version_returns_unsupported_snapshot():
    config = build_config()
    raw = _read_fixture("windows_exporter_0316_full.metrics")

    snapshot = normalize_exporter_metrics(config, WINDOWS_UNSUPPORTED, raw, now=1784049820.304)

    assert snapshot.status == "unsupported_version"
    assert snapshot.supported is False
    assert snapshot.series == ()


def test_parse_error_returns_unsupported_snapshot():
    config = build_config()

    snapshot = normalize_exporter_metrics(config, WINDOWS_0316, "{{{ not prometheus text }}}", now=1784049820.304)

    assert snapshot.status == "parse_error"
    assert snapshot.supported is False
    assert snapshot.series == ()


def test_host_metrics_collector_emits_only_self_metrics_when_version_unsupported():
    config = build_config()
    cache = RawMetricsCache()
    raw = _read_fixture("windows_exporter_0316_full.metrics")
    snapshot = normalize_exporter_metrics(config, WINDOWS_UNSUPPORTED, raw, now=1784049820.304)
    assert snapshot.series == ()

    cache.update_success(
        raw_text=raw,
        detected=WINDOWS_UNSUPPORTED,
        duration=0.05,
        monotonic_now=100.0,
        wall_now=1784049820.304,
        normalized=snapshot,
    )

    metrics = NormalizerMetrics(version="0.1.0", config=config, cache=cache)
    output = generate_latest(metrics.registry).decode("utf-8")

    assert 'host_asset_info{' in output
    for prefix in (
        "host_cpu_",
        "host_memory_",
        "host_disk_",
        "host_network_",
        "host_filesystem_",
        "host_uptime_seconds",
        "host_os_info",
    ):
        assert prefix not in output
