from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

from prometheus_client.exposition import generate_latest

from .cache import RawMetricsCache
from .config import AppConfig
from .detect import detect_from_raw
from .normalization import normalize_exporter_metrics
from .metrics import NormalizerMetrics
from .scraper import scrape

if TYPE_CHECKING:
    from .server import HealthState


class MetricsRefresher:
    def __init__(
        self,
        config: AppConfig,
        cache: RawMetricsCache,
        metrics: NormalizerMetrics,
        health: HealthState,
    ):
        self._config = config
        self._endpoint = config.source_exporter.endpoint
        self._timeout = config.source_exporter.timeout_seconds
        self._stale_after = config.cache.stale_after_seconds
        self._cache = cache
        self._metrics = metrics
        self._health = health
        # Serializes scrape+render across concurrent /metrics requests: NormalizerMetrics
        # tracks the current exporter label with an unlocked clear()-then-relabel sequence
        # (see update_source_exporter) that isn't safe under concurrent writers.
        self._lock = threading.Lock()

    def refresh_and_render(self) -> bytes:
        with self._lock:
            self._refresh_locked()
            return generate_latest(self._metrics.registry)

    def _refresh_locked(self) -> None:
        result = scrape(self._endpoint, self._timeout)
        monotonic_now = time.monotonic()
        wall_now = time.time()

        if result.success:
            detected = detect_from_raw(result.raw_text)
            normalized = normalize_exporter_metrics(
                self._config,
                detected,
                result.raw_text,
                now=wall_now,
            )
            if normalized.status == "parse_error":
                self._metrics.record_normalizer_error()
            self._cache.update_success(
                result.raw_text,
                detected,
                result.duration_seconds,
                monotonic_now,
                wall_now,
                normalized=normalized,
            )
        else:
            self._cache.update_failure(result.duration_seconds, monotonic_now, wall_now)
            self._metrics.record_scrape_error()

        snapshot = self._cache.get()
        stale = self._cache.is_stale(self._stale_after, monotonic_now)

        self._metrics.update_normalizer_scrape(snapshot, stale)
        self._metrics.update_source_exporter(snapshot, endpoint=self._endpoint)
        self._health.update(
            source_exporter_up=snapshot.last_scrape_success,
            last_scrape_success=snapshot.last_scrape_success,
            last_scrape_timestamp=int(snapshot.last_scrape_wall or 0),
            exporter=snapshot.detected.type,
            exporter_version=snapshot.detected.version,
            os_family=snapshot.detected.os_family,
        )
