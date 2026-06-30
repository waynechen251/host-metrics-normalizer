from pathlib import Path

from host_metrics_normalizer.detect import UNKNOWN, detect_from_raw

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_detects_windows_exporter():
    raw = _read_fixture("windows_exporter.metrics")

    result = detect_from_raw(raw)

    assert result.type == "windows_exporter"
    assert result.os_family == "windows"
    assert result.version == "0.31.6"


def test_detects_node_exporter():
    raw = _read_fixture("node_exporter.metrics")

    result = detect_from_raw(raw)

    assert result.type == "node_exporter"
    assert result.os_family == "linux"
    assert result.version == "1.8.2"


def test_unknown_exporter_returns_unknown():
    raw = _read_fixture("unknown.metrics")

    result = detect_from_raw(raw)

    assert result == UNKNOWN


def test_go_build_info_alone_does_not_trigger_false_positive():
    raw = (
        '# TYPE go_build_info gauge\n'
        'go_build_info{path="example.com/x",version="v0.31.6+dirty"} 1\n'
    )

    result = detect_from_raw(raw)

    assert result == UNKNOWN


def test_empty_text_returns_unknown():
    assert detect_from_raw("") == UNKNOWN


def test_malformed_text_does_not_raise():
    result = detect_from_raw("this is not valid prometheus exposition format {{{")

    assert result == UNKNOWN


def test_missing_version_label_returns_empty_string():
    raw = (
        '# TYPE windows_exporter_build_info gauge\n'
        'windows_exporter_build_info{goos="windows"} 1\n'
    )

    result = detect_from_raw(raw)

    assert result.type == "windows_exporter"
    assert result.os_family == "windows"
    assert result.version == ""


def test_both_build_info_present_returns_unknown():
    raw = (
        '# TYPE windows_exporter_build_info gauge\n'
        'windows_exporter_build_info{goos="windows",version="0.31.6"} 1\n'
        '# TYPE node_exporter_build_info gauge\n'
        'node_exporter_build_info{goos="linux",version="1.8.2"} 1\n'
    )

    result = detect_from_raw(raw)

    assert result == UNKNOWN
