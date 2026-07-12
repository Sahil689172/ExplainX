"""Build source-specific Ollama prompts for EducationalScript generation."""

from __future__ import annotations

import json

from app.core.enums import SourceType
from app.features.input.schemas import RawContentSection
from app.features.script.durations import word_budget
from app.features.script.ollama import templates
from app.features.script.schemas import EducationalScript, ScriptConcept


class PromptBuilder:
    """Separate prompt templates for topic, custom script, and PDF."""

    def __init__(self, *, template_version: str = templates.PROMPT_TEMPLATE_VERSION) -> None:
        self.template_version = template_version

    def build(
        self,
        *,
        source_type: SourceType,
        title: str,
        language: str,
        sections: list[RawContentSection],
        concepts: list[ScriptConcept],
        target_duration_sec: int,
    ) -> tuple[str, str]:
        """Return (system_prompt, user_prompt)."""
        sections_text = self._format_sections(sections)
        concepts_text = self._format_concepts(concepts)
        common = {
            "title": title,
            "language": language,
            "target_duration_sec": target_duration_sec,
            "word_budget": word_budget(target_duration_sec),
            "sections_text": sections_text,
            "concepts_text": concepts_text,
            # .format() unescapes {{ }} in the JSON example block.
            "json_schema_instructions": templates.JSON_SCHEMA_INSTRUCTIONS.format(),
        }

        if source_type == SourceType.TOPIC:
            return templates.TOPIC_SYSTEM, templates.TOPIC_USER.format(**common)
        if source_type == SourceType.SCRIPT:
            return templates.SCRIPT_SYSTEM, templates.SCRIPT_USER.format(**common)
        if source_type == SourceType.PDF:
            return templates.PDF_SYSTEM, templates.PDF_USER.format(**common)

        # Fallback: treat unknown types like PDF extracted text.
        return templates.PDF_SYSTEM, templates.PDF_USER.format(**common)

    def build_repair(self, *, previous_response: str) -> tuple[str, str]:
        system = (
            "You repair invalid JSON for ExplainX EducationalScript. "
            "Return STRICT JSON only."
        )
        user = templates.REPAIR_USER.format(
            previous_response=previous_response[:12_000],
            json_schema_instructions=templates.JSON_SCHEMA_INSTRUCTIONS.format(),
        )
        return system, user

    def build_expand(
        self,
        *,
        script: EducationalScript,
        current_duration_sec: float,
        current_words: int,
        target_duration_sec: int,
    ) -> tuple[str, str]:
        """Prompt to expand a too-short script toward the V1 duration band."""
        payload = {
            "title": script.title,
            "language": script.language,
            "summary": script.summary,
            "key_concepts": [c.model_dump(mode="json") for c in script.key_concepts],
            "learning_objectives": list(script.learning_objectives),
            "teaching_sections": [
                {
                    "id": section.id,
                    "title": section.title,
                    "narration": section.narration,
                    "concept_tags": list(section.concept_tags),
                }
                for section in script.teaching_sections
            ],
            "warnings": list(script.warnings),
        }
        user = templates.EXPAND_USER.format(
            current_duration_sec=current_duration_sec,
            current_words=current_words,
            target_duration_sec=target_duration_sec,
            word_budget=word_budget(target_duration_sec),
            script_json=json.dumps(payload, ensure_ascii=False, indent=2)[:14_000],
            json_schema_instructions=templates.JSON_SCHEMA_INSTRUCTIONS.format(),
        )
        return templates.EXPAND_SYSTEM, user

    @staticmethod
    def _format_sections(sections: list[RawContentSection]) -> str:
        if not sections:
            return "(no sections)"
        blocks: list[str] = []
        for section in sections:
            # Text only — never include processor metadata or file paths.
            heading = section.title.strip() if section.title else f"Section {section.order}"
            body = " ".join(section.text.split()).strip()
            blocks.append(f"[{section.id}] {heading}\n{body}")
        return "\n\n".join(blocks)

    @staticmethod
    def _format_concepts(concepts: list[ScriptConcept]) -> str:
        if not concepts:
            return "(none)"
        return "\n".join(f"- {c.id}: {c.label}" for c in concepts)
