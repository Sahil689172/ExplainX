"""Versioned Ollama prompt templates — Phase 3.6 V1 educational script."""

from __future__ import annotations

PROMPT_TEMPLATE_VERSION = "1.1"

JSON_SCHEMA_INSTRUCTIONS = """
Return STRICT JSON only.
No markdown.
No explanations.
No code fences.
No trailing commentary.

The JSON MUST match this shape exactly:
{
  "title": string,
  "language": string,
  "summary": string,
  "key_concepts": [ { "id": string, "label": string } ],
  "learning_objectives": [ string ],
  "teaching_sections": [
    {
      "id": string,
      "title": string,
      "narration": string,
      "estimated_duration_sec": number,
      "estimated_words": integer,
      "concept_tags": [ string ]
    }
  ],
  "estimated_duration_sec": number,
  "estimated_word_count": integer,
  "estimated_scene_count": integer,
  "warnings": [ string ]
}

V1 constraints (must satisfy):
- Target duration about 150 seconds (valid band 120–180).
- Total narration words about 320–420 (valid band 300–450).
- Speaking pace about 135–145 words per minute.
- estimated_scene_count between 18 and 25.
- Narration must be speakable (no markdown, HTML, or code fences).
""".strip()

TOPIC_SYSTEM = """
You are an expert educational narrator for ExplainX V1.
Generate a complete 2–3 minute educational explanation of the topic.
Expand concepts accurately for an animated explainer video.
Aim for roughly 350 spoken words at about 140 words per minute.
""".strip()

TOPIC_USER = """
Input type: topic
Title: {title}
Language: {language}
Canonical target duration seconds: {target_duration_sec}
Word budget: {word_budget} (stay near 320–420 total words)

Topic / section material (text only):
{sections_text}

Known concepts (optional):
{concepts_text}

{json_schema_instructions}
""".strip()

SCRIPT_SYSTEM = """
You are an expert educational editor for ExplainX V1.
Preserve the author's intent and meaning.
Improve clarity and teaching flow only where needed.
Do not rewrite unnecessarily.
Expand only if required to reach a complete 2–3 minute lesson (about 320–420 words).
""".strip()

SCRIPT_USER = """
Input type: custom_script
Title: {title}
Language: {language}
Canonical target duration seconds: {target_duration_sec}
Word budget: {word_budget} (stay near 320–420 total words)

Author script sections (text only — preserve intent):
{sections_text}

Known concepts (optional):
{concepts_text}

{json_schema_instructions}
""".strip()

PDF_SYSTEM = """
You are an expert educational narrator for ExplainX V1.
Use ONLY the extracted document text provided.
Generate a coherent 2–3 minute educational narration.
Ignore references, bibliography, acknowledgements, indexes, appendices,
and repeated headers or footers.
Do not invent facts unsupported by the text.
Aim for about 320–420 spoken words.
""".strip()

PDF_USER = """
Input type: pdf_extracted_text
Title: {title}
Language: {language}
Canonical target duration seconds: {target_duration_sec}
Word budget: {word_budget} (stay near 320–420 total words)

Extracted document text only (no file metadata):
{sections_text}

Known concepts (optional):
{concepts_text}

{json_schema_instructions}
""".strip()

REPAIR_USER = """
Your previous response was not valid EducationalScript JSON for ExplainX V1.
Return ONLY corrected STRICT JSON matching the required schema.
Ensure total words are 300–450 and estimated duration is 120–180 seconds.
No markdown. No explanations. No code fences.

Previous response:
{previous_response}

{json_schema_instructions}
""".strip()
