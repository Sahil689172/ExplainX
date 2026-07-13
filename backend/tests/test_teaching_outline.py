"""Tests for Phase 3.7 Teaching Outline Service."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.core.timeutil import utc_now_iso
from app.db import session as db_session
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.outline.budget import (
    WORD_BUDGET_TOLERANCE,
    apply_word_budget,
    compute_total_word_budget,
    distribute_word_budget,
)
from app.features.outline.generator import PlaceholderOutlineGenerator
from app.features.outline.ollama.generator import OllamaOutlineGenerator
from app.features.outline.schemas import (
    OUTLINE_SECTION_MAX,
    OUTLINE_SECTION_MIN,
    TeachingOutline,
    TeachingSection,
)
from app.features.outline.service import TeachingOutlineService
from app.features.outline.validator import OutlineValidator
from app.features.script.durations import V1_TARGET_DURATION_SEC, V1_WPM


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


def test_compute_total_word_budget_at_140_wpm() -> None:
    assert compute_total_word_budget(60) == int(round((V1_WPM / 60.0) * 60))
    assert compute_total_word_budget(150) == 350
    assert compute_total_word_budget(180) == 420


def test_distribute_word_budget_sums_exactly() -> None:
    for total in (300, 350, 420):
        for count in range(OUTLINE_SECTION_MIN, OUTLINE_SECTION_MAX + 1):
            parts = distribute_word_budget(total, count)
            assert len(parts) == count
            assert sum(parts) == total
            assert all(p >= 1 for p in parts)


def test_placeholder_outline_has_8_to_12_sections() -> None:
    outline = PlaceholderOutlineGenerator().generate(
        _raw(),
        target_duration_sec=V1_TARGET_DURATION_SEC,
        total_target_words=compute_total_word_budget(V1_TARGET_DURATION_SEC),
    )
    assert OUTLINE_SECTION_MIN <= len(outline.sections) <= OUTLINE_SECTION_MAX
    assert outline.total_target_words == 350
    assert outline.allocated_words == 350
    for section in outline.sections:
        assert section.learning_objective
        assert section.target_words >= 1
        assert section.key_concepts
    assert "narration" not in TeachingSection.model_fields
    OutlineValidator().validate(outline, raw=_raw())


def test_outline_has_no_narration_fields() -> None:
    outline = PlaceholderOutlineGenerator().generate(
        _raw(),
        target_duration_sec=150,
        total_target_words=350,
    )
    dumped = outline.model_dump(mode="json")
    assert "narration" not in dumped
    for section in dumped["sections"]:
        assert "narration" not in section
        assert set(section.keys()) >= {
            "id",
            "title",
            "learning_objective",
            "target_words",
            "key_concepts",
        }


def test_validator_rejects_word_budget_mismatch() -> None:
    outline = PlaceholderOutlineGenerator().generate(
        _raw(),
        target_duration_sec=150,
        total_target_words=350,
    )
    bad_sections = list(outline.sections)
    bad_sections[0] = bad_sections[0].model_copy(
        update={"target_words": bad_sections[0].target_words + WORD_BUDGET_TOLERANCE + 5}
    )
    bad = outline.model_copy(update={"sections": bad_sections})
    with pytest.raises(ValidationAppError) as exc:
        OutlineValidator().validate(bad)
    assert exc.value.code == "OUTLINE_VALIDATION_ERROR"


def test_apply_word_budget_restores_exact_total() -> None:
    outline = PlaceholderOutlineGenerator().generate(
        _raw(),
        target_duration_sec=150,
        total_target_words=350,
    )
    skewed = outline.model_copy(
        update={
            "sections": [
                s.model_copy(update={"target_words": 10}) for s in outline.sections
            ]
        }
    )
    fixed = apply_word_budget(skewed, total_target_words=350)
    assert fixed.allocated_words == 350
    OutlineValidator().validate(fixed)


def test_ollama_outline_generator_with_mock() -> None:
    class MockClient:
        model = "mock-model:test"

        def generate(self, *, system: str, prompt: str) -> str:
            sections = []
            for i in range(10):
                sections.append(
                    {
                        "id": f"outline-{i+1}",
                        "title": f"Section {i+1}",
                        "learning_objective": f"Learn point {i+1} about Linear Search.",
                        "key_concepts": ["Linear Search", f"Point {i+1}"],
                    }
                )
            return json.dumps(
                {
                    "title": "Linear Search",
                    "language": "en",
                    "sections": sections,
                }
            )

    outline = OllamaOutlineGenerator(MockClient()).generate(
        _raw(),
        target_duration_sec=150,
        total_target_words=350,
    )
    assert len(outline.sections) == 10
    assert outline.allocated_words == 350
    assert outline.metadata.get("llm") is True
    OutlineValidator().validate(outline, raw=_raw())


def test_teaching_outline_service_persists_artifact(
    client: TestClient, _test_env: Path
) -> None:
    project_id = _create_project(client, "Outline Persist Project")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Binary search for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    db_session.get_engine()
    assert db_session.SessionLocal is not None
    with db_session.SessionLocal() as session:
        from app.core.config import get_settings

        service = TeachingOutlineService(session, get_settings())
        outline = service.generate_outline(project_id)

    path = _test_env / "projects" / project_id / "artifacts" / "teaching_outline.json"
    assert path.is_file()
    loaded = TeachingOutline.model_validate_json(path.read_text(encoding="utf-8"))
    assert loaded.outline_id == outline.outline_id
    assert OUTLINE_SECTION_MIN <= len(loaded.sections) <= OUTLINE_SECTION_MAX
    assert loaded.allocated_words == loaded.total_target_words


def test_script_generation_also_writes_outline(
    client: TestClient, _test_env: Path
) -> None:
    project_id = _create_project(client, "Outline Via Script Project")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Hash tables for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    created = client.post(f"/api/v1/projects/{project_id}/script")
    assert created.status_code == 201, created.text

    artifacts = _test_env / "projects" / project_id / "artifacts"
    assert (artifacts / "teaching_outline.json").is_file()
    assert (artifacts / "educational_script.json").is_file()
    assert (artifacts / "narration.json").is_file()
    outline = TeachingOutline.model_validate_json(
        (artifacts / "teaching_outline.json").read_text(encoding="utf-8")
    )
    assert outline.metadata.get("derived_from_script") is True
    assert outline.metadata.get("llm") is False
    assert OUTLINE_SECTION_MIN <= len(outline.sections) <= OUTLINE_SECTION_MAX
    script_meta = created.json()["data"]["metadata"]
    assert script_meta.get("teaching_outline_id") == outline.outline_id
    assert script_meta.get("narration_pipeline") is True
