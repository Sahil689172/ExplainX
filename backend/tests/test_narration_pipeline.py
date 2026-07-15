"""Tests for narration-first pipeline (SceneBuilder + one LLM narration)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.enums import SourceType
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.narration.generator import PlaceholderNarrationGenerator
from app.features.scene_builder.builder import SceneBuilder, split_sentences
from app.features.script.durations import SCRIPT_MIN_DURATION_SEC, V1_TARGET_DURATION_SEC
from app.features.script.validator import ScriptValidator
from app.shared.pipeline_timing import pipeline_timing_scope, timed_step


def _raw(
    *,
    source_type: SourceType = SourceType.TOPIC,
    text: str = "Binary search finds items in sorted arrays efficiently.",
    title: str = "Binary Search",
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


def test_split_sentences() -> None:
    parts = split_sentences("Hello there. Next we continue! Finally we stop?")
    assert len(parts) >= 3


def test_scene_builder_builds_educational_script() -> None:
    raw = _raw()
    narration = PlaceholderNarrationGenerator().generate(
        raw, target_duration_sec=V1_TARGET_DURATION_SEC
    )
    script = SceneBuilder().build(narration, raw=raw)
    assert 8 <= len(script.teaching_sections) <= 12
    assert script.estimated_duration_sec >= SCRIPT_MIN_DURATION_SEC
    assert script.metadata.get("narration_pipeline") is True
    ScriptValidator().validate(script, raw=raw)

    outline = SceneBuilder().derive_outline(script, narration=narration)
    assert len(outline.sections) == len(script.teaching_sections)
    assert outline.metadata.get("derived_from_script") is True
    assert outline.metadata.get("llm") is False


def test_custom_script_preserves_wording_via_narration() -> None:
    text = "Welcome students. Today we study recursion carefully. We end with practice."
    raw = _raw(source_type=SourceType.SCRIPT, text=text, title="Recursion")
    narration = PlaceholderNarrationGenerator().generate(
        raw, target_duration_sec=V1_TARGET_DURATION_SEC
    )
    assert "Welcome students" in narration.text
    assert narration.metadata.get("preserve_intent") is True
    assert narration.metadata.get("llm") is False


def test_api_uses_narration_pipeline(client: TestClient, _test_env: Path, capsys) -> None:
    project_id = _create_project(client, "Narration Pipeline API")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Hash tables for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    created = client.post(f"/api/v1/projects/{project_id}/script")
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["metadata"].get("narration_pipeline") is True
    assert data["metadata"].get("single_script_generation") is False
    assert data["metadata"].get("quality_assured") is True
    assert data["status"] == "ready"
    assert 8 <= len(data["teaching_sections"]) <= 12

    artifacts = _test_env / "projects" / project_id / "artifacts"
    assert (artifacts / "narration.json").is_file()
    assert (artifacts / "narration.txt").is_file()
    assert (artifacts / "narration_en.txt").is_file()
    assert (artifacts / "teaching_outline.json").is_file()
    assert (artifacts / "educational_script.json").is_file()
    assert (artifacts / "approved_script.json").is_file()

    out = capsys.readouterr().out
    assert "[Narration]" in out
    assert "[SceneBuilder]" in out
    assert "[QualityAssurance]" in out
    assert "TOTAL:" in out


def test_pipeline_timing_labels_for_narration(capsys) -> None:
    with pipeline_timing_scope(project_id="p1"):
        with timed_step("Narration"):
            pass
        with timed_step("SceneBuilder"):
            pass
        with timed_step("QualityAssurance"):
            pass
    out = capsys.readouterr().out
    assert "[Narration]" in out
    assert "[SceneBuilder]" in out
    assert "[QualityAssurance]" in out
