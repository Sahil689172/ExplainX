"""Shared helpers for Phase 3 content processors."""

from __future__ import annotations

import re
import uuid

from app.features.input.schemas import RawContent
from app.features.presentation.schemas import PresentationPlan
from app.features.script.schemas import ScriptConcept

_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def resolve_title(raw: RawContent, plan: PresentationPlan | None) -> str:
    if plan and plan.title.strip():
        return plan.title.strip()[:200]
    for section in raw.sections:
        if section.title and section.title.strip():
            return section.title.strip()[:200]
    first = raw.text.strip().splitlines()[0].strip() if raw.text.strip() else ""
    return (first[:120] if first else "Educational Script")


def resolve_language(raw: RawContent, plan: PresentationPlan | None) -> str:
    """Educational script language is always English (canonical).

    Requested output language lives on the project (``target_language_code``)
    and is applied at translation / audio time — never here.
    """
    _ = (raw, plan)
    return "en"


def resolve_concepts(raw: RawContent, plan: PresentationPlan | None) -> list[ScriptConcept]:
    if plan and plan.key_concepts:
        return [ScriptConcept(id=c.id, label=c.label) for c in plan.key_concepts]
    label = (
        raw.sections[0].title.strip()
        if raw.sections and raw.sections[0].title
        else " ".join(raw.text.strip().split()[:4]) or "Core topic"
    )
    return [ScriptConcept(id=new_id("concept"), label=label[:200])]


def improve_readability(text: str) -> str:
    """Preserve author intent while normalizing whitespace and punctuation."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _MULTI_SPACE.sub(" ", cleaned)
    cleaned = _MULTI_NL.sub("\n\n", cleaned)
    paragraphs: list[str] = []
    for block in cleaned.split("\n\n"):
        para = " ".join(block.split()).strip()
        if not para:
            continue
        if para[-1] not in ".!?":
            para += "."
        paragraphs.append(para)
    return "\n\n".join(paragraphs)
