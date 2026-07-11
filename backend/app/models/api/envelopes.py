"""API response envelopes matching docs/API_SPECIFICATION.md."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class ResponseMeta(BaseModel):
    request_id: str
    api_version: str = "v1"
    timestamp: str = Field(default_factory=utc_now_iso)


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: ResponseMeta


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    retriable: bool = False
    docs_url: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody
    meta: ResponseMeta


def success_payload(data: Any, *, request_id: str, api_version: str = "v1") -> dict[str, Any]:
    return SuccessResponse(
        data=data,
        meta=ResponseMeta(request_id=request_id, api_version=api_version),
    ).model_dump()


def error_payload(
    *,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
    retriable: bool = False,
    api_version: str = "v1",
) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=details or {},
            retriable=retriable,
        ),
        meta=ResponseMeta(request_id=request_id, api_version=api_version),
    ).model_dump()
