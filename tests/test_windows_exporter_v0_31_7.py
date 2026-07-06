from pathlib import Path

import pytest

from host_metrics_normalizer.config import (
    AppConfig,
    AssetConfig,
    CacheConfig,
    NormalizationConfig,
    ServerConfig,
    SourceExporterConfig,
)
from host_metrics_normalizer.detect import DetectedExporter
from host_metrics_normalizer.normalization import normalize_exporter_metrics

FIXTURES_DIR = Path(__file__).parent / "fixtures"
WINDOWS_0317 = DetectedExporter(type="windows_exporter", os_family="windows", version="0.31.7")


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


def test_windows_exporter_0317_full_fixture_normalizes_expected_metrics():
    # 0.31.6 and 0.31.7's official collector docs are byte-for-byte identical,
    # so this reuses the 0.31.6 fixture; v0_31_7.py itself is a fully independent
    # implementation (not an alias), so it still gets its own complete assertions.
    config = build_config()
    raw = _read_fixture("windows_exporter_0316_full.metrics")

    snapshot = normalize_exporter_metrics(
        config,
        WINDOWS_0317,
        raw,
        now=1784049820.304,
    )

    assert snapshot.status == "ok"
    assert snapshot.supported is True
    assert snapshot.exporter == "windows_exporter"
    assert snapshot.version == "0.31.7"
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

    # GPU metrics are no longer sourced from windows_exporter's `windows_gpu_*`
    # families at all (see gpu/ package) -- confirm none leak through here even
    # though the shared fixture still contains windows_gpu_* sample lines.
    assert "host_gpu_info" not in series
