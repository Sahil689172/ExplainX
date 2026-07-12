"""Versioned Ollama prompt templates for EducationalScript generation (Phase 3.5)."""

from __future__ import annotations

PROMPT_TEMPLATE_VERSION = "1.0"

JSON_SCHEMA_INSTRUCTIONS = """
Return STRICT JSON only.
No markdown.
No explanations.
No code fences.
No trailing commentary.

The JSON MUST match this shape exactly (field names and types):
{
  "title": string,
  "language": string,
  "full_text": string,
  "sections": [
    {
      "id": string,
      "order": integer starting at 1,
      "title": string,
      "narration_text": string,
      "estimated_duration_sec": number,
      "beat_ids": [string],
      "concept_ids": [string],
      "source_section_ids": [string]
    }
  ],
  "beats": [
    {
      "id": string,
      "order": integer starting at 1,
      "text": string,
      "section_id": string,
      "scene_hint": string or null,
      "approx_sec": number,
      "concept_ids": [string]
    }
  ],
  "key_concepts": [
    { "id": string, "label": string }
  ],
  "estimated_duration_sec": number,
  "warnings": [string]
}

Rules:
- Every beat.section_id must reference a section.id.
- Every section.beat_ids must list that section's beat ids exactly.
- orders must be contiguous starting at 1.
- Beat text must be speakable narration (no markdown, HTML, or code fences).
- estimated_duration_sec should be close to the target duration.
""".strip()

TOPIC_SYSTEM = """
You are an expert educational narrator for ExplainX.
Given a topic, expand concepts accurately into clear spoken teaching narration.
Respect the target duration (word budget).
Do not invent unrelated subjects.
""".strip()

TOPIC_USER = """
Input type: topic
Title: {title}
Language: {language}
Target duration seconds: {target_duration_sec}
Approximate word budget: {word_budget}

Topic / section material (text only):
{sections_text}

Known concepts (optional):
{concepts_text}

{json_schema_instructions}
""".strip()

SCRIPT_SYSTEM = """
You are an expert educational editor for ExplainX.
Preserve the author's intent and wording where possible.
Improve clarity and teaching flow only where needed.
Do not rewrite unnecessarily.
Respect the target duration.
""".strip()

SCRIPT_USER = """
Input type: custom_script
Title: {title}
Language: {language}
Target duration seconds: {target_duration_sec}
Approximate word budget: {word_budget}

Author script sections (text only — preserve intent):
{sections_text}

Known concepts (optional):
{concepts_text}

{json_schema_instructions}
""".strip()

PDF_SYSTEM = """
You are an expert educational narrator for ExplainX.
Use ONLY the extracted document text provided.
Do not invent facts not supported by the text.
Produce coherent educational narration.
Remove repetitive or irrelevant content.
Respect the target duration.
""".strip()

PDF_USER = """
Input type: pdf_extracted_text
Title: {title}
Language: {language}
Target duration seconds: {target_duration_sec}
Approximate word budget: {word_budget}

Extracted document text only (no file metadata):
{sections_text}

Known concepts (optional):
{concepts_text}

{json_schema_instructions}
""".strip()

REPAIR_USER = """
Your previous response was not valid EducationalScript JSON.
Return ONLY corrected STRICT JSON matching the required schema.
No markdown. No explanations. No code fences.

Previous response:
{previous_response}

{json_schema_instructions}
""".strip()
