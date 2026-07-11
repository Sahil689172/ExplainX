"""Top-level API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()

# Unversioned health for probes
api_router.include_router(health.router)

# Versioned aliases under /api/v1
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(health.router)
api_router.include_router(api_v1)
