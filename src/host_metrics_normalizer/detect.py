from __future__ import annotations

import logging
from dataclasses import dataclass

from prometheus_client.parser import text_string_to_metric_families

logger = logging.getLogger(__name__)

_BUILD_INFO_FAMILIES = {
    "windows_exporter_build_info": ("windows_exporter", "windows"),
    "node_exporter_build_info": ("node_exporter", "linux"),
}


@dataclass(frozen=True)
class DetectedExporter:
    type: str
    os_family: str
    version: str


UNKNOWN = DetectedExporter(type="unknown", os_family="unknown", version="")


def detect_from_raw(raw_text: str) -> DetectedExporter:
    matches: list[DetectedExporter] = []

    try:
        families = list(text_string_to_metric_families(raw_text))
    except Exception:
        logger.warning("Failed to parse raw exporter metrics for auto-detection", exc_info=True)
        return UNKNOWN

    for family in families:
        mapping = _BUILD_INFO_FAMILIES.get(family.name)
        if mapping is None:
            continue
        exporter_type, os_family = mapping
        version = ""
        for sample in family.samples:
            if sample.name == family.name:
                version = sample.labels.get("version", "")
                break
        matches.append(DetectedExporter(type=exporter_type, os_family=os_family, version=version))

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        logger.warning(
            "Multiple exporter build_info families found in raw metrics (%s); "
            "cannot determine exporter type unambiguously",
            [m.type for m in matches],
        )
    return UNKNOWN
