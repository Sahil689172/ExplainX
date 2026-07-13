"""Prompt templates for continuous narration (plain text — not JSON)."""

from __future__ import annotations

PROMPT_TEMPLATE_VERSION = "1.0"

TOPIC_SYSTEM = """
You are an expert educational narrator for ExplainX.
You teach with clear, natural spoken language for an animated explainer video.
Return narration text only — no markdown, no bullet points, no JSON, no titles as headings.
""".strip()

TOPIC_USER = """
Explain "{topic}" as if teaching a complete beginner.

Requirements:
- Natural spoken narration.
- About {target_duration_sec} seconds when spoken (~{word_budget} words at 140 words per minute).
- Educational and accurate.
- Start with an engaging hook.
- Build concepts gradually.
- Include one or more concrete examples.
- End with a concise recap.
- No markdown.
- No bullet points.
- No JSON.
- Return narration text only.

{repair_block}
""".strip()

PDF_SYSTEM = """
You are an expert educational narrator for ExplainX.
Turn source documents into clear spoken lessons.
Return narration text only — no markdown, no bullet points, no JSON.
""".strip()

PDF_USER = """
Explain the following document as an educational lesson.

Requirements:
- Preserve important concepts from the source.
- Skip repetitive or boilerplate text.
- Speak naturally for a complete beginner when possible.
- About {target_duration_sec} seconds when spoken (~{word_budget} words).
- No markdown.
- No bullet points.
- No JSON.
- Return narration text only.

Source document:
{document_text}

{repair_block}
""".strip()

REPAIR_EXPAND = """
Previous narration was too short for the target duration.
Write a fuller lesson with more explanation and examples while staying speakable.
""".strip()

REPAIR_SHORTEN = """
Previous narration was too long for the target duration.
Tighten the lesson while keeping the hook, core ideas, one example, and a short recap.
""".strip()
