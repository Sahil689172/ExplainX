"""SQLAlchemy engine/session scaffolding — no domain models in Phase 1.1."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for future ORM models (Phase 1.2+)."""


def _sqlite_connect_args(url: str) -> dict[str, bool]:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def create_db_engine():
    settings = get_settings()
    url = settings.resolved_database_url
    return create_engine(
        url,
        connect_args=_sqlite_connect_args(url),
        future=True,
    )


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db_session() -> Generator[Session, None, None]:
    """Yield a DB session (unused until repositories exist)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
