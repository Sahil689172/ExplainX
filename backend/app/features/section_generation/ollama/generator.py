"""OllamaSectionGenerator — one TeachingOutline section per LLM call (Phase 3.8)."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.outline.schemas import TeachingOutline, TeachingSection
from app.features.script.ollama.client import OllamaClient, OllamaClientProtocol
from app.features.section_generation.ollama import templates
from app.features.section_generation.ollama.response_parser import SectionResponseParser
from app.features.section_generation.schemas import SectionOutput

logger = get_logger(__name__)


class OllamaSectionGenerator:
    """Generate narration for a single outline section via Ollama."""

    def __init__(
        self,
        client: OllamaClientProtocol,
        *,
        parser: SectionResponseParser | None = None,
        model_name: str | None = None,
    ) -> None:
        self._client = client
        self._parser = parser or SectionResponseParser()
        self._model_name = model_name or getattr(client, "model", "unknown")

    @classmethod
    def from_settings(cls, settings: Settings) -> OllamaSectionGenerator:
        client = OllamaClient.from_settings(settings)
        return cls(client, model_name=client.model)

    def generate_section(
        self,
        *,
        outline: TeachingOutline,
        section: TeachingSection,
        index: int,
        previous_section_summary: str,
        next_section_title: str | None,
    ) -> SectionOutput:
        schema_instructions = templates.JSON_SCHEMA_INSTRUCTIONS.format(
            target_words=section.target_words
        )
        user = templates.USER.format(
            lesson_title=outline.title,
            language=outline.language,
            index=index,
            section_title=section.title,
            learning_objective=section.learning_objective,
            key_concepts=", ".join(section.key_concepts) or "(none)",
            target_words=section.target_words,
            previous_section_summary=previous_section_summary.strip()
            or "(none — this is the first section)",
            next_section_title=next_section_title or "(none — this is the last section)",
            json_schema_instructions=schema_instructions,
        )

        first = self._client.generate(system=templates.SYSTEM, prompt=user)

        def _retry(previous: str) -> str:
            repair = templates.REPAIR_USER.format(
                target_words=section.target_words,
                previous_response=previous[:8_000],
                json_schema_instructions=schema_instructions,
            )
            return self._client.generate(
                system="You repair invalid section JSON. Return STRICT JSON only.",
                prompt=repair,
            )

        output = self._parser.parse(
            first,
            section=section,
            index=index,
            retry_fn=_retry,
            model_name=self._model_name,
        )

        logger.info(
            "Ollama section narration generated",
            extra={
                "event": "ollama_section_generated",
                "component": "ollama_section_generator",
                "project_id": outline.project_id,
                "outline_section_id": section.id,
                "index": index,
                "target_words": section.target_words,
                "model": self._model_name,
            },
        )
        return output
