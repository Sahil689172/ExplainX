"""Tests for Script Generation / Content Intelligence (updated for Phase 3.6)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.script.durations import V1_TARGET_DURATION_SEC
from app.features.script.generator import PlaceholderScriptGenerator
from app.features.script.protocols import ScriptGenerator
from app.features.script.schemas import EducationalScript, ScriptConcept, TeachingSection
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


def test_placeholder_implements_protocol() -> None:
    generator: ScriptGenerator = PlaceholderScriptGenerator()
    script = generator.generate(_raw())
    assert script.status == "placeholder"
    assert script.title == "Binary Search"
    assert script.language == "en"
    assert len(script.teaching_sections) >= 1
    assert script.target_duration_sec == V1_TARGET_DURATION_SEC
    assert script.estimated_duration_sec > 0
    assert script.metadata["llm"] is False


def test_custom_script_preserves_wording() -> None:
    text = "Welcome students. Today we study recursion carefully."
    script = PlaceholderScriptGenerator().generate(
        _raw(source_type=SourceType.SCRIPT, text=text, title="Recursion")
    )
    assert script.source_type == SourceType.SCRIPT
    assert "Welcome students" in script.full_text


def test_pdf_source_generates_teaching_sections() -> None:
    script = PlaceholderScriptGenerator().generate(
        _raw(
            source_type=SourceType.PDF,
            text="Photosynthesis converts light into chemical energy.",
            title="Photosynthesis",
        )
    )
    assert script.source_type == SourceType.PDF
    assert len(script.teaching_sections) >= 1


def test_validator_accepts_valid_script() -> None:
    raw = _raw()
    script = PlaceholderScriptGenerator().generate(raw)
    ScriptValidator().validate(script, raw=raw)


def test_validator_rejects_unspeakable_narration() -> None:
    script = PlaceholderScriptGenerator().generate(_raw())
    bad = script.teaching_sections[0].model_copy(update={"narration": "See ```code``` block " + ("word " * 80)})
    # Keep word count roughly valid by padding
    script = script.model_copy(update={"teaching_sections": [bad, *script.teaching_sections[1:]]})
    with pytest.raises(ValidationAppError) as exc:
        ScriptValidator().validate(script)
    assert exc.value.code == "SCRIPT_VALIDATION_ERROR"


def test_validator_rejects_content_id_mismatch() -> None:
    raw = _raw()
    script = PlaceholderScriptGenerator().generate(raw)
    other = raw.model_copy(update={"content_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"})
    with pytest.raises(ValidationAppError):
        ScriptValidator().validate(script, raw=other)


def test_schema_requires_teaching_sections() -> None:
    with pytest.raises(Exception):
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
            summary="S",
            teaching_sections=[],
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


def test_api_generate_and_get_script(client: TestClient, _test_env) -> None:
    project_id = _create_project(client, "Script Project")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Hash tables for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    plan = client.post(f"/api/v1/projects/{project_id}/presentation-plan")
    assert plan.status_code == 201, plan.text

    missing = client.get(f"/api/v1/projects/{project_id}/script")
    assert missing.status_code == 404

    created = client.post(f"/api/v1/projects/{project_id}/script")
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["status"] == "ready"
    assert data["source_type"] == "topic"
    assert len(data["teaching_sections"]) >= 1
    assert len(data["key_concepts"]) >= 1
    assert data["target_duration_sec"] == V1_TARGET_DURATION_SEC
    assert data["estimated_duration_sec"] > 0
    assert data["metadata"].get("single_script_generation") is True
    assert data["metadata"].get("section_generation") is False
    assert data["metadata"].get("quality_assured") is True

    artifact = _test_env / "projects" / project_id / "artifacts" / "educational_script.json"
    assert artifact.is_file()
    assert (_test_env / "projects" / project_id / "artifacts" / "approved_script.json").is_file()
    assert (_test_env / "projects" / project_id / "artifacts" / "teaching_outline.json").is_file()
    assert (_test_env / "projects" / project_id / "artifacts" / "quality_report.json").is_file()
    assert (_test_env / "projects" / project_id / "artifacts" / "repair_log.json").is_file()

    fetched = client.get(f"/api/v1/projects/{project_id}/script")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["script_id"] == data["script_id"]


def test_api_script_from_custom_script_input(client: TestClient) -> None:
    project_id = _create_project(client, "Custom Script Project")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/script",
        json={
            "script": "Hello class. We will study sorting algorithms today.",
            "title": "Sorting",
            "replace": True,
        },
    )
    assert ingest.status_code == 200, ingest.text
    created = client.post(f"/api/v1/projects/{project_id}/script")
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["source_type"] == "script"
    assert data["status"] == "ready"
    assert data["metadata"].get("quality_assured") is True
    assert len(data["teaching_sections"]) >= 1
    assert data["estimated_word_count"] > 0


def test_api_requires_raw_content(client: TestClient) -> None:
    project_id = _create_project(client, "No Input")
    response = client.post(f"/api/v1/projects/{project_id}/script")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RAW_CONTENT_NOT_FOUND"


def test_model_helpers() -> None:
    ScriptConcept(id="c1", label="Hashing")
    TeachingSection(
        id="t1",
        title="Intro",
        narration="Hello learners.",
        estimated_duration_sec=2.0,
        estimated_words=2,
        concept_tags=["Hashing"],
    )
