"""Top-level API router — mounts probes and versioned `/api/v1` surface."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health, system
from app.features.agents.router import router as agents_router
from app.features.input.documents import router as documents_router
from app.features.input.router import router as inputs_router
from app.features.presentation.router import router as presentation_router
from app.features.projects.router import router as projects_router
from app.features.rendering.router import router as rendering_router
from app.features.script.router import router as script_router
from app.features.settings.router import router as settings_router
from app.features.visual_intelligence.router import router as visual_intelligence_router

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
api_v1.include_router(projects_router)
api_v1.include_router(inputs_router)
api_v1.include_router(presentation_router)
api_v1.include_router(script_router)
api_v1.include_router(documents_router)
api_v1.include_router(agents_router)
api_v1.include_router(rendering_router)
api_v1.include_router(settings_router)
api_v1.include_router(visual_intelligence_router)

api_router.include_router(api_v1)
