"""Deterministic PlaceholderNarrationGenerator — no LLM."""

from __future__ import annotations

import uuid

from app.core.enums import SourceType
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContent
from app.features.narration.normalize import normalize_author_script
from app.features.narration.protocols import NarrationGenerator
from app.features.narration.schemas import NarrationDocument
from app.features.script.durations import V1_WPM, word_budget
from app.features.script.processors.common import resolve_language, resolve_title


def _pad_to_words(text: str, *, target_words: int) -> str:
    words = text.split()
    if len(words) >= target_words:
        result = " ".join(words[:target_words])
        if not result.endswith((".", "!", "?")):
            result += "."
        return result
    fillers = [
        "We keep each idea clear so every learner can follow along.",
        "A short example shows how the concept works in practice.",
        "Notice how each step connects smoothly to the next idea.",
        "In everyday situations, the same pattern appears again and again.",
        "Finally, we restate the key takeaway so it sticks.",
    ]
    idx = 0
    while len(words) < target_words:
        words.extend(fillers[idx % len(fillers)].split())
        idx += 1
    result = " ".join(words[:target_words])
    if not result.endswith((".", "!", "?")):
        result += "."
    return result


class PlaceholderNarrationGenerator:
    """Build continuous narration without calling an LLM."""

    def generate(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        repair_hint: str | None = None,
    ) -> NarrationDocument:
        title = resolve_title(raw, None)
        language = resolve_language(raw, None)
        budget = word_budget(target_duration_sec)
        hint = (repair_hint or "").lower()
        if "shorten" in hint or "too long" in hint:
            budget = int(budget * 0.75)
        elif "fuller" in hint or "too short" in hint or "expand" in hint:
            budget = int(budget * 1.15)

        if raw.source_type == SourceType.SCRIPT:
            text = normalize_author_script(raw.text)
            status: str = "ready"
            warnings = ["Author script used as narration (whitespace normalized only)."]
            meta = {
                "generator": "placeholder_narration_v1",
                "llm": False,
                "preserve_intent": True,
            }
        else:
            topic = title
            seed = (
                f"Welcome. Today we explore {topic}. "
                f"We begin with a simple hook: why {topic} matters for everyday thinking. "
                f"Next we build the idea step by step with clear language. "
                f"For example, imagine applying {topic} in a practical situation. "
                f"We check understanding, then connect related ideas carefully. "
                f"Finally, here is a concise recap of {topic}."
            )
            if raw.source_type == SourceType.PDF and raw.text.strip():
                seed = (
                    f"Welcome. This lesson explains the document about {topic}. "
                    f"{' '.join(raw.text.split()[:80])} "
                    f"We highlight the important concepts, skip repetition, "
                    f"and end with a short recap."
                )
            text = _pad_to_words(seed, target_words=budget)
            status = "placeholder"
            warnings = ["Placeholder continuous narration — deterministic text."]
            meta = {"generator": "placeholder_narration_v1", "llm": False}

        return NarrationDocument(
            narration_id=str(uuid.uuid4()),
            project_id=raw.project_id,
            content_id=raw.content_id,
            source_type=raw.source_type,
            status=status,  # type: ignore[arg-type]
            title=title,
            language=language,
            text=text,
            target_duration_sec=target_duration_sec,
            warnings=warnings,
            metadata={
                **meta,
                "word_budget": budget,
                "wpm": V1_WPM,
                "repair_hint": repair_hint,
            },
            created_at=utc_now_iso(),
        )


_: NarrationGenerator = PlaceholderNarrationGenerator()
