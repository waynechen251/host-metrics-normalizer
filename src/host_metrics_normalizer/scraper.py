from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrapeResult:
    success: bool
    raw_text: str | None
    duration_seconds: float
    status_code: int | None
    error_kind: str | None


def scrape(endpoint: str, timeout_seconds: float) -> ScrapeResult:
    start = time.perf_counter()
    try:
        response = requests.get(endpoint, timeout=timeout_seconds)
    except requests.exceptions.Timeout:
        duration = time.perf_counter() - start
        logger.warning("Scrape of %s timed out after %.3fs", endpoint, duration)
        return ScrapeResult(
            success=False,
            raw_text=None,
            duration_seconds=duration,
            status_code=None,
            error_kind="timeout",
        )
    except requests.exceptions.ConnectionError as exc:
        duration = time.perf_counter() - start
        logger.warning("Scrape of %s failed to connect: %s", endpoint, exc)
        return ScrapeResult(
            success=False,
            raw_text=None,
            duration_seconds=duration,
            status_code=None,
            error_kind="connection_error",
        )
    except requests.exceptions.RequestException as exc:
        duration = time.perf_counter() - start
        logger.warning("Scrape of %s failed: %s", endpoint, exc)
        return ScrapeResult(
            success=False,
            raw_text=None,
            duration_seconds=duration,
            status_code=None,
            error_kind="request_error",
        )

    duration = time.perf_counter() - start

    if response.status_code != 200:
        logger.warning(
            "Scrape of %s returned unexpected status %s", endpoint, response.status_code
        )
        return ScrapeResult(
            success=False,
            raw_text=None,
            duration_seconds=duration,
            status_code=response.status_code,
            error_kind="http_status",
        )

    return ScrapeResult(
        success=True,
        raw_text=response.text,
        duration_seconds=duration,
        status_code=response.status_code,
        error_kind=None,
    )
