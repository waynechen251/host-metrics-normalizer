import os
import sys

from host_metrics_normalizer.main import (
    DEFAULT_CONFIG_LINUX,
    DEFAULT_CONFIG_WINDOWS,
    _default_config_path,
)


def test_frozen_exe_defaults_to_config_next_to_executable(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\opt\hmn\host-metrics-normalizer.exe")

    result = _default_config_path()

    assert result == os.path.join(r"C:\opt\hmn", "config.yml")


def test_non_frozen_windows_uses_program_files_default(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(os, "name", "nt")

    result = _default_config_path()

    assert result == DEFAULT_CONFIG_WINDOWS


def test_non_frozen_posix_uses_etc_default(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(os, "name", "posix")

    result = _default_config_path()

    assert result == DEFAULT_CONFIG_LINUX
