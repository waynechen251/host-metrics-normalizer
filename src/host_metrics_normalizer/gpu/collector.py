from __future__ import annotations

import logging
import platform
import threading

from ..config import AppConfig
from ..host_metrics import _resolve_host, build_metric_families
from ..normalized import NormalizedSeries
from . import linux as _linux
from . import windows as _windows
from ._util import warn_once

logger = logging.getLogger(__name__)


def collect_gpu_series(
    host: str,
    *,
    state: _windows.UtilizationState | None = None,
    system: str | None = None,
) -> tuple[NormalizedSeries, ...]:
    system_name = system if system is not None else platform.system()
    try:
        if system_name == "Windows":
            if state is None:
                state = _windows.UtilizationState()
            return _windows.collect(host, state=state)
        if system_name == "Linux":
            return _linux.collect(host)
        return ()
    except Exception:
        warn_once(
            logger,
            f"gpu-collect-unexpected-{system_name}",
            "GPU metrics collection raised an unexpected error on %s; "
            "further occurrences will be suppressed",
            system_name,
            exc_info=True,
        )
        return ()


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

    def collect_series(self) -> tuple[NormalizedSeries, ...]:
        """Single call path shared by the prometheus collect() protocol method and
        the /debug/gpu HTTP handler, so both read/write the same UtilizationState
        instead of maintaining two independent (and mutually corrupting) samplers."""
        host = _resolve_host(self._config)
        with self._lock:
            return collect_gpu_series(host, state=self._state)

    def collect(self):
        yield from build_metric_families(self.collect_series())
