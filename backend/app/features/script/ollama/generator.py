"""OllamaContentGenerator — ContentGenerator backed by local Ollama (Phase 3.5)."""

from __future__ import annotations

from collections.abc import Callable

from app.core.config import Settings
from app.core.enums import SourceType
from app.core.logging import get_logger
from app.features.input.schemas import RawContentSection
from app.features.script.durations import (
    V1_MAX_DURATION_SEC,
    V1_MIN_DURATION_SEC,
    V1_MIN_WORDS,
    V1_TARGET_DURATION_SEC,
    label_for_seconds,
    word_budget,
)
from app.features.script.metrics import ScriptMetricsCalculator, enrich_script_with_metrics
from app.features.script.ollama.client import OllamaClient, OllamaClientProtocol
from app.features.script.ollama.prompt_builder import PromptBuilder
from app.features.script.ollama.response_parser import ResponseParser
from app.features.script.ollama.templates import PROMPT_TEMPLATE_VERSION
from app.features.script.schemas import EducationalScript, ScriptConcept

logger = get_logger(__name__)


class OllamaContentGenerator:
    """Generate EducationalScript via Ollama while preserving ContentGenerator API.

    Downstream processors / ContentIntelligenceService stay unchanged — inject
    this class instead of PlaceholderContentGenerator.

    If the first draft is shorter than the V1 band, one expansion pass is run
    to stretch narration toward ~180 seconds without dropping structure.
    """

    def __init__(
        self,
        client: OllamaClientProtocol,
        *,
        prompt_builder: PromptBuilder | None = None,
        response_parser: ResponseParser | None = None,
        model_name: str | None = None,
    ) -> None:
        self._client = client
        self._prompts = prompt_builder or PromptBuilder()
        self._parser = response_parser or ResponseParser()
        self._model_name = model_name or getattr(client, "model", "unknown")
        self._metrics = ScriptMetricsCalculator()

    @classmethod
    def from_settings(cls, settings: Settings) -> OllamaContentGenerator:
        client = OllamaClient.from_settings(settings)
        return cls(client, model_name=client.model)

    def generate(
        self,
        *,
        project_id: str,
        content_id: str,
        source_type: SourceType,
        title: str,
        language: str,
        sections: list[RawContentSection],
        concepts: list[ScriptConcept],
        target_duration_sec: int,
        warnings: list[str] | None = None,
        metadata: dict | None = None,
    ) -> EducationalScript:
        system, user = self._prompts.build(
            source_type=source_type,
            title=title,
            language=language,
            sections=sections,
            concepts=concepts,
            target_duration_sec=V1_MAX_DURATION_SEC,
        )

        first = self._client.generate(system=system, prompt=user)

        def _retry(previous: str) -> str:
            repair_system, repair_user = self._prompts.build_repair(
                previous_response=previous
            )
            return self._client.generate(system=repair_system, prompt=repair_user)

        script = self._parser.parse(
            first,
            project_id=project_id,
            content_id=content_id,
            source_type=source_type,
            target_duration_sec=V1_TARGET_DURATION_SEC,
            fallback_title=title,
            fallback_language=language,
            retry_fn=_retry,
        )
        script = enrich_script_with_metrics(script)

        expanded = False
        if self._needs_expansion(script):
            script = self._expand_short_script(
                script,
                project_id=project_id,
                content_id=content_id,
                source_type=source_type,
                title=title,
                language=language,
                retry_fn=_retry,
            )
            expanded = True

        out_warnings = list(warnings or []) + list(script.warnings)
        if expanded:
            out_warnings.append(
                "Script was shorter than the V1 band; one expansion pass was applied."
            )

        meta = {
            "generator": "ollama_content_v1_1",
            "llm": True,
            "ollama_model": self._model_name,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION,
            "target_duration": label_for_seconds(V1_TARGET_DURATION_SEC),
            "target_duration_sec": V1_TARGET_DURATION_SEC,
            "word_budget": word_budget(V1_MAX_DURATION_SEC),
            "requested_target_duration_sec": target_duration_sec,
            "expanded": expanded,
            **(metadata or {}),
            **(script.metadata or {}),
        }

        script = script.model_copy(
            update={
                "warnings": out_warnings,
                "metadata": meta,
                "target_duration_sec": V1_TARGET_DURATION_SEC,
            }
        )
        script = enrich_script_with_metrics(script)

        logger.info(
            "Ollama EducationalScript generated",
            extra={
                "event": "ollama_script_generated",
                "component": "ollama_content_generator",
                "project_id": project_id,
                "source_type": source_type.value,
                "model": self._model_name,
                "expanded": expanded,
                "estimated_duration_sec": script.estimated_duration_sec,
                "estimated_word_count": script.estimated_word_count,
            },
        )
        return script

    def _needs_expansion(self, script: EducationalScript) -> bool:
        metrics = self._metrics.compute(script)
        return (
            metrics.total_duration_sec < V1_MIN_DURATION_SEC
            or metrics.total_words < V1_MIN_WORDS
        )

    def _expand_short_script(
        self,
        script: EducationalScript,
        *,
        project_id: str,
        content_id: str,
        source_type: SourceType,
        title: str,
        language: str,
        retry_fn: Callable[[str], str],
    ) -> EducationalScript:
        metrics = self._metrics.compute(script)
        logger.info(
            "Expanding short Ollama script toward V1 duration band",
            extra={
                "event": "ollama_script_expand",
                "component": "ollama_content_generator",
                "project_id": project_id,
                "current_duration_sec": metrics.total_duration_sec,
                "current_words": metrics.total_words,
                "target_duration_sec": V1_MAX_DURATION_SEC,
            },
        )
        system, user = self._prompts.build_expand(
            script=script,
            current_duration_sec=metrics.total_duration_sec,
            current_words=metrics.total_words,
            target_duration_sec=V1_MAX_DURATION_SEC,
        )
        expanded_raw = self._client.generate(system=system, prompt=user)
        expanded = self._parser.parse(
            expanded_raw,
            project_id=project_id,
            content_id=content_id,
            source_type=source_type,
            target_duration_sec=V1_TARGET_DURATION_SEC,
            fallback_title=title,
            fallback_language=language,
            retry_fn=retry_fn,
        )
        # Preserve identity from the first draft when the expand pass rewrites ids.
        return enrich_script_with_metrics(
            expanded.model_copy(
                update={
                    "script_id": script.script_id,
                    "project_id": script.project_id,
                    "content_id": script.content_id,
                }
            )
        )
