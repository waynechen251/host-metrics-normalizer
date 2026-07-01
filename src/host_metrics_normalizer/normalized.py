from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class NormalizedSeries:
    name: str
    value: float
    labels: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(
        cls,
        name: str,
        value: float,
        labels: Mapping[str, str] | None = None,
    ) -> "NormalizedSeries":
        items = tuple((str(key), str(val)) for key, val in (labels or {}).items())
        return cls(name=name, value=float(value), labels=items)

    def label_names(self) -> tuple[str, ...]:
        return tuple(key for key, _ in self.labels)

    def label_values(self) -> tuple[str, ...]:
        return tuple(value for _, value in self.labels)

    def label_dict(self) -> dict[str, str]:
        return dict(self.labels)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "value": self.value,
            "labels": self.label_dict(),
        }


@dataclass(frozen=True)
class NormalizedSnapshot:
    status: str
    supported: bool
    exporter: str
    version: str
    os_family: str
    host: str
    series: tuple[NormalizedSeries, ...] = field(default_factory=tuple)
    missing_metrics: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    parsed_metric_names: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "supported": self.supported,
            "exporter": self.exporter,
            "version": self.version,
            "os_family": self.os_family,
            "host": self.host,
            "series": [series.to_dict() for series in self.series],
            "missing_metrics": list(self.missing_metrics),
            "notes": list(self.notes),
            "parsed_metric_names": list(self.parsed_metric_names),
        }


def unsupported_snapshot(
    *,
    status: str,
    exporter: str,
    version: str,
    os_family: str,
    host: str,
    notes: tuple[str, ...] = (),
) -> NormalizedSnapshot:
    return NormalizedSnapshot(
        status=status,
        supported=False,
        exporter=exporter,
        version=version,
        os_family=os_family,
        host=host,
        series=(),
        missing_metrics=(),
        notes=notes,
        parsed_metric_names=(),
    )
