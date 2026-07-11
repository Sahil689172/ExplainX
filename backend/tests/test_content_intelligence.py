"""Tests for Phase 2.3 Content Intelligence (PresentationPlan)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.presentation.planner import PlaceholderPresentationPlanner
from app.features.presentation.protocols import PresentationPlanner
from app.features.presentation.schemas import (
    KeyConcept,
    LearningObjective,
    PresentationPlan,
    TeachingSection,
    VisualCandidate,
)
from app.features.presentation.validators import PresentationPlanValidator


def _sample_raw(**overrides: object) -> RawContent:
    data = {
        "content_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "project_id": "11111111-1111-1111-1111-111111111111",
        "source_type": SourceType.TOPIC,
        "text": "Binary search finds items in sorted arrays efficiently.",
        "sections": [
            RawContentSection(
                id="section-1",
                text="Binary search finds items in sorted arrays efficiently.",
                order=1,
                title="Binary Search",
            )
        ],
        "warnings": [],
        "extraction_stats": ExtractionStats(
            char_count=55, word_count=8, page_count=0, section_count=1
        ),
        "source_path": "projects/11111111-1111-1111-1111-111111111111/source/topic.txt",
        "source_hash": "sha256:abc",
        "metadata": {"language_hint": "en"},
        "created_at": utc_now_iso(),
    }
    data.update(overrides)
    return RawContent(**data)  # type: ignore[arg-type]


def test_placeholder_planner_implements_protocol() -> None:
    planner: PresentationPlanner = PlaceholderPresentationPlanner()
    plan = planner.plan(_sample_raw())
    assert plan.status == "placeholder"
    assert plan.title == "Binary Search"
    assert plan.language == "en"
    assert plan.estimated_duration_sec >= 15.0
    assert len(plan.key_concepts) >= 1
    assert len(plan.learning_objectives) >= 1
    assert len(plan.visual_candidates) >= 1
    assert len(plan.teaching_sections) == 1
    assert plan.content_id == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert plan.metadata.get("llm") is False


def test_presentation_plan_schema_rejects_empty_sections() -> None:
    with pytest.raises(ValidationError):
        PresentationPlan(
            plan_id="p1",
            project_id="11111111-1111-1111-1111-111111111111",
            content_id="c1",
            title="T",
            language="en",
            estimated_duration_sec=30,
            teaching_sections=[],
            created_at=utc_now_iso(),
        )


def test_validator_catches_bad_cross_refs() -> None:
    plan = PlaceholderPresentationPlanner().plan(_sample_raw())
    plan.teaching_sections[0].concept_ids = ["missing-concept"]
    with pytest.raises(ValidationAppError) as exc:
        PresentationPlanValidator().validate(plan)
    assert exc.value.code == "PLAN_VALIDATION_ERROR"


def test_validator_requires_matching_content_id() -> None:
    raw = _sample_raw()
    plan = PlaceholderPresentationPlanner().plan(raw)
    other = raw.model_copy(update={"content_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"})
    with pytest.raises(ValidationAppError):
        PresentationPlanValidator().validate(plan, raw=other)


def test_validator_accepts_valid_plan() -> None:
    raw = _sample_raw()
    plan = PlaceholderPresentationPlanner().plan(raw)
    PresentationPlanValidator().validate(plan, raw=raw)


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


def test_api_generate_and_get_presentation_plan(client: TestClient, _test_env) -> None:
    project_id = _create_project(client, "Plan Project")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Photosynthesis for grade eight students", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    missing = client.get(f"/api/v1/projects/{project_id}/presentation-plan")
    assert missing.status_code == 404

    created = client.post(f"/api/v1/projects/{project_id}/presentation-plan")
    assert created.status_code == 201, created.text
    plan = created.json()["data"]
    assert plan["status"] == "placeholder"
    assert plan["title"]
    assert plan["language"]
    assert plan["estimated_duration_sec"] >= 0
    assert len(plan["teaching_sections"]) >= 1
    assert len(plan["key_concepts"]) >= 1
    assert len(plan["learning_objectives"]) >= 1
    assert len(plan["visual_candidates"]) >= 1
    assert plan["metadata"]["llm"] is False

    artifact = (
        _test_env
        / "projects"
        / project_id
        / "artifacts"
        / "v1"
        / "presentation_plan.json"
    )
    assert artifact.is_file()

    fetched = client.get(f"/api/v1/projects/{project_id}/presentation-plan")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["plan_id"] == plan["plan_id"]


def test_api_requires_raw_content_first(client: TestClient) -> None:
    project_id = _create_project(client, "No Raw Yet")
    response = client.post(f"/api/v1/projects/{project_id}/presentation-plan")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RAW_CONTENT_NOT_FOUND"


def test_model_field_constraints() -> None:
    KeyConcept(id="c1", label="Hashing")
    LearningObjective(id="o1", text="Explain hashing")
    VisualCandidate(id="v1", kind="diagram", description="Hash table diagram")
    TeachingSection(id="t1", order=1, title="Intro")
