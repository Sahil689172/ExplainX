"""Request size / payload guard middleware.

Field-level validation is performed by Pydantic on route models; failed
checks are normalized by ``RequestValidationError`` in the global exception
handler. This middleware rejects obviously oversized bodies early.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.api.middleware.request_id import get_request_id
from app.core.config import get_settings
from app.models.api.envelopes import error_payload

# 32 MiB default — large enough for future document uploads; tune later.
DEFAULT_MAX_BODY_BYTES = 32 * 1024 * 1024


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds the configured maximum."""

    def __init__(self, app, max_body_bytes: int = DEFAULT_MAX_BODY_BYTES) -> None:
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                body = error_payload(
                    code="VALIDATION_ERROR",
                    message="Invalid Content-Length header.",
                    request_id=get_request_id(request),
                    details={"fields": [{"path": "content-length", "message": "must be an integer", "code": "type_error"}]},
                    api_version=get_settings().api_version,
                )
                return JSONResponse(status_code=400, content=body)
            if length > self.max_body_bytes:
                body = error_payload(
                    code="PAYLOAD_TOO_LARGE",
                    message="Request body exceeds the maximum allowed size.",
                    request_id=get_request_id(request),
                    details={"max_bytes": self.max_body_bytes, "content_length": length},
                    api_version=get_settings().api_version,
                )
                return JSONResponse(status_code=413, content=body)
        return await call_next(request)
