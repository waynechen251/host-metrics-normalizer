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
    # Derived from the number of distinct `core` labels on windows_cpu_time_total,
    # since 0.31.x has no windows_cpu_logical_processor/windows_cs_logical_processors
    # source (confirmed via the official collector docs: no `cs` collector exists).
    assert series["host_cpu_threads_total"].value == pytest.approx(2.0)
    assert series["host_cpu_cores_total"].value == pytest.approx(12.0)
    assert series["host_cpu_sockets_total"].value == pytest.approx(1.0)
    assert series["host_cpu_info"].label_dict() == {
        "host": "srv-app-01",
        "model": "AMD Ryzen 9 5900X 12-Core Processor",
        "architecture": "x86_64",
    }
    assert series["host_memory_bytes_total"].value == pytest.approx(17179869184.0)
    assert series["host_memory_bytes_available"].value == pytest.approx(8589934592.0)
    assert series["host_memory_usage_percent"].value == pytest.approx(50.0)
    assert series["host_memory_swap_bytes_total"].value == pytest.approx(6442450944.0)
    expected_swap_usage = 100.0 * (1.0 - 6025797632.0 / 6442450944.0)
    assert series["host_memory_swap_usage_percent"].value == pytest.approx(expected_swap_usage)
    assert series["host_uptime_seconds"].value == pytest.approx(1234567.0)
    assert series["host_network_receive_bytes_total"].value == pytest.approx(123456.0)
    assert series["host_network_transmit_bytes_total"].value == pytest.approx(654321.0)
    assert series["host_network_receive_errors_total"].value == pytest.approx(2.0)
    assert series["host_network_transmit_errors_total"].value == pytest.approx(1.0)
    assert series["host_network_link_up"].value == pytest.approx(1.0)
    assert series["host_network_speed_bits"].value == pytest.approx(1000000000.0)

    filesystem = series["host_filesystem_size_bytes"]
    assert filesystem.label_dict()["mount"] == "C:"
    # Populated via the windows_logical_disk_info join, since
    # windows_logical_disk_size_bytes/free_bytes themselves carry no filesystem label.
    assert filesystem.label_dict()["filesystem"] == "NTFS"
    assert filesystem.label_dict()["role"] == "system"
    assert series["host_filesystem_usage_percent"].value == pytest.approx(76.5608796737)

    assert series["host_disk_queue_length"].label_dict()["disk"] == "0"
    assert series["host_disk_queue_length"].value == pytest.approx(0.2)
    assert series["host_disk_read_bytes_total"].value == pytest.approx(123456789.0)
    assert series["host_disk_write_bytes_total"].value == pytest.approx(987654321.0)
    assert series["host_disk_reads_total"].value == pytest.approx(4242.0)
    assert series["host_disk_writes_total"].value == pytest.approx(1337.0)

    expected_cpu_usage = 100.0 * (
        1.0
        - (6844.765625 + 6710.78125)
        / (6844.765625 + 279.484375 + 6710.78125 + 413.46875)
    )
    assert series["host_cpu_usage_percent"].value == pytest.approx(expected_cpu_usage)


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
    assert '# TYPE host_disk_read_bytes_total counter' in output
    assert (
        'host_disk_read_bytes_total{disk="0",host="srv-app-01"} 1.23456789e+08'
        in output
    )
