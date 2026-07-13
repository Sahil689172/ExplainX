"""Resolve the user-requested topic string for prompts and verification."""

from __future__ import annotations

from app.core.enums import SourceType
from app.features.input.schemas import RawContent
from app.features.script.processors.common import resolve_title

_GENERIC_TITLES = frozenset({"topic", "document", "pdf", "script", "untitled", "educational script"})


def resolve_requested_topic(raw: RawContent) -> str:
    """Return the exact topic the model must explain.

    For TOPIC inputs, prefer ``raw.text`` (the user topic). Section titles may be
    a generic label like \"Topic\", which must never be sent to the LLM as the subject.
    """
    if raw.source_type == SourceType.TOPIC:
        body = (raw.text or "").strip()
        if body:
            return body[:200]
    title = resolve_title(raw, None).strip()
    if title and title.lower() not in _GENERIC_TITLES:
        return title[:200]
    body = (raw.text or "").strip()
    if body:
        first = body.splitlines()[0].strip()
        return (first[:200] if first else body[:200])
    return (title or "Educational topic")[:200]
