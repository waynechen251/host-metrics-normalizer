from __future__ import annotations

import time

from ...detect import DetectedExporter
from ...normalized import NormalizedSeries, NormalizedSnapshot
from .common import (
    _DEVICE_LABEL_KEYS,
    _cpu_info_core_socket_counts,
    _cpu_usage_percent,
    _distinct_label_count,
    _filesystem_metrics,
    _first_family,
    _first_family_value,
    _first_label,
    _first_non_empty,
    _labeled_series,
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

    build_info = families.get("node_exporter_build_info")
    architecture = _normalize_architecture(_first_label(build_info, "goarch")) if build_info else ""

    os_info_family = families.get("node_os_info")
    os_name = _first_label(os_info_family, "pretty_name", "name") if os_info_family else ""
    os_version = _first_label(os_info_family, "version_id", "version") if os_info_family else ""
    if os_info_family is None:
        missing.append("node_os_info")

    uname_family = families.get("node_uname_info")
    kernel_version = _first_label(uname_family, "release") if uname_family else ""
    if uname_family is None:
        missing.append("node_uname_info")

    series.append(
        NormalizedSeries.from_mapping(
            "host_os_info",
            1.0,
            {
                "host": host,
                "os_family": "linux",
                "os_name": os_name,
                "os_version": os_version,
                "kernel_version": kernel_version,
                "architecture": architecture,
            },
        )
    )

    cpu_family = _first_family(families, "node_cpu_seconds_total", "node_cpu_seconds")
    if cpu_family is None:
        missing.append("node_cpu_seconds_total")
    else:
        cpu_usage = _cpu_usage_percent(cpu_family)
        if cpu_usage is not None:
            series.append(
                NormalizedSeries.from_mapping("host_cpu_usage_percent", cpu_usage, {"host": host})
            )
        else:
            missing.append("node_cpu_seconds_total")

    if cpu_family is not None:
        thread_count = _distinct_label_count(cpu_family, "cpu")
        threads = float(thread_count) if thread_count is not None else None
    else:
        threads = None
    if threads is None:
        missing.append("node_cpu_seconds_total")
    else:
        series.append(NormalizedSeries.from_mapping("host_cpu_threads_total", threads, {"host": host}))

    cpu_info_family = families.get("node_cpu_info")
    if cpu_info_family is None:
        missing.append("node_cpu_info")
    else:
        cores_total, sockets_total = _cpu_info_core_socket_counts(cpu_info_family)
        if cores_total is not None:
            series.append(NormalizedSeries.from_mapping("host_cpu_cores_total", cores_total, {"host": host}))
        if sockets_total is not None:
            series.append(NormalizedSeries.from_mapping("host_cpu_sockets_total", sockets_total, {"host": host}))
        cpu_model = _first_label(cpu_info_family, "model_name")
        series.append(
            NormalizedSeries.from_mapping(
                "host_cpu_info",
                1.0,
                {"host": host, "model": cpu_model, "architecture": architecture},
            )
        )

    memory_total = _first_family_value(families, "node_memory_MemTotal_bytes")
    memory_available = _first_family_value(
        families,
        "node_memory_MemAvailable_bytes",
        "node_memory_MemFree_bytes",
    )
    if memory_total is None:
        missing.append("node_memory_MemTotal_bytes")
    else:
        series.append(NormalizedSeries.from_mapping("host_memory_bytes_total", memory_total, {"host": host}))
    if memory_available is None:
        missing.append("node_memory_MemAvailable_bytes")
    else:
        series.append(
            NormalizedSeries.from_mapping("host_memory_bytes_available", memory_available, {"host": host})
        )
    if memory_total is not None and memory_available is not None and memory_total > 0:
        usage_percent = max(0.0, min(100.0, 100.0 * (1.0 - memory_available / memory_total)))
        series.append(NormalizedSeries.from_mapping("host_memory_usage_percent", usage_percent, {"host": host}))

    swap_total = _first_family_value(families, "node_memory_SwapTotal_bytes")
    swap_free = _first_family_value(families, "node_memory_SwapFree_bytes")
    if swap_total is None:
        missing.append("node_memory_SwapTotal_bytes")
    else:
        series.append(NormalizedSeries.from_mapping("host_memory_swap_bytes_total", swap_total, {"host": host}))
        if swap_free is not None and swap_total > 0:
            swap_usage = max(0.0, min(100.0, 100.0 * (1.0 - swap_free / swap_total)))
            series.append(
                NormalizedSeries.from_mapping("host_memory_swap_usage_percent", swap_usage, {"host": host})
            )
    if swap_free is None:
        missing.append("node_memory_SwapFree_bytes")

    filesystem_size_family = families.get("node_filesystem_size_bytes")
    filesystem_avail_family = families.get("node_filesystem_avail_bytes")
    if filesystem_size_family is None:
        missing.append("node_filesystem_size_bytes")
    if filesystem_avail_family is None:
        missing.append("node_filesystem_avail_bytes")
    if filesystem_size_family is not None or filesystem_avail_family is not None:
        series.extend(_filesystem_metrics(filesystem_size_family, filesystem_avail_family, host))

    disk_queue_family = families.get("node_disk_io_now")
    if disk_queue_family is None:
        missing.append("node_disk_io_now")
    else:
        series.extend(_labeled_series(disk_queue_family, "host_disk_queue_length", host, "disk", *_DEVICE_LABEL_KEYS))

    disk_read_family = _first_family(families, "node_disk_read_bytes_total", "node_disk_read_bytes")
    if disk_read_family is None:
        missing.append("node_disk_read_bytes_total")
    else:
        series.extend(
            _labeled_series(disk_read_family, "host_disk_read_bytes_total", host, "disk", *_DEVICE_LABEL_KEYS)
        )

    disk_write_family = _first_family(families, "node_disk_written_bytes_total", "node_disk_written_bytes")
    if disk_write_family is None:
        missing.append("node_disk_written_bytes_total")
    else:
        series.extend(
            _labeled_series(disk_write_family, "host_disk_write_bytes_total", host, "disk", *_DEVICE_LABEL_KEYS)
        )

    disk_reads_family = _first_family(families, "node_disk_reads_completed_total", "node_disk_reads_completed")
    if disk_reads_family is None:
        missing.append("node_disk_reads_completed_total")
    else:
        series.extend(
            _labeled_series(disk_reads_family, "host_disk_reads_total", host, "disk", *_DEVICE_LABEL_KEYS)
        )

    disk_writes_family = _first_family(families, "node_disk_writes_completed_total", "node_disk_writes_completed")
    if disk_writes_family is None:
        missing.append("node_disk_writes_completed_total")
    else:
        series.extend(
            _labeled_series(disk_writes_family, "host_disk_writes_total", host, "disk", *_DEVICE_LABEL_KEYS)
        )

    network_rx_family = _first_family(
        families, "node_network_receive_bytes_total", "node_network_receive_bytes"
    )
    network_tx_family = _first_family(
        families, "node_network_transmit_bytes_total", "node_network_transmit_bytes"
    )
    if network_rx_family is None:
        missing.append("node_network_receive_bytes_total")
    else:
        series.extend(
            _labeled_series(network_rx_family, "host_network_receive_bytes_total", host, "nic", *_DEVICE_LABEL_KEYS)
        )
    if network_tx_family is None:
        missing.append("node_network_transmit_bytes_total")
    else:
        series.extend(
            _labeled_series(network_tx_family, "host_network_transmit_bytes_total", host, "nic", *_DEVICE_LABEL_KEYS)
        )

    net_rx_err_family = _first_family(
        families, "node_network_receive_errs_total", "node_network_receive_errs"
    )
    if net_rx_err_family is None:
        missing.append("node_network_receive_errs_total")
    else:
        series.extend(
            _labeled_series(
                net_rx_err_family, "host_network_receive_errors_total", host, "nic", *_DEVICE_LABEL_KEYS
            )
        )

    net_tx_err_family = _first_family(
        families, "node_network_transmit_errs_total", "node_network_transmit_errs"
    )
    if net_tx_err_family is None:
        missing.append("node_network_transmit_errs_total")
    else:
        series.extend(
            _labeled_series(
                net_tx_err_family, "host_network_transmit_errors_total", host, "nic", *_DEVICE_LABEL_KEYS
            )
        )

    link_family = families.get("node_network_up")
    if link_family is None:
        missing.append("node_network_up")
    else:
        series.extend(_labeled_series(link_family, "host_network_link_up", host, "nic", *_DEVICE_LABEL_KEYS))

    bandwidth_family = families.get("node_network_speed_bytes")
    if bandwidth_family is None:
        missing.append("node_network_speed_bytes")
    else:
        for sample in getattr(bandwidth_family, "samples", ()):
            # The kernel reports speed as -1 via sysfs for interfaces with no
            # negotiated/known link speed (bridges, down interfaces, etc.);
            # node_exporter passes that sentinel through as a negative byte count.
            if sample.value < 0:
                continue
            labels = getattr(sample, "labels", {}) or {}
            nic = _first_non_empty(labels, *_DEVICE_LABEL_KEYS)
            speed_bits = float(sample.value) * 8.0
            series.append(
                NormalizedSeries.from_mapping("host_network_speed_bits", speed_bits, {"host": host, "nic": nic})
            )

    uptime = _uptime_seconds(
        families.get("node_boot_time_seconds"),
        now if now is not None else time.time(),
    )
    if uptime is None:
        missing.append("node_boot_time_seconds")
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
