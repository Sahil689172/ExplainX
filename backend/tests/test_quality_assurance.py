"""Tests for Phase 3.9 Quality Assurance Engine."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.enums import SourceType
from app.core.errors import ValidationAppError
from app.core.timeutil import utc_now_iso
from app.db import session as db_session
from app.features.input.schemas import ExtractionStats, RawContent, RawContentSection
from app.features.outline.budget import compute_total_word_budget
from app.features.outline.generator import PlaceholderOutlineGenerator
from app.features.quality.generator import PlaceholderRepairGenerator
from app.features.quality.inspector import QualityInspector
from app.features.quality.repair import ScriptRepairService
from app.features.quality.schemas import RepairAction, SectionRepairRequest
from app.features.quality.service import QualityAssuranceService
from app.features.script.durations import (
    SCRIPT_MIN_DURATION_SEC,
    V1_TARGET_DURATION_SEC,
)
from app.features.script.metrics import count_words, enrich_script_with_metrics
from app.features.script.schemas import EducationalScript, ScriptConcept, TeachingSection
from app.features.section_generation.generator import PlaceholderSectionGenerator
from app.features.section_generation.merger import SectionMerger


def _raw() -> RawContent:
    text = "Linear search checks each element until a match is found."
    return RawContent(
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        project_id="11111111-1111-1111-1111-111111111111",
        source_type=SourceType.TOPIC,
        text=text,
        sections=[RawContentSection(id="section-1", text=text, order=1, title="Linear Search")],
        warnings=[],
        extraction_stats=ExtractionStats(
            char_count=len(text), word_count=len(text.split()), section_count=1
        ),
        source_path="projects/11111111-1111-1111-1111-111111111111/source/topic.txt",
        source_hash="sha256:abc",
        metadata={"language_hint": "en"},
        created_at=utc_now_iso(),
    )


def _good_script() -> EducationalScript:
    outline = PlaceholderOutlineGenerator().generate(
        _raw(),
        target_duration_sec=V1_TARGET_DURATION_SEC,
        total_target_words=compute_total_word_budget(V1_TARGET_DURATION_SEC),
    )
    generator = PlaceholderSectionGenerator()
    outputs = []
    prev = ""
    for index, section in enumerate(outline.sections, start=1):
        nxt = outline.sections[index].title if index < len(outline.sections) else None
        output = generator.generate_section(
            outline=outline,
            section=section,
            index=index,
            previous_section_summary=prev,
            next_section_title=nxt,
        )
        outputs.append(output)
        prev = output.summary
    return SectionMerger().merge(outline, outputs)


def _short_script() -> EducationalScript:
    sections = [
        TeachingSection(
            id=f"s{i}",
            title=f"Section {i}",
            narration="Too short.",
            estimated_duration_sec=0.0,
            estimated_words=0,
            concept_tags=["Linear Search"],
        )
        for i in range(1, 9)
    ]
    script = EducationalScript(
        script_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        project_id="11111111-1111-1111-1111-111111111111",
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        source_type=SourceType.TOPIC,
        status="draft",
        title="Linear Search",
        language="en",
        target_duration_sec=150,
        estimated_duration_sec=0.0,
        estimated_word_count=0,
        estimated_scene_count=0,
        summary="A short overview.",
        key_concepts=[ScriptConcept(id="c1", label="Linear Search")],
        learning_objectives=["Explain linear search"],
        teaching_sections=sections,
        created_at=utc_now_iso(),
    )
    return enrich_script_with_metrics(script)


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


def test_placeholder_repair_expands_section() -> None:
    request = SectionRepairRequest(
        section_id="s1",
        action=RepairAction.EXPAND,
        validation_failures=["too short"],
        target_words=40,
        actual_words=2,
        learning_objective="Explain the idea",
        previous_section_summary="",
        next_section_title="Next",
        original_narration="Too short.",
        original_title="Intro",
    )
    repaired = PlaceholderRepairGenerator().repair_section(request)
    assert count_words(repaired) == 40


def test_inspector_flags_short_script() -> None:
    findings, errors, *_ = QualityInspector().inspect(_short_script())
    assert errors
    assert any(f.code == "TOO_SHORT" for f in findings)
    assert any(f.repair_action == RepairAction.EXPAND for f in findings)


def test_inspector_does_not_repair_for_target_words() -> None:
    """Per-section length vs target_words is not a repair trigger."""
    script = _good_script()
    long = " ".join(f"word{i}" for i in range(200)) + "."
    sections = list(script.teaching_sections)
    sections[0] = sections[0].model_copy(update={"narration": long})
    script = enrich_script_with_metrics(
        script.model_copy(update={"teaching_sections": sections})
    )
    findings, *_ = QualityInspector().inspect(script)
    too_long = [f for f in findings if f.code == "TOO_LONG"]
    for finding in too_long:
        assert finding.repair_action is None


def test_qa_approves_good_script(_test_env: Path) -> None:
    from app.core.config import get_settings

    db_session.get_engine()
    assert db_session.SessionLocal is not None
    script = _good_script()
    with db_session.SessionLocal() as session:
        # Use a real project directory under test env.
        project_id = script.project_id
        root = _test_env / "projects" / project_id
        root.mkdir(parents=True, exist_ok=True)
        settings = get_settings()
        qa = QualityAssuranceService(session, settings)
        approved = qa.assure(project_id, script, raw=_raw())

    assert approved.status == "ready"
    assert approved.metadata.get("quality_assured") is True
    assert approved.estimated_duration_sec >= SCRIPT_MIN_DURATION_SEC
    assert approved.estimated_word_count > 0
    artifacts = _test_env / "projects" / project_id / "artifacts"
    assert (artifacts / "quality_report.json").is_file()
    assert (artifacts / "approved_script.json").is_file()
    assert (artifacts / "repair_log.json").is_file()


def test_qa_repairs_short_script(_test_env: Path) -> None:
    from app.core.config import get_settings

    db_session.get_engine()
    assert db_session.SessionLocal is not None
    script = _short_script()
    project_id = script.project_id
    (_test_env / "projects" / project_id).mkdir(parents=True, exist_ok=True)

    with db_session.SessionLocal() as session:
        settings = get_settings()
        qa = QualityAssuranceService(session, settings)
        approved = qa.assure(project_id, script, raw=_raw())

    assert approved.status == "ready"
    assert approved.estimated_duration_sec >= SCRIPT_MIN_DURATION_SEC
    assert approved.estimated_word_count > 0
    assert approved.metadata.get("repair_attempts", 0) >= 1
    report_path = _test_env / "projects" / project_id / "artifacts" / "quality_report.json"
    assert report_path.is_file()


def test_repair_service_only_changes_target_sections() -> None:
    from app.core.config import get_settings

    script = _short_script()
    findings, *_ = QualityInspector().inspect(script)
    service = ScriptRepairService(get_settings(), generator=PlaceholderRepairGenerator())
    requests = service.build_requests(script, findings, attempt=1)
    assert requests
    original = {s.id: s.narration for s in script.teaching_sections}
    repaired, entries = service.repair(script, requests[:1], attempt=1)
    assert entries
    changed_id = requests[0].section_id
    assert repaired.teaching_sections[0].id == script.teaching_sections[0].id
    for section in repaired.teaching_sections:
        if section.id == changed_id:
            assert section.narration != original[section.id]
        # untouched sections keep narration when not in request


def test_script_api_writes_qa_artifacts(client: TestClient, _test_env: Path) -> None:
    project_id = _create_project(client, "QA API Project")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Binary search for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text
    created = client.post(f"/api/v1/projects/{project_id}/script")
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["status"] == "ready"
    assert data["metadata"].get("quality_assured") is True

    artifacts = _test_env / "projects" / project_id / "artifacts"
    assert (artifacts / "educational_script.json").is_file()
    assert (artifacts / "approved_script.json").is_file()
    assert (artifacts / "quality_report.json").is_file()
    assert (artifacts / "repair_log.json").is_file()
