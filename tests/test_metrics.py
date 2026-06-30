from prometheus_client import generate_latest

from host_metrics_normalizer.cache import CacheSnapshot
from host_metrics_normalizer.detect import UNKNOWN, DetectedExporter
from host_metrics_normalizer.metrics import NormalizerMetrics

WINDOWS = DetectedExporter(type="windows_exporter", os_family="windows", version="0.31.6")
NODE = DetectedExporter(type="node_exporter", os_family="linux", version="1.8.2")
ENDPOINT = "http://127.0.0.1:9182/metrics"


def _data_lines(output: str, metric_name: str) -> list[str]:
    """Actual series lines for metric_name, excluding # HELP / # TYPE comments."""
    return [
        line
        for line in output.splitlines()
        if not line.startswith("#") and line.startswith(metric_name)
    ]


def test_normalizer_metrics_initial_output():
    metrics = NormalizerMetrics(version="0.1.0", config_version="manual")

    output = generate_latest(metrics.registry).decode("utf-8")

    assert 'host_normalizer_info{config_version="manual",version="0.1.0"} 1.0' in output
    assert "host_normalizer_up 1.0" in output
    assert "host_normalizer_scrape_duration_seconds 0.0" in output
    assert "host_normalizer_last_scrape_timestamp_seconds 0.0" in output
    assert "host_normalizer_last_scrape_success 0.0" in output
    assert "host_normalizer_errors_total 0.0" in output
    assert "host_metrics_stale 0.0" in output


def test_normalizer_metrics_registry_excludes_process_collectors():
    metrics = NormalizerMetrics(version="0.1.0")

    output = generate_latest(metrics.registry).decode("utf-8")

    assert "process_cpu_seconds_total" not in output
    assert "python_gc_" not in output


def test_source_exporter_metrics_absent_before_first_successful_scrape():
    metrics = NormalizerMetrics(version="0.1.0")

    output = generate_latest(metrics.registry).decode("utf-8")

    assert _data_lines(output, "host_source_exporter_up") == []
    assert _data_lines(output, "host_source_exporter_scrape_duration_seconds") == []
    assert _data_lines(output, "host_source_exporter_last_scrape_success") == []
    # Info always emits an unlabeled sentinel line until .info() is first
    # called; .info() fully replaces (not appends to) the label set, so this
    # never accumulates into a residual series once detection succeeds.
    assert _data_lines(output, "host_source_exporter_info") == ["host_source_exporter_info 1.0"]


def test_update_source_exporter_publishes_windows_series():
    metrics = NormalizerMetrics(version="0.1.0")
    snapshot = CacheSnapshot(
        raw_text="x",
        detected=WINDOWS,
        last_scrape_success=True,
        last_scrape_duration=0.05,
    )

    metrics.update_source_exporter(snapshot, endpoint=ENDPOINT)
    output = generate_latest(metrics.registry).decode("utf-8")

    assert 'host_source_exporter_up{exporter="windows_exporter"} 1.0' in output
    assert (
        'host_source_exporter_info{endpoint="http://127.0.0.1:9182/metrics",'
        'exporter="windows_exporter",version="0.31.6"} 1.0' in output
    )


def test_update_source_exporter_never_leaves_unknown_label_after_detection():
    """Regression: switching from undetected to windows_exporter must not
    leave a stale exporter="unknown" series behind in the registry."""
    metrics = NormalizerMetrics(version="0.1.0")

    # First tick: scrape succeeded but detection failed (genuinely unknown).
    first = CacheSnapshot(
        raw_text="some_other_metric 1\n",
        detected=UNKNOWN,
        last_scrape_success=True,
        last_scrape_duration=0.02,
    )
    metrics.update_source_exporter(first, endpoint=ENDPOINT)

    # Second tick: now correctly detected as windows_exporter.
    second = CacheSnapshot(
        raw_text="windows_exporter_build_info 1\n",
        detected=WINDOWS,
        last_scrape_success=True,
        last_scrape_duration=0.03,
    )
    metrics.update_source_exporter(second, endpoint=ENDPOINT)

    output = generate_latest(metrics.registry).decode("utf-8")

    assert 'exporter="unknown"' not in output
    assert 'host_source_exporter_up{exporter="windows_exporter"} 1.0' in output
    # Only one series per metric should remain, including Info's own series.
    assert output.count("host_source_exporter_up{") == 1
    assert _data_lines(output, "host_source_exporter_info") == [
        'host_source_exporter_info{endpoint="http://127.0.0.1:9182/metrics",'
        'exporter="windows_exporter",version="0.31.6"} 1.0'
    ]


def test_update_source_exporter_no_series_before_any_successful_scrape():
    metrics = NormalizerMetrics(version="0.1.0")
    snapshot = CacheSnapshot(raw_text=None, detected=UNKNOWN, last_scrape_success=False)

    metrics.update_source_exporter(snapshot, endpoint=ENDPOINT)
    output = generate_latest(metrics.registry).decode("utf-8")

    assert _data_lines(output, "host_source_exporter_up") == []


def test_record_scrape_error_before_detection_uses_normalizer_errors():
    metrics = NormalizerMetrics(version="0.1.0")

    metrics.record_scrape_error()
    output = generate_latest(metrics.registry).decode("utf-8")

    assert "host_normalizer_errors_total 1.0" in output
    assert _data_lines(output, "host_source_exporter_errors_total") == []


def test_record_scrape_error_after_detection_uses_source_exporter_errors():
    metrics = NormalizerMetrics(version="0.1.0")
    snapshot = CacheSnapshot(
        raw_text="x", detected=WINDOWS, last_scrape_success=True, last_scrape_duration=0.01
    )
    metrics.update_source_exporter(snapshot, endpoint=ENDPOINT)

    metrics.record_scrape_error()
    output = generate_latest(metrics.registry).decode("utf-8")

    assert 'host_source_exporter_errors_total{exporter="windows_exporter"} 1.0' in output


def test_switching_exporter_label_resets_error_counter_for_new_label():
    metrics = NormalizerMetrics(version="0.1.0")
    metrics.update_source_exporter(
        CacheSnapshot(raw_text="x", detected=UNKNOWN, last_scrape_success=True),
        endpoint=ENDPOINT,
    )
    metrics.record_scrape_error()

    metrics.update_source_exporter(
        CacheSnapshot(raw_text="x", detected=NODE, last_scrape_success=True),
        endpoint=ENDPOINT,
    )
    output = generate_latest(metrics.registry).decode("utf-8")

    assert 'exporter="unknown"' not in output
    assert 'host_source_exporter_errors_total{exporter="node_exporter"} 0.0' in output
