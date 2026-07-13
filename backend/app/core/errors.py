"""Domain and HTTP-facing error types with stable error codes."""

from __future__ import annotations

from typing import Any


class ExplainXError(Exception):
    """Base application error with machine-readable code."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        retriable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.retriable = retriable


class NotFoundError(ExplainXError):
    def __init__(self, message: str, *, code: str = "NOT_FOUND", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code=code, status_code=404, details=details)


class ValidationAppError(ExplainXError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=422, details=details, retriable=False)


class ConflictError(ExplainXError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=409, details=details)


class OffTopicGenerationError(ExplainXError):
    """Narration failed deterministic topic verification after retries."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="OFF_TOPIC_GENERATION",
            status_code=422,
            details=details,
            retriable=False,
        )
