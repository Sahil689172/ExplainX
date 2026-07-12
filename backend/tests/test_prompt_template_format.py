"""Ensure Ollama prompt templates with JSON examples do not break str.format()."""

from __future__ import annotations

import uuid

from app.core.enums import SourceType
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContentSection
from app.features.outline.ollama import templates as outline_templates
from app.features.quality.ollama import templates as quality_templates
from app.features.quality.schemas import RepairAction
from app.features.script.ollama.prompt_builder import PromptBuilder
from app.features.script.schemas import EducationalScript, ScriptConcept, TeachingSection
from app.features.section_generation.ollama import templates as section_templates


def test_script_prompt_builder_all_templates_format_without_keyerror() -> None:
    builder = PromptBuilder()
    sections = [
        RawContentSection(
            id="section-1",
            text="Binary search finds items in sorted arrays.",
            order=1,
            title="Binary Search",
        )
    ]
    concepts = [ScriptConcept(id="c1", label="Binary Search")]

    for source_type in (SourceType.TOPIC, SourceType.SCRIPT, SourceType.PDF):
        system, user = builder.build(
            source_type=source_type,
            title="Binary Search",
            language="en",
            sections=sections,
            concepts=concepts,
            target_duration_sec=150,
        )
        assert system
        assert '"title": string' in user
        assert "{{" not in user

    repair_system, repair_user = builder.build_repair(previous_response='{"bad": true}')
    assert repair_system
    assert '"narration": string' in repair_user
    assert "{{" not in repair_user

    script = EducationalScript(
        script_id=str(uuid.uuid4()),
        project_id="11111111-1111-1111-1111-111111111111",
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        source_type=SourceType.TOPIC,
        title="Binary Search",
        language="en",
        target_duration_sec=150,
        estimated_duration_sec=40.0,
        estimated_word_count=90,
        estimated_scene_count=10,
        summary="Short summary.",
        key_concepts=concepts,
        learning_objectives=["Explain binary search"],
        teaching_sections=[
            TeachingSection(
                id="t1",
                title="Intro",
                narration="Short narration about binary search for learners.",
                estimated_duration_sec=5.0,
                estimated_words=7,
                concept_tags=["Binary Search"],
            )
        ],
        created_at=utc_now_iso(),
    )
    expand_system, expand_user = builder.build_expand(
        script=script,
        current_duration_sec=40.0,
        current_words=90,
        target_duration_sec=180,
    )
    assert expand_system
    assert '"teaching_sections"' in expand_user or "teaching_sections" in expand_user
    assert "{{" not in expand_user


def test_section_prompt_templates_format_without_keyerror() -> None:
    schema = section_templates.JSON_SCHEMA_INSTRUCTIONS.format(target_words=42)
    assert '"narration": string' in schema
    assert "42" in schema
    assert "{{" not in schema

    user = section_templates.USER.format(
        lesson_title="Linear Search",
        language="en",
        index=1,
        section_title="Hook",
        learning_objective="Spark curiosity",
        key_concepts="Linear Search",
        target_words=42,
        previous_section_summary="(none)",
        next_section_title="Core idea",
        json_schema_instructions=schema,
    )
    assert "Hook" in user
    assert '"narration": string' in user
    assert "{{" not in user

    repair = section_templates.REPAIR_USER.format(
        target_words=42,
        previous_response='{"narration": "x"}',
        json_schema_instructions=schema,
    )
    assert "42" in repair
    assert "{{" not in repair


def test_outline_prompt_templates_format_without_keyerror() -> None:
    schema = outline_templates.JSON_SCHEMA_INSTRUCTIONS.format()
    assert '"learning_objective": string' in schema
    assert "{{" not in schema

    user = outline_templates.USER.format(
        title="Linear Search",
        language="en",
        target_duration_sec=150,
        total_target_words=350,
        section_count=10,
        sections_text="Linear search checks each element.",
        json_schema_instructions=schema,
    )
    assert "Linear Search" in user
    assert '"key_concepts"' in user
    assert "{{" not in user

    repair = outline_templates.REPAIR_USER.format(
        previous_response="{}",
        json_schema_instructions=schema,
    )
    assert "{{" not in repair


def test_quality_repair_prompt_template_format_without_keyerror() -> None:
    user = quality_templates.USER.format(
        action=RepairAction.EXPAND.value,
        title="Intro",
        learning_objective="Explain the idea",
        target_words=40,
        actual_words=2,
        validation_failures="- too short",
        previous_section_summary="(none)",
        next_section_title="Next",
        original_narration="Too short.",
    )
    assert '"narration": string' in user
    assert "{{" not in user
    assert "expand_section" in user
    assert "Actual spoken words: 2" in user
