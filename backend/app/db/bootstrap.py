"""Bootstrap schema and seed builtin themes/languages."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import BUILTIN_LANGUAGE_CODES, BUILTIN_THEME_IDS
from app.core.timeutil import utc_now_iso
from app.db import models  # noqa: F401 — register mappers
from app.db.models import Language, Theme
from app.db.session import Base, get_engine


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
    "es": ("Spanish", "Español"),
    "fr": ("French", "Français"),
    "de": ("German", "Deutsch"),
}


def init_database() -> None:
    """Create tables if missing and seed reference data."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
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
                    tts_supported=1 if code == "en" else 0,
                    translation_supported=1 if code in {"en", "hi"} else 0,
                    default_voice_id="en_US-lessac-medium" if code == "en" else None,
                    is_enabled=1,
                    created_at=now,
                    updated_at=now,
                )
            )
