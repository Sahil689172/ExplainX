"""Prompt templates for single-pass EducationalScript generation."""

from __future__ import annotations

from app.shared.prompt_format import dumps_schema, format_prompt

PROMPT_TEMPLATE_VERSION = "1.0"

SINGLE_SCRIPT_JSON_SCHEMA: dict = {
    "title": "<string>",
    "sections": [
        {
            "id": "<string>",
            "title": "<string>",
            "objective": "<string>",
            "narration": "<string>",
        }
    ],
}

JSON_SCHEMA_INSTRUCTIONS = """
Return STRICT JSON only.
No markdown.
No explanations.
No code fences.

The JSON MUST match this shape exactly:
{schema_json}

Rules:
- Generate spoken narration for EVERY outline section in ONE response.
- Keep section ids exactly as provided in the teaching outline.
- Keep section titles aligned with the outline.
- Do NOT invent extra sections or drop outline sections.
- Do NOT include word counts, durations, or other numerical metadata.
- Narration must be speakable (no markdown, HTML, or code fences).
- Aim for about {total_target_words} total spoken words across all sections
  (about {target_duration_sec} seconds at 140 words per minute).
""".strip()

SYSTEM = """
You are an expert educational narrator for ExplainX.
You write a complete multi-section spoken lesson in a SINGLE response.
Follow the teaching outline order, objectives, and concepts strictly.
""".strip()

USER = """
Generate a full EducationalScript narration from this TeachingOutline.

Topic / lesson title: {title}
Language: {language}
Target duration seconds: {target_duration_sec}
Total spoken word budget: {total_target_words}

Learning objectives:
{learning_objectives}

Key concepts:
{key_concepts}

Teaching outline (plan only — write narration for each section):
{outline_sections}

{json_schema_instructions}
""".strip()

REPAIR_USER = """
Your previous response was not valid single-script JSON for ExplainX.
Return ONLY corrected STRICT JSON with title and sections.
Keep every outline section id. No markdown. No numerical metadata.

Previous response:
{previous_response}

{json_schema_instructions}
""".strip()


def render_json_schema_instructions(
    *,
    total_target_words: int,
    target_duration_sec: int,
) -> str:
    return format_prompt(
        JSON_SCHEMA_INSTRUCTIONS,
        schema_json=dumps_schema(SINGLE_SCRIPT_JSON_SCHEMA),
        total_target_words=total_target_words,
        target_duration_sec=target_duration_sec,
    )
