"""Tests for deterministic topic verification (before QA)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.core.enums import SourceType
from app.core.errors import OffTopicGenerationError
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.narration.schemas import NarrationDocument
from app.features.narration.service import NarrationGenerationService
from app.features.narration.topic_resolve import resolve_requested_topic
from app.features.narration.topic_verification import TopicVerificationService


PHOTOSYNTHESIS_WRONG = (
    "Multiplication is a basic arithmetic operation. "
    "When we multiply numbers, we find the product of factors. "
    "For example, three times four equals twelve. "
    "Students practice multiplication tables every day."
)

MONTE_CARLO_WRONG = (
    "Day and night happen because the Earth rotates on its axis. "
    "Sunlight reaches one side of the planet while the other side stays dark. "
    "This cycle repeats every twenty-four hours."
)

BINARY_SEARCH_RIGHT = (
    "Binary search finds a target value in a sorted array efficiently. "
    "We compare the target with the middle element and discard half the search space "
    "each step. For example, looking for seven in a sorted list of integers uses "
    "binary search until the middle equals seven. Finally, binary search finishes "
    "in logarithmic time. Learners practice binary search on many sorted collections "
    "so the pattern becomes automatic and reliable during interviews and coursework."
)


def test_photosynthesis_vs_multiplication_fails() -> None:
    result = TopicVerificationService(threshold=0.45).verify(
        "Photosynthesis", PHOTOSYNTHESIS_WRONG
    )
    TopicVerificationService().log_result(result)
    assert result.passed is False
    assert result.topic_relevance_score < 0.45


def test_monte_carlo_vs_day_night_fails() -> None:
    result = TopicVerificationService(threshold=0.45).verify(
        "Monte Carlo Simulation", MONTE_CARLO_WRONG
    )
    assert result.passed is False
    assert result.topic_relevance_score < 0.45


def test_binary_search_correct_passes() -> None:
    result = TopicVerificationService(threshold=0.45).verify(
        "Binary Search", BINARY_SEARCH_RIGHT
    )
    assert result.passed is True
    assert result.topic_relevance_score >= 0.45
    assert "binary" in result.detected_keywords
    assert "search" in result.detected_keywords


def test_resolve_requested_topic_ignores_generic_section_title() -> None:
    raw = RawContent(
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        project_id="11111111-1111-1111-1111-111111111111",
        source_type=SourceType.TOPIC,
        text="Photosynthesis",
        sections=[
            RawContentSection(
                id="section-1",
                text="Photosynthesis",
                order=1,
                title="Topic",
            ),
        ],
        warnings=[],
        extraction_stats=ExtractionStats(char_count=14, word_count=1, section_count=1),
        source_path="projects/x/source/topic.txt",
        source_hash="sha256:abc",
        metadata={},
        created_at=utc_now_iso(),
    )
    assert resolve_requested_topic(raw) == "Photosynthesis"


class _ScriptedGenerator:
    """Returns canned narrations in order (then repeats the last)."""

    def __init__(self, texts: list[str]) -> None:
        self.texts = list(texts)
        self.calls = 0
        self.hints: list[str | None] = []

    def generate(
        self,
        raw: RawContent,
        *,
        target_duration_sec: int,
        repair_hint: str | None = None,
    ) -> NarrationDocument:
        self.calls += 1
        self.hints.append(repair_hint)
        text = self.texts[min(self.calls - 1, len(self.texts) - 1)]
        return NarrationDocument(
            narration_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            project_id=raw.project_id,
            content_id=raw.content_id,
            source_type=raw.source_type,
            status="draft",
            title=resolve_requested_topic(raw),
            language="en",
            text=text,
            target_duration_sec=target_duration_sec,
            warnings=[],
            metadata={"llm": True, "generator": "scripted_test"},
            created_at=utc_now_iso(),
        )


def _raw_topic(topic: str) -> RawContent:
    return RawContent(
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        project_id="11111111-1111-1111-1111-111111111111",
        source_type=SourceType.TOPIC,
        text=topic,
        sections=[
            RawContentSection(id="section-1", text=topic, order=1, title=topic),
        ],
        warnings=[],
        extraction_stats=ExtractionStats(
            char_count=len(topic),
            word_count=len(topic.split()),
            section_count=1,
        ),
        source_path="projects/11111111-1111-1111-1111-111111111111/source/topic.txt",
        source_hash="sha256:abc",
        metadata={},
        created_at=utc_now_iso(),
    )


def test_service_retries_then_raises_off_topic(tmp_path: Path) -> None:
    settings = Settings(
        data_root=str(tmp_path),
        env="testing",
        ollama_enabled=False,
        topic_relevance_threshold=0.45,
        topic_verification_max_attempts=3,
    )
    project_id = "11111111-1111-1111-1111-111111111111"
    (tmp_path / "projects" / project_id / "artifacts").mkdir(parents=True)

    session = MagicMock()
    repo_get = MagicMock(return_value=object())
    service = NarrationGenerationService(
        session,
        settings,
        generator=_ScriptedGenerator([PHOTOSYNTHESIS_WRONG]),
    )
    service._repo.get = repo_get  # type: ignore[method-assign]
    service._require_project = lambda _pid: None  # type: ignore[method-assign]

    with pytest.raises(OffTopicGenerationError) as exc_info:
        service.generate(project_id, raw=_raw_topic("Photosynthesis"), target_duration_sec=90)

    err = exc_info.value
    assert err.code == "OFF_TOPIC_GENERATION"
    assert err.details["requested_topic"] == "Photosynthesis"
    assert err.details["attempt_count"] == 3
    assert err.details["topic_relevance_score"] < 0.45


def test_service_accepts_on_topic_after_retry(tmp_path: Path) -> None:
    settings = Settings(
        data_root=str(tmp_path),
        env="testing",
        ollama_enabled=False,
        topic_relevance_threshold=0.45,
        topic_verification_max_attempts=3,
    )
    project_id = "11111111-1111-1111-1111-111111111111"
    (tmp_path / "projects" / project_id / "artifacts").mkdir(parents=True)

    session = MagicMock()
    gen = _ScriptedGenerator([PHOTOSYNTHESIS_WRONG, BINARY_SEARCH_RIGHT])
    # Second attempt still wrong topic name but we need on-topic for Binary Search:
    gen = _ScriptedGenerator(
        [
            "Multiplication is unrelated filler about arithmetic products only. "
            "Students memorize multiplication tables and compute products of integers "
            "without mentioning any searching algorithm whatsoever in this narration.",
            (
                "Binary search locates values in sorted arrays by checking the middle "
                "and discarding half the range each step until binary search succeeds. "
                "We repeat the comparison carefully, keep only the relevant half, and "
                "finish when the middle element equals the target found by binary search. "
                "This lesson stays focused on binary search from start to finish."
            ),
        ]
    )
    service = NarrationGenerationService(session, settings, generator=gen)
    service._require_project = lambda _pid: None  # type: ignore[method-assign]

    doc = service.generate(
        project_id,
        raw=_raw_topic("Binary Search"),
        target_duration_sec=90,
    )
    assert gen.calls == 2
    assert "binary search" in doc.text.lower()
    assert doc.metadata.get("topic_verification") == "PASS"
    assert any(
        h and "did not explain the requested topic" in h.lower() for h in gen.hints if h
    )
