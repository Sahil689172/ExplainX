"""Tests for Phase 3.8 Section Generation Engine."""

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
from app.features.script.durations import V1_MIN_DURATION_SEC, V1_MIN_WORDS, V1_TARGET_DURATION_SEC
from app.features.script.metrics import count_words
from app.features.script.validator import ScriptValidator
from app.features.section_generation.generator import PlaceholderSectionGenerator
from app.features.section_generation.merger import SectionMerger
from app.features.section_generation.ollama.generator import OllamaSectionGenerator
from app.features.section_generation.service import SectionGenerationService
from app.features.section_generation.validator import SectionValidator


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


def test_placeholder_generates_one_section_at_a_time() -> None:
    outline = _outline()
    generator = PlaceholderSectionGenerator()
    section = outline.sections[0]
    output = generator.generate_section(
        outline=outline,
        section=section,
        index=1,
        previous_section_summary="",
        next_section_title=outline.sections[1].title,
    )
    assert output.outline_section_id == section.id
    assert output.index == 1
    assert count_words(output.narration) == section.target_words
    SectionValidator().validate(output, expected=section, index=1)


def test_section_merger_builds_educational_script() -> None:
    outline = _outline()
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
        SectionValidator().validate(output, expected=section, index=index)
        outputs.append(output)
        prev = output.summary

    script = SectionMerger().merge(outline, outputs)
    assert len(script.teaching_sections) == len(outline.sections)
    assert script.estimated_word_count >= V1_MIN_WORDS
    assert script.estimated_duration_sec >= V1_MIN_DURATION_SEC
    assert script.metadata.get("section_generation") is True
    ScriptValidator().validate(script, raw=_raw())


def test_ollama_section_generator_one_call_per_section() -> None:
    calls: list[tuple[str, str]] = []

    class MockClient:
        model = "mock-llama3:latest"

        def generate(self, *, system: str, prompt: str) -> str:
            calls.append((system, prompt))
            # Extract target from prompt roughly; return enough words.
            words = " ".join(f"spoken{i}" for i in range(40))
            return json.dumps(
                {
                    "narration": words + ".",
                    "summary": "This section covered the core idea briefly.",
                }
            )

    outline = _outline()
    # Shrink targets so mock 40 words sits inside validator band.
    thin_sections = [
        s.model_copy(update={"target_words": 40}) for s in outline.sections
    ]
    outline = outline.model_copy(
        update={
            "sections": thin_sections,
            "total_target_words": 40 * len(thin_sections),
        }
    )
    generator = OllamaSectionGenerator(MockClient())
    for index, section in enumerate(outline.sections[:3], start=1):
        output = generator.generate_section(
            outline=outline,
            section=section,
            index=index,
            previous_section_summary="Earlier we introduced the topic.",
            next_section_title="Next idea",
        )
        assert "spoken0" in output.narration
        SectionValidator().validate(output, expected=section, index=index)

    assert len(calls) == 3
    assert "one teaching section" in calls[0][0].lower() or "ONE teaching section" in calls[0][0]


def test_section_generation_service_persists_outputs(
    client: TestClient, _test_env: Path
) -> None:
    project_id = _create_project(client, "Section Gen Persist")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Binary search for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    # Outline via API script path happens in full flow; here call services directly.
    from app.core.config import get_settings
    from app.features.outline.service import TeachingOutlineService

    db_session.get_engine()
    assert db_session.SessionLocal is not None
    with db_session.SessionLocal() as session:
        settings = get_settings()
        outline = TeachingOutlineService(session, settings).generate_outline(project_id)
        script = SectionGenerationService(session, settings).generate_from_outline(
            project_id, outline=outline
        )

    root = _test_env / "projects" / project_id / "artifacts" / "section_outputs"
    files = sorted(root.glob("section_*.json"))
    assert len(files) == len(outline.sections)
    assert files[0].name == "section_01.json"
    assert script.estimated_word_count >= V1_MIN_WORDS


def test_script_api_uses_section_generation(
    client: TestClient, _test_env: Path
) -> None:
    project_id = _create_project(client, "Section Gen API Project")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Hash tables for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    created = client.post(f"/api/v1/projects/{project_id}/script")
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["metadata"].get("section_generation") is True

    artifacts = _test_env / "projects" / project_id / "artifacts"
    assert (artifacts / "teaching_outline.json").is_file()
    assert (artifacts / "educational_script.json").is_file()
    section_files = sorted((artifacts / "section_outputs").glob("section_*.json"))
    assert len(section_files) >= 8
    assert section_files[0].name == "section_01.json"
