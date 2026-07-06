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
    "_distinct_core_count",
    "_first_family",
    "_first_family_value",
    "_first_label",
    "_first_non_empty",
    "_first_sample_value",
    "_labeled_series",
    "_normalize_architecture",
    "_uptime_seconds",
    "_NIC_LABEL_KEYS",
    "_FilesystemKey",
    "_logical_disk_filesystem_map",
    "_filesystem_metrics",
    "_filesystem_key",
]

_NIC_LABEL_KEYS = ("nic", "interface", "device", "name", "adapter")


def _distinct_core_count(family) -> int | None:
    return _distinct_label_count(family, "core")


@dataclass(frozen=True)
class _FilesystemKey:
    mount: str
    filesystem: str
    role: str


def _logical_disk_filesystem_map(info_family) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for sample in getattr(info_family, "samples", ()):
        labels = getattr(sample, "labels", {}) or {}
        volume = _first_non_empty(labels, "volume")
        filesystem = _first_non_empty(labels, "filesystem")
        if volume and filesystem:
            mapping[volume] = filesystem
    return mapping


def _filesystem_metrics(
    size_family,
    free_family,
    host: str,
    filesystem_by_volume: dict[str, str],
) -> list[NormalizedSeries]:
    entries: dict[_FilesystemKey, dict[str, float | str]] = defaultdict(dict)

    for sample in getattr(size_family, "samples", ()) if size_family is not None else ():
        key = _filesystem_key(sample, filesystem_by_volume)
        entries[key]["size"] = float(sample.value)

    for sample in getattr(free_family, "samples", ()) if free_family is not None else ():
        key = _filesystem_key(sample, filesystem_by_volume)
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


def _filesystem_key(sample, filesystem_by_volume: dict[str, str]) -> _FilesystemKey:
    labels = getattr(sample, "labels", {}) or {}
    mount = _first_non_empty(labels, "mount", "volume", "device", "name", "path")
    filesystem = _first_non_empty(labels, "filesystem", "fstype", "fs_type") or filesystem_by_volume.get(mount, "")
    role = _first_non_empty(labels, "role")
    if not role and mount in {"C:", "/"}:
        role = "system"
    return _FilesystemKey(mount=mount, filesystem=filesystem, role=role)
