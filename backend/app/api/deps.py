"""FastAPI dependency helpers."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.di import AppContainer, get_container
from app.db.session import get_db_session
from app.services.project_service import ProjectService


def settings_dep() -> Settings:
    return get_settings()


def container_dep() -> AppContainer:
    return get_container()


def request_id_dep(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def get_project_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(settings_dep),
) -> ProjectService:
    return ProjectService(session, settings)
