from __future__ import annotations

import threading
import time

from .cache import RawMetricsCache
from .config import AppConfig
from .detect import detect_from_raw
from .metrics import NormalizerMetrics
from .scraper import scrape
from .server import HealthState


class ScrapeWorker:
    def __init__(
        self,
        config: AppConfig,
        cache: RawMetricsCache,
        metrics: NormalizerMetrics,
        health: HealthState,
        stop_event: threading.Event,
    ):
        self._endpoint = config.source_exporter.endpoint
        self._timeout = config.source_exporter.timeout_seconds
        self._interval = max(1, config.cache.ttl_seconds)
        self._stale_after = config.cache.stale_after_seconds
        self._cache = cache
        self._metrics = metrics
        self._health = health
        self._stop = stop_event

    def run(self) -> None:
        while not self._stop.is_set():
            self._scrape_once()
            self._stop.wait(self._interval)

    def _scrape_once(self) -> None:
        result = scrape(self._endpoint, self._timeout)
        monotonic_now = time.monotonic()
        wall_now = time.time()

        if result.success:
            detected = detect_from_raw(result.raw_text)
            self._cache.update_success(
                result.raw_text, detected, result.duration_seconds, monotonic_now, wall_now
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
