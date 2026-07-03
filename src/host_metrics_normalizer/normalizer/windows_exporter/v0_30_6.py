from __future__ import annotations

import time

from ...detect import DetectedExporter
from ...normalized import NormalizedSeries, NormalizedSnapshot
from .common import (
    _NIC_LABEL_KEYS,
    _cpu_usage_percent,
    _distinct_core_count,
    _filesystem_metrics,
    _first_family,
    _first_family_value,
    _first_label,
    _first_non_empty,
    _labeled_series,
    _logical_disk_filesystem_map,
    _normalize_architecture,
    _uptime_seconds,
)


def normalize(
    families: dict[str, object],
    detected: DetectedExporter,
    *,
    host: str,
    now: float | None = None,
) -> NormalizedSnapshot:
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
                NormalizedSeries.from_mapping("host_cpu_usage_percent", cpu_usage, {"host": host})
            )
        else:
            missing.append("windows_cpu_time_total")

    # 0.30.6 still ships the deprecated `cs` collector alongside its replacement
    # `windows_cpu_logical_processor` (confirmed on a live 0.30.6 instance).
    threads = _first_family_value(
        families, "windows_cpu_logical_processor", "windows_cs_logical_processors"
    )
    if threads is None and cpu_family is not None:
        core_count = _distinct_core_count(cpu_family)
        threads = float(core_count) if core_count is not None else None
    if threads is None:
        missing.append("windows_cpu_logical_processor")
    else:
        series.append(NormalizedSeries.from_mapping("host_cpu_threads_total", threads, {"host": host}))

    cpu_info_core_family = families.get("windows_cpu_info_core")
    if cpu_info_core_family is None:
        missing.append("windows_cpu_info_core")
    else:
        cpu_info_core_samples = getattr(cpu_info_core_family, "samples", ())
        cores_total = sum(float(sample.value) for sample in cpu_info_core_samples)
        series.append(NormalizedSeries.from_mapping("host_cpu_cores_total", cores_total, {"host": host}))
        sockets_total = float(len(cpu_info_core_samples))
        series.append(NormalizedSeries.from_mapping("host_cpu_sockets_total", sockets_total, {"host": host}))

    cpu_info_family = families.get("windows_cpu_info")
    if cpu_info_family is None:
        missing.append("windows_cpu_info")
    else:
        cpu_model = _first_label(cpu_info_family, "name")
        series.append(
            NormalizedSeries.from_mapping(
                "host_cpu_info",
                1.0,
                {"host": host, "model": cpu_model, "architecture": architecture},
            )
        )

    memory_total = _first_family_value(families, "windows_memory_physical_total_bytes")
    memory_available = _first_family_value(
        families,
        "windows_memory_physical_free_bytes",
        "windows_memory_available_bytes",
    )
    if memory_total is None:
        missing.append("windows_memory_physical_total_bytes")
    else:
        series.append(NormalizedSeries.from_mapping("host_memory_bytes_total", memory_total, {"host": host}))
    if memory_available is None:
        missing.append("windows_memory_physical_free_bytes")
    else:
        series.append(
            NormalizedSeries.from_mapping("host_memory_bytes_available", memory_available, {"host": host})
        )
    if memory_total is not None and memory_available is not None and memory_total > 0:
        usage_percent = max(0.0, min(100.0, 100.0 * (1.0 - memory_available / memory_total)))
        series.append(NormalizedSeries.from_mapping("host_memory_usage_percent", usage_percent, {"host": host}))

    pagefile_limit_family = families.get("windows_pagefile_limit_bytes")
    pagefile_free_family = families.get("windows_pagefile_free_bytes")
    if pagefile_limit_family is None:
        missing.append("windows_pagefile_limit_bytes")
    else:
        swap_total = sum(float(sample.value) for sample in getattr(pagefile_limit_family, "samples", ()))
        series.append(NormalizedSeries.from_mapping("host_memory_swap_bytes_total", swap_total, {"host": host}))
        if pagefile_free_family is not None and swap_total > 0:
            swap_free = sum(float(sample.value) for sample in getattr(pagefile_free_family, "samples", ()))
            swap_usage = max(0.0, min(100.0, 100.0 * (1.0 - swap_free / swap_total)))
            series.append(
                NormalizedSeries.from_mapping("host_memory_swap_usage_percent", swap_usage, {"host": host})
            )
    if pagefile_free_family is None:
        missing.append("windows_pagefile_free_bytes")

    filesystem_size_family = families.get("windows_logical_disk_size_bytes")
    filesystem_free_family = families.get("windows_logical_disk_free_bytes")
    filesystem_info_family = families.get("windows_logical_disk_info")
    filesystem_by_volume = (
        _logical_disk_filesystem_map(filesystem_info_family) if filesystem_info_family is not None else {}
    )
    if filesystem_size_family is None:
        missing.append("windows_logical_disk_size_bytes")
    if filesystem_free_family is None:
        missing.append("windows_logical_disk_free_bytes")
    if filesystem_size_family is not None or filesystem_free_family is not None:
        series.extend(
            _filesystem_metrics(filesystem_size_family, filesystem_free_family, host, filesystem_by_volume)
        )

    disk_queue_family = families.get("windows_physical_disk_requests_queued")
    if disk_queue_family is None:
        missing.append("windows_physical_disk_requests_queued")
    else:
        series.extend(_labeled_series(disk_queue_family, "host_disk_queue_length", host, "disk", "disk"))

    disk_read_family = _first_family(
        families, "windows_physical_disk_read_bytes_total", "windows_physical_disk_read_bytes"
    )
    if disk_read_family is None:
        missing.append("windows_physical_disk_read_bytes_total")
    else:
        series.extend(_labeled_series(disk_read_family, "host_disk_read_bytes_total", host, "disk", "disk"))

    disk_write_family = _first_family(
        families, "windows_physical_disk_write_bytes_total", "windows_physical_disk_write_bytes"
    )
    if disk_write_family is None:
        missing.append("windows_physical_disk_write_bytes_total")
    else:
        series.extend(_labeled_series(disk_write_family, "host_disk_write_bytes_total", host, "disk", "disk"))

    disk_reads_family = _first_family(
        families, "windows_physical_disk_reads_total", "windows_physical_disk_reads"
    )
    if disk_reads_family is None:
        missing.append("windows_physical_disk_reads_total")
    else:
        series.extend(_labeled_series(disk_reads_family, "host_disk_reads_total", host, "disk", "disk"))

    disk_writes_family = _first_family(
        families, "windows_physical_disk_writes_total", "windows_physical_disk_writes"
    )
    if disk_writes_family is None:
        missing.append("windows_physical_disk_writes_total")
    else:
        series.extend(_labeled_series(disk_writes_family, "host_disk_writes_total", host, "disk", "disk"))

    network_rx_family = _first_family(
        families, "windows_net_bytes_received_total", "windows_net_bytes_received"
    )
    network_tx_family = _first_family(
        families, "windows_net_bytes_sent_total", "windows_net_bytes_sent"
    )
    if network_rx_family is None:
        missing.append("windows_net_bytes_received_total")
    else:
        series.extend(
            _labeled_series(network_rx_family, "host_network_receive_bytes_total", host, "nic", *_NIC_LABEL_KEYS)
        )
    if network_tx_family is None:
        missing.append("windows_net_bytes_sent_total")
    else:
        series.extend(
            _labeled_series(network_tx_family, "host_network_transmit_bytes_total", host, "nic", *_NIC_LABEL_KEYS)
        )

    net_rx_err_family = _first_family(
        families, "windows_net_packets_received_errors_total", "windows_net_packets_received_errors"
    )
    if net_rx_err_family is None:
        missing.append("windows_net_packets_received_errors_total")
    else:
        series.extend(
            _labeled_series(net_rx_err_family, "host_network_receive_errors_total", host, "nic", *_NIC_LABEL_KEYS)
        )

    net_tx_err_family = _first_family(
        families, "windows_net_packets_outbound_errors_total", "windows_net_packets_outbound_errors"
    )
    if net_tx_err_family is None:
        missing.append("windows_net_packets_outbound_errors_total")
    else:
        series.extend(
            _labeled_series(net_tx_err_family, "host_network_transmit_errors_total", host, "nic", *_NIC_LABEL_KEYS)
        )

    link_family = families.get("windows_net_nic_operation_status")
    if link_family is None:
        missing.append("windows_net_nic_operation_status")
    else:
        for sample in getattr(link_family, "samples", ()):
            labels = getattr(sample, "labels", {}) or {}
            nic = _first_non_empty(labels, *_NIC_LABEL_KEYS)
            status = str(labels.get("status", ""))
            link_up = 1.0 if status == "1" else 0.0
            series.append(
                NormalizedSeries.from_mapping("host_network_link_up", link_up, {"host": host, "nic": nic})
            )

    bandwidth_family = families.get("windows_net_current_bandwidth_bytes")
    if bandwidth_family is None:
        missing.append("windows_net_current_bandwidth_bytes")
    else:
        for sample in getattr(bandwidth_family, "samples", ()):
            labels = getattr(sample, "labels", {}) or {}
            nic = _first_non_empty(labels, *_NIC_LABEL_KEYS)
            speed_bits = float(sample.value) * 8.0
            series.append(
                NormalizedSeries.from_mapping("host_network_speed_bits", speed_bits, {"host": host, "nic": nic})
            )

    uptime = _uptime_seconds(
        families.get("windows_system_boot_time_timestamp"),
        now if now is not None else time.time(),
    )
    if uptime is None:
        missing.append("windows_system_boot_time_timestamp")
    else:
        series.append(NormalizedSeries.from_mapping("host_uptime_seconds", uptime, {"host": host}))

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
