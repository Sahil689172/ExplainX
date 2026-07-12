"""Prompt templates for single-section repair."""

from __future__ import annotations

PROMPT_TEMPLATE_VERSION = "1.0"

SYSTEM = """
You are an expert educational editor for ExplainX.
You repair ONE teaching section of spoken narration at a time.
Never rewrite the entire lesson.
Return STRICT JSON only with a single key: narration.
""".strip()

USER = """
Repair ONLY this teaching section.

Repair action: {action}
Section title: {title}
Learning objective: {learning_objective}
Target spoken words: {target_words}
Actual spoken words: {actual_words}

Validation failures:
{validation_failures}

Previous section summary:
{previous_section_summary}

Next section title:
{next_section_title}

Original narration:
{original_narration}

Return STRICT JSON only:
{{
  "narration": string
}}

Rules:
- Return ONLY the repaired narration for this section.
- Do not include other sections.
- Do not include titles, markdown, or numerical metadata.
- Aim for about {target_words} spoken words.
""".strip()
