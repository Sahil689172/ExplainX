"""Shared domain enums for Phase 1.2+."""

from __future__ import annotations

from enum import Enum


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ProjectPhase(str, Enum):
    """Coarse pipeline phase — foundation until later modules advance it."""

    FOUNDATION = "foundation"
    DOCUMENT = "document"
    KNOWLEDGE = "knowledge"
    CONTENT = "content"
    PRESENTATION = "presentation"
    ANIMATION = "animation"
    MULTILINGUAL = "multilingual"
    RENDERING = "rendering"
    COMPLETED = "completed"


class SourceType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    TOPIC = "topic"
    SCRIPT = "script"


class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class QualityProfile(str, Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"


BUILTIN_THEME_IDS: tuple[str, ...] = (
    "notebooklm",
    "whiteboard",
    "corporate",
    "minimal",
    "comic",
    "dark",
)

BUILTIN_LANGUAGE_CODES: tuple[str, ...] = ("en", "hi", "te", "es", "fr", "de")

PROJECT_SUBDIRS: tuple[str, ...] = (
    "source",
    "assets",
    "scenes",
    "audio",
    "subtitles",
    "generated",
    "export",
    "logs",
    "temp",
    "artifacts",
)

DSL_VERSION = "1.0"
PROJECT_SCHEMA_VERSION = "1.0"
