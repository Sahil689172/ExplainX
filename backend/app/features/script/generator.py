"""Deterministic PlaceholderContentGenerator — V1 2–3 minute educational script."""

from __future__ import annotations

import uuid

from app.core.enums import SourceType
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContent, RawContentSection
from app.features.presentation.schemas import PresentationPlan
from app.features.script.durations import (
    V1_TARGET_DURATION_SEC,
    V1_TARGET_WORDS_MAX,
    V1_TARGET_WORDS_MIN,
    V1_WPM,
    duration_from_words,
    estimate_scene_count,
    label_for_seconds,
    word_budget,
)
from app.features.script.metrics import count_words, enrich_script_with_metrics
from app.features.script.protocols import ContentGenerator
from app.features.script.schemas import EducationalScript, ScriptConcept, TeachingSection


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _pad_to_word_target(text: str, *, min_words: int, max_words: int) -> str:
    """Expand or trim narration to land inside the V1 word band."""
    words = text.split()
    if len(words) > max_words:
        trimmed = " ".join(words[:max_words]).rstrip(",;:")
        if not trimmed.endswith((".", "!", "?")):
            trimmed += "."
        return trimmed

    fillers = [
        "We will keep the explanation clear and practical.",
        "Notice how each step builds on the previous idea.",
        "A short example helps make the concept easier to remember.",
        "In practice, this is how learners apply the idea with confidence.",
        "Finally, we connect the pieces into one coherent understanding.",
    ]
    idx = 0
    while len(words) < min_words:
        words.extend(fillers[idx % len(fillers)].split())
        idx += 1
    if len(words) > max_words:
        words = words[:max_words]
    result = " ".join(words)
    if not result.endswith((".", "!", "?")):
        result += "."
    return result


class PlaceholderContentGenerator:
    """Build a V1 EducationalScript sized for a 2–3 minute explainer."""

    def generate(
        self,
        *,
        project_id: str,
        content_id: str,
        source_type: SourceType,
        title: str,
        language: str,
        sections: list[RawContentSection],
        concepts: list[ScriptConcept],
        target_duration_sec: int,
        warnings: list[str] | None = None,
        metadata: dict | None = None,
    ) -> EducationalScript:
        # V1 ignores alternate duration presets.
        target = V1_TARGET_DURATION_SEC
        budget = word_budget(target)
        source_sections = sections or [
            RawContentSection(id="section-1", text=title, order=1, title=title)
        ]
        concept_list = concepts or [
            ScriptConcept(id=_new_id("concept"), label=title[:200] or "Core topic")
        ]
        concept_tags = [c.label for c in concept_list]

        teaching = self._build_teaching_sections(
            source_type=source_type,
            title=title,
            source_sections=source_sections,
            concept_tags=concept_tags,
            word_budget=budget,
        )

        total_words = sum(s.estimated_words for s in teaching)
        # Ensure global band even if section packing drifted.
        if total_words < V1_TARGET_WORDS_MIN or total_words > V1_TARGET_WORDS_MAX:
            joined = " ".join(s.narration for s in teaching)
            joined = _pad_to_word_target(
                joined,
                min_words=V1_TARGET_WORDS_MIN,
                max_words=V1_TARGET_WORDS_MAX,
            )
            teaching = self._repack_from_text(joined, title=title, concept_tags=concept_tags)

        duration = duration_from_words(sum(s.estimated_words for s in teaching), wpm=V1_WPM)
        scene_count = estimate_scene_count(duration)
        summary = (
            f"A clear 2–3 minute explanation of {title}, covering the core idea, "
            f"key steps, and a practical takeaway for learners."
        )
        objectives = [
            f"Explain what {title} means in plain language.",
            f"Describe the main steps or parts of {title}.",
            f"Apply {title} with a simple example.",
        ]

        out_warnings = list(warnings or [])
        out_warnings.append(
            "Placeholder content generator — deterministic V1 2–3 minute script."
        )

        script = EducationalScript(
            script_id=str(uuid.uuid4()),
            project_id=project_id,
            content_id=content_id,
            source_type=source_type,
            status="placeholder",
            title=title[:200],
            language=language,
            target_duration_sec=target,
            estimated_duration_sec=duration,
            estimated_word_count=sum(s.estimated_words for s in teaching),
            estimated_scene_count=scene_count,
            summary=summary,
            key_concepts=concept_list,
            learning_objectives=objectives,
            teaching_sections=teaching,
            warnings=out_warnings,
            metadata={
                "generator": "placeholder_content_v1_1",
                "llm": False,
                "target_duration": label_for_seconds(target),
                "target_duration_sec": target,
                "word_budget": budget,
                "requested_target_duration_sec": target_duration_sec,
                **(metadata or {}),
            },
            created_at=utc_now_iso(),
        )
        return enrich_script_with_metrics(script)

    def _build_teaching_sections(
        self,
        *,
        source_type: SourceType,
        title: str,
        source_sections: list[RawContentSection],
        concept_tags: list[str],
        word_budget: int,
    ) -> list[TeachingSection]:
        outlines: list[tuple[str, str]]
        if source_type == SourceType.TOPIC:
            outlines = [
                (
                    "Introduction",
                    f"Today we explore {title}. In the next few minutes, we will build a clear "
                    f"understanding of what it is, why it matters, and how to use it.",
                ),
                (
                    "Core idea",
                    f"At its heart, {title} is about a reliable way to think through a problem. "
                    f"{' '.join(source_sections[0].text.split())} "
                    "We keep the definition simple so every learner can follow.",
                ),
                (
                    "How it works",
                    f"Here is how {title} works step by step. First, identify the goal. "
                    "Next, apply the key rule carefully. Then, check the result and adjust. "
                    "Each step is short, intentional, and easy to repeat.",
                ),
                (
                    "Worked example",
                    f"Consider a short example of {title}. We start with a familiar situation, "
                    "apply the method, and observe how the answer becomes clear. "
                    "The example shows why the method is practical, not just theoretical.",
                ),
                (
                    "Common mistakes",
                    f"Learners often rush or skip a check when using {title}. "
                    "Slow down, verify each step, and name the concept out loud. "
                    "That habit prevents confusion and builds lasting understanding.",
                ),
                (
                    "Summary",
                    f"To summarize, {title} gives us a clear process, a useful example, "
                    "and a habit of careful checking. With practice, the idea becomes natural.",
                ),
            ]
        elif source_type == SourceType.SCRIPT:
            body = " ".join(
                " ".join(section.text.split()) for section in source_sections if section.text.strip()
            )
            body = body or title
            outlines = [
                ("Opening", f"We begin with the author's core message. {body}"),
                (
                    "Clarified flow",
                    "We keep the original meaning while improving teaching flow. "
                    "Transitions are smoother, and each idea is easier to say aloud.",
                ),
                (
                    "Key emphasis",
                    f"The most important points about {title} stay intact. "
                    "We only expand slightly so the narration fits a complete 2–3 minute lesson.",
                ),
                (
                    "Closing",
                    "We end with a clear takeaway the learner can remember and apply.",
                ),
            ]
        else:
            # PDF / document extract path.
            body = " ".join(
                " ".join(section.text.split()) for section in source_sections if section.text.strip()
            )
            body = body or title
            outlines = [
                (
                    "Introduction",
                    f"Let's turn the source material into a clear lesson on {title}.",
                ),
                (
                    "Main ideas",
                    f"From the extracted text: {body}",
                ),
                (
                    "Teaching focus",
                    "We remove noise and keep only what helps a learner understand the topic.",
                ),
                (
                    "Application",
                    f"In practice, {title} becomes useful when we apply these ideas carefully.",
                ),
                (
                    "Summary",
                    f"In short, {title} can be explained clearly from the source content "
                    "without distractions.",
                ),
            ]

        # Distribute word budget across outline sections.
        per = max(40, word_budget // max(len(outlines), 1))
        teaching: list[TeachingSection] = []
        for index, (section_title, seed) in enumerate(outlines, start=1):
            narration = _pad_to_word_target(seed, min_words=per - 5, max_words=per + 10)
            words = count_words(narration)
            teaching.append(
                TeachingSection(
                    id=_new_id("teach"),
                    title=section_title,
                    narration=narration,
                    estimated_duration_sec=duration_from_words(words),
                    estimated_words=words,
                    concept_tags=list(concept_tags),
                )
            )
        return teaching

    def _repack_from_text(
        self,
        text: str,
        *,
        title: str,
        concept_tags: list[str],
    ) -> list[TeachingSection]:
        words = text.split()
        chunk_size = max(40, len(words) // 6)
        chunks: list[list[str]] = []
        for i in range(0, len(words), chunk_size):
            chunks.append(words[i : i + chunk_size])
        if not chunks:
            chunks = [title.split()]
        titles = [
            "Introduction",
            "Core idea",
            "How it works",
            "Example",
            "Practice tips",
            "Summary",
        ]
        teaching: list[TeachingSection] = []
        for index, chunk in enumerate(chunks[:6], start=1):
            narration = " ".join(chunk)
            if not narration.endswith((".", "!", "?")):
                narration += "."
            w = count_words(narration)
            teaching.append(
                TeachingSection(
                    id=_new_id("teach"),
                    title=titles[index - 1] if index <= len(titles) else f"Section {index}",
                    narration=narration,
                    estimated_duration_sec=duration_from_words(w),
                    estimated_words=w,
                    concept_tags=list(concept_tags),
                )
            )
        return teaching


_: ContentGenerator = PlaceholderContentGenerator()


class PlaceholderScriptGenerator:
    """Legacy facade — routes through Phase 3 processors with V1 duration."""

    def __init__(self, generator: ContentGenerator | None = None) -> None:
        from app.features.script.processors.pdf_processor import PDFContentProcessor
        from app.features.script.processors.script_processor import ScriptContentProcessor
        from app.features.script.processors.topic_processor import TopicContentProcessor

        self._generator = generator or PlaceholderContentGenerator()
        self._processors = {
            SourceType.TOPIC: TopicContentProcessor(self._generator),
            SourceType.SCRIPT: ScriptContentProcessor(self._generator),
            SourceType.PDF: PDFContentProcessor(self._generator),
        }

    def generate(
        self,
        raw: RawContent,
        *,
        plan: PresentationPlan | None = None,
        target_duration_sec: int = V1_TARGET_DURATION_SEC,
    ) -> EducationalScript:
        processor = self._processors.get(raw.source_type)
        if processor is None:
            from app.features.script.processors.topic_processor import TopicContentProcessor

            processor = TopicContentProcessor(self._generator)
        return processor.process(
            raw,
            target_duration_sec=target_duration_sec or V1_TARGET_DURATION_SEC,
            plan=plan,
            pdf_path=None,
        )
