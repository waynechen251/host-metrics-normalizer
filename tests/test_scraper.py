import requests

from host_metrics_normalizer.scraper import scrape

VALID_ERROR_KINDS = {"timeout", "connection_error", "http_status", "request_error"}


class _FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


def test_scrape_success(monkeypatch):
    def fake_get(url, timeout):
        assert url == "http://127.0.0.1:9182/metrics"
        assert timeout == 3
        return _FakeResponse(200, "metric_a 1\n")

    monkeypatch.setattr(requests, "get", fake_get)

    result = scrape("http://127.0.0.1:9182/metrics", timeout_seconds=3)

    assert result.success is True
    assert result.raw_text == "metric_a 1\n"
    assert result.status_code == 200
    assert result.error_kind is None
    assert result.duration_seconds >= 0


def test_scrape_timeout(monkeypatch):
    def fake_get(url, timeout):
        raise requests.exceptions.Timeout("timed out")

    monkeypatch.setattr(requests, "get", fake_get)

    result = scrape("http://127.0.0.1:9182/metrics", timeout_seconds=3)

    assert result.success is False
    assert result.raw_text is None
    assert result.error_kind == "timeout"
    assert result.error_kind in VALID_ERROR_KINDS


def test_scrape_connection_error(monkeypatch):
    def fake_get(url, timeout):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(requests, "get", fake_get)

    result = scrape("http://127.0.0.1:9182/metrics", timeout_seconds=3)

    assert result.success is False
    assert result.error_kind == "connection_error"


def test_scrape_http_error_status(monkeypatch):
    def fake_get(url, timeout):
        return _FakeResponse(500, "")

    monkeypatch.setattr(requests, "get", fake_get)

    result = scrape("http://127.0.0.1:9182/metrics", timeout_seconds=3)

    assert result.success is False
    assert result.raw_text is None
    assert result.status_code == 500
    assert result.error_kind == "http_status"


def test_scrape_generic_request_exception(monkeypatch):
    def fake_get(url, timeout):
        raise requests.exceptions.RequestException("something else")

    monkeypatch.setattr(requests, "get", fake_get)

    result = scrape("http://127.0.0.1:9182/metrics", timeout_seconds=3)

    assert result.success is False
    assert result.error_kind == "request_error"


def test_error_kind_never_contains_exception_text(monkeypatch):
    secret_message = "password=hunter2 leaked-in-traceback"

    def fake_get(url, timeout):
        raise requests.exceptions.ConnectionError(secret_message)

    monkeypatch.setattr(requests, "get", fake_get)

    result = scrape("http://127.0.0.1:9182/metrics", timeout_seconds=3)

    assert result.error_kind in VALID_ERROR_KINDS
    assert secret_message not in (result.error_kind or "")
