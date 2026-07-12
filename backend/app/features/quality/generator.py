"""Deterministic PlaceholderRepairGenerator (Phase 3.9)."""

from __future__ import annotations

import re

from app.features.quality.protocols import RepairGenerator
from app.features.quality.schemas import RepairAction, SectionRepairRequest
from app.features.script.metrics import count_words

_FILLERS = [
    "We keep the explanation clear and practical for every learner.",
    "A short concrete example makes the idea easier to remember.",
    "Notice how each step builds carefully on the previous point.",
    "In practice, slow checking turns confusion into confidence.",
    "Finally, we restate the takeaway in plain spoken language.",
]


def _pad_to(text: str, target: int) -> str:
    words = text.split()
    if len(words) >= target:
        return " ".join(words[:target]).rstrip(",;:") + (
            "" if text.rstrip().endswith((".", "!", "?")) else "."
        )
    idx = 0
    while len(words) < target:
        words.extend(_FILLERS[idx % len(_FILLERS)].split())
        idx += 1
    result = " ".join(words[:target])
    if not result.endswith((".", "!", "?")):
        result += "."
    return result


def _trim_to(text: str, target: int) -> str:
    words = text.split()
    if len(words) <= target:
        return text.strip()
    trimmed = " ".join(words[:target]).rstrip(",;:")
    if not trimmed.endswith((".", "!", "?")):
        trimmed += "."
    return trimmed


def _dedupe_sentences(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    seen: set[str] = set()
    kept: list[str] = []
    for part in parts:
        key = re.sub(r"\s+", " ", part.strip().lower())
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(part.strip())
    return " ".join(kept) if kept else text.strip()


class PlaceholderRepairGenerator:
    """Apply deterministic local repairs — never regenerates the full script."""

    def repair_section(self, request: SectionRepairRequest) -> str:
        narration = request.original_narration.strip()
        target = max(1, request.target_words)
        action = request.action

        if action == RepairAction.EXPAND:
            return _pad_to(narration, target)
        if action == RepairAction.SHORTEN:
            return _trim_to(narration, target)
        if action == RepairAction.REMOVE_REPETITION:
            cleaned = _dedupe_sentences(narration)
            words = count_words(cleaned)
            if words < max(8, int(target * 0.6)):
                return _pad_to(cleaned, max(target, words))
            if words > int(target * 1.2):
                return _trim_to(cleaned, target)
            return cleaned
        if action == RepairAction.SIMPLIFY:
            simplified = (
                narration.replace("consequently", "so")
                .replace("therefore", "so")
                .replace("utilize", "use")
                .replace("commence", "start")
            )
            return _pad_to(simplified, target) if count_words(simplified) < target else simplified
        if action == RepairAction.STRENGTHEN_INTRODUCTION:
            hook = (
                f"Let's begin with {request.original_title}. "
                f"Our goal is simple: {request.learning_objective or 'build a clear foundation'}."
            )
            return _pad_to(f"{hook} {narration}", target)
        if action == RepairAction.IMPROVE_CONCLUSION:
            closing = (
                " To close this idea, remember the key takeaway and carry it into practice."
            )
            return _pad_to(narration + closing, target)
        if action == RepairAction.IMPROVE_TRANSITIONS:
            bridge = ""
            if request.previous_section_summary.strip():
                bridge = f"Building on that — {request.previous_section_summary.strip()} "
            forward = ""
            if request.next_section_title:
                forward = f" Next we prepare for {request.next_section_title}."
            return _pad_to(f"{bridge}{narration}{forward}", target)

        return _pad_to(narration, target)


_: RepairGenerator = PlaceholderRepairGenerator()
