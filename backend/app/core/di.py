"""Dependency injection / composition root stubs for Phase 1.1."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class AppContainer:
    """Application service container.

    Phase 1.2: settings. ProjectService is request-scoped via FastAPI Depends.
    """

    settings: Settings


def build_container() -> AppContainer:
    """Build the root DI container."""
    return AppContainer(settings=get_settings())


def get_container() -> AppContainer:
    """FastAPI-friendly accessor (stateless rebuild is fine while container is tiny)."""
    return build_container()
