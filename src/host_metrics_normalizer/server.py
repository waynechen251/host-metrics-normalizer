from __future__ import annotations

import json
import logging
import socketserver
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from prometheus_client.exposition import CONTENT_TYPE_LATEST, generate_latest

from .cache import RawMetricsCache
from .config import AppConfig
from .metrics import NormalizerMetrics

logger = logging.getLogger(__name__)


@dataclass
class HealthState:
    version: str
    status: str = "ok"
    source_exporter_up: bool = False
    last_scrape_success: bool = False
    last_scrape_timestamp: int = 0
    exporter: str = "unknown"
    exporter_version: str = ""
    os_family: str = "unknown"
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False, compare=False
    )

    def update(
        self,
        *,
        source_exporter_up: bool,
        last_scrape_success: bool,
        last_scrape_timestamp: int,
        exporter: str,
        exporter_version: str,
        os_family: str,
    ) -> None:
        with self._lock:
            self.source_exporter_up = source_exporter_up
            self.last_scrape_success = last_scrape_success
            self.last_scrape_timestamp = last_scrape_timestamp
            self.exporter = exporter
            self.exporter_version = exporter_version
            self.os_family = os_family

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "status": self.status,
                "version": self.version,
                "source_exporter_up": self.source_exporter_up,
                "last_scrape_success": self.last_scrape_success,
                "last_scrape_timestamp": self.last_scrape_timestamp,
                "exporter": self.exporter,
                "exporter_version": self.exporter_version,
                "os_family": self.os_family,
            }


def make_handler(
    config: AppConfig,
    metrics: NormalizerMetrics,
    health: HealthState,
    cache: RawMetricsCache,
) -> type[BaseHTTPRequestHandler]:
    class NormalizerRequestHandler(BaseHTTPRequestHandler):
        server_version = "host-metrics-normalizer/0.1"

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == config.server.metrics_path:
                self._handle_metrics()
            elif path == config.server.health_path:
                self._handle_health()
            elif path.startswith("/debug/"):
                self._handle_debug(path)
            elif path == "/":
                self._redirect(config.server.metrics_path)
            else:
                self._write_json(404, {"error": "not found"})

        def _handle_metrics(self) -> None:
            stale = cache.is_stale(config.cache.stale_after_seconds, time.monotonic())
            metrics.refresh_stale(stale)
            output = generate_latest(metrics.registry)
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(output)))
            self.end_headers()
            self.wfile.write(output)

        def _handle_health(self) -> None:
            self._write_json(200, health.snapshot())

        def _handle_debug(self, path: str) -> None:
            if not config.server.debug_enabled:
                self._write_json(404, {"error": "not found"})
                return
            if path == "/debug/raw":
                self._handle_debug_raw()
            elif path == "/debug/normalized":
                self._handle_debug_normalized()
            else:
                self._write_json(404, {"error": "not found"})

        def _handle_debug_raw(self) -> None:
            snapshot = cache.get()
            if snapshot.raw_text is None:
                self._write_text(503, "no source exporter data cached yet\n")
                return
            self._write_text(200, snapshot.raw_text)

        def _handle_debug_normalized(self) -> None:
            snapshot = cache.get()
            normalized = snapshot.normalized
            if normalized is None:
                self._write_json(503, {"error": "no normalized data cached yet"})
                return

            payload = normalized.to_dict()
            payload.update(
                {
                    "last_scrape_success": snapshot.last_scrape_success,
                    "last_scrape_timestamp": int(snapshot.last_scrape_wall or 0),
                    "last_scrape_duration_seconds": snapshot.last_scrape_duration,
                }
            )
            self._write_json(200, payload)

        def _redirect(self, location: str) -> None:
            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _write_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _write_text(self, status: int, text: str) -> None:
            body = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            logger.debug("%s - %s", self.address_string(), fmt % args)

    return NormalizerRequestHandler


class _NoFqdnHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer without the reverse-DNS lookup in server_bind().

    The base HTTPServer.server_bind() calls socket.getfqdn(host) purely to
    populate self.server_name, which this handler never reads. That lookup
    can block for several seconds (or longer with a misbehaving resolver),
    delaying service startup on every restart for no benefit here.
    """

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


class NormalizerHTTPServer:
    def __init__(
        self,
        config: AppConfig,
        metrics: NormalizerMetrics,
        health: HealthState,
        cache: RawMetricsCache,
    ):
        handler_cls = make_handler(config, metrics, health, cache)
        self._httpd = _NoFqdnHTTPServer(
            (config.server.listen_address, config.server.listen_port), handler_cls
        )

    @property
    def server_address(self) -> tuple[str, int]:
        return self._httpd.server_address

    def serve_forever(self) -> None:
        self._httpd.serve_forever()

    def shutdown(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
