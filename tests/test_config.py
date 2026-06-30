import dataclasses

import pytest

from host_metrics_normalizer.config import ConfigError, load_config

FULL_CONFIG = """
server:
  listen_address: "0.0.0.0"
  listen_port: 9527
  metrics_path: "/metrics"
  health_path: "/healthz"
  debug_enabled: true

source_exporter:
  endpoint: "http://127.0.0.1:9182/metrics"
  timeout_seconds: 3

cache:
  enabled: true
  ttl_seconds: 60
  stale_after_seconds: 180

asset:
  asset_id: "ASSET-001"
  hostname: "srv-app-01"
  display_name: "App Server 01"
  owner: "infra"
  environment: "prod"
  location: "office-3f"
  role: "app-server"
  criticality: "medium"
  managed_by: "wayne"
  note: "VMware Workstation host"

labels:
  site: "hq"
  team: "infra"
  platform_group: "legacy-pc"

normalization:
  filesystem_ignore_regex:
    - "^/run"
    - "^/sys"
  network_ignore_regex:
    - "^Loopback"
    - "^lo$"
"""

MINIMAL_CONFIG = """
source_exporter:
  endpoint: "http://127.0.0.1:9100/metrics"
"""


def write_config(tmp_path, content):
    config_path = tmp_path / "config.yml"
    config_path.write_text(content, encoding="utf-8")
    return config_path


def test_full_config_loads_all_sections(tmp_path):
    config_path = write_config(tmp_path, FULL_CONFIG)

    config = load_config(config_path)

    assert config.server.listen_address == "0.0.0.0"
    assert config.server.listen_port == 9527
    assert config.server.metrics_path == "/metrics"
    assert config.server.health_path == "/healthz"
    assert config.server.debug_enabled is True

    assert config.source_exporter.endpoint == "http://127.0.0.1:9182/metrics"
    assert config.source_exporter.timeout_seconds == 3

    assert config.cache.enabled is True
    assert config.cache.ttl_seconds == 60
    assert config.cache.stale_after_seconds == 180

    assert config.asset.asset_id == "ASSET-001"
    assert config.asset.hostname == "srv-app-01"

    assert config.labels["site"] == "hq"
    assert config.labels["team"] == "infra"

    assert "^/run" in config.normalization.filesystem_ignore_regex
    assert "^Loopback" in config.normalization.network_ignore_regex


def test_minimal_config_falls_back_to_defaults(tmp_path):
    config_path = write_config(tmp_path, MINIMAL_CONFIG)

    config = load_config(config_path)

    assert config.server.listen_port == 9527
    assert config.server.debug_enabled is True
    assert config.cache.ttl_seconds == 60
    assert config.asset.asset_id == ""
    assert config.labels == {}
    assert config.normalization.filesystem_ignore_regex == ()


def test_missing_source_exporter_section_raises(tmp_path):
    config_path = write_config(tmp_path, "server:\n  listen_port: 9527\n")

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_missing_source_exporter_endpoint_raises(tmp_path):
    config_path = write_config(tmp_path, "source_exporter:\n  timeout_seconds: 5\n")

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_source_exporter_type_field_is_ignored_if_present(tmp_path):
    """type is no longer a config field; auto-detection makes it obsolete.
    A stray `type:` key should simply be ignored like any unknown field."""
    config_path = write_config(
        tmp_path,
        "source_exporter:\n  type: \"windows_exporter\"\n  endpoint: \"http://127.0.0.1:9100/metrics\"\n",
    )

    config = load_config(config_path)

    assert config.source_exporter.endpoint == "http://127.0.0.1:9100/metrics"
    assert not hasattr(config.source_exporter, "type")


def test_missing_file_raises(tmp_path):
    missing_path = tmp_path / "does-not-exist.yml"

    with pytest.raises(ConfigError):
        load_config(missing_path)


def test_invalid_yaml_raises(tmp_path):
    config_path = write_config(tmp_path, "server: [unterminated\n")

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_non_mapping_top_level_raises(tmp_path):
    config_path = write_config(tmp_path, "- just\n- a\n- list\n")

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_labels_values_are_normalized_to_strings(tmp_path):
    config_path = write_config(
        tmp_path,
        MINIMAL_CONFIG + "\nlabels:\n  team: 123\n",
    )

    config = load_config(config_path)

    assert config.labels["team"] == "123"


def test_unknown_fields_are_ignored(tmp_path):
    config_path = write_config(
        tmp_path,
        MINIMAL_CONFIG + "\nserver:\n  foo: bar\n  listen_port: 9999\n",
    )

    config = load_config(config_path)

    assert config.server.listen_port == 9999
    assert not hasattr(config.server, "foo")


def test_app_config_is_frozen(tmp_path):
    config_path = write_config(tmp_path, MINIMAL_CONFIG)
    config = load_config(config_path)

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.server.listen_port = 1
