from prometheus_client import CollectorRegistry, Counter, Gauge, Info

from .cache import CacheSnapshot


class NormalizerMetrics:
    def __init__(
        self,
        version: str,
        config_version: str = "manual",
        config=None,
        cache=None,
    ):
        self.registry = CollectorRegistry()

        self.info = Info(
            "host_normalizer",
            "host-metrics-normalizer build info",
            registry=self.registry,
        )
        self.info.info({"version": version, "config_version": config_version})

        self.up = Gauge(
            "host_normalizer_up",
            "Whether the host-metrics-normalizer process is running",
            registry=self.registry,
        )
        self.scrape_duration = Gauge(
            "host_normalizer_scrape_duration_seconds",
            "Duration of the last source exporter scrape and normalization",
            registry=self.registry,
        )
        self.last_scrape_timestamp = Gauge(
            "host_normalizer_last_scrape_timestamp_seconds",
            "Unix timestamp of the last source exporter scrape attempt",
            registry=self.registry,
        )
        self.last_scrape_success = Gauge(
            "host_normalizer_last_scrape_success",
            "Whether the last source exporter scrape succeeded",
            registry=self.registry,
        )
        self.errors = Counter(
            "host_normalizer_errors",
            "Total number of normalizer errors",
            registry=self.registry,
        )
        self.stale = Gauge(
            "host_metrics_stale",
            "Whether the currently served metrics are stale",
            registry=self.registry,
        )

        self.source_info = Info(
            "host_source_exporter",
            "Detected source exporter build info",
            registry=self.registry,
        )
        self.source_up = Gauge(
            "host_source_exporter_up",
            "Whether the last scrape of the source exporter succeeded",
            ["exporter"],
            registry=self.registry,
        )
        self.source_scrape_duration = Gauge(
            "host_source_exporter_scrape_duration_seconds",
            "Duration of the last source exporter scrape",
            ["exporter"],
            registry=self.registry,
        )
        self.source_last_scrape_success = Gauge(
            "host_source_exporter_last_scrape_success",
            "Whether the last source exporter scrape succeeded",
            ["exporter"],
            registry=self.registry,
        )
        self.source_errors = Counter(
            "host_source_exporter_errors",
            "Total number of source exporter scrape errors",
            ["exporter"],
            registry=self.registry,
        )
        self._current_exporter_label: str | None = None

        self.up.set(1)
        self.scrape_duration.set(0)
        self.last_scrape_timestamp.set(0)
        self.last_scrape_success.set(0)
        self.stale.set(0)

        if config is not None and cache is not None:
            from .host_metrics import HostMetricsCollector

            self.registry.register(HostMetricsCollector(config, cache))

    def update_normalizer_scrape(self, snapshot: CacheSnapshot, stale: bool) -> None:
        self.scrape_duration.set(snapshot.last_scrape_duration)
        self.last_scrape_timestamp.set(snapshot.last_scrape_wall or 0)
        self.last_scrape_success.set(1 if snapshot.last_scrape_success else 0)
        self.stale.set(1 if stale else 0)

    def refresh_stale(self, stale: bool) -> None:
        self.stale.set(1 if stale else 0)

    def record_normalizer_error(self) -> None:
        self.errors.inc()

    def update_source_exporter(self, snapshot: CacheSnapshot, endpoint: str) -> None:
        detected = snapshot.detected
        if detected.type == "unknown" and snapshot.raw_text is None:
            # No successful scrape yet: emit nothing labeled, so we never
            # publish a transient exporter="unknown" series that would
            # linger in Prometheus once the real type is detected.
            return

        exporter = detected.type

        if exporter != self._current_exporter_label:
            if self._current_exporter_label is not None:
                self.source_errors.remove(self._current_exporter_label)
            self.source_up.clear()
            self.source_scrape_duration.clear()
            self.source_last_scrape_success.clear()
            self._current_exporter_label = exporter
            self.source_errors.labels(exporter=exporter)  # initialize series at 0

        self.source_up.labels(exporter=exporter).set(1 if snapshot.last_scrape_success else 0)
        self.source_scrape_duration.labels(exporter=exporter).set(snapshot.last_scrape_duration)
        self.source_last_scrape_success.labels(exporter=exporter).set(
            1 if snapshot.last_scrape_success else 0
        )
        self.source_info.info(
            {"exporter": exporter, "endpoint": endpoint, "version": detected.version}
        )

    def record_scrape_error(self) -> None:
        """Call when a source-exporter scrape attempt fails.

        Before the first successful scrape there is no exporter label to
        attribute the error to (per the label-stability policy above), so
        it is folded into the unlabeled host_normalizer_errors_total instead.
        """
        if self._current_exporter_label is not None:
            self.source_errors.labels(exporter=self._current_exporter_label).inc()
        else:
            self.errors.inc()
