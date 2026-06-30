import threading

from host_metrics_normalizer.cache import RawMetricsCache
from host_metrics_normalizer.detect import UNKNOWN, DetectedExporter

WINDOWS = DetectedExporter(type="windows_exporter", os_family="windows", version="0.31.6")


def test_initial_snapshot_is_empty_and_stale():
    cache = RawMetricsCache()

    snapshot = cache.get()

    assert snapshot.raw_text is None
    assert snapshot.detected == UNKNOWN
    assert snapshot.last_scrape_success is False
    assert cache.is_stale(stale_after_seconds=180, now_monotonic=1000.0) is True


def test_update_success_populates_snapshot():
    cache = RawMetricsCache()

    cache.update_success(
        raw_text="metric_a 1\n",
        detected=WINDOWS,
        duration=0.05,
        monotonic_now=100.0,
        wall_now=1700000000.0,
    )
    snapshot = cache.get()

    assert snapshot.raw_text == "metric_a 1\n"
    assert snapshot.detected == WINDOWS
    assert snapshot.last_scrape_success is True
    assert snapshot.last_scrape_duration == 0.05
    assert snapshot.last_success_monotonic == 100.0
    assert snapshot.last_success_wall == 1700000000.0


def test_update_failure_preserves_last_successful_data():
    cache = RawMetricsCache()
    cache.update_success(
        raw_text="metric_a 1\n",
        detected=WINDOWS,
        duration=0.05,
        monotonic_now=100.0,
        wall_now=1700000000.0,
    )

    cache.update_failure(duration=3.0, monotonic_now=110.0, wall_now=1700000010.0)
    snapshot = cache.get()

    assert snapshot.raw_text == "metric_a 1\n"
    assert snapshot.detected == WINDOWS
    assert snapshot.last_scrape_success is False
    assert snapshot.last_scrape_duration == 3.0
    assert snapshot.last_scrape_wall == 1700000010.0
    assert snapshot.last_success_monotonic == 100.0


def test_is_stale_false_right_after_success():
    cache = RawMetricsCache()
    cache.update_success(
        raw_text="x", detected=WINDOWS, duration=0.01, monotonic_now=100.0, wall_now=1.0
    )

    assert cache.is_stale(stale_after_seconds=180, now_monotonic=150.0) is False


def test_is_stale_true_after_threshold():
    cache = RawMetricsCache()
    cache.update_success(
        raw_text="x", detected=WINDOWS, duration=0.01, monotonic_now=100.0, wall_now=1.0
    )

    assert cache.is_stale(stale_after_seconds=180, now_monotonic=400.0) is True


def test_concurrent_updates_do_not_raise_and_remain_consistent():
    cache = RawMetricsCache()
    errors = []

    def writer(i):
        try:
            for j in range(50):
                if j % 2 == 0:
                    cache.update_success(
                        raw_text=f"writer-{i}-{j}",
                        detected=WINDOWS,
                        duration=0.01,
                        monotonic_now=float(j),
                        wall_now=float(j),
                    )
                else:
                    cache.update_failure(duration=0.02, monotonic_now=float(j), wall_now=float(j))
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    def reader():
        try:
            for _ in range(50):
                cache.get()
                cache.is_stale(180, 1000.0)
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
    threads += [threading.Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert errors == []
    final = cache.get()
    assert final.raw_text is not None
