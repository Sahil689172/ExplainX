"""Shared helpers and processor protocol for Input Intelligence."""

from __future__ import annotations

import hashlib
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.enums import SourceType
from app.core.timeutil import utc_now_iso
from app.models.artifacts.raw_content import (
    ExtractionStats,
    RawContent,
    RawContentSection,
)


def sha256_text(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def sha256_bytes(data: bytes) -> str:
    digest = hashlib.sha256(data).hexdigest()
    return f"sha256:{digest}"


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def new_content_id() -> str:
    return str(uuid.uuid4())


@dataclass(slots=True)
class ProcessorContext:
    """Normalized input handed to a processor (files already on disk when applicable)."""

    project_id: str
    source_type: SourceType
    topic: str | None = None
    script_text: str | None = None
    file_path: Path | None = None
    original_filename: str | None = None
    language_hint: str | None = None
    source_path_relative: str | None = None
    source_hash: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class BaseInputProcessor(ABC):
    """Every processor must emit the same RawContent schema."""

    source_type: SourceType

    @abstractmethod
    def process(self, ctx: ProcessorContext) -> RawContent:
        raise NotImplementedError

    def _build(
        self,
        *,
        project_id: str,
        sections: list[RawContentSection],
        warnings: list[str],
        source_path: str | None,
        source_hash: str,
        metadata: dict[str, Any],
        page_count: int = 0,
    ) -> RawContent:
        text = "\n\n".join(s.text for s in sections if s.text.strip()).strip()
        stats = ExtractionStats(
            char_count=len(text),
            word_count=count_words(text),
            page_count=page_count,
            section_count=len(sections),
        )
        return RawContent(
            content_id=new_content_id(),
            project_id=project_id,
            source_type=self.source_type,
            text=text,
            sections=sections,
            warnings=warnings,
            extraction_stats=stats,
            source_path=source_path,
            source_hash=source_hash,
            metadata=metadata,
            created_at=utc_now_iso(),
        )
