from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ...normalized import NormalizedSeries

_NIC_LABEL_KEYS = ("nic", "interface", "device", "name", "adapter")


@dataclass(frozen=True)
class _FilesystemKey:
    mount: str
    filesystem: str
    role: str


def _first_family_value(families: dict[str, object], *names: str) -> float | None:
    family = _first_family(families, *names)
    if family is None:
        return None
    return _first_sample_value(family)


def _first_family(families: dict[str, object], *names: str):
    for name in names:
        family = families.get(name)
        if family is not None:
            return family
    return None


def _first_sample_value(family) -> float | None:
    if family is None:
        return None
    samples = getattr(family, "samples", ())
    if not samples:
        return None
    return float(samples[0].value)


def _first_label(family, *keys: str) -> str:
    if family is None:
        return ""
    samples = getattr(family, "samples", ())
    for sample in samples:
        labels = getattr(sample, "labels", {}) or {}
        for key in keys:
            value = labels.get(key)
            if value:
                return str(value)
    return ""


def _normalize_architecture(goarch: str) -> str:
    mapping = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "aarch64",
        "aarch64": "aarch64",
        "386": "x86",
    }
    return mapping.get(goarch, goarch)


def _cpu_usage_percent(family) -> float | None:
    samples = getattr(family, "samples", ())
    if not samples:
        return None
    total = 0.0
    idle = 0.0
    for sample in samples:
        value = float(sample.value)
        total += value
        mode = str((getattr(sample, "labels", {}) or {}).get("mode", "")).lower()
        if mode == "idle":
            idle += value
    if total <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1.0 - idle / total)))


def _distinct_core_count(family) -> int | None:
    cores = {
        str((getattr(sample, "labels", {}) or {}).get("core", ""))
        for sample in getattr(family, "samples", ())
        if (getattr(sample, "labels", {}) or {}).get("core")
    }
    return len(cores) if cores else None


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


def _labeled_series(family, metric_name: str, host: str, label_key: str, *label_source_keys: str) -> list[NormalizedSeries]:
    series: list[NormalizedSeries] = []
    for sample in getattr(family, "samples", ()):
        labels = getattr(sample, "labels", {}) or {}
        label_value = _first_non_empty(labels, *label_source_keys)
        series.append(
            NormalizedSeries.from_mapping(
                metric_name,
                float(sample.value),
                {"host": host, label_key: label_value},
            )
        )
    return series


def _uptime_seconds(boot_family, now: float) -> float | None:
    boot_time = _first_sample_value(boot_family)
    if boot_time is None:
        return None
    return max(0.0, now - boot_time)


def _first_non_empty(labels: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = labels.get(key)
        if value:
            return str(value)
    return ""
