from __future__ import annotations

import threading
from dataclasses import dataclass, replace

from .detect import UNKNOWN, DetectedExporter
from .normalized import NormalizedSnapshot


@dataclass(frozen=True)
class CacheSnapshot:
    raw_text: str | None = None
    detected: DetectedExporter = UNKNOWN
    normalized: NormalizedSnapshot | None = None
    last_scrape_wall: float | None = None
    last_scrape_success: bool = False
    last_scrape_duration: float = 0.0
    last_success_monotonic: float | None = None
    last_success_wall: float | None = None


class RawMetricsCache:
    def __init__(self):
        self._lock = threading.Lock()
        self._snapshot = CacheSnapshot()

    def get(self) -> CacheSnapshot:
        with self._lock:
            return self._snapshot

    def update_success(
        self,
        raw_text: str,
        detected: DetectedExporter,
        duration: float,
        monotonic_now: float,
        wall_now: float,
        normalized: NormalizedSnapshot | None = None,
    ) -> None:
        with self._lock:
            self._snapshot = CacheSnapshot(
                raw_text=raw_text,
                detected=detected,
                normalized=normalized,
                last_scrape_wall=wall_now,
                last_scrape_success=True,
                last_scrape_duration=duration,
                last_success_monotonic=monotonic_now,
                last_success_wall=wall_now,
            )

    def update_failure(self, duration: float, monotonic_now: float, wall_now: float) -> None:
        with self._lock:
            self._snapshot = replace(
                self._snapshot,
                last_scrape_wall=wall_now,
                last_scrape_success=False,
                last_scrape_duration=duration,
            )

    def is_stale(self, stale_after_seconds: float, now_monotonic: float) -> bool:
        with self._lock:
            last_success = self._snapshot.last_success_monotonic
        if last_success is None:
            return True
        return (now_monotonic - last_success) > stale_after_seconds
