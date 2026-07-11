"""Global exception handlers producing API error envelopes."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.middleware.request_id import get_request_id
from app.core.config import get_settings
from app.core.errors import ExplainXError
from app.shared.envelopes import error_payload

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ExplainXError)
    async def explainx_error_handler(request: Request, exc: ExplainXError) -> JSONResponse:
        request_id = get_request_id(request)
        logger.warning(
            exc.message,
            extra={
                "event": "app_error",
                "request_id": request_id,
                "error_code": exc.code,
                "component": "api",
            },
        )
        body = error_payload(
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            details=exc.details,
            retriable=exc.retriable,
            api_version=get_settings().api_version,
        )
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = get_request_id(request)
        fields = []
        for err in exc.errors():
            loc = [str(part) for part in err.get("loc", ()) if part != "body"]
            fields.append(
                {
                    "path": ".".join(loc) if loc else "body",
                    "message": err.get("msg", "Invalid value"),
                    "code": err.get("type", "value_error"),
                }
            )
        body = error_payload(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            request_id=request_id,
            details={"fields": fields},
            api_version=get_settings().api_version,
        )
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = get_request_id(request)
        code = "HTTP_ERROR"
        if exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 405:
            code = "METHOD_NOT_ALLOWED"
        body = error_payload(
            code=code,
            message=str(exc.detail),
            request_id=request_id,
            api_version=get_settings().api_version,
        )
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = get_request_id(request)
        logger.exception(
            "Unhandled exception",
            extra={
                "event": "unhandled_exception",
                "request_id": request_id,
                "error_code": "INTERNAL_ERROR",
                "component": "api",
            },
        )
        message = str(exc) if get_settings().debug else "An unexpected error occurred."
        body = error_payload(
            code="INTERNAL_ERROR",
            message=message,
            request_id=request_id,
            api_version=get_settings().api_version,
        )
        return JSONResponse(status_code=500, content=body)
