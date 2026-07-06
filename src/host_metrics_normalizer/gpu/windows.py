from __future__ import annotations

import logging
import re
import threading
from typing import Callable

from ..normalized import NormalizedSeries
from ._util import warn_once

logger = logging.getLogger(__name__)

try:
    import pythoncom
    import win32com.client

    _HAS_WIN32COM = True
except ImportError:  # pragma: no cover - exercised only off-Windows
    pythoncom = None  # type: ignore[assignment]
    win32com = None  # type: ignore[assignment]
    _HAS_WIN32COM = False

try:
    import win32pdh

    _HAS_WIN32PDH = True
except ImportError:  # pragma: no cover - exercised only off-Windows
    win32pdh = None  # type: ignore[assignment]
    _HAS_WIN32PDH = False

try:
    import winreg

    _HAS_WINREG = True
except ImportError:  # pragma: no cover - exercised only off-Windows
    winreg = None  # type: ignore[assignment]
    _HAS_WINREG = False

WmiQuery = Callable[[str], list[dict]]
VramReader = Callable[[int], "int | None"]

_DISPLAY_CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
_VEN_DEV_RE = re.compile(r"VEN_[0-9A-Fa-f]{4}&DEV_[0-9A-Fa-f]{4}")
_PHYS_RE = re.compile(r"phys_(?P<phys>\d+)")

# Confirmed empirically against a real Windows 10/11 host via `win32pdh.EnumObjects`:
# "GPU Engine" and "GPU Adapter Memory" are standard WDDM performance-counter objects
# (the same raw source windows_exporter's own `gpu` collector reads), available
# regardless of GPU vendor. Deliberately NOT using the WMI mirror classes
# (Win32_PerfRawData_Counters_GPUEngine/GPUAdapterMemory): on a real test host they
# raised "invalid class" (WBEM_E_INVALID_CLASS) even though the underlying PDH
# counters were present, apparently because these newer perf objects were never
# synced into the WMI root\cimv2 namespace on that machine.
_ENGINE_COUNTER_PATH = r"\GPU Engine(*)\Utilization Percentage"
_MEMORY_COUNTER_PATH = r"\GPU Adapter Memory(*)\Dedicated Usage"


class UtilizationState:
    """Owns a persistent PDH query across HTTP requests.

    PDH computes the "Utilization Percentage" counter as a delta between two
    successive CollectQueryData() calls on the SAME query/counter handle, so this
    object must stay open for the life of the process rather than being reopened
    per request -- the first sample after (re)opening legitimately has no data yet.

    Has its own lock: ThreadingHTTPServer may invoke GpuMetricsCollector.collect()
    concurrently for overlapping /metrics requests, and MetricsRefresher._lock does
    NOT protect this collector (it is registered independently and invoked directly
    by generate_latest(), not through MetricsRefresher).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._query = None
        self._engine_handle = None
        self._memory_handle = None

    def _ensure_open(self) -> None:
        if self._query is not None:
            return
        self._query = win32pdh.OpenQuery()
        self._engine_handle = win32pdh.AddCounter(self._query, _ENGINE_COUNTER_PATH)
        self._memory_handle = win32pdh.AddCounter(self._query, _MEMORY_COUNTER_PATH)

    def sample(self) -> tuple[dict[str, float], dict[str, float]]:
        """Returns (utilization_percent_by_phys, memory_used_bytes_by_phys)."""
        if not _HAS_WIN32PDH:
            return {}, {}
        with self._lock:
            self._ensure_open()
            win32pdh.CollectQueryData(self._query)

            memory_by_phys = _group_by_phys(
                win32pdh.GetFormattedCounterArray(self._memory_handle, win32pdh.PDH_FMT_LARGE)
            )
            try:
                utilization_by_phys = _group_by_phys(
                    win32pdh.GetFormattedCounterArray(self._engine_handle, win32pdh.PDH_FMT_DOUBLE),
                    aggregate=max,
                )
            except Exception:
                # Rate-type counters like "Utilization Percentage" have no delta to
                # report on the very first sample after (re)opening the query.
                utilization_by_phys = {}
            return utilization_by_phys, memory_by_phys


def collect(
    host: str,
    *,
    state: UtilizationState,
    wmi_query: WmiQuery | None = None,
    vram_reader: VramReader | None = None,
) -> tuple[NormalizedSeries, ...]:
    query = wmi_query or _wmi_query
    reader = vram_reader or _read_vram_total_bytes

    try:
        adapters = query("SELECT Name, PNPDeviceID FROM Win32_VideoController")
    except Exception:
        warn_once(
            logger,
            "windows-videocontroller-query",
            "Windows GPU collection: Win32_VideoController query failed",
            exc_info=True,
        )
        adapters = []
    adapters = sorted(adapters, key=lambda row: str(row.get("PNPDeviceID", "")))

    try:
        utilization_by_phys, memory_by_phys = state.sample()
    except Exception:
        warn_once(
            logger,
            "windows-pdh-sample",
            "Windows GPU collection: PDH counter sampling failed",
            exc_info=True,
        )
        utilization_by_phys, memory_by_phys = {}, {}

    # The PDH "phys" index is the OS's own physical-adapter numbering and is the
    # canonical `gpu` label; WMI's Win32_VideoController list is only correlated to
    # it best-effort by position, since Win32_VideoController does not expose the
    # adapter LUID needed for an exact join (confirmed on a real host to sometimes
    # under-enumerate relative to what the WDDM perf counters see, e.g. hybrid-
    # graphics laptops -- a known Phase 1 limitation).
    known_phys = sorted(set(utilization_by_phys) | set(memory_by_phys), key=int)
    if not known_phys:
        known_phys = [str(i) for i in range(len(adapters))]
    if not known_phys and not adapters:
        return ()

    series: list[NormalizedSeries] = []
    for position, phys in enumerate(known_phys):
        gpu = phys
        name = ""
        device_id = ""
        total = None
        if position < len(adapters):
            adapter = adapters[position]
            name = str(adapter.get("Name") or "")
            device_id = _extract_device_id(str(adapter.get("PNPDeviceID") or ""))
            total = reader(position)

        series.append(
            NormalizedSeries.from_mapping(
                "host_gpu_info", 1.0, {"host": host, "gpu": gpu, "name": name, "device_id": device_id}
            )
        )
        if total is not None and total > 0:
            series.append(
                NormalizedSeries.from_mapping(
                    "host_gpu_memory_total_bytes", float(total), {"host": host, "gpu": gpu}
                )
            )

        used = memory_by_phys.get(phys)
        if used is not None:
            series.append(
                NormalizedSeries.from_mapping(
                    "host_gpu_memory_used_bytes", float(used), {"host": host, "gpu": gpu}
                )
            )
            if total is not None and total > 0:
                usage = max(0.0, min(100.0, 100.0 * used / total))
                series.append(
                    NormalizedSeries.from_mapping(
                        "host_gpu_memory_usage_percent", usage, {"host": host, "gpu": gpu}
                    )
                )

        percent = utilization_by_phys.get(phys)
        if percent is not None:
            series.append(
                NormalizedSeries.from_mapping(
                    "host_gpu_utilization_percent",
                    max(0.0, min(100.0, percent)),
                    {"host": host, "gpu": gpu},
                )
            )

    return tuple(series)


def _group_by_phys(
    items: dict[str, float], *, aggregate: Callable[[list[float]], float] = sum
) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for instance_name, value in items.items():
        match = _PHYS_RE.search(instance_name)
        if not match:
            continue
        grouped.setdefault(match.group("phys"), []).append(float(value))
    return {phys: aggregate(values) for phys, values in grouped.items()}


def _extract_device_id(pnp_device_id: str) -> str:
    match = _VEN_DEV_RE.search(pnp_device_id)
    if match:
        return f"PCI\\{match.group(0)}"
    return pnp_device_id


def _wmi_query(wql: str) -> list[dict]:
    if not _HAS_WIN32COM:
        return []
    # Each /metrics request is handled on a fresh thread (ThreadingHTTPServer), and
    # COM requires explicit per-thread initialization -- without this, GetObject()
    # fails with a misleading "invalid syntax" com_error on any thread other than
    # the one that happened to initialize COM first (confirmed on a real host).
    pythoncom.CoInitialize()
    try:
        wmi = win32com.client.GetObject("winmgmts:root\\cimv2")
        return [{prop.Name: prop.Value for prop in obj.Properties_} for obj in wmi.ExecQuery(wql)]
    finally:
        pythoncom.CoUninitialize()


def _read_vram_total_bytes(index: int) -> int | None:
    if not _HAS_WINREG:
        return None
    subkey = f"{_DISPLAY_CLASS_KEY}\\{index:04d}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey) as key:
            value, _ = winreg.QueryValueEx(key, "HardwareInformation.qwMemorySize")
            return int(value)
    except OSError:
        return None
