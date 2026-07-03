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
WINDOWS_0306 = DetectedExporter(type="windows_exporter", os_family="windows", version="0.30.6")


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


def test_windows_exporter_0306_full_fixture_normalizes_expected_metrics():
    config = build_config()
    raw = _read_fixture("windows_exporter_0306_full.metrics")

    snapshot = normalize_exporter_metrics(
        config,
        WINDOWS_0306,
        raw,
        now=1784049820.304,
    )

    assert snapshot.status == "ok"
    assert snapshot.supported is True
    assert snapshot.version == "0.30.6"
    # cpu_info (non-default collector), pagefile and nic_operation_status were not
    # emitted on the real machine this fixture was captured from.
    assert snapshot.missing_metrics == (
        "windows_cpu_info_core",
        "windows_cpu_info",
        "windows_pagefile_limit_bytes",
        "windows_pagefile_free_bytes",
        "windows_net_nic_operation_status",
    )

    series = {series.name: series for series in snapshot.series}

    assert series["host_os_info"].label_dict() == {
        "host": "srv-app-01",
        "os_family": "windows",
        "os_name": "Windows 11 Pro",
        "os_version": "10.0.26200",
        "kernel_version": "10.0.26200",
        "architecture": "x86_64",
    }
    # Resolved directly from windows_cpu_logical_processor (the deprecation
    # replacement for windows_cs_logical_processors), both present on 0.30.6.
    assert series["host_cpu_threads_total"].value == pytest.approx(6.0)
    assert "host_cpu_cores_total" not in series
    assert "host_cpu_info" not in series
    assert "host_memory_swap_bytes_total" not in series
    assert "host_network_link_up" not in series

    assert series["host_memory_bytes_total"].value == pytest.approx(25634922496.0)
    assert series["host_memory_bytes_available"].value == pytest.approx(5048688640.0)
    expected_memory_usage = 100.0 * (1.0 - 5048688640.0 / 25634922496.0)
    assert series["host_memory_usage_percent"].value == pytest.approx(expected_memory_usage)

    filesystem = series["host_filesystem_size_bytes"]
    assert filesystem.label_dict()["mount"] == "C:"
    assert filesystem.label_dict()["filesystem"] == "NTFS"
    assert filesystem.label_dict()["role"] == "system"
    expected_fs_usage = 100.0 * (1.0 - 246939648000.0 / 499116933120.0)
    assert series["host_filesystem_usage_percent"].value == pytest.approx(expected_fs_usage)

    assert series["host_disk_read_bytes_total"].value == pytest.approx(6476520609280.0)
    assert series["host_disk_write_bytes_total"].value == pytest.approx(494122797056.0)
    assert series["host_disk_reads_total"].value == pytest.approx(77696116.0)
    assert series["host_disk_writes_total"].value == pytest.approx(13734561.0)

    nic = "Realtek PCIe GbE Family Controller"
    assert series["host_network_receive_bytes_total"].label_dict()["nic"] == nic
    assert series["host_network_receive_bytes_total"].value == pytest.approx(159561982830.0)
    assert series["host_network_transmit_bytes_total"].value == pytest.approx(153019617955.0)
    assert series["host_network_receive_errors_total"].value == pytest.approx(0.0)
    assert series["host_network_transmit_errors_total"].value == pytest.approx(0.0)
    assert series["host_network_speed_bits"].value == pytest.approx(1000000000.0)

    assert series["host_uptime_seconds"].value == pytest.approx(2458857.304)

    idle = 1.23692609375e06 + 1.0280035e06 + 1.180519671875e06
    dpc = 10881.90625 + 3504.9375 + 2747.4375
    interrupt = 14262.859375 + 6716.984375 + 5567.46875
    privileged = 129788.65625 + 210831.53125 + 140119.3125
    user = 101636.046875 + 229515.734375 + 147711.78125
    total = idle + dpc + interrupt + privileged + user
    expected_cpu_usage = 100.0 * (1.0 - idle / total)
    assert series["host_cpu_usage_percent"].value == pytest.approx(expected_cpu_usage)
