"""Deterministic SceneBuilder — continuous narration → EducationalScript (+ outline)."""

from __future__ import annotations

import re
import uuid

from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContent
from app.features.narration.schemas import NarrationDocument
from app.features.outline.schemas import (
    OUTLINE_SECTION_MAX,
    OUTLINE_SECTION_MIN,
    TeachingOutline,
)
from app.features.outline.schemas import TeachingSection as OutlineSection
from app.features.script.durations import V1_TARGET_DURATION_SEC, V1_WPM
from app.features.script.metrics import count_words, enrich_script_with_metrics
from app.features.script.schemas import (
    EDUCATIONAL_SCRIPT_SCHEMA_VERSION,
    EducationalScript,
    ScriptConcept,
    TeachingSection,
)

_TRANSITION_RE = re.compile(
    r"^\s*(now|next|then|finally|meanwhile|however|therefore|in summary|"
    r"to begin|first|second|third|lastly|in conclusion|for example)\b",
    re.IGNORECASE,
)


def split_sentences(text: str) -> list[str]:
    """Split narration into speakable sentences."""
    cleaned = " ".join(text.replace("\r\n", "\n").split())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    sentences = [p.strip() for p in parts if p.strip()]
    return sentences or [cleaned]


def _title_from_sentence(sentence: str, index: int) -> str:
    words = sentence.split()
    if not words:
        return f"Scene {index}"
    chunk = " ".join(words[:6]).rstrip(",;:")
    if len(chunk) > 60:
        chunk = chunk[:57] + "…"
    if chunk and chunk[0].islower():
        chunk = chunk[0].upper() + chunk[1:]
    return chunk or f"Scene {index}"


def _choose_scene_count(total_words: int) -> int:
    """Always emit 8–12 teaching sections for outline/schema compatibility."""
    if total_words <= 0:
        return OUTLINE_SECTION_MIN
    raw = max(OUTLINE_SECTION_MIN, round(total_words / 40))
    return max(OUTLINE_SECTION_MIN, min(OUTLINE_SECTION_MAX, raw))


def _group_sentences(sentences: list[str], *, scene_count: int) -> list[list[str]]:
    if not sentences:
        return [["Let's continue the lesson."]] * scene_count

    # If fewer sentences than scenes, reuse/split words so every scene has text.
    if len(sentences) < scene_count:
        words = " ".join(sentences).split()
        if not words:
            words = ["Let's", "continue", "the", "lesson."]
        chunk = max(1, len(words) // scene_count)
        groups: list[list[str]] = []
        for i in range(scene_count):
            start = i * chunk
            end = len(words) if i == scene_count - 1 else min(len(words), (i + 1) * chunk)
            piece = words[start:end] or words[-3:]
            groups.append([" ".join(piece)])
        return groups

    total = len(sentences)
    target_size = max(1, total / scene_count)
    groups = []
    current: list[str] = []
    for sentence in sentences:
        force_break = (
            bool(current)
            and _TRANSITION_RE.match(sentence) is not None
            and len(groups) < scene_count - 1
            and len(current) >= max(1, int(target_size * 0.6))
        )
        size_break = (
            bool(current)
            and len(current) >= max(1, int(round(target_size)))
            and len(groups) < scene_count - 1
        )
        if force_break or size_break:
            groups.append(current)
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        groups.append(current)

    while len(groups) > scene_count:
        last = groups.pop()
        groups[-1].extend(last)
    while len(groups) < scene_count:
        lengths = [len(g) for g in groups]
        idx = lengths.index(max(lengths))
        group = groups[idx]
        if len(group) < 2:
            groups.append([group[-1]])
            break
        mid = len(group) // 2
        groups[idx] = group[:mid]
        groups.insert(idx + 1, group[mid:])
    return groups[:scene_count]


class SceneBuilder:
    """Python-only structure builder — never calls an LLM."""

    def build(
        self,
        narration: NarrationDocument,
        *,
        raw: RawContent,
    ) -> EducationalScript:
        sentences = split_sentences(narration.text)
        total_words = count_words(narration.text)
        scene_count = _choose_scene_count(total_words)
        groups = _group_sentences(sentences, scene_count=scene_count)

        teaching_sections: list[TeachingSection] = []
        for index, group in enumerate(groups, start=1):
            body = " ".join(group).strip()
            if not body:
                body = f"This section continues the lesson on {narration.title}."
            teaching_sections.append(
                TeachingSection(
                    id=f"section-{index}",
                    title=_title_from_sentence(group[0] if group else body, index),
                    narration=body,
                    estimated_duration_sec=0.0,
                    estimated_words=0,
                    concept_tags=[narration.title],
                )
            )

        concepts = [
            ScriptConcept(id=f"concept-{uuid.uuid4().hex[:8]}", label=narration.title[:200])
        ]
        objectives = [
            f"Understand: {section.title}" for section in teaching_sections
        ]
        summary = (
            f"A structured educational explanation of {narration.title}, "
            f"spoken across {len(teaching_sections)} scenes."
        )

        script = EducationalScript(
            script_id=str(uuid.uuid4()),
            project_id=narration.project_id,
            content_id=narration.content_id,
            source_type=narration.source_type,
            status="draft" if (narration.metadata or {}).get("llm") else "placeholder",
            title=narration.title,
            language=narration.language,
            target_duration_sec=narration.target_duration_sec or V1_TARGET_DURATION_SEC,
            estimated_duration_sec=0.0,
            estimated_word_count=0,
            estimated_scene_count=0,
            summary=summary[:2000],
            key_concepts=concepts,
            learning_objectives=objectives,
            teaching_sections=teaching_sections,
            warnings=list(narration.warnings),
            metadata={
                "generator": "scene_builder_v1",
                "narration_id": narration.narration_id,
                "narration_pipeline": True,
                "single_script_generation": False,
                "section_generation": False,
                "llm": bool((narration.metadata or {}).get("llm")),
                "source_words": total_words,
                "wpm": V1_WPM,
                **{
                    k: v
                    for k, v in (narration.metadata or {}).items()
                    if k in {"ollama_model", "prompt_template_version", "preserve_intent"}
                },
            },
            created_at=utc_now_iso(),
            schema_version=EDUCATIONAL_SCRIPT_SCHEMA_VERSION,
        )
        _ = raw  # reserved for future grounding checks
        return enrich_script_with_metrics(script)

    def derive_outline(
        self,
        script: EducationalScript,
        *,
        narration: NarrationDocument | None = None,
    ) -> TeachingOutline:
        """Deterministic TeachingOutline from scenes (no LLM)."""
        sections: list[OutlineSection] = []
        for section in script.teaching_sections:
            words = max(1, section.estimated_words or count_words(section.narration))
            sections.append(
                OutlineSection(
                    id=section.id,
                    title=section.title,
                    learning_objective=(
                        f"Explain {section.title}"
                        if not script.learning_objectives
                        else next(
                            (
                                o
                                for o in script.learning_objectives
                                if section.title in o
                            ),
                            f"Explain {section.title}",
                        )
                    ),
                    target_words=words,
                    key_concepts=list(section.concept_tags) or [script.title],
                )
            )

        # Outline section count already matches script (SceneBuilder emits 8–12).
        total = sum(s.target_words for s in sections)
        return TeachingOutline(
            outline_id=str(uuid.uuid4()),
            project_id=script.project_id,
            content_id=script.content_id,
            source_type=script.source_type,
            status="ready",
            title=script.title,
            language=script.language,
            target_duration_sec=script.target_duration_sec,
            total_target_words=max(1, total),
            sections=sections,
            warnings=["Deterministic outline derived from SceneBuilder scenes."],
            metadata={
                "generator": "scene_builder_outline_v1",
                "llm": False,
                "narration_id": (narration.narration_id if narration else None),
                "derived_from_script": True,
            },
            created_at=utc_now_iso(),
        )
