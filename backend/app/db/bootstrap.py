"""Bootstrap schema via Alembic and seed builtin themes/languages."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import BUILTIN_LANGUAGE_CODES, BUILTIN_THEME_IDS
from app.core.timeutil import utc_now_iso
from app.db import models  # noqa: F401 — register mappers
from app.db.models import Language, Theme
from app.db.session import get_engine


_THEME_NAMES = {
    "notebooklm": "NotebookLM",
    "whiteboard": "Whiteboard",
    "corporate": "Corporate",
    "minimal": "Minimal",
    "comic": "Comic",
    "dark": "Dark",
}

_LANGUAGE_NAMES = {
    "en": ("English", "English"),
    "hi": ("Hindi", "हिन्दी"),
    "te": ("Telugu", "తెలుగు"),
    "es": ("Spanish", "Español"),
    "fr": ("French", "Français"),
    "de": ("German", "Deutsch"),
}


def _alembic_config() -> Config:
    """Build Alembic config pointed at the runtime database URL."""
    backend_root = Path(__file__).resolve().parents[2]
    ini_path = backend_root / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(backend_root / "app" / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", get_settings().resolved_database_url)
    return cfg


def run_migrations() -> None:
    """Apply Alembic migrations to head.

    Databases created by the former ``create_all`` path (tables present, no
    ``alembic_version``) are stamped at head so existing installs are not broken.
    """
    engine = get_engine()
    cfg = _alembic_config()
    inspector = inspect(engine)
    has_projects = inspector.has_table("projects")
    has_alembic = inspector.has_table("alembic_version")
    if has_projects and not has_alembic:
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")


def init_database() -> None:
    """Migrate schema to head and seed reference data."""
    run_migrations()
    from app.db.session import SessionLocal

    assert SessionLocal is not None
    with SessionLocal() as session:
        seed_reference_data(session)
        session.commit()


def seed_reference_data(session: Session) -> None:
    now = utc_now_iso()
    for theme_id in BUILTIN_THEME_IDS:
        if session.get(Theme, theme_id) is None:
            session.add(
                Theme(
                    theme_id=theme_id,
                    name=_THEME_NAMES.get(theme_id, theme_id.title()),
                    version="1.0.0",
                    description=f"Built-in {theme_id} theme",
                    pack_path=f"themes/{theme_id}",
                    is_builtin=1,
                    is_enabled=1,
                    created_at=now,
                    updated_at=now,
                )
            )
    for code in BUILTIN_LANGUAGE_CODES:
        if session.get(Language, code) is None:
            name, native = _LANGUAGE_NAMES.get(code, (code, code))
            session.add(
                Language(
                    language_code=code,
                    name=name,
                    native_name=native,
                    tts_supported=1 if code in {"en", "hi", "te"} else 0,
                    translation_supported=0,
                    default_voice_id={
                        "en": "en_US-lessac-medium",
                        "hi": "hi_IN-pratham-medium",
                        "te": "te_IN-venkatesh-medium",
                    }.get(code),
                    is_enabled=1,
                    created_at=now,
                    updated_at=now,
                )
            )
