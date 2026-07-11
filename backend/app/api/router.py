"""Top-level API router — mounts probes and versioned `/api/v1` surface."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    agents,
    documents,
    health,
    projects,
    rendering,
    settings,
    system,
)

api_router = APIRouter()

# ---------------------------------------------------------------------------
# Unversioned probes (load balancers / local tooling)
# ---------------------------------------------------------------------------
api_router.include_router(health.router)
api_router.include_router(system.router)  # /system/info, /system/modules

# ---------------------------------------------------------------------------
# Versioned API — all product routes live under /api/v1
# ---------------------------------------------------------------------------
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(health.router)
api_v1.include_router(system.router)
api_v1.include_router(projects.router)
api_v1.include_router(documents.router)
api_v1.include_router(agents.router)
api_v1.include_router(rendering.router)
api_v1.include_router(settings.router)

api_router.include_router(api_v1)
