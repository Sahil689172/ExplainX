"""OllamaOutlineGenerator — TeachingOutline via local Ollama (Phase 3.7)."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.input.schemas import RawContent
from app.features.outline.ollama import templates
from app.features.outline.ollama.response_parser import OutlineResponseParser
from app.features.outline.schemas import OUTLINE_SECTION_MIN, TeachingOutline
from app.features.script.ollama.client import OllamaClient, OllamaClientProtocol
from app.features.script.processors.common import resolve_language, resolve_title

logger = get_logger(__name__)


class OllamaOutlineGenerator:
    """Generate a lesson-plan TeachingOutline (never narration)."""

    def __init__(
        self,
        client: OllamaClientProtocol,
        *,
        parser: OutlineResponseParser | None = None,
        model_name: str | None = None,
        section_count: int = 10,
    ) -> None:
        self._client = client
        self._parser = parser or OutlineResponseParser()
        self._model_name = model_name or getattr(client, "model", "unknown")
        self._section_count = max(OUTLINE_SECTION_MIN, min(12, section_count))

    @classmethod
    def from_settings(cls, settings: Settings) -> OllamaOutlineGenerator:
        client = OllamaClient.from_settings(settings)
        return cls(client, model_name=client.model)

    def generate(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        total_target_words: int,
    ) -> TeachingOutline:
        title = resolve_title(raw, None)
        language = resolve_language(raw, None)
        sections_text = self._format_sections(raw)

        system = templates.SYSTEM
        user = templates.USER.format(
            title=title,
            language=language,
            target_duration_sec=target_duration_sec,
            total_target_words=total_target_words,
            section_count=self._section_count,
            sections_text=sections_text,
            json_schema_instructions=templates.JSON_SCHEMA_INSTRUCTIONS,
        )

        first = self._client.generate(system=system, prompt=user)

        def _retry(previous: str) -> str:
            repair_user = templates.REPAIR_USER.format(
                previous_response=previous[:12_000],
                json_schema_instructions=templates.JSON_SCHEMA_INSTRUCTIONS,
            )
            return self._client.generate(
                system="You repair invalid TeachingOutline JSON. Return STRICT JSON only.",
                prompt=repair_user,
            )

        outline = self._parser.parse(
            first,
            raw=raw,
            target_duration_sec=target_duration_sec,
            total_target_words=total_target_words,
            fallback_title=title,
            fallback_language=language,
            retry_fn=_retry,
        )
        meta = {
            **(outline.metadata or {}),
            "ollama_model": self._model_name,
            "prompt_template_version": templates.PROMPT_TEMPLATE_VERSION,
        }
        outline = outline.model_copy(update={"metadata": meta})

        logger.info(
            "Ollama TeachingOutline generated",
            extra={
                "event": "ollama_outline_generated",
                "component": "ollama_outline_generator",
                "project_id": raw.project_id,
                "section_count": len(outline.sections),
                "total_target_words": outline.total_target_words,
                "model": self._model_name,
            },
        )
        return outline

    @staticmethod
    def _format_sections(raw: RawContent) -> str:
        if not raw.sections:
            body = " ".join(raw.text.split()).strip() or "(empty)"
            return body[:8_000]
        blocks: list[str] = []
        for section in raw.sections:
            heading = section.title.strip() if section.title else f"Section {section.order}"
            body = " ".join(section.text.split()).strip()
            blocks.append(f"[{section.id}] {heading}\n{body}")
        return "\n\n".join(blocks)[:8_000]
