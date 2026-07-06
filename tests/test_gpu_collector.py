from host_metrics_normalizer.config import (
    AppConfig,
    AssetConfig,
    CacheConfig,
    GpuConfig,
    NormalizationConfig,
    ServerConfig,
    SourceExporterConfig,
)
from host_metrics_normalizer.gpu import collector as gpu_collector
from host_metrics_normalizer.normalized import NormalizedSeries


def build_config(gpu_enabled: bool = True, hostname: str = "srv-app-01") -> AppConfig:
    return AppConfig(
        server=ServerConfig(),
        source_exporter=SourceExporterConfig(endpoint="http://127.0.0.1:9182/metrics"),
        cache=CacheConfig(),
        asset=AssetConfig(hostname=hostname),
        labels={},
        normalization=NormalizationConfig(),
        gpu=GpuConfig(enabled=gpu_enabled),
    )


def test_collect_gpu_series_dispatches_to_linux(monkeypatch):
    called_with = {}

    def _fake_linux_collect(host, **kwargs):
        called_with["host"] = host
        return (NormalizedSeries.from_mapping("host_gpu_info", 1.0, {"host": host}),)

    monkeypatch.setattr(gpu_collector._linux, "collect", _fake_linux_collect)

    series = gpu_collector.collect_gpu_series("srv-01", system="Linux")

    assert called_with["host"] == "srv-01"
    assert series[0].name == "host_gpu_info"


def test_collect_gpu_series_dispatches_to_windows(monkeypatch):
    called = {}

    def _fake_windows_collect(host, *, state, **kwargs):
        called["host"] = host
        called["state"] = state
        return ()

    monkeypatch.setattr(gpu_collector._windows, "collect", _fake_windows_collect)

    gpu_collector.collect_gpu_series("srv-01", system="Windows")

    assert called["host"] == "srv-01"
    assert called["state"] is not None


def test_collect_gpu_series_unknown_platform_returns_empty():
    assert gpu_collector.collect_gpu_series("srv-01", system="Darwin") == ()


def test_collect_gpu_series_swallows_unexpected_exceptions(monkeypatch):
    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(gpu_collector._linux, "collect", _raise)

    series = gpu_collector.collect_gpu_series("srv-01", system="Linux")

    assert series == ()


def test_gpu_metrics_collector_collect_series_resolves_host_from_config(monkeypatch):
    monkeypatch.setattr(
        gpu_collector,
        "collect_gpu_series",
        lambda host, **kwargs: (NormalizedSeries.from_mapping("host_gpu_info", 1.0, {"host": host}),),
    )
    config = build_config(hostname="from-config")
    collector = gpu_collector.GpuMetricsCollector(config)

    series = collector.collect_series()

    assert series[0].label_dict()["host"] == "from-config"


def test_gpu_metrics_collector_collect_shares_same_series_via_build_metric_families(monkeypatch):
    monkeypatch.setattr(
        gpu_collector,
        "collect_gpu_series",
        lambda host, **kwargs: (
            NormalizedSeries.from_mapping("host_gpu_utilization_percent", 12.0, {"host": host, "gpu": "0"}),
        ),
    )
    config = build_config()
    collector = gpu_collector.GpuMetricsCollector(config)

    families = list(collector.collect())

    assert len(families) == 1
    assert families[0].name == "host_gpu_utilization_percent"
