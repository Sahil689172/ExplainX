"""Prompt templates for continuous narration (plain text — not JSON)."""

from __future__ import annotations

PROMPT_TEMPLATE_VERSION = "2.1"

TOPIC_SYSTEM = """
You are ExplainX, an expert educational narrator.
""".strip()

TOPIC_USER = """
Your task is to explain ONLY the topic below.

If you do not know the topic, respond exactly with:

ERROR_UNKNOWN_TOPIC

TOPIC:
{topic}

Requirements:
- Explain only this topic.
- Use natural spoken language.
- Teach a beginner.
- 320–380 words.
- Begin with a strong hook.
- Explain concepts step by step.
- Include at least one simple real-world example.
- End with a brief recap.
- Return plain text only.
- No markdown.
- No JSON.
- No bullet points.

{repair_block}
""".strip()

PDF_SYSTEM = """
You are ExplainX, an expert educational narrator.
""".strip()

PDF_USER = """
Your task is to explain ONLY the document topic below using the source text.

If you do not know the topic, respond exactly with:

ERROR_UNKNOWN_TOPIC

TOPIC:
{topic}

Requirements:
- Explain only this topic.
- Preserve important concepts from the source; skip boilerplate.
- Use natural spoken language.
- Teach a beginner.
- 320–380 words.
- Begin with a strong hook.
- Explain concepts step by step.
- Include at least one simple real-world example.
- End with a brief recap.
- Return plain text only.
- No markdown.
- No JSON.
- No bullet points.

Source document:
{document_text}

{repair_block}
""".strip()

REPAIR_EXPAND = """
Previous narration was too short.
Write a fuller lesson (aim for 320–380 words) with more explanation and examples.
Do not change the topic.
""".strip()

REPAIR_SHORTEN = """
Previous narration was too long.
Tighten to about 320–380 words while keeping the hook, core ideas, one example, and a short recap.
Do not change the topic.
""".strip()

OFF_TOPIC_RETRY = """
The previous response did not explain the requested topic.

Explain ONLY:

TOPIC:
{topic}

If you cannot explain this topic, respond exactly:

ERROR_UNKNOWN_TOPIC
""".strip()

# Kept for NarrationGenerationService attempt branching (same text; no default-prompt retry).
OFF_TOPIC_RETRY_ATTEMPT_2 = OFF_TOPIC_RETRY
OFF_TOPIC_RETRY_ATTEMPT_3 = OFF_TOPIC_RETRY
