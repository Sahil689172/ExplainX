"""Prompt templates for single-section narration generation."""

from __future__ import annotations

from app.shared.prompt_format import dumps_schema, format_prompt

PROMPT_TEMPLATE_VERSION = "1.0"

SECTION_JSON_SCHEMA: dict = {
    "narration": "<string>",
    "summary": "<string>",
}

JSON_SCHEMA_INSTRUCTIONS = """
Return STRICT JSON only.
No markdown.
No explanations.
No code fences.

The JSON MUST match this shape exactly:
{schema_json}

Rules:
- Write spoken narration ONLY for this one teaching section.
- Do NOT write other sections.
- Do NOT include titles as headings inside narration.
- Do NOT include word counts, durations, or other numerical metadata.
- Aim for about {target_words} spoken words (±15%).
- Narration must be speakable (no markdown, HTML, or code fences).
- Summary must be 1–2 short sentences capturing what this section taught.
""".strip()

SYSTEM = """
You are an expert educational narrator for ExplainX.
You write ONE teaching section of spoken narration at a time.
Keep continuity with the previous section summary and prepare a soft transition
toward the next section title when provided.
""".strip()

USER = """
Lesson title: {lesson_title}
Language: {language}
Section index: {index}

Section title: {section_title}
Learning objective: {learning_objective}
Key concepts: {key_concepts}
Target spoken words: {target_words}

Previous section summary:
{previous_section_summary}

Next section title:
{next_section_title}

{json_schema_instructions}
""".strip()

REPAIR_USER = """
Your previous response was not valid section JSON.
Return ONLY corrected STRICT JSON with keys narration and summary.
Write about {target_words} spoken words for this single section.
No markdown. No numerical metadata.

Previous response:
{previous_response}

{json_schema_instructions}
""".strip()


def render_json_schema_instructions(*, target_words: int) -> str:
    return format_prompt(
        JSON_SCHEMA_INSTRUCTIONS,
        schema_json=dumps_schema(SECTION_JSON_SCHEMA),
        target_words=target_words,
    )
