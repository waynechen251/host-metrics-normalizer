from __future__ import annotations

import logging
import platform
import threading
import time
from dataclasses import dataclass

from ..config import AppConfig
from ..host_metrics import _resolve_host, build_metric_families
from ..normalized import NormalizedSeries
from . import linux as _linux
from . import nvidia as _nvidia
from . import windows as _windows
from ._util import warn_once

logger = logging.getLogger(__name__)

_CAPABILITY_METRICS = {
    "utilization": "host_gpu_utilization_percent",
    "memory": "host_gpu_memory_usage_percent",
    "temperature": "host_gpu_temperature_celsius",
    "power": "host_gpu_power_watts",
}


@dataclass(frozen=True)
class GpuCollectionResult:
    series: tuple[NormalizedSeries, ...]
    collection_up: bool
    duration_seconds: float


def collect_gpu_series(
    host: str,
    *,
    state: _windows.UtilizationState | None = None,
    system: str | None = None,
) -> tuple[NormalizedSeries, ...]:
    system_name = system if system is not None else platform.system()
    try:
        return _collect_os_series(host, state=state, system=system_name)
    except Exception:
        warn_once(
            logger,
            f"gpu-collect-unexpected-{system_name}",
            "GPU metrics collection raised an unexpected error on %s; further occurrences will be suppressed",
            system_name,
            exc_info=True,
        )
        return ()


def _collect_os_series(
    host: str,
    *,
    state: _windows.UtilizationState | None = None,
    system: str | None = None,
) -> tuple[NormalizedSeries, ...]:
    system_name = system if system is not None else platform.system()
    if system_name == "Windows":
        if state is None:
            state = _windows.UtilizationState()
        return _windows.collect(host, state=state)
    if system_name == "Linux":
        return _linux.collect(host)
    return ()


def collect_gpu_result(
    host: str,
    *,
    state: _windows.UtilizationState | None = None,
    system: str | None = None,
) -> GpuCollectionResult:
    """Collect a normalized GPU fleet view and record collection health separately."""
    started = time.perf_counter()
    system_name = system if system is not None else platform.system()
    try:
        generic = _collect_os_series(host, state=state, system=system_name)
        merged = _enrich_with_nvidia(host, generic)
        return GpuCollectionResult(tuple(merged), True, time.perf_counter() - started)
    except Exception:
        warn_once(
            logger,
            f"gpu-collect-result-{system_name}",
            "GPU metrics collection failed on %s; reporting collection failure",
            system_name,
            exc_info=True,
        )
        return GpuCollectionResult((), False, time.perf_counter() - started)


def _enrich_with_nvidia(host: str, generic: tuple[NormalizedSeries, ...]) -> tuple[NormalizedSeries, ...]:
    nvidia_devices = _nvidia.collect()
    if not nvidia_devices:
        return generic

    device_to_gpu: dict[str, str] = {}
    used_gpus: set[str] = set()
    for item in generic:
        if item.name != "host_gpu_info":
            continue
        labels = item.label_dict()
        device_id = labels.get("device_id", "").lower()
        gpu = labels.get("gpu", "")
        if device_id:
            device_to_gpu[device_id] = gpu
        if gpu:
            used_gpus.add(gpu)

    replacement: dict[tuple[str, str], NormalizedSeries] = {}
    next_gpu = _next_gpu_index(used_gpus)
    for device in nvidia_devices:
        gpu = device_to_gpu.get(device.device_id.lower())
        if gpu is None:
            gpu = str(next_gpu)
            next_gpu += 1
            used_gpus.add(gpu)
        replacement[("host_gpu_info", gpu)] = NormalizedSeries.from_mapping(
            "host_gpu_info",
            1.0,
            {"host": host, "gpu": gpu, "vendor": "nvidia", "name": device.name, "device_id": device.device_id},
        )
        for name, value in _nvidia_metric_values(device).items():
            replacement[(name, gpu)] = NormalizedSeries.from_mapping(name, value, {"host": host, "gpu": gpu})

    merged: list[NormalizedSeries] = []
    seen: set[tuple[str, str]] = set()
    for item in generic:
        key = (item.name, item.label_dict().get("gpu", ""))
        if key in replacement:
            if key not in seen:
                merged.append(replacement[key])
                seen.add(key)
        else:
            merged.append(item)
    for key, item in replacement.items():
        if key not in seen:
            merged.append(item)
    return tuple(merged)


def _nvidia_metric_values(device: _nvidia.NvidiaDevice) -> dict[str, float]:
    values: dict[str, float] = {}
    if device.memory_total_bytes is not None:
        values["host_gpu_memory_total_bytes"] = float(device.memory_total_bytes)
    if device.memory_used_bytes is not None:
        values["host_gpu_memory_used_bytes"] = float(device.memory_used_bytes)
    if device.memory_total_bytes and device.memory_used_bytes is not None:
        values["host_gpu_memory_usage_percent"] = max(0.0, min(100.0, 100.0 * device.memory_used_bytes / device.memory_total_bytes))
    if device.utilization_percent is not None:
        values["host_gpu_utilization_percent"] = max(0.0, min(100.0, device.utilization_percent))
    if device.temperature_celsius is not None:
        values["host_gpu_temperature_celsius"] = device.temperature_celsius
    if device.power_watts is not None:
        values["host_gpu_power_watts"] = device.power_watts
    return values


def _next_gpu_index(used_gpus: set[str]) -> int:
    numeric = [int(value) for value in used_gpus if value.isdigit()]
    return max(numeric, default=-1) + 1


def _status_series(host: str, result: GpuCollectionResult, errors_total: int) -> tuple[NormalizedSeries, ...]:
    devices = [item for item in result.series if item.name == "host_gpu_info"]
    status = [
        NormalizedSeries.from_mapping("host_gpu_collection_up", 1.0 if result.collection_up else 0.0, {"host": host}),
        NormalizedSeries.from_mapping("host_gpu_devices_total", float(len(devices)), {"host": host}),
        NormalizedSeries.from_mapping("host_gpu_collection_errors_total", float(errors_total), {"host": host}),
        NormalizedSeries.from_mapping("host_gpu_scrape_duration_seconds", result.duration_seconds, {"host": host}),
    ]
    by_gpu: dict[str, set[str]] = {}
    for item in result.series:
        labels = item.label_dict()
        gpu = labels.get("gpu")
        if gpu is not None:
            by_gpu.setdefault(gpu, set()).add(item.name)
    for gpu, names in by_gpu.items():
        for capability, metric_name in _CAPABILITY_METRICS.items():
            status.append(
                NormalizedSeries.from_mapping(
                    "host_gpu_metric_available",
                    1.0 if metric_name in names else 0.0,
                    {"host": host, "gpu": gpu, "metric": capability},
                )
            )
    return tuple(status)


class GpuMetricsCollector:
    """Independent prometheus_client collector for self-collected GPU metrics.

    Registered directly into NormalizerMetrics.registry alongside HostMetricsCollector
    (see metrics.py), not routed through MetricsRefresher/RawMetricsCache: GPU data is
    read fresh from OS-native APIs every time the registry is walked, independent of
    whether the local windows_exporter/node_exporter scrape succeeds.
    """

    def __init__(self, config: AppConfig):
        self._config = config
        self._state = _windows.UtilizationState()
        self._lock = threading.Lock()
        self._errors_total = 0

    def _collect_result(self) -> GpuCollectionResult:
        host = _resolve_host(self._config)
        with self._lock:
            result = collect_gpu_result(host, state=self._state)
            if not result.collection_up:
                self._errors_total += 1
            return result

    def collect_series(self) -> tuple[NormalizedSeries, ...]:
        """Single call path shared by the prometheus collect() protocol method and
        the /debug/gpu HTTP handler, so both read/write the same UtilizationState
        instead of maintaining two independent (and mutually corrupting) samplers."""
        return self._collect_result().series

    def collect(self):
        host = _resolve_host(self._config)
        result = self._collect_result()
        with self._lock:
            errors_total = self._errors_total
        yield from build_metric_families((*result.series, *_status_series(host, result, errors_total)))
