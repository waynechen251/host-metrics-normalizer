from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass

from ..detect import DetectedExporter
from ..normalized import NormalizedSeries, NormalizedSnapshot, unsupported_snapshot
from ..parser.prometheus_text import family_map

logger = logging.getLogger(__name__)

SUPPORTED_WINDOWS_EXPORTER_VERSIONS = {"0.31.6"}

_CPU_USAGE_LABELS = {"host"}
_CPU_THREADS_LABELS = {"host"}
_MEMORY_TOTAL_LABELS = {"host"}
_MEMORY_AVAILABLE_LABELS = {"host"}
_MEMORY_USAGE_LABELS = {"host"}
_OS_INFO_LABELS = ("host", "os_family", "os_name", "os_version", "kernel_version", "architecture")
_FILESYSTEM_LABELS = ("host", "mount", "filesystem", "role")
_NETWORK_LABELS = ("host", "nic")
_UPTIME_LABELS = ("host",)


@dataclass(frozen=True)
class _FilesystemKey:
    mount: str
    filesystem: str
    role: str


def normalize_windows_exporter(
    raw_text: str,
    detected: DetectedExporter,
    *,
    host: str,
    now: float | None = None,
) -> NormalizedSnapshot:
    if detected.type != "windows_exporter":
        return unsupported_snapshot(
            status="unsupported_exporter",
            exporter=detected.type,
            version=detected.version,
            os_family=detected.os_family,
            host=host,
            notes=("source exporter is not windows_exporter",),
        )

    if detected.version not in SUPPORTED_WINDOWS_EXPORTER_VERSIONS:
        return unsupported_snapshot(
            status="unsupported_version",
            exporter=detected.type,
            version=detected.version,
            os_family=detected.os_family,
            host=host,
            notes=(f"unsupported windows_exporter version: {detected.version or 'unknown'}",),
        )

    try:
        families = family_map(raw_text)
    except Exception:
        logger.exception("Failed to parse windows_exporter exposition")
        return unsupported_snapshot(
            status="parse_error",
            exporter=detected.type,
            version=detected.version,
            os_family=detected.os_family,
            host=host,
            notes=("failed to parse windows_exporter exposition",),
        )

    series: list[NormalizedSeries] = []
    missing: list[str] = []
    notes: list[str] = []
    parsed_metric_names = tuple(sorted(families))

    build_info = families.get("windows_exporter_build_info")
    architecture = _normalize_architecture(_first_label(build_info, "goarch")) if build_info else ""

    os_info = families.get("windows_os_info")
    os_name = _first_label(os_info, "product", "caption", "name") if os_info else ""
    os_version = _first_label(os_info, "version", "build_number", "major_version") if os_info else ""
    kernel_version = _first_label(
        os_info, "version", "build_number", "major_version", "minor_version"
    ) if os_info else ""
    series.append(
        NormalizedSeries.from_mapping(
            "host_os_info",
            1.0,
            {
                "host": host,
                "os_family": "windows",
                "os_name": os_name,
                "os_version": os_version,
                "kernel_version": kernel_version,
                "architecture": architecture,
            },
        )
    )
    if os_info is None:
        missing.append("windows_os_info")

    cpu_family = _first_family(families, "windows_cpu_time_total", "windows_cpu_time")
    if cpu_family is None:
        missing.append("windows_cpu_time_total")
    else:
        cpu_usage = _cpu_usage_percent(cpu_family)
        if cpu_usage is not None:
            series.append(
                NormalizedSeries.from_mapping(
                    "host_cpu_usage_percent",
                    cpu_usage,
                    {"host": host},
                )
            )
        else:
            missing.append("windows_cpu_time_total")

    threads = _first_sample_value(families.get("windows_cs_logical_processors"))
    if threads is None:
        missing.append("windows_cs_logical_processors")
    else:
        series.append(
            NormalizedSeries.from_mapping(
                "host_cpu_threads_total",
                threads,
                {"host": host},
            )
        )

    memory_total = _first_family_value(
        families,
        "windows_memory_physical_total_bytes",
        "windows_cs_physical_memory_bytes",
    )
    memory_available = _first_family_value(
        families,
        "windows_memory_physical_available_bytes",
        "windows_memory_physical_free_bytes",
        "windows_memory_available_bytes",
    )
    if memory_total is None:
        missing.append("windows_memory_physical_total_bytes")
    else:
        series.append(
            NormalizedSeries.from_mapping(
                "host_memory_bytes_total",
                memory_total,
                {"host": host},
            )
        )
    if memory_available is None:
        missing.append("windows_memory_physical_available_bytes")
    else:
        series.append(
            NormalizedSeries.from_mapping(
                "host_memory_bytes_available",
                memory_available,
                {"host": host},
            )
        )
    if memory_total is not None and memory_available is not None and memory_total > 0:
        usage_percent = max(0.0, min(100.0, 100.0 * (1.0 - memory_available / memory_total)))
        series.append(
            NormalizedSeries.from_mapping(
                "host_memory_usage_percent",
                usage_percent,
                {"host": host},
            )
        )

    filesystem_size_family = families.get("windows_logical_disk_size_bytes")
    filesystem_free_family = families.get("windows_logical_disk_free_bytes")
    if filesystem_size_family is None:
        missing.append("windows_logical_disk_size_bytes")
    if filesystem_free_family is None:
        missing.append("windows_logical_disk_free_bytes")
    if filesystem_size_family is not None or filesystem_free_family is not None:
        filesystem_metrics = _filesystem_metrics(
            filesystem_size_family,
            filesystem_free_family,
            host,
        )
        series.extend(filesystem_metrics)

    network_rx_family = _first_family(
        families,
        "windows_net_bytes_received_total",
        "windows_net_bytes_received",
    )
    network_tx_family = _first_family(
        families,
        "windows_net_bytes_sent_total",
        "windows_net_bytes_sent",
    )
    if network_rx_family is None:
        missing.append("windows_net_bytes_received_total")
    else:
        series.extend(_network_series(network_rx_family, "host_network_receive_bytes_total", host))
    if network_tx_family is None:
        missing.append("windows_net_bytes_sent_total")
    else:
        series.extend(_network_series(network_tx_family, "host_network_transmit_bytes_total", host))

    uptime = _uptime_seconds(
        families.get("windows_system_boot_time_timestamp"),
        families.get("windows_system_system_up_time"),
        now if now is not None else time.time(),
    )
    if uptime is None:
        missing.append("windows_system_boot_time_timestamp")
    else:
        series.append(
            NormalizedSeries.from_mapping(
                "host_uptime_seconds",
                uptime,
                {"host": host},
            )
        )

    return NormalizedSnapshot(
        status="ok",
        supported=True,
        exporter=detected.type,
        version=detected.version,
        os_family=detected.os_family,
        host=host,
        series=tuple(series),
        missing_metrics=tuple(dict.fromkeys(missing)),
        notes=tuple(notes),
        parsed_metric_names=parsed_metric_names,
    )


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


def _filesystem_metrics(size_family, free_family, host: str) -> list[NormalizedSeries]:
    entries: dict[_FilesystemKey, dict[str, float | str]] = defaultdict(dict)

    for sample in getattr(size_family, "samples", ()) if size_family is not None else ():
        key = _filesystem_key(sample)
        entries[key]["size"] = float(sample.value)

    for sample in getattr(free_family, "samples", ()) if free_family is not None else ():
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


def _filesystem_key(sample) -> _FilesystemKey:
    labels = getattr(sample, "labels", {}) or {}
    mount = _first_non_empty(labels, "mount", "volume", "device", "name", "path")
    filesystem = _first_non_empty(labels, "filesystem", "fstype", "fs_type")
    role = _first_non_empty(labels, "role")
    if not role and mount in {"C:", "/"}:
        role = "system"
    return _FilesystemKey(mount=mount, filesystem=filesystem, role=role)


def _network_series(family, metric_name: str, host: str) -> list[NormalizedSeries]:
    series: list[NormalizedSeries] = []
    for sample in getattr(family, "samples", ()):
        labels = getattr(sample, "labels", {}) or {}
        nic = _first_non_empty(labels, "nic", "interface", "device", "name", "adapter")
        series.append(
            NormalizedSeries.from_mapping(
                metric_name,
                float(sample.value),
                {"host": host, "nic": nic},
            )
        )
    return series


def _uptime_seconds(boot_family, uptime_family, now: float) -> float | None:
    if uptime_family is not None:
        uptime = _first_sample_value(uptime_family)
        if uptime is not None:
            return uptime
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
