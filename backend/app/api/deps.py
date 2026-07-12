"""FastAPI dependency injection helpers.

Route handlers depend on these factories instead of constructing services
directly. Future modules (documents, agents, rendering) should add typed
deps here so routers stay thin.
"""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.di import AppContainer, get_container
from app.db.session import get_db_session
from app.features.input.service import InputService
from app.features.presentation.service import PresentationPlanService
from app.features.projects.service import ProjectService
from app.features.script.service import ContentIntelligenceService


def settings_dep() -> Settings:
    """Inject application settings."""
    return get_settings()


def container_dep() -> AppContainer:
    """Inject the application DI container (ports/adapters later)."""
    return get_container()


def request_id_dep(request: Request) -> str:
    """Inject the per-request correlation id."""
    return getattr(request.state, "request_id", "unknown")


def db_session_dep(session: Session = Depends(get_db_session)) -> Session:
    """Inject a request-scoped SQLAlchemy session."""
    return session


def get_project_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(settings_dep),
) -> ProjectService:
    """Inject ProjectService (Phase 1.2)."""
    return ProjectService(session, settings)


def get_input_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(settings_dep),
) -> InputService:
    """Inject InputService (Phase 2.1 / 2.2)."""
    return InputService(session, settings)


def get_presentation_plan_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(settings_dep),
) -> PresentationPlanService:
    """Inject PresentationPlanService (Phase 2.3)."""
    return PresentationPlanService(session, settings)


def get_content_intelligence_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(settings_dep),
) -> ContentIntelligenceService:
    """Inject ContentIntelligenceService (Phase 3 — EducationalScript)."""
    return ContentIntelligenceService(session, settings)


# Backward-compatible aliases
get_script_generation_service = get_content_intelligence_service
