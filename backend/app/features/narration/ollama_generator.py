"""OllamaNarrationGenerator — one plain-text narration call."""

from __future__ import annotations

import uuid

from app.core.config import Settings
from app.core.enums import SourceType
from app.core.logging import get_logger
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContent
from app.features.narration import templates
from app.features.narration.normalize import normalize_author_script, strip_llm_wrappers
from app.features.narration.schemas import NarrationDocument
from app.features.narration.topic_resolve import resolve_requested_topic
from app.features.script.durations import word_budget
from app.features.script.ollama.client import OllamaClient, OllamaClientProtocol
from app.features.script.processors.common import resolve_language
from app.shared.prompt_format import format_prompt

logger = get_logger(__name__)


class OllamaNarrationGenerator:
    """Generate continuous narration via a single Ollama text call."""

    def __init__(
        self,
        client: OllamaClientProtocol,
        *,
        model_name: str | None = None,
    ) -> None:
        self._client = client
        self._model_name = model_name or getattr(client, "model", "unknown")

    @classmethod
    def from_settings(cls, settings: Settings) -> OllamaNarrationGenerator:
        client = OllamaClient.from_settings(settings)
        return cls(client, model_name=client.model)

    def generate(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        repair_hint: str | None = None,
    ) -> NarrationDocument:
        topic = resolve_requested_topic(raw)
        language = resolve_language(raw, None)
        budget = word_budget(target_duration_sec)

        if raw.source_type == SourceType.SCRIPT:
            text = normalize_author_script(raw.text)
            return NarrationDocument(
                narration_id=str(uuid.uuid4()),
                project_id=raw.project_id,
                content_id=raw.content_id,
                source_type=raw.source_type,
                status="ready",
                title=topic,
                language=language,
                text=text,
                target_duration_sec=target_duration_sec,
                warnings=["Author script used as narration (whitespace normalized only)."],
                metadata={
                    "generator": "author_script_narration_v1",
                    "llm": False,
                    "preserve_intent": True,
                },
                created_at=utc_now_iso(),
            )

        repair_block = repair_hint.strip() if repair_hint else ""
        if raw.source_type == SourceType.PDF:
            system = templates.PDF_SYSTEM
            user = format_prompt(
                templates.PDF_USER,
                topic=topic,
                target_duration_sec=target_duration_sec,
                word_budget=budget,
                document_text=self._document_text(raw),
                repair_block=repair_block or "(none)",
            )
        else:
            system = templates.TOPIC_SYSTEM
            user = format_prompt(
                templates.TOPIC_USER,
                topic=topic,
                target_duration_sec=target_duration_sec,
                word_budget=budget,
                repair_block=repair_block or "(none)",
            )

        raw_text = self._client.generate(
            system=system, prompt=user, json_format=False
        )
        text = strip_llm_wrappers(raw_text)
        if not text:
            text = strip_llm_wrappers(raw_text.replace("\n", " "))

        logger.info(
            "Ollama continuous narration generated",
            extra={
                "event": "ollama_narration_generated",
                "component": "ollama_narration_generator",
                "project_id": raw.project_id,
                "source_type": raw.source_type.value,
                "model": self._model_name,
                "requested_topic": topic,
            },
        )
        return NarrationDocument(
            narration_id=str(uuid.uuid4()),
            project_id=raw.project_id,
            content_id=raw.content_id,
            source_type=raw.source_type,
            status="draft",
            title=topic,
            language=language,
            text=text,
            target_duration_sec=target_duration_sec,
            warnings=[],
            metadata={
                "generator": "ollama_narration_v1",
                "llm": True,
                "ollama_model": self._model_name,
                "prompt_template_version": templates.PROMPT_TEMPLATE_VERSION,
                "word_budget": budget,
                "repair_hint": repair_hint,
                "requested_topic": topic,
            },
            created_at=utc_now_iso(),
        )

    @staticmethod
    def _document_text(raw: RawContent) -> str:
        body = " ".join(raw.text.split()).strip() or "(empty document)"
        return body[:12_000]
