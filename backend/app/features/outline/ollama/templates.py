"""Ollama prompt templates for TeachingOutline (lesson plan only)."""

from __future__ import annotations

PROMPT_TEMPLATE_VERSION = "1.0"

JSON_SCHEMA_INSTRUCTIONS = """
Return STRICT JSON only.
No markdown.
No explanations.
No code fences.

The JSON MUST match this shape exactly:
{
  "title": string,
  "language": string,
  "sections": [
    {
      "id": string,
      "title": string,
      "learning_objective": string,
      "key_concepts": [ string ]
    }
  ]
}

Rules:
- Produce a lesson PLAN only — never write narration or spoken script text.
- Include between 8 and 12 sections (inclusive).
- Each section needs a clear teaching title, one learning objective, and key concepts.
- Do NOT include target_words, estimated_words, duration, or narration fields.
- ExplainX assigns word budgets after generation.
""".strip()

SYSTEM = """
You are an expert curriculum designer for ExplainX.
Create a structured teaching outline for a short educational explainer video.
Focus on logical lesson flow — not spoken narration.
""".strip()

USER = """
Build a TeachingOutline lesson plan.

Title hint: {title}
Language: {language}
Target duration seconds: {target_duration_sec}
Total word budget (for later narration, not for this JSON): {total_target_words}
Required section count: {section_count} (must be between 8 and 12)

Source material (text only):
{sections_text}

{json_schema_instructions}
""".strip()

REPAIR_USER = """
Your previous response was not valid TeachingOutline JSON.
Return ONLY corrected STRICT JSON with 8–12 sections.
Each section needs id, title, learning_objective, and key_concepts.
No narration. No target_words. No markdown.

Previous response:
{previous_response}

{json_schema_instructions}
""".strip()
