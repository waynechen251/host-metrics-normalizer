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
NODE_1_10_2 = DetectedExporter(type="node_exporter", os_family="linux", version="1.10.2")


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def build_config() -> AppConfig:
    return AppConfig(
        server=ServerConfig(),
        source_exporter=SourceExporterConfig(endpoint="http://127.0.0.1:9100/metrics"),
        cache=CacheConfig(),
        asset=AssetConfig(
            asset_id="ASSET-002",
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


def test_node_exporter_1_10_2_full_fixture_normalizes_expected_metrics():
    config = build_config()
    raw = _read_fixture("node_exporter_1_10_2_full.metrics")

    snapshot = normalize_exporter_metrics(
        config,
        NODE_1_10_2,
        raw,
        now=1418788076.0,
    )

    assert snapshot.status == "ok"
    assert snapshot.supported is True
    assert snapshot.exporter == "node_exporter"
    assert snapshot.version == "1.10.2"
    assert snapshot.os_family == "linux"
    assert snapshot.host == "srv-app-01"
    assert snapshot.missing_metrics == ()

    series = {series.name: series for series in snapshot.series}

    assert series["host_os_info"].label_dict() == {
        "host": "srv-app-01",
        "os_family": "linux",
        "os_name": "Ubuntu 22.04.3 LTS",
        "os_version": "22.04",
        "kernel_version": "5.15.0-91-generic",
        "architecture": "x86_64",
    }

    # Derived from the number of distinct `cpu` labels on node_cpu_seconds_total
    # (the `cpu` collector is enabled by default, unlike windows_exporter which
    # sometimes needs a multi-tier fallback).
    assert series["host_cpu_threads_total"].value == pytest.approx(2.0)
    # node_cpu_info shows cpu=0,4 sharing core=0 and cpu=1,5 sharing core=1, all on
    # package=0 -> 2 distinct (package,core) pairs, 1 distinct package.
    assert series["host_cpu_cores_total"].value == pytest.approx(2.0)
    assert series["host_cpu_sockets_total"].value == pytest.approx(1.0)
    assert series["host_cpu_info"].label_dict() == {
        "host": "srv-app-01",
        "model": "Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz",
        "architecture": "x86_64",
    }

    assert series["host_memory_bytes_total"].value == pytest.approx(3831959552.0)
    assert series["host_memory_bytes_available"].value == pytest.approx(1500000000.0)
    expected_memory_usage = 100.0 * (1.0 - 1500000000.0 / 3831959552.0)
    assert series["host_memory_usage_percent"].value == pytest.approx(expected_memory_usage)

    assert series["host_memory_swap_bytes_total"].value == pytest.approx(4294963200.0)
    expected_swap_usage = 100.0 * (1.0 - 3231088640.0 / 4294963200.0)
    assert series["host_memory_swap_usage_percent"].value == pytest.approx(expected_swap_usage)

    filesystem = series["host_filesystem_size_bytes"]
    assert filesystem.label_dict() == {
        "host": "srv-app-01",
        "mount": "/",
        "filesystem": "ext4",
        "role": "system",
    }
    assert filesystem.value == pytest.approx(53687091200.0)
    assert series["host_filesystem_free_bytes"].value == pytest.approx(21474836480.0)
    assert series["host_filesystem_usage_percent"].value == pytest.approx(60.0)

    assert series["host_disk_queue_length"].label_dict()["disk"] == "sda"
    assert series["host_disk_queue_length"].value == pytest.approx(0.0)
    assert series["host_disk_read_bytes_total"].value == pytest.approx(513713216512.0)
    assert series["host_disk_write_bytes_total"].value == pytest.approx(258916880384.0)
    assert series["host_disk_reads_total"].value == pytest.approx(25354637.0)
    assert series["host_disk_writes_total"].value == pytest.approx(28444756.0)

    assert series["host_network_receive_bytes_total"].label_dict()["nic"] == "eth0"
    assert series["host_network_receive_bytes_total"].value == pytest.approx(987654321.0)
    assert series["host_network_transmit_bytes_total"].value == pytest.approx(123456789.0)
    assert series["host_network_receive_errors_total"].value == pytest.approx(1.0)
    assert series["host_network_transmit_errors_total"].value == pytest.approx(0.0)
    assert series["host_network_link_up"].value == pytest.approx(1.0)
    assert series["host_network_speed_bits"].value == pytest.approx(1000000000.0)

    # node_network_speed_bytes{device="docker0"} is -125000 in the fixture, mirroring
    # the kernel's -1 (unknown/no negotiated speed) sysfs sentinel for bridges/down
    # interfaces observed on a real host — must not surface as a negative bits/sec value.
    speed_series = [s for s in snapshot.series if s.name == "host_network_speed_bits"]
    assert {s.label_dict()["nic"] for s in speed_series} == {"eth0"}

    assert series["host_uptime_seconds"].value == pytest.approx(604800.0)

    idle = 10870.69 + 11107.87
    total = (
        10870.69 + 2.2 + 0.01 + 0.19 + 34.1 + 0 + 210.45 + 444.9
        + 11107.87 + 5.91 + 0 + 0.23 + 0.46 + 0 + 164.74 + 478.69
    )
    expected_cpu_usage = 100.0 * (1.0 - idle / total)
    assert series["host_cpu_usage_percent"].value == pytest.approx(expected_cpu_usage)


def test_host_metrics_collector_emits_asset_and_normalized_series():
    config = build_config()
    cache = RawMetricsCache()
    raw = _read_fixture("node_exporter_1_10_2_full.metrics")
    snapshot = normalize_exporter_metrics(
        config,
        NODE_1_10_2,
        raw,
        now=1418788076.0,
    )
    cache.update_success(
        raw_text=raw,
        detected=NODE_1_10_2,
        duration=0.05,
        monotonic_now=100.0,
        wall_now=1418788076.0,
        normalized=snapshot,
    )

    metrics = NormalizerMetrics(version="0.1.0", config=config, cache=cache)
    output = generate_latest(metrics.registry).decode("utf-8")

    assert (
        'host_os_info{architecture="x86_64",host="srv-app-01",kernel_version="5.15.0-91-generic",'
        'os_family="linux",os_name="Ubuntu 22.04.3 LTS",os_version="22.04"} 1.0'
        in output
    )
    assert (
        'host_network_receive_bytes_total{host="srv-app-01",nic="eth0"} 9.87654321e+08'
        in output
    )
    assert '# TYPE host_network_receive_bytes_total counter' in output
    assert '# TYPE host_disk_read_bytes_total counter' in output
