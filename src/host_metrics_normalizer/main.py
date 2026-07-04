from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading

from . import __version__
from .cache import RawMetricsCache
from .config import ConfigError, load_config
from .logging_config import setup_logging
from .metrics import NormalizerMetrics
from .refresher import MetricsRefresher
from .server import HealthState, NormalizerHTTPServer

DEFAULT_CONFIG_WINDOWS = r"C:\Program Files\host-metrics-normalizer\config.yml"
DEFAULT_CONFIG_LINUX = "/etc/host-metrics-normalizer/config.yml"


def _default_config_path() -> str:
    if getattr(sys, "frozen", False):
        # Packaged PyInstaller exe: default to config.yml next to the executable.
        return os.path.join(os.path.dirname(sys.executable), "config.yml")
    return DEFAULT_CONFIG_WINDOWS if os.name == "nt" else DEFAULT_CONFIG_LINUX


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="host-metrics-normalizer",
        description="Cross-platform host metrics normalization layer for Prometheus and Grafana.",
    )
    parser.add_argument(
        "--config",
        default=_default_config_path(),
        help="Path to config.yml (default: %(default)s)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    setup_logging()
    log = logging.getLogger(__name__)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        log.error("Failed to load config: %s", exc)
        return 2

    log.info("Config loaded from %s", args.config)

    cache = RawMetricsCache()
    metrics = NormalizerMetrics(version=__version__, config_version="manual", config=config, cache=cache)
    health = HealthState(version=__version__)
    refresher = MetricsRefresher(config, cache, metrics, health)
    server = NormalizerHTTPServer(config, metrics, health, cache, refresher)

    stop_event = threading.Event()

    def _handle_stop_signal(signum, frame):
        log.info("Received signal %s, shutting down", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_stop_signal)
    signal.signal(signal.SIGTERM, _handle_stop_signal)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    log.info(
        "Listening on %s:%s",
        config.server.listen_address,
        server.server_address[1],
    )
    log.info(
        "On-demand scrape mode: each /metrics request triggers a live scrape of %s (timeout=%ss)",
        config.source_exporter.endpoint,
        config.source_exporter.timeout_seconds,
    )

    stop_event.wait()
    server.shutdown()
    server_thread.join(timeout=5)

    log.info("Server stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
