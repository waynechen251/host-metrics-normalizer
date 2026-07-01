from __future__ import annotations

import logging
import socket

from .config import AppConfig
from .detect import DetectedExporter
from .normalized import NormalizedSnapshot, unsupported_snapshot
from .normalizer import normalize_windows_exporter

logger = logging.getLogger(__name__)


def resolve_host_label(config: AppConfig) -> str:
    if config.asset.hostname:
        return config.asset.hostname
    return socket.gethostname()


def normalize_exporter_metrics(
    config: AppConfig,
    detected: DetectedExporter,
    raw_text: str,
    *,
    now: float | None = None,
) -> NormalizedSnapshot:
    host = resolve_host_label(config)

    try:
        if detected.type == "windows_exporter":
            return normalize_windows_exporter(raw_text, detected, host=host, now=now)
    except Exception:
        logger.exception("Normalization failed for exporter=%s version=%s", detected.type, detected.version)
        return unsupported_snapshot(
            status="parse_error",
            exporter=detected.type,
            version=detected.version,
            os_family=detected.os_family,
            host=host,
            notes=("normalization failed",),
        )

    return unsupported_snapshot(
        status="unsupported_exporter",
        exporter=detected.type,
        version=detected.version,
        os_family=detected.os_family,
        host=host,
        notes=("no normalizer registered for detected exporter",),
    )
