"""Centralized logging: console + optional rotating file handlers."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from app.core.config import Settings

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    """Minimal structured JSON log formatter for file output."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "component": getattr(record, "component", "backend"),
        }
        for key in (
            "event",
            "request_id",
            "project_id",
            "job_id",
            "stage",
            "error_code",
            "env",
            "version",
            "data_root",
            "duration_ms",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None)
        suffix = f" request_id={request_id}" if request_id else ""
        base = super().format(record)
        return f"{base}{suffix}"


def setup_logging(settings: Settings) -> None:
    """Configure root logging once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, settings.log_level, logging.INFO)
    root = logging.getLogger()
    # Keep pytest LogCaptureHandler (and similar) so tests can still capture logs.
    preserved = [
        handler
        for handler in root.handlers
        if type(handler).__name__ == "LogCaptureHandler"
    ]
    root.handlers.clear()
    root.setLevel(level)
    for handler in preserved:
        root.addHandler(handler)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(
        ConsoleFormatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    root.addHandler(console)

    if settings.log_to_file:
        settings.logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            settings.logs_dir / "explainx.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(JsonFormatter())
        root.addHandler(file_handler)

    # Quiet noisy third-party loggers in production-ish modes
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
