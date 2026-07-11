"""FastAPI dependency helpers."""

from __future__ import annotations

from fastapi import Request

from app.core.config import Settings, get_settings
from app.core.di import AppContainer, get_container


def settings_dep() -> Settings:
    return get_settings()


def container_dep() -> AppContainer:
    return get_container()


def request_id_dep(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")
