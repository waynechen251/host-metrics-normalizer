from __future__ import annotations

import logging
from typing import Callable

from ...detect import DetectedExporter
from ...normalized import NormalizedSnapshot, unsupported_snapshot
from ...parser.prometheus_text import family_map
from . import v0_30_6, v0_31_6, v0_31_7

logger = logging.getLogger(__name__)

_VersionHandler = Callable[..., NormalizedSnapshot]

_VERSION_HANDLERS: dict[str, _VersionHandler] = {
    "0.30.6": v0_30_6.normalize,
    "0.31.6": v0_31_6.normalize,
    "0.31.7": v0_31_7.normalize,
}

SUPPORTED_WINDOWS_EXPORTER_VERSIONS = frozenset(_VERSION_HANDLERS)


def normalize_windows_exporter(
    raw_text: str,
    detected: DetectedExporter,
    *,
    host: str,
    now: float | None = None,
) -> NormalizedSnapshot:
    if detected.type != "windows_exporter":
        return unsupported_snapshot(
            status="unsupported_exporter",
            exporter=detected.type,
            version=detected.version,
            os_family=detected.os_family,
            host=host,
            notes=("source exporter is not windows_exporter",),
        )

    handler = _VERSION_HANDLERS.get(detected.version)
    if handler is None:
        return unsupported_snapshot(
            status="unsupported_version",
            exporter=detected.type,
            version=detected.version,
            os_family=detected.os_family,
            host=host,
            notes=(f"unsupported windows_exporter version: {detected.version or 'unknown'}",),
        )

    try:
        families = family_map(raw_text)
    except Exception:
        logger.exception("Failed to parse windows_exporter exposition")
        return unsupported_snapshot(
            status="parse_error",
            exporter=detected.type,
            version=detected.version,
            os_family=detected.os_family,
            host=host,
            notes=("failed to parse windows_exporter exposition",),
        )

    return handler(families, detected, host=host, now=now)
