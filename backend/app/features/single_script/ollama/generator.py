"""OllamaSingleScriptGenerator — full EducationalScript in one LLM call."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.outline.schemas import TeachingOutline
from app.features.script.ollama.client import OllamaClient, OllamaClientProtocol
from app.features.script.schemas import EducationalScript
from app.features.single_script.ollama import templates
from app.features.single_script.ollama.response_parser import SingleScriptResponseParser
from app.shared.prompt_format import format_prompt

logger = get_logger(__name__)


def _format_outline_sections(outline: TeachingOutline) -> str:
    blocks: list[str] = []
    for index, section in enumerate(outline.sections, start=1):
        blocks.append(
            "\n".join(
                [
                    f"Section {index}:",
                    f"  id: {section.id}",
                    f"  title: {section.title}",
                    f"  learning_objective: {section.learning_objective}",
                    f"  key_concepts: {', '.join(section.key_concepts) or '(none)'}",
                    f"  target_words: {section.target_words}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _collect_learning_objectives(outline: TeachingOutline) -> str:
    lines = [
        f"- {section.learning_objective}"
        for section in outline.sections
        if section.learning_objective.strip()
    ]
    return "\n".join(lines) if lines else "- (none)"


def _collect_key_concepts(outline: TeachingOutline) -> str:
    seen: set[str] = set()
    labels: list[str] = []
    for section in outline.sections:
        for label in section.key_concepts:
            key = label.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            labels.append(label.strip())
    return ", ".join(labels) if labels else "(none)"


class OllamaSingleScriptGenerator:
    """Generate all teaching-section narrations in a single Ollama request."""

    def __init__(
        self,
        client: OllamaClientProtocol,
        *,
        parser: SingleScriptResponseParser | None = None,
        model_name: str | None = None,
    ) -> None:
        self._client = client
        self._parser = parser or SingleScriptResponseParser()
        self._model_name = model_name or getattr(client, "model", "unknown")

    @classmethod
    def from_settings(cls, settings: Settings) -> OllamaSingleScriptGenerator:
        client = OllamaClient.from_settings(settings)
        return cls(client, model_name=client.model)

    def generate(self, outline: TeachingOutline) -> EducationalScript:
        schema_instructions = templates.render_json_schema_instructions(
            total_target_words=outline.total_target_words,
            target_duration_sec=outline.target_duration_sec,
        )
        user = format_prompt(
            templates.USER,
            title=outline.title,
            language=outline.language,
            target_duration_sec=outline.target_duration_sec,
            total_target_words=outline.total_target_words,
            learning_objectives=_collect_learning_objectives(outline),
            key_concepts=_collect_key_concepts(outline),
            outline_sections=_format_outline_sections(outline),
            json_schema_instructions=schema_instructions,
        )

        first = self._client.generate(system=templates.SYSTEM, prompt=user)

        def _retry(previous: str) -> str:
            repair = format_prompt(
                templates.REPAIR_USER,
                previous_response=previous[:12_000],
                json_schema_instructions=schema_instructions,
            )
            return self._client.generate(
                system=(
                    "You repair invalid EducationalScript JSON. "
                    "Return STRICT JSON only with title and sections."
                ),
                prompt=repair,
            )

        script = self._parser.parse(
            first,
            outline=outline,
            retry_fn=_retry,
            model_name=self._model_name,
        )

        logger.info(
            "Ollama single-script narration generated",
            extra={
                "event": "ollama_single_script_generated",
                "component": "ollama_single_script_generator",
                "project_id": outline.project_id,
                "outline_id": outline.outline_id,
                "section_count": len(outline.sections),
                "model": self._model_name,
                "estimated_word_count": script.estimated_word_count,
            },
        )
        return script
