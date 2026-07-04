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
    "_gpu_phys_map",
    "_gpu_memory_metrics",
    "_gpu_engine_seconds",
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


def _gpu_phys_map(info_family) -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    for sample in getattr(info_family, "samples", ()):
        labels = getattr(sample, "labels", {}) or {}
        phys = labels.get("phys", "")
        if phys:
            mapping[(labels.get("device_id", ""), labels.get("luid", ""))] = phys
    return mapping


def _gpu_memory_metrics(
    total_family,
    used_family,
    gpu_phys_map: dict[tuple[str, str], str],
    host: str,
) -> list[NormalizedSeries]:
    entries: dict[str, dict[str, float]] = defaultdict(dict)

    for sample in getattr(total_family, "samples", ()) if total_family is not None else ():
        labels = getattr(sample, "labels", {}) or {}
        # windows_gpu_dedicated_video_memory_size_bytes has no `phys` label, so it
        # needs to be resolved through windows_gpu_info's (device_id, luid) -> phys map.
        gpu = gpu_phys_map.get((labels.get("device_id", ""), labels.get("luid", "")), "")
        if gpu:
            entries[gpu]["total"] = float(sample.value)

    for sample in getattr(used_family, "samples", ()) if used_family is not None else ():
        labels = getattr(sample, "labels", {}) or {}
        gpu = labels.get("phys", "")
        if gpu:
            entries[gpu]["used"] = float(sample.value)

    series: list[NormalizedSeries] = []
    for gpu, values in sorted(entries.items()):
        labels = {"host": host, "gpu": gpu}
        total = values.get("total")
        used = values.get("used")
        if total is not None:
            series.append(NormalizedSeries.from_mapping("host_gpu_memory_total_bytes", total, labels))
        if used is not None:
            series.append(NormalizedSeries.from_mapping("host_gpu_memory_used_bytes", used, labels))
        if total is not None and used is not None and total > 0:
            usage = max(0.0, min(100.0, 100.0 * (used / total)))
            series.append(NormalizedSeries.from_mapping("host_gpu_memory_usage_percent", usage, labels))
    return series


def _gpu_engine_seconds(engine_family, host: str) -> list[NormalizedSeries]:
    totals: dict[tuple[str, str], float] = defaultdict(float)
    for sample in getattr(engine_family, "samples", ()):
        labels = getattr(sample, "labels", {}) or {}
        gpu = labels.get("phys", "")
        engtype = labels.get("engtype", "")
        # Sums across `process_id` and `eng` (per-engine-instance index): the host
        # schema only tracks device-level busy time, not per-process/per-instance detail.
        totals[(gpu, engtype)] += float(sample.value)

    return [
        NormalizedSeries.from_mapping(
            "host_gpu_engine_seconds_total", value, {"host": host, "gpu": gpu, "engtype": engtype}
        )
        for (gpu, engtype), value in sorted(totals.items())
    ]
