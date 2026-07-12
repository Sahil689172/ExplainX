"""Tests for Phase 3 Content Intelligence (EducationalScript from any input)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.core.timeutil import utc_now_iso
from app.features.input.pdf_extract import PDF_MAX_PAGES, PDF_MAX_BYTES, validate_pdf_size
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.script.durations import resolve_target_duration_sec, word_budget
from app.features.script.generator import PlaceholderContentGenerator
from app.features.script.processors.pdf_processor import PDFContentProcessor
from app.features.script.processors.script_processor import ScriptContentProcessor
from app.features.script.processors.topic_processor import TopicContentProcessor
from app.features.script.protocols import ContentGenerator


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


def test_target_duration_labels() -> None:
    assert resolve_target_duration_sec(label="30s") == 30
    assert resolve_target_duration_sec(label="60s") == 60
    assert resolve_target_duration_sec(label="90s") == 90
    assert resolve_target_duration_sec(label="3min") == 180
    assert resolve_target_duration_sec(label="5min") == 300
    assert resolve_target_duration_sec(seconds=180) == 180
    with pytest.raises(ValidationAppError):
        resolve_target_duration_sec(label="2min")
    with pytest.raises(ValidationAppError):
        resolve_target_duration_sec(seconds=45)


def test_placeholder_generator_implements_protocol() -> None:
    generator: ContentGenerator = PlaceholderContentGenerator()
    script = generator.generate(
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
        concepts=[],
        target_duration_sec=60,
    )
    assert script.status == "placeholder"
    assert script.target_duration_sec == 60
    assert script.metadata["llm"] is False
    assert script.metadata["generator"] == "placeholder_content_v1"
    assert len(script.beats) >= 1


def test_topic_processor_research_placeholder() -> None:
    script = TopicContentProcessor().process(_raw(), target_duration_sec=90)
    assert script.source_type == SourceType.TOPIC
    assert script.target_duration_sec == 90
    assert "Today we will learn" in script.full_text
    assert script.metadata["research_mode"] == "placeholder"
    assert script.metadata["processor"] == "topic_content_v1"


def test_script_processor_preserves_intent() -> None:
    text = "Welcome students. Today we study recursion carefully"
    script = ScriptContentProcessor().process(
        _raw(source_type=SourceType.SCRIPT, text=text, title="Recursion"),
        target_duration_sec=60,
    )
    assert "Welcome students" in script.full_text
    assert script.metadata["preserve_intent"] is True
    # Readability pass adds terminal punctuation when missing.
    assert script.full_text.rstrip().endswith(".")


def test_pdf_processor_framing_from_raw() -> None:
    script = PDFContentProcessor().process(
        _raw(
            source_type=SourceType.PDF,
            text="Photosynthesis converts light into chemical energy.",
            title="Photosynthesis",
        ),
        target_duration_sec=60,
        pdf_path=None,
    )
    assert script.source_type == SourceType.PDF
    assert "Let's begin." in script.full_text
    assert script.metadata["extractor"] == "pymupdf4llm"


def test_longer_target_allows_more_words() -> None:
    short = word_budget(30)
    long = word_budget(300)
    assert long > short


def test_pdf_size_limit() -> None:
    validate_pdf_size(1024)
    with pytest.raises(Exception) as exc:
        validate_pdf_size(PDF_MAX_BYTES + 1)
    assert getattr(exc.value, "code", None) == "UPLOAD_TOO_LARGE"


def test_api_generate_with_target_duration(client: TestClient, _test_env: Path) -> None:
    project_id = _create_project(client, "Phase3 Duration")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Hash tables for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    created = client.post(
        f"/api/v1/projects/{project_id}/script",
        json={"target_duration": "3min"},
    )
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["target_duration_sec"] == 180
    assert data["metadata"]["target_duration"] == "3min"
    assert data["metadata"]["processor"] == "topic_content_v1"
    assert data["status"] == "placeholder"

    artifact = _test_env / "projects" / project_id / "artifacts" / "v1" / "script.json"
    assert artifact.is_file()


def test_api_rejects_invalid_duration(client: TestClient) -> None:
    project_id = _create_project(client, "Bad Duration")
    client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Valid topic text here", "replace": True},
    )
    response = client.post(
        f"/api/v1/projects/{project_id}/script",
        json={"target_duration": "2min"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_api_script_from_custom_script(client: TestClient) -> None:
    project_id = _create_project(client, "Custom Script Phase3")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/script",
        json={
            "script": "Hello class. We will study sorting algorithms today.",
            "title": "Sorting",
            "replace": True,
        },
    )
    assert ingest.status_code == 200, ingest.text
    created = client.post(
        f"/api/v1/projects/{project_id}/script",
        json={"target_duration_sec": 90},
    )
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["source_type"] == "script"
    assert data["target_duration_sec"] == 90
    assert "Hello class" in data["full_text"]


def test_pdf_max_pages_constant() -> None:
    assert PDF_MAX_PAGES == 30
    assert PDF_MAX_BYTES == 25 * 1024 * 1024
