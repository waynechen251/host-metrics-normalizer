from __future__ import annotations

from ..normalized import NormalizedSeries


def _first_family_value(families: dict[str, object], *names: str) -> float | None:
    family = _first_family(families, *names)
    if family is None:
        return None
    return _first_sample_value(family)


def _first_family(families: dict[str, object], *names: str):
    for name in names:
        family = families.get(name)
        if family is not None:
            return family
    return None


def _first_sample_value(family) -> float | None:
    if family is None:
        return None
    samples = getattr(family, "samples", ())
    if not samples:
        return None
    return float(samples[0].value)


def _first_label(family, *keys: str) -> str:
    if family is None:
        return ""
    samples = getattr(family, "samples", ())
    for sample in samples:
        labels = getattr(sample, "labels", {}) or {}
        for key in keys:
            value = labels.get(key)
            if value:
                return str(value)
    return ""


def _first_non_empty(labels: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = labels.get(key)
        if value:
            return str(value)
    return ""


def _normalize_architecture(goarch: str) -> str:
    mapping = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "aarch64",
        "aarch64": "aarch64",
        "386": "x86",
    }
    return mapping.get(goarch, goarch)


def _cpu_usage_percent(family) -> float | None:
    samples = getattr(family, "samples", ())
    if not samples:
        return None
    total = 0.0
    idle = 0.0
    for sample in samples:
        value = float(sample.value)
        total += value
        mode = str((getattr(sample, "labels", {}) or {}).get("mode", "")).lower()
        if mode == "idle":
            idle += value
    if total <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1.0 - idle / total)))


def _distinct_label_count(family, label_key: str) -> int | None:
    values = {
        str((getattr(sample, "labels", {}) or {}).get(label_key, ""))
        for sample in getattr(family, "samples", ())
        if (getattr(sample, "labels", {}) or {}).get(label_key)
    }
    return len(values) if values else None


def _labeled_series(family, metric_name: str, host: str, label_key: str, *label_source_keys: str) -> list[NormalizedSeries]:
    series: list[NormalizedSeries] = []
    for sample in getattr(family, "samples", ()):
        labels = getattr(sample, "labels", {}) or {}
        label_value = _first_non_empty(labels, *label_source_keys)
        series.append(
            NormalizedSeries.from_mapping(
                metric_name,
                float(sample.value),
                {"host": host, label_key: label_value},
            )
        )
    return series


def _uptime_seconds(boot_family, now: float) -> float | None:
    boot_time = _first_sample_value(boot_family)
    if boot_time is None:
        return None
    return max(0.0, now - boot_time)
