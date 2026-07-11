"""SQLAlchemy ORM models for project management (Phase 1.2)."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Theme(Base):
    __tablename__ = "themes"

    theme_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pack_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    is_builtin: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class Language(Base):
    __tablename__ = "languages"

    language_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    native_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tts_supported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    translation_supported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    default_voice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    current_phase: Mapped[str] = mapped_column(String(32), nullable=False, default="foundation")
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    theme_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("themes.theme_id"), nullable=False
    )
    source_language_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("languages.language_code"), nullable=False
    )
    target_language_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("languages.language_code"), nullable=False
    )
    voice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dsl_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timeline_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    project_root: Mapped[str] = mapped_column(String(512), nullable=False)
    project_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    dsl_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    estimated_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    completed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deleted_at: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    settings: Mapped[ProjectSettings | None] = relationship(
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ProjectSettings(Base):
    __tablename__ = "project_settings"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.project_id", ondelete="CASCADE"), primary_key=True
    )
    export_width: Mapped[int] = mapped_column(Integer, nullable=False, default=1280)
    export_height: Mapped[int] = mapped_column(Integer, nullable=False, default=720)
    fps: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)
    quality_profile: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    burn_in_subtitles: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subtitle_formats: Mapped[str] = mapped_column(Text, nullable=False, default='["srt","vtt"]')
    speaking_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    max_scenes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plugin_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)

    project: Mapped[Project] = relationship(back_populates="settings")
