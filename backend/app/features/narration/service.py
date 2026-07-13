"""NarrationGenerationService — RawContent → continuous NarrationDocument."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import SourceType
from app.core.errors import NotFoundError, OffTopicGenerationError
from app.core.logging import get_logger
from app.features.input.schemas import RawContent
from app.features.input.store import InputArtifactStore
from app.features.narration import templates
from app.features.narration.factory import create_narration_generator
from app.features.narration.protocols import NarrationGenerator
from app.features.narration.schemas import NarrationDocument
from app.features.narration.store import NarrationArtifactStore
from app.features.narration.topic_resolve import resolve_requested_topic
from app.features.narration.topic_verification import (
    TopicVerificationResult,
    TopicVerificationService,
)
from app.features.narration.validator import NarrationValidator
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.script.durations import resolve_target_duration_sec
from app.shared.pipeline_timing import timed_step
from app.shared.prompt_format import format_prompt

logger = get_logger(__name__)


class NarrationGenerationService:
    """Produce continuous narration (one LLM call for topic/PDF; none for script).

    For topic/PDF sources, deterministic topic verification runs after generation
    and before NarrationValidator / downstream QA.
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        generator: NarrationGenerator | None = None,
        validator: NarrationValidator | None = None,
        topic_verifier: TopicVerificationService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._raw_store = InputArtifactStore(self._fs)
        self._store = NarrationArtifactStore(self._fs)
        self._generator = generator or create_narration_generator(settings)
        self._validator = validator or NarrationValidator()
        self._topic_verifier = topic_verifier or TopicVerificationService(
            threshold=settings.topic_relevance_threshold
        )

    def generate(
        self,
        project_id: str,
        *,
        raw: RawContent | None = None,
        target_duration_sec: int | None = None,
        repair_hint: str | None = None,
    ) -> NarrationDocument:
        validate_project_id(project_id)
        self._require_project(project_id)
        content = raw or self._raw_store.read_raw_content(project_id)
        duration = target_duration_sec or resolve_target_duration_sec()
        topic = resolve_requested_topic(content)
        skip_topic_check = content.source_type == SourceType.SCRIPT
        max_attempts = (
            1
            if skip_topic_check
            else int(self._settings.topic_verification_max_attempts)
        )

        last_result: TopicVerificationResult | None = None
        narration: NarrationDocument | None = None

        with timed_step("Narration"):
            for attempt in range(1, max_attempts + 1):
                attempt_hint = self._compose_repair_hint(
                    topic=topic,
                    base_hint=repair_hint,
                    attempt=attempt,
                    skip_topic_check=skip_topic_check,
                )
                narration = self._generator.generate(
                    content,
                    target_duration_sec=duration,
                    repair_hint=attempt_hint,
                )

                if skip_topic_check:
                    break

                last_result = self._topic_verifier.verify(topic, narration.text)
                self._topic_verifier.log_result(last_result)
                logger.info(
                    "Topic verification %s",
                    "PASS" if last_result.passed else "FAIL",
                    extra={
                        "event": "topic_verification",
                        "project_id": project_id,
                        "requested_topic": topic,
                        "topic_relevance_score": last_result.topic_relevance_score,
                        "attempt": attempt,
                        "passed": last_result.passed,
                        "keywords": last_result.detected_keywords,
                    },
                )

                if last_result.passed:
                    meta = dict(narration.metadata or {})
                    meta["topic_relevance_score"] = last_result.topic_relevance_score
                    meta["topic_verification_attempt"] = attempt
                    meta["topic_verification"] = "PASS"
                    narration = narration.model_copy(update={"metadata": meta})
                    break

                if attempt >= max_attempts:
                    raise OffTopicGenerationError(
                        "Generated narration is not about the requested topic.",
                        details={
                            "requested_topic": topic,
                            "topic_relevance_score": last_result.topic_relevance_score,
                            "attempt_count": attempt,
                            "threshold": self._topic_verifier.threshold,
                            "detected_keywords": last_result.detected_keywords,
                            "keyword_coverage": last_result.keyword_coverage,
                            "cosine_similarity": last_result.cosine_similarity,
                        },
                    )

            assert narration is not None
            self._validator.validate(narration)
            self._store.write(project_id, narration)

        logger.info(
            "Narration ready",
            extra={
                "event": "narration_generated",
                "project_id": project_id,
                "narration_id": narration.narration_id,
                "source_type": narration.source_type.value,
                "llm": bool((narration.metadata or {}).get("llm")),
                "requested_topic": topic,
            },
        )
        return narration

    @staticmethod
    def _compose_repair_hint(
        *,
        topic: str,
        base_hint: str | None,
        attempt: int,
        skip_topic_check: bool,
    ) -> str | None:
        parts: list[str] = []
        if base_hint and base_hint.strip():
            parts.append(base_hint.strip())
        if not skip_topic_check and attempt == 2:
            parts.append(
                format_prompt(templates.OFF_TOPIC_RETRY_ATTEMPT_2, topic=topic)
            )
        elif not skip_topic_check and attempt >= 3:
            parts.append(
                format_prompt(templates.OFF_TOPIC_RETRY_ATTEMPT_3, topic=topic)
            )
        if not parts:
            return None
        return "\n\n".join(parts)

    def _require_project(self, project_id: str) -> None:
        if self._repo.get(project_id) is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )
