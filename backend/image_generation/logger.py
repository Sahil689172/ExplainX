"""Structured logging for generation jobs."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from image_generation.models import GenerationJob, GenerationStatus


def get_engine_logger(name: str = "image_generation") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


class GenerationJobLogger:
    """Logs structured fields for each generation job lifecycle event."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._log = logger or get_engine_logger()

    def job_started(self, job: GenerationJob) -> None:
        self._emit(
            "JOB_START",
            job,
            extra={"status": job.status.value},
        )

    def job_finished(self, job: GenerationJob) -> None:
        self._emit(
            "JOB_END",
            job,
            extra={
                "status": job.status.value,
                "duration_ms": job.duration_ms,
                "error": job.error,
            },
        )

    def job_failed(self, job: GenerationJob, error: str) -> None:
        self._emit(
            "JOB_FAIL",
            job,
            level=logging.ERROR,
            extra={"status": GenerationStatus.FAILED.value, "error": error},
        )

    def info(self, message: str, **fields: Any) -> None:
        self._log.info(self._format(message, fields))

    def error(self, message: str, **fields: Any) -> None:
        self._log.error(self._format(message, fields))

    def _emit(
        self,
        event: str,
        job: GenerationJob,
        *,
        level: int = logging.INFO,
        extra: dict[str, Any] | None = None,
    ) -> None:
        fields: dict[str, Any] = {
            "event": event,
            "job_id": str(job.job_id),
            "request_id": str(job.request.request_id),
            "backend": job.backend_id,
            "start_time": _fmt(job.started_at),
            "end_time": _fmt(job.finished_at),
            "duration_ms": job.duration_ms,
            "status": job.status.value,
        }
        if extra:
            fields.update(extra)
        self._log.log(level, self._format(event, fields))

    @staticmethod
    def _format(message: str, fields: dict[str, Any]) -> str:
        parts = [message]
        for key, value in fields.items():
            if value is None:
                continue
            parts.append(f"{key}={value}")
        return " ".join(parts)


def _fmt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def format_uuid(value: UUID) -> str:
    return str(value)
