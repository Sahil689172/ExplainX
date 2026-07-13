"""Tests for single-pass EducationalScript generation."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.enums import SourceType
from app.core.timeutil import utc_now_iso
from app.db import session as db_session
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.outline.budget import compute_total_word_budget
from app.features.outline.generator import PlaceholderOutlineGenerator
from app.features.outline.schemas import TeachingOutline
from app.features.script.durations import (
    SCRIPT_MIN_DURATION_SEC,
    V1_TARGET_DURATION_SEC,
)
from app.features.script.validator import ScriptValidator
from app.features.single_script.generator import PlaceholderSingleScriptGenerator
from app.features.single_script.ollama.generator import OllamaSingleScriptGenerator
from app.features.single_script.protocols import SingleScriptGenerator
from app.features.single_script.service import SingleScriptGenerationService
from app.shared.pipeline_timing import pipeline_timing_scope


def _raw(
    *,
    text: str = "Linear search checks each element until a match is found.",
    title: str = "Linear Search",
) -> RawContent:
    return RawContent(
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        project_id="11111111-1111-1111-1111-111111111111",
        source_type=SourceType.TOPIC,
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


def _outline() -> TeachingOutline:
    total = compute_total_word_budget(V1_TARGET_DURATION_SEC)
    return PlaceholderOutlineGenerator().generate(
        _raw(),
        target_duration_sec=V1_TARGET_DURATION_SEC,
        total_target_words=total,
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


def test_placeholder_implements_protocol() -> None:
    generator: SingleScriptGenerator = PlaceholderSingleScriptGenerator()
    script = generator.generate(_outline())
    assert len(script.teaching_sections) >= 8
    assert script.estimated_duration_sec >= SCRIPT_MIN_DURATION_SEC
    assert script.metadata.get("single_script_generation") is True
    assert script.metadata.get("section_generation") is False
    ScriptValidator().validate(script, raw=_raw())


def test_ollama_single_script_one_call() -> None:
    calls: list[tuple[str, str]] = []
    outline = _outline()

    class MockClient:
        model = "mock-model:test"

        def generate(self, *, system: str, prompt: str) -> str:
            calls.append((system, prompt))
            sections = []
            for section in outline.sections:
                words = " ".join(f"spoken{i}" for i in range(max(25, section.target_words // 2)))
                sections.append(
                    {
                        "id": section.id,
                        "title": section.title,
                        "objective": section.learning_objective,
                        "narration": words + ".",
                    }
                )
            return json.dumps({"title": outline.title, "sections": sections})

    script = OllamaSingleScriptGenerator(MockClient()).generate(outline)
    assert len(calls) == 1
    assert "SINGLE" in calls[0][0] or "single" in calls[0][0].lower()
    assert len(script.teaching_sections) == len(outline.sections)
    assert script.metadata.get("single_script_generation") is True
    assert "spoken0" in script.teaching_sections[0].narration


def test_single_script_service_timed(
    client: TestClient, _test_env: Path, capsys
) -> None:
    project_id = _create_project(client, "Single Script Timed")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Binary search for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    from app.core.config import get_settings
    from app.features.outline.service import TeachingOutlineService

    db_session.get_engine()
    assert db_session.SessionLocal is not None
    with db_session.SessionLocal() as session:
        settings = get_settings()
        with pipeline_timing_scope(project_id=project_id) as timer:
            outline = TeachingOutlineService(session, settings).generate_outline(
                project_id
            )
            script = SingleScriptGenerationService(
                session, settings
            ).generate_from_outline(project_id, outline=outline)

    labels = [label for label, _ in timer.steps]
    assert "Outline" in labels
    assert "SingleScript" in labels
    out = capsys.readouterr().out
    assert "[Outline]" in out
    assert "[SingleScript]" in out
    assert "TOTAL:" in out
    assert script.estimated_duration_sec >= SCRIPT_MIN_DURATION_SEC
    assert script.metadata.get("single_script_generation") is True


def test_script_api_uses_narration_pipeline(
    client: TestClient, _test_env: Path, capsys
) -> None:
    project_id = _create_project(client, "Single Script API Project")
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

    artifacts = _test_env / "projects" / project_id / "artifacts"
    assert (artifacts / "teaching_outline.json").is_file()
    assert (artifacts / "educational_script.json").is_file()
    assert (artifacts / "narration.json").is_file()
    assert (artifacts / "quality_report.json").is_file()
    assert (artifacts / "approved_script.json").is_file()
    assert (artifacts / "repair_log.json").is_file()

    out = capsys.readouterr().out
    assert "[Narration]" in out
    assert "[SceneBuilder]" in out
    assert "[QualityAssurance]" in out
    assert "TOTAL:" in out
