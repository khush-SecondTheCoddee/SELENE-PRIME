"""Structured JSON logging helpers without configuring the root logger."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, TextIO

_RESERVED = frozenset(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
}


class JsonLineFormatter(logging.Formatter):
    """Format a log record as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC)
        payload: dict[str, object] = {
            "timestamp": timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED and not key.startswith("_")
        }
        if fields:
            payload["fields"] = fields
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)


def configure_logging(level: int | str = logging.INFO, *, stream: TextIO | None = None) -> logging.Logger:
    """Configure the package logger only; leave the root logger untouched.

    Calling this more than once updates the existing package handler rather than
    adding duplicate output handlers.
    """
    logger = logging.getLogger("selene_prime")
    logger.setLevel(level)
    logger.propagate = False
    handler: logging.StreamHandler[Any] | None = None
    for candidate in logger.handlers:
        if getattr(candidate, "_selene_handler", False) and isinstance(
            candidate, logging.StreamHandler
        ):
            handler = candidate
            break
    if handler is None:
        handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
        handler.setFormatter(JsonLineFormatter())
        setattr(handler, "_selene_handler", True)
        logger.addHandler(handler)
    else:
        handler.setStream(stream if stream is not None else sys.stderr)
    return logger
