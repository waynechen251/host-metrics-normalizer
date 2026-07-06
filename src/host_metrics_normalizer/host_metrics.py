from __future__ import annotations

import socket
from typing import Iterable, Iterator

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from .cache import RawMetricsCache
from .config import AppConfig
from .normalized import NormalizedSeries

_INFO_METRIC_HELP = {
    "host_asset_info": "Static host asset metadata",
}

_METRIC_HELP = {
    "host_os_info": "Detected host operating system information",
    "host_cpu_usage_percent": "Normalized host CPU usage percentage",
    "host_cpu_threads_total": "Normalized host logical CPU threads total",
    "host_cpu_cores_total": "Normalized host physical CPU cores total",
    "host_cpu_sockets_total": "Normalized host CPU sockets total",
    "host_cpu_info": "Normalized host CPU model information",
    "host_memory_bytes_total": "Normalized host physical memory total in bytes",
    "host_memory_bytes_available": "Normalized host physical memory available in bytes",
    "host_memory_usage_percent": "Normalized host memory usage percentage",
    "host_memory_swap_bytes_total": "Normalized host swap/pagefile total in bytes",
    "host_memory_swap_usage_percent": "Normalized host swap/pagefile usage percentage",
    "host_filesystem_size_bytes": "Normalized host filesystem size in bytes",
    "host_filesystem_free_bytes": "Normalized host filesystem free bytes",
    "host_filesystem_usage_percent": "Normalized host filesystem usage percentage",
    "host_disk_queue_length": "Normalized host physical disk queue length",
    "host_disk_read_bytes_total": "Normalized host physical disk read bytes total",
    "host_disk_write_bytes_total": "Normalized host physical disk write bytes total",
    "host_disk_reads_total": "Normalized host physical disk read operations total",
    "host_disk_writes_total": "Normalized host physical disk write operations total",
    "host_network_receive_bytes_total": "Normalized host network receive bytes total",
    "host_network_transmit_bytes_total": "Normalized host network transmit bytes total",
    "host_network_receive_errors_total": "Normalized host network receive errors total",
    "host_network_transmit_errors_total": "Normalized host network transmit errors total",
    "host_network_link_up": "Normalized host network interface link status",
    "host_network_speed_bits": "Normalized host network interface speed in bits per second",
    "host_uptime_seconds": "Normalized host uptime in seconds",
    "host_gpu_info": "Normalized GPU device information",
    "host_gpu_memory_total_bytes": "Normalized host GPU dedicated video memory total in bytes",
    "host_gpu_memory_used_bytes": "Normalized host GPU dedicated memory usage in bytes",
    "host_gpu_memory_usage_percent": "Normalized host GPU memory usage percentage",
    "host_gpu_utilization_percent": "Normalized host GPU utilization percentage",
    "host_gpu_temperature_celsius": "Normalized host GPU temperature in degrees Celsius (Linux only)",
}

_COUNTER_METRICS = {
    "host_disk_read_bytes_total",
    "host_disk_write_bytes_total",
    "host_disk_reads_total",
    "host_disk_writes_total",
    "host_network_receive_bytes_total",
    "host_network_transmit_bytes_total",
    "host_network_receive_errors_total",
    "host_network_transmit_errors_total",
}

_ASSET_LABELS = (
    "host",
    "asset_id",
    "display_name",
    "owner",
    "environment",
    "location",
    "role",
    "criticality",
    "managed_by",
)


class HostMetricsCollector:
    def __init__(self, config: AppConfig, cache: RawMetricsCache):
        self._config = config
        self._cache = cache

    def collect(self):
        snapshot = self._cache.get()
        host = snapshot.normalized.host if snapshot.normalized is not None else _resolve_host(self._config)

        yield self._asset_family(host)

        normalized = snapshot.normalized
        if normalized is None or not normalized.series:
            return

        yield from build_metric_families(normalized.series)

    def _asset_family(self, host: str) -> GaugeMetricFamily:
        asset = self._config.asset
        family = GaugeMetricFamily("host_asset_info", _INFO_METRIC_HELP["host_asset_info"], labels=list(_ASSET_LABELS))
        family.add_metric(
            [
                host,
                asset.asset_id,
                asset.display_name,
                asset.owner,
                asset.environment,
                asset.location,
                asset.role,
                asset.criticality,
                asset.managed_by,
            ],
            1.0,
        )
        return family


def build_metric_families(
    series: Iterable[NormalizedSeries],
) -> Iterator[GaugeMetricFamily | CounterMetricFamily]:
    grouped: dict[str, list[NormalizedSeries]] = {}
    for item in series:
        grouped.setdefault(item.name, []).append(item)

    for metric_name in sorted(grouped):
        series_list = grouped[metric_name]
        label_names = _merge_label_names(series_list)
        family_cls = CounterMetricFamily if metric_name in _COUNTER_METRICS else GaugeMetricFamily
        family = family_cls(
            metric_name,
            _METRIC_HELP.get(metric_name, metric_name.replace("_", " ")),
            labels=list(label_names),
        )
        for item in series_list:
            label_values = [item.label_dict().get(label_name, "") for label_name in label_names]
            family.add_metric(label_values, item.value)
        yield family


def _merge_label_names(series_list: Iterable[NormalizedSeries]) -> tuple[str, ...]:
    label_names: list[str] = []
    seen: set[str] = set()
    for series in series_list:
        for label_name in series.label_names():
            if label_name not in seen:
                seen.add(label_name)
                label_names.append(label_name)
    return tuple(label_names)


def _resolve_host(config: AppConfig) -> str:
    if config.asset.hostname:
        return config.asset.hostname
    return socket.gethostname()
