from __future__ import annotations

import socket
from typing import Iterable

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from .cache import RawMetricsCache
from .config import AppConfig
from .normalized import NormalizedSeries

_INFO_METRIC_HELP = {
    "host_asset_info": "Static host asset metadata",
    "host_os_info": "Detected host operating system information",
}

_METRIC_HELP = {
    "host_cpu_usage_percent": "Normalized host CPU usage percentage",
    "host_cpu_threads_total": "Normalized host logical CPU threads total",
    "host_memory_bytes_total": "Normalized host physical memory total in bytes",
    "host_memory_bytes_available": "Normalized host physical memory available in bytes",
    "host_memory_usage_percent": "Normalized host memory usage percentage",
    "host_filesystem_size_bytes": "Normalized host filesystem size in bytes",
    "host_filesystem_free_bytes": "Normalized host filesystem free bytes",
    "host_filesystem_usage_percent": "Normalized host filesystem usage percentage",
    "host_network_receive_bytes_total": "Normalized host network receive bytes total",
    "host_network_transmit_bytes_total": "Normalized host network transmit bytes total",
    "host_uptime_seconds": "Normalized host uptime in seconds",
}

_COUNTER_METRICS = {
    "host_network_receive_bytes_total",
    "host_network_transmit_bytes_total",
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

        grouped: dict[str, list[NormalizedSeries]] = {}
        for series in normalized.series:
            grouped.setdefault(series.name, []).append(series)

        for metric_name in sorted(grouped):
            series_list = grouped[metric_name]
            label_names = _merge_label_names(series_list)
            family_cls = CounterMetricFamily if metric_name in _COUNTER_METRICS else GaugeMetricFamily
            family = family_cls(
                metric_name,
                _METRIC_HELP.get(metric_name, metric_name.replace("_", " ")),
                labels=list(label_names),
            )
            for series in series_list:
                label_values = [series.label_dict().get(label_name, "") for label_name in label_names]
                family.add_metric(label_values, series.value)
            yield family

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
