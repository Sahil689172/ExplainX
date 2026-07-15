"""Prompt templates for continuous English narration (plain text — not JSON)."""

from __future__ import annotations

PROMPT_TEMPLATE_VERSION = "4.0"

TOPIC_SYSTEM = """
You are ExplainX, an expert educational narrator.
You are an educational narrator.
Generate natural spoken English.
Write directly in English. Do not translate from another language.
""".strip()

TOPIC_USER = """
Your ONLY task is to explain the topic below in English.

Explain the requested topic naturally.
If the topic is ambiguous, make your best reasonable interpretation.
Never respond with ERROR_UNKNOWN_TOPIC.
Never refuse; always produce spoken educational narration in English.

TOPIC:
{topic}

Requirements:
- Explain ONLY this topic.
- Speak naturally for a beginner.
- Educational spoken narration in English (about 320–380 words).
- Begin with a strong hook.
- Explain concepts step by step.
- Include at least one simple real-world example.
- End with a brief recap.
- Return plain spoken text only.
- No markdown.
- No JSON.
- No bullet points.
- No headings.
- Write directly in English.

{repair_block}
""".strip()

PDF_SYSTEM = """
You are ExplainX, an expert educational narrator.
You are an educational narrator.
Generate natural spoken English.
Write directly in English. Do not translate from another language.
""".strip()

PDF_USER = """
Your ONLY task is to explain the document topic below in English.

Explain the requested topic naturally.
If the topic is ambiguous, make your best reasonable interpretation.
Never respond with ERROR_UNKNOWN_TOPIC.
Never refuse; always produce spoken educational narration in English.

TOPIC:
{topic}

Requirements:
- Explain ONLY this topic using the source.
- Preserve important concepts; skip boilerplate.
- Speak naturally for a beginner.
- Educational spoken narration in English (about 320–380 words).
- Begin with a strong hook.
- Explain concepts step by step.
- Include at least one simple real-world example.
- End with a brief recap.
- Return plain spoken text only.
- No markdown.
- No JSON.
- No bullet points.
- No headings.
- Write directly in English.

Source document:
{document_text}

{repair_block}
""".strip()

REPAIR_EXPAND = """
Previous narration was too short.
Write a fuller English lesson (aim for 320–380 words) with more explanation and examples.
Do not change the topic.
""".strip()

REPAIR_SHORTEN = """
Previous narration was too long.
Tighten to about 320–380 words of English while keeping the hook, core ideas, one example, and a short recap.
Do not change the topic.
""".strip()

OFF_TOPIC_RETRY = """
The previous response did not explain the requested topic.

Explain ONLY this topic naturally, in English:

TOPIC:
{topic}

If the topic is ambiguous, make your best reasonable interpretation.
Never respond with ERROR_UNKNOWN_TOPIC.
""".strip()

OFF_TOPIC_RETRY_ATTEMPT_2 = OFF_TOPIC_RETRY
OFF_TOPIC_RETRY_ATTEMPT_3 = OFF_TOPIC_RETRY
