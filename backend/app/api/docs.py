"""OpenAPI / docs configuration helpers."""

from __future__ import annotations

from fastapi.openapi.utils import get_openapi

from app import __version__
from app.core.config import Settings

API_TAGS_METADATA = [
    {"name": "health", "description": "Liveness and readiness probes"},
    {"name": "system", "description": "System information and doctor checks"},
    {"name": "projects", "description": "Project lifecycle management"},
    {"name": "inputs", "description": "Input Intelligence — topic, PDF, script → RawContent"},
    {
        "name": "content-intelligence",
        "description": "Content Intelligence — RawContent → PresentationPlan (placeholder)",
    },
    {
        "name": "script-generation",
        "description": "Script Generation — RawContent → EducationalScript (placeholder)",
    },
    {"name": "documents", "description": "Document listing hints (uploads are project-scoped)"},
    {"name": "agents", "description": "Agent pipeline controls (stub)"},
    {"name": "rendering", "description": "Render job controls (stub)"},
    {"name": "settings", "description": "Application and project settings (stub)"},
]


def build_openapi_schema(app, settings: Settings) -> dict:
    """Custom OpenAPI schema with ExplainX metadata."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=f"{settings.app_name} API",
        version=__version__,
        description=(
            "ExplainX local control plane. "
            "Versioned under `/api/v1`. "
            "Success and error responses use a standard envelope "
            "(`success`, `data`|`error`, `meta`)."
        ),
        routes=app.routes,
        tags=API_TAGS_METADATA,
    )
    schema["info"]["x-explainx-api-version"] = settings.api_version
    schema["servers"] = [
        {"url": f"http://{settings.host}:{settings.port}", "description": "Local API"},
    ]
    app.openapi_schema = schema
    return app.openapi_schema
