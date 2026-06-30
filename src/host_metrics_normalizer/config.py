from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    pass


def _filter_known(data: dict[str, Any], known_fields: set[str]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if key in known_fields}


@dataclass(frozen=True)
class ServerConfig:
    listen_address: str = "0.0.0.0"
    listen_port: int = 9527
    metrics_path: str = "/metrics"
    health_path: str = "/healthz"
    debug_enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServerConfig":
        known = _filter_known(data, set(cls.__dataclass_fields__))
        return cls(**known)


@dataclass(frozen=True)
class SourceExporterConfig:
    endpoint: str
    timeout_seconds: int = 3

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceExporterConfig":
        if not data:
            raise ConfigError("Missing required config section: source_exporter")
        endpoint = data.get("endpoint")
        if not endpoint:
            raise ConfigError("source_exporter.endpoint is required")
        known = _filter_known(data, set(cls.__dataclass_fields__))
        return cls(**known)


@dataclass(frozen=True)
class CacheConfig:
    enabled: bool = True
    ttl_seconds: int = 60
    stale_after_seconds: int = 180

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheConfig":
        known = _filter_known(data, set(cls.__dataclass_fields__))
        return cls(**known)


@dataclass(frozen=True)
class AssetConfig:
    asset_id: str = ""
    hostname: str = ""
    display_name: str = ""
    owner: str = ""
    environment: str = ""
    location: str = ""
    role: str = ""
    criticality: str = ""
    managed_by: str = ""
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetConfig":
        known = _filter_known(data, set(cls.__dataclass_fields__))
        return cls(**known)


@dataclass(frozen=True)
class NormalizationConfig:
    filesystem_ignore_regex: tuple[str, ...] = field(default_factory=tuple)
    network_ignore_regex: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NormalizationConfig":
        known = _filter_known(data, set(cls.__dataclass_fields__))
        if "filesystem_ignore_regex" in known:
            known["filesystem_ignore_regex"] = tuple(known["filesystem_ignore_regex"])
        if "network_ignore_regex" in known:
            known["network_ignore_regex"] = tuple(known["network_ignore_regex"])
        return cls(**known)


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    source_exporter: SourceExporterConfig
    cache: CacheConfig
    asset: AssetConfig
    labels: dict[str, str]
    normalization: NormalizationConfig


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw_text = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML config '{config_path}': {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError(
            f"Invalid config structure in '{config_path}': expected a mapping at the top level"
        )

    labels_raw = data.get("labels") or {}
    if not isinstance(labels_raw, dict):
        raise ConfigError("labels must be a mapping of string keys to values")
    labels = {str(key): str(value) for key, value in labels_raw.items()}

    try:
        return AppConfig(
            server=ServerConfig.from_dict(data.get("server") or {}),
            source_exporter=SourceExporterConfig.from_dict(data.get("source_exporter") or {}),
            cache=CacheConfig.from_dict(data.get("cache") or {}),
            asset=AssetConfig.from_dict(data.get("asset") or {}),
            labels=labels,
            normalization=NormalizationConfig.from_dict(data.get("normalization") or {}),
        )
    except ConfigError:
        raise
    except TypeError as exc:
        raise ConfigError(f"Invalid config structure in '{config_path}': {exc}") from exc
