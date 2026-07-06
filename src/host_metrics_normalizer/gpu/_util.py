from __future__ import annotations

import logging
import threading

_lock = threading.Lock()
_warned: set[str] = set()


def warn_once(logger: logging.Logger, key: str, message: str, *args: object, exc_info: bool = False) -> None:
    """Log `message` via `logger.warning` at most once per distinct `key` for the
    life of the process, so a persistently-failing GPU query doesn't spam the log
    on every single /metrics scrape."""
    with _lock:
        if key in _warned:
            return
        _warned.add(key)
    logger.warning(message, *args, exc_info=exc_info)
