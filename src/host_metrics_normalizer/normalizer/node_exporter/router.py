from __future__ import annotations

import logging
from typing import Callable

from ...detect import DetectedExporter
from ...normalized import NormalizedSnapshot, unsupported_snapshot
from ...parser.prometheus_text import family_map
from . import v1_10_2

logger = logging.getLogger(__name__)

_VersionHandler = Callable[..., NormalizedSnapshot]

_VERSION_HANDLERS: dict[str, _VersionHandler] = {
    "1.10.2": v1_10_2.normalize,
}

SUPPORTED_NODE_EXPORTER_VERSIONS = frozenset(_VERSION_HANDLERS)


def normalize_node_exporter(
    raw_text: str,
    detected: DetectedExporter,
    *,
    host: str,
    now: float | None = None,
) -> NormalizedSnapshot:
    if detected.type != "node_exporter":
        return unsupported_snapshot(
            status="unsupported_exporter",
            exporter=detected.type,
            version=detected.version,
            os_family=detected.os_family,
            host=host,
            notes=("source exporter is not node_exporter",),
        )

    handler = _VERSION_HANDLERS.get(detected.version)
    if handler is None:
        return unsupported_snapshot(
            status="unsupported_version",
            exporter=detected.type,
            version=detected.version,
            os_family=detected.os_family,
            host=host,
            notes=(f"unsupported node_exporter version: {detected.version or 'unknown'}",),
        )

    try:
        families = family_map(raw_text)
    except Exception:
        logger.exception("Failed to parse node_exporter exposition")
        return unsupported_snapshot(
            status="parse_error",
            exporter=detected.type,
            version=detected.version,
            os_family=detected.os_family,
            host=host,
            notes=("failed to parse node_exporter exposition",),
        )

    return handler(families, detected, host=host, now=now)
