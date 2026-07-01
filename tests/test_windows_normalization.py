from pathlib import Path

import pytest
from prometheus_client import generate_latest

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
from host_metrics_normalizer.normalization import normalize_exporter_metrics

FIXTURES_DIR = Path(__file__).parent / "fixtures"
WINDOWS_0316 = DetectedExporter(type="windows_exporter", os_family="windows", version="0.31.6")


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
    )


def test_windows_exporter_0316_full_fixture_normalizes_expected_metrics():
    config = build_config()
    raw = _read_fixture("windows_exporter_0316_full.metrics")

    snapshot = normalize_exporter_metrics(
        config,
        WINDOWS_0316,
        raw,
        now=1784049820.304,
    )

    assert snapshot.status == "ok"
    assert snapshot.supported is True
    assert snapshot.exporter == "windows_exporter"
    assert snapshot.version == "0.31.6"
    assert snapshot.os_family == "windows"
    assert snapshot.host == "srv-app-01"
    assert snapshot.missing_metrics == ()

    series = {series.name: series for series in snapshot.series}

    assert series["host_os_info"].label_dict() == {
        "host": "srv-app-01",
        "os_family": "windows",
        "os_name": "Windows 10 Pro",
        "os_version": "10.0.19045",
        "kernel_version": "10.0.19045",
        "architecture": "x86_64",
    }
    assert series["host_cpu_threads_total"].value == pytest.approx(28.0)
    assert series["host_memory_bytes_total"].value == pytest.approx(17179869184.0)
    assert series["host_memory_bytes_available"].value == pytest.approx(8589934592.0)
    assert series["host_memory_usage_percent"].value == pytest.approx(50.0)
    assert series["host_uptime_seconds"].value == pytest.approx(1234567.0)
    assert series["host_network_receive_bytes_total"].value == pytest.approx(123456.0)
    assert series["host_network_transmit_bytes_total"].value == pytest.approx(654321.0)

    filesystem = series["host_filesystem_size_bytes"]
    assert filesystem.label_dict()["mount"] == "C:"
    assert filesystem.label_dict()["filesystem"] == "NTFS"
    assert filesystem.label_dict()["role"] == "system"
    assert series["host_filesystem_usage_percent"].value == pytest.approx(76.5608796737)

    expected_cpu_usage = 100.0 * (
        1.0
        - (6844.765625 + 6710.78125)
        / (6844.765625 + 279.484375 + 6710.78125 + 413.46875)
    )
    assert series["host_cpu_usage_percent"].value == pytest.approx(expected_cpu_usage)


def test_unsupported_windows_version_returns_unsupported_snapshot():
    config = build_config()
    raw = _read_fixture("windows_exporter_0316_full.metrics")
    detected = DetectedExporter(type="windows_exporter", os_family="windows", version="0.31.7")

    snapshot = normalize_exporter_metrics(config, detected, raw, now=1784049820.304)

    assert snapshot.status == "unsupported_version"
    assert snapshot.supported is False
    assert snapshot.series == ()


def test_host_metrics_collector_emits_asset_and_normalized_series():
    config = build_config()
    cache = RawMetricsCache()
    raw = _read_fixture("windows_exporter_0316_full.metrics")
    snapshot = normalize_exporter_metrics(
        config,
        WINDOWS_0316,
        raw,
        now=1784049820.304,
    )
    cache.update_success(
        raw_text=raw,
        detected=WINDOWS_0316,
        duration=0.05,
        monotonic_now=100.0,
        wall_now=1784049820.304,
        normalized=snapshot,
    )

    metrics = NormalizerMetrics(version="0.1.0", config=config, cache=cache)
    output = generate_latest(metrics.registry).decode("utf-8")

    assert (
        'host_asset_info{asset_id="ASSET-001",criticality="medium",display_name="App Server 01",'
        'environment="prod",host="srv-app-01",location="office-3f",managed_by="wayne",'
        'owner="infra",role="app-server"} 1.0' in output
    )
    assert (
        'host_os_info{architecture="x86_64",host="srv-app-01",kernel_version="10.0.19045",'
        'os_family="windows",os_name="Windows 10 Pro",os_version="10.0.19045"} 1.0'
        in output
    )
    assert 'host_memory_usage_percent{host="srv-app-01"} 50.0' in output
    assert (
        'host_network_receive_bytes_total{host="srv-app-01",nic="Ethernet"} 123456.0'
        in output
    )
    assert '# TYPE host_network_receive_bytes_total counter' in output
