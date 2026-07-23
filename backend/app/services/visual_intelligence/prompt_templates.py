"""Prompt templates for FUTURE LLM-based visual classification.

These are intentionally unused by the current deterministic analyzer. They are
kept here so that swapping in an LLM classifier later requires no schema
changes: the model is asked to return exactly the JSON shape of
:class:`~app.services.visual_intelligence.schemas.VisualIntent`.

Nothing in this module calls an LLM.
"""

from __future__ import annotations

from app.services.visual_intelligence.schemas import VisualType

PROMPT_TEMPLATE_VERSION = "1.0.0"

VISUAL_TYPE_GUIDE = "\n".join(
    f"- {vt.value}: {desc}"
    for vt, desc in {
        VisualType.DIAGRAM: "labelled structural relationships between parts",
        VisualType.FLOWCHART: "steps/decisions in a process with arrows",
        VisualType.TIMELINE: "events ordered in time",
        VisualType.CHART: "quantitative data (bar/line/pie)",
        VisualType.TABLE: "rows/columns of comparable values",
        VisualType.MAP: "geographic or spatial layout",
        VisualType.MATHEMATICAL: "equations, proofs, geometric constructions",
        VisualType.SCIENTIFIC: "physical/biological/chemical phenomena",
        VisualType.ILLUSTRATION: "stylised drawing of a concept or object",
        VisualType.PHOTO: "photorealistic real-world imagery",
        VisualType.ICON: "single symbolic glyph",
        VisualType.BACKGROUND: "full-frame ambient backdrop",
        VisualType.TEXT_ONLY: "the words themselves carry the meaning",
        VisualType.MIXED: "combination requiring multiple visual kinds",
    }.items()
)

SYSTEM_PROMPT = (
    "You are an educational visual director. Given a scene, decide the single "
    "best visual type to teach its idea. Respond ONLY with strict JSON matching "
    "the VisualIntent schema. Do not add commentary."
)

CLASSIFICATION_PROMPT = """\
Scene title: {title}
Learning objective: {learning_objective}
Educational concepts: {concepts}
Keywords: {keywords}
Narration:
\"\"\"{narration}\"\"\"

Choose exactly one visual_type from:
{visual_type_guide}

Return JSON with keys:
  visual_type (one of the values above),
  confidence (0..1),
  reasoning (one sentence),
  suggested_renderer (mermaid|svg|matplotlib|manim|openvino|icon|background),
  estimated_duration (seconds, number),
  complexity (trivial|simple|moderate|complex),
  matched_keywords (array of strings),
  alternatives (array of visual_type values).
"""


def build_classification_prompt(
    *,
    title: str,
    learning_objective: str,
    concepts: list[str],
    keywords: list[str],
    narration: str,
) -> dict[str, str]:
    """Render the system+user prompt pair (for future LLM use)."""
    user = CLASSIFICATION_PROMPT.format(
        title=title or "(none)",
        learning_objective=learning_objective or "(none)",
        concepts=", ".join(concepts) or "(none)",
        keywords=", ".join(keywords) or "(none)",
        narration=(narration or "(none)").strip(),
        visual_type_guide=VISUAL_TYPE_GUIDE,
    )
    return {"system": SYSTEM_PROMPT, "user": user, "version": PROMPT_TEMPLATE_VERSION}
