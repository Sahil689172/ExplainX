"""Versioned Ollama prompt templates — Phase 3.6 V1 educational script."""

from __future__ import annotations

PROMPT_TEMPLATE_VERSION = "1.3"

# JSON example braces are doubled ({{ }}) so embedding via .format() is safe.
JSON_SCHEMA_INSTRUCTIONS = """
Return STRICT JSON only.
No markdown.
No explanations.
No code fences.
No trailing commentary.

The JSON MUST match this shape exactly:
{{
  "title": string,
  "language": string,
  "summary": string,
  "key_concepts": [ {{ "id": string, "label": string }} ],
  "learning_objectives": [ string ],
  "teaching_sections": [
    {{
      "id": string,
      "title": string,
      "narration": string,
      "concept_tags": [ string ]
    }}
  ],
  "warnings": [ string ]
}}

CRITICAL — do NOT include any numerical metadata.
Do NOT output estimated_words, estimated_duration_sec, estimated_word_count,
estimated_scene_count, total_words, total_duration, or similar count/duration fields.
ExplainX calculates all timing and word counts deterministically after generation.

Content constraints (must satisfy via narration length, not via number fields):
- Target about 180 seconds of speech when possible (valid band 120–180).
- Total narration words about 350–420 (valid band 300–450). Hard minimum ~300 words.
- Speaking pace is about 140 words per minute.
- Narration must be speakable (no markdown, HTML, or code fences).
- Short scripts will be rejected — write a FULL 2–3 minute lesson, not a brief summary.
""".strip()

TOPIC_SYSTEM = """
You are an expert educational narrator for ExplainX V1.
Generate a complete 2–3 minute educational explanation of the topic.
Expand concepts accurately for an animated explainer video.
Aim for roughly 400 spoken words at about 140 words per minute (near 180 seconds).
Never invent word counts or duration numbers — write narration only.
Do not produce a short overview — every teaching section needs substantial spoken narration.
""".strip()

TOPIC_USER = """
Input type: topic
Title: {title}
Language: {language}
Canonical target duration seconds: {target_duration_sec}
Word budget: {word_budget} (stay near 350–420 total words in narration text)

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
Never invent word counts or duration numbers — write narration only.
""".strip()

SCRIPT_USER = """
Input type: custom_script
Title: {title}
Language: {language}
Canonical target duration seconds: {target_duration_sec}
Word budget: {word_budget} (stay near 350–420 total words in narration text)

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
Never invent word counts or duration numbers — write narration only.
""".strip()

PDF_USER = """
Input type: pdf_extracted_text
Title: {title}
Language: {language}
Canonical target duration seconds: {target_duration_sec}
Word budget: {word_budget} (stay near 350–420 total words in narration text)

Extracted document text only (no file metadata):
{sections_text}

Known concepts (optional):
{concepts_text}

{json_schema_instructions}
""".strip()

REPAIR_USER = """
Your previous response was not valid EducationalScript JSON for ExplainX V1.
Return ONLY corrected STRICT JSON matching the required schema.
Include title, summary, key_concepts, learning_objectives, and teaching_sections
with id, title, narration, and concept_tags only.
Do NOT include any numerical metadata fields.
Ensure total narration words are about 350–420 by writing enough narration text.
No markdown. No explanations. No code fences.

Previous response:
{previous_response}

{json_schema_instructions}
""".strip()

EXPAND_SYSTEM = """
You are an expert educational editor for ExplainX V1.
You expand short educational scripts into full 2–3 minute spoken lessons.
Keep the existing structure and every fact already present.
Never invent word counts or duration numbers — write narration only.
""".strip()

EXPAND_USER = """
The script below is too short for ExplainX V1.

Current approximate speaking duration: {current_duration_sec} seconds
Current total words: {current_words}
Target speaking duration: {target_duration_sec} seconds
Word budget: about {word_budget} spoken words at 140 words per minute

Rules:
- Keep the existing structure (same teaching_sections ids and titles).
- Do not remove information.
- Expand each section's narration with examples, analogies, clearer explanations,
  and smooth transitions between ideas.
- Return the FULL script as STRICT JSON matching the schema below.
- Do NOT include any numerical metadata fields.

Current script JSON:
{script_json}

{json_schema_instructions}
""".strip()
