from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ...normalized import NormalizedSeries
from .._prometheus_helpers import (
    _cpu_usage_percent,
    _distinct_label_count,
    _first_family,
    _first_family_value,
    _first_label,
    _first_non_empty,
    _first_sample_value,
    _labeled_series,
    _normalize_architecture,
    _uptime_seconds,
)

__all__ = [
    "_cpu_usage_percent",
    "_distinct_label_count",
    "_first_family",
    "_first_family_value",
    "_first_label",
    "_first_non_empty",
    "_first_sample_value",
    "_labeled_series",
    "_normalize_architecture",
    "_uptime_seconds",
    "_DEVICE_LABEL_KEYS",
    "_filesystem_metrics",
    "_cpu_info_core_socket_counts",
]

_DEVICE_LABEL_KEYS = ("device",)


@dataclass(frozen=True)
class _FilesystemKey:
    mount: str
    filesystem: str
    role: str


def _filesystem_key(sample) -> _FilesystemKey:
    labels = getattr(sample, "labels", {}) or {}
    mount = _first_non_empty(labels, "mountpoint")
    filesystem = _first_non_empty(labels, "fstype")
    role = "system" if mount == "/" else ""
    return _FilesystemKey(mount=mount, filesystem=filesystem, role=role)


def _filesystem_metrics(size_family, avail_family, host: str) -> list[NormalizedSeries]:
    # node_filesystem_size_bytes/avail_bytes already carry `fstype` directly on each
    # sample, unlike windows_exporter's logical_disk_size_bytes/free_bytes (which need
    # a join against a separate *_info family) — so no lookup table is needed here.
    entries: dict[_FilesystemKey, dict[str, float]] = defaultdict(dict)

    for sample in getattr(size_family, "samples", ()) if size_family is not None else ():
        key = _filesystem_key(sample)
        entries[key]["size"] = float(sample.value)

    for sample in getattr(avail_family, "samples", ()) if avail_family is not None else ():
        key = _filesystem_key(sample)
        entries[key]["free"] = float(sample.value)

    series: list[NormalizedSeries] = []
    for key, values in sorted(
        entries.items(),
        key=lambda item: (item[0].mount, item[0].filesystem, item[0].role),
    ):
        labels = {
            "host": host,
            "mount": key.mount,
            "filesystem": key.filesystem,
            "role": key.role,
        }
        size = values.get("size")
        free = values.get("free")
        if size is not None:
            series.append(
                NormalizedSeries.from_mapping("host_filesystem_size_bytes", float(size), labels)
            )
        if free is not None:
            series.append(
                NormalizedSeries.from_mapping("host_filesystem_free_bytes", float(free), labels)
            )
        if size is not None and free is not None and float(size) > 0:
            usage = max(0.0, min(100.0, 100.0 * (1.0 - float(free) / float(size))))
            series.append(
                NormalizedSeries.from_mapping("host_filesystem_usage_percent", usage, labels)
            )
    return series


def _cpu_info_core_socket_counts(family) -> tuple[float | None, float | None]:
    cores: set[tuple[str, str]] = set()
    sockets: set[str] = set()
    for sample in getattr(family, "samples", ()):
        labels = getattr(sample, "labels", {}) or {}
        package = labels.get("package")
        core = labels.get("core")
        if package:
            sockets.add(package)
            if core:
                cores.add((package, core))
    cores_total = float(len(cores)) if cores else None
    sockets_total = float(len(sockets)) if sockets else None
    return cores_total, sockets_total
