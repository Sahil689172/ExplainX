"""Tests for Phase 3.6 Educational Script Standardization (V1 2–3 min)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.script.durations import (
    V1_MAX_DURATION_SEC,
    V1_MAX_WORDS,
    V1_MIN_DURATION_SEC,
    V1_MIN_WORDS,
    V1_TARGET_DURATION_SEC,
    resolve_target_duration_sec,
)
from app.features.script.generator import PlaceholderContentGenerator, PlaceholderScriptGenerator
from app.features.script.metrics import ScriptMetricsCalculator, count_words, enrich_script_with_metrics
from app.features.script.processors.pdf_filter import filter_pdf_sections
from app.features.script.processors.topic_processor import TopicContentProcessor
from app.features.script.schemas import (
    EducationalScript,
    ScriptConcept,
    TeachingSection,
)
from app.features.script.validator import ScriptValidator


def _raw(
    *,
    source_type: SourceType = SourceType.TOPIC,
    text: str = "Binary search finds items in sorted arrays.",
    title: str | None = "Binary Search",
) -> RawContent:
    return RawContent(
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        project_id="11111111-1111-1111-1111-111111111111",
        source_type=source_type,
        text=text,
        sections=[
            RawContentSection(id="section-1", text=text, order=1, title=title),
        ],
        warnings=[],
        extraction_stats=ExtractionStats(
            char_count=len(text),
            word_count=len(text.split()),
            section_count=1,
        ),
        source_path="projects/11111111-1111-1111-1111-111111111111/source/topic.txt",
        source_hash="sha256:abc",
        metadata={"language_hint": "en"},
        created_at=utc_now_iso(),
    )


def _create_project(client: TestClient, title: str) -> str:
    response = client.post(
        "/api/v1/projects",
        json={
            "title": title,
            "source_type": "topic",
            "source_topic": "placeholder topic for create",
            "theme_id": "notebooklm",
            "source_language_code": "en",
            "target_language_code": "en",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["project_id"]


def test_v1_duration_is_canonical() -> None:
    assert resolve_target_duration_sec() == V1_TARGET_DURATION_SEC
    assert resolve_target_duration_sec(label="30s") == V1_TARGET_DURATION_SEC
    assert resolve_target_duration_sec(seconds=300) == V1_TARGET_DURATION_SEC


def test_placeholder_meets_v1_band() -> None:
    script = PlaceholderContentGenerator().generate(
        project_id="11111111-1111-1111-1111-111111111111",
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        source_type=SourceType.TOPIC,
        title="Binary Search",
        language="en",
        sections=[
            RawContentSection(
                id="s1",
                text="Binary search finds items in sorted arrays.",
                order=1,
                title="Binary Search",
            )
        ],
        concepts=[ScriptConcept(id="c1", label="Binary Search")],
        target_duration_sec=60,  # ignored
    )
    assert script.target_duration_sec == V1_TARGET_DURATION_SEC
    assert V1_MIN_WORDS <= script.estimated_word_count <= V1_MAX_WORDS
    assert V1_MIN_DURATION_SEC <= script.estimated_duration_sec <= V1_MAX_DURATION_SEC
    assert 18 <= script.estimated_scene_count <= 25
    assert script.summary
    assert script.learning_objectives
    assert len(script.teaching_sections) >= 1
    ScriptValidator().validate(script)


def test_topic_processor_produces_v1_script() -> None:
    script = TopicContentProcessor().process(_raw(), target_duration_sec=30)
    assert script.source_type == SourceType.TOPIC
    assert "Binary Search" in script.title or "binary" in script.full_text.lower()
    ScriptValidator().validate(script, raw=_raw())


def test_custom_script_preserves_intent() -> None:
    text = "Welcome students. Today we study recursion carefully and with examples."
    script = PlaceholderScriptGenerator().generate(
        _raw(source_type=SourceType.SCRIPT, text=text, title="Recursion"),
        target_duration_sec=150,
    )
    assert "Welcome students" in script.full_text
    ScriptValidator().validate(script)


def test_validator_rejects_too_short() -> None:
    script = PlaceholderContentGenerator().generate(
        project_id="11111111-1111-1111-1111-111111111111",
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        source_type=SourceType.TOPIC,
        title="X",
        language="en",
        sections=[RawContentSection(id="s1", text="X", order=1, title="X")],
        concepts=[],
        target_duration_sec=150,
    )
    short = script.model_copy(
        update={
            "teaching_sections": [
                TeachingSection(
                    id="t1",
                    title="Too short",
                    narration="Too short.",
                    estimated_duration_sec=1.0,
                    estimated_words=2,
                    concept_tags=[],
                )
            ],
            "estimated_word_count": 2,
            "estimated_duration_sec": 1.0,
        }
    )
    with pytest.raises(ValidationAppError) as exc:
        ScriptValidator().validate(short)
    assert exc.value.code == "SCRIPT_VALIDATION_ERROR"


def test_script_metrics_calculator() -> None:
    script = PlaceholderContentGenerator().generate(
        project_id="11111111-1111-1111-1111-111111111111",
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        source_type=SourceType.TOPIC,
        title="Hash Tables",
        language="en",
        sections=[
            RawContentSection(id="s1", text="Hash tables store key value pairs.", order=1, title="Hash")
        ],
        concepts=[ScriptConcept(id="c1", label="Hashing")],
        target_duration_sec=150,
    )
    metrics = ScriptMetricsCalculator().compute(script)
    assert metrics.total_words == count_words(script.full_text)
    assert metrics.total_duration_sec == metrics.estimated_duration_sec
    assert metrics.language == "en"
    assert metrics.reading_level in {"beginner", "intermediate", "advanced"}
    assert metrics.average_words_per_section > 0
    for section in script.teaching_sections:
        assert section.estimated_words == count_words(section.narration)


def test_enrich_overwrites_inconsistent_llm_numbers() -> None:
    """LLM-style wrong estimated_words must not survive enrichment."""
    narration = " ".join(f"word{i}" for i in range(20)) + "."
    script = EducationalScript(
        script_id="s1",
        project_id="11111111-1111-1111-1111-111111111111",
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        source_type=SourceType.TOPIC,
        title="T",
        language="en",
        target_duration_sec=150,
        estimated_duration_sec=999.0,
        estimated_word_count=70,
        estimated_scene_count=99,
        summary="Summary text for the lesson.",
        teaching_sections=[
            TeachingSection(
                id="t1",
                title="Section",
                narration=narration,
                estimated_duration_sec=30.0,
                estimated_words=70,  # deliberately wrong vs 20 actual words
                concept_tags=[],
            )
        ],
        created_at=utc_now_iso(),
    )
    fixed = enrich_script_with_metrics(script)
    assert fixed.teaching_sections[0].estimated_words == 20
    assert fixed.estimated_word_count == 20
    assert fixed.estimated_duration_sec == ScriptMetricsCalculator().duration_for_words(20)


def test_pdf_filter_drops_bibliography() -> None:
    sections = [
        RawContentSection(id="1", text="Useful teaching content about trees.", order=1, title="Trees"),
        RawContentSection(id="2", text="Smith 2020. Jones 2021.", order=2, title="References"),
        RawContentSection(id="3", text="Appendix A details", order=3, title="Appendix"),
    ]
    kept = filter_pdf_sections(sections)
    assert len(kept) == 1
    assert kept[0].title == "Trees"


def test_schema_requires_teaching_sections() -> None:
    with pytest.raises(ValidationError):
        EducationalScript(
            script_id="s1",
            project_id="11111111-1111-1111-1111-111111111111",
            content_id="c1",
            source_type=SourceType.TOPIC,
            title="T",
            language="en",
            target_duration_sec=150,
            estimated_duration_sec=150,
            estimated_word_count=350,
            estimated_scene_count=20,
            summary="Summary",
            teaching_sections=[],
            created_at=utc_now_iso(),
        )


def test_api_persists_v1_artifacts(client: TestClient, _test_env: Path) -> None:
    project_id = _create_project(client, "V1 Script Project")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Hash tables for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    # Duration presets are accepted by the API but ignored in V1.
    created = client.post(
        f"/api/v1/projects/{project_id}/script",
        json={"target_duration": "30s"},
    )
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["target_duration_sec"] == V1_TARGET_DURATION_SEC
    assert V1_MIN_WORDS <= data["estimated_word_count"] <= V1_MAX_WORDS
    assert V1_MIN_DURATION_SEC <= data["estimated_duration_sec"] <= V1_MAX_DURATION_SEC
    assert data["summary"]
    assert data["learning_objectives"]
    assert len(data["teaching_sections"]) >= 1
    assert "schema_version" in data

    artifacts = _test_env / "projects" / project_id / "artifacts"
    assert (artifacts / "educational_script.json").is_file()
    assert (artifacts / "educational_script.md").is_file()
    assert (artifacts / "script_metrics.json").is_file()

    fetched = client.get(f"/api/v1/projects/{project_id}/script")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["script_id"] == data["script_id"]
