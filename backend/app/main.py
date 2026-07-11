"""ExplainX FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.docs import API_TAGS_METADATA, build_openapi_schema
from app.api.middleware.error_handler import register_exception_handlers
from app.api.middleware.request_id import RequestIdMiddleware
from app.api.middleware.request_logging import RequestLoggingMiddleware
from app.api.middleware.validation import RequestValidationMiddleware
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.paths import ensure_runtime_directories
from app.db.bootstrap import init_database


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown hooks."""
    settings = get_settings()
    setup_logging(settings)
    logger = get_logger(__name__)

    ensure_runtime_directories(settings)
    init_database()
    logger.info(
        "application_started",
        extra={
            "event": "application_started",
            "env": settings.env,
            "version": __version__,
            "data_root": str(settings.data_root_path),
        },
    )
    yield
    logger.info("application_shutdown", extra={"event": "application_shutdown"})


def create_app() -> FastAPI:
    """Application factory (composition root for the HTTP layer)."""
    settings = get_settings()
    docs_enabled = settings.debug or settings.is_testing

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        openapi_tags=API_TAGS_METADATA,
    )

    # Middleware order: last added runs first on the request (outermost).
    # Incoming: RequestId → Logging → Validation → CORS → route
    # Field validation (Pydantic) runs in the route; 422s go to exception handlers.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "X-ExplainX-Api-Version"],
    )
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router)

    def custom_openapi() -> dict:
        return build_openapi_schema(app, settings)

    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app


app = create_app()
