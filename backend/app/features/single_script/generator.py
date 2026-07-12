"""Deterministic PlaceholderSingleScriptGenerator — one full script, no LLM."""

from __future__ import annotations

from app.features.outline.schemas import TeachingOutline
from app.features.script.schemas import EducationalScript
from app.features.single_script.assembler import assemble_educational_script
from app.features.single_script.protocols import SingleScriptGenerator


def _pad_to_words(text: str, *, target_words: int) -> str:
    words = text.split()
    if len(words) > target_words:
        trimmed = " ".join(words[:target_words]).rstrip(",;:")
        if not trimmed.endswith((".", "!", "?")):
            trimmed += "."
        return trimmed

    fillers = [
        "We keep the explanation clear and practical for every learner.",
        "Notice how each idea connects smoothly to the next teaching beat.",
        "A short example helps the concept stick in long-term memory.",
        "In practice, careful checking turns confusion into confidence.",
        "Finally, we restate the point so the takeaway is unmistakable.",
    ]
    idx = 0
    while len(words) < target_words:
        words.extend(fillers[idx % len(fillers)].split())
        idx += 1
    words = words[:target_words]
    result = " ".join(words)
    if not result.endswith((".", "!", "?")):
        result += "."
    return result


class PlaceholderSingleScriptGenerator:
    """Build full EducationalScript from outline without an LLM."""

    def generate(self, outline: TeachingOutline) -> EducationalScript:
        narrations: dict[str, str] = {}
        for index, section in enumerate(outline.sections, start=1):
            prev = outline.sections[index - 2].title if index > 1 else ""
            nxt = (
                outline.sections[index].title if index < len(outline.sections) else ""
            )
            bridge = (
                f"Building on {prev}. "
                if prev
                else "We begin the lesson here. "
            )
            forward = (
                f" Next we move toward {nxt}."
                if nxt
                else " This closes the teaching arc for now."
            )
            concepts = ", ".join(section.key_concepts) or outline.title
            seed = (
                f"{bridge}"
                f"In this section, {section.title}, our goal is: "
                f"{section.learning_objective} "
                f"We focus on {concepts} within {outline.title}. "
                f"The explanation stays speakable, concrete, and easy to follow aloud."
                f"{forward}"
            )
            narrations[section.id] = _pad_to_words(
                seed, target_words=section.target_words
            )

        return assemble_educational_script(
            outline,
            narrations=narrations,
            title=outline.title,
            warnings=[
                "Placeholder single-script generator — deterministic full narration."
            ],
            metadata={
                "generator": "placeholder_single_script_v1",
                "llm": False,
            },
        )


_: SingleScriptGenerator = PlaceholderSingleScriptGenerator()
