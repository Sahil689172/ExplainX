"""Ensure every Ollama prompt template formats without KeyError from JSON braces."""

from __future__ import annotations

import json
import re
import uuid

import pytest

from app.core.enums import SourceType
from app.core.timeutil import utc_now_iso
from app.features.input.schemas import RawContentSection
from app.features.outline.ollama import templates as outline_templates
from app.features.quality.ollama import templates as quality_templates
from app.features.quality.schemas import RepairAction
from app.features.script.ollama import templates as script_templates
from app.features.script.ollama.prompt_builder import PromptBuilder
from app.features.script.schemas import EducationalScript, ScriptConcept, TeachingSection
from app.features.section_generation.ollama import templates as section_templates
from app.features.single_script.ollama import templates as single_script_templates
from app.shared.prompt_format import dumps_schema, format_prompt

# Literal `{name}` fields only — not `{{` escapes (we no longer use those in templates).
_FIELD_RE = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})")


def _fields(template: str) -> set[str]:
    return set(_FIELD_RE.findall(template))


def test_no_template_contains_raw_json_object_braces() -> None:
    """Template source must not embed JSON with single braces (use schema_json)."""
    modules = (
        script_templates,
        section_templates,
        single_script_templates,
        outline_templates,
        quality_templates,
    )
    for mod in modules:
        for name in dir(mod):
            if name.startswith("_") or name != name.upper():
                continue
            value = getattr(mod, name)
            if not isinstance(value, str):
                continue
            # Disallow patterns like `{ "key"` which indicate unescaped JSON.
            assert not re.search(r'\{\s*"', value), (
                f"{mod.__name__}.{name} embeds raw JSON braces; "
                "inject via dumps_schema / {{schema_json}}"
            )


def test_script_prompt_builder_never_raises_keyerror() -> None:
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
        assert '"title"' in user
        assert '"narration"' in user

    # previous_response with braces must not break formatting
    repair_system, repair_user = builder.build_repair(
        previous_response='{"bad": true, "nested": {"x": 1}}'
    )
    assert repair_system
    assert '"teaching_sections"' in repair_user or "teaching_sections" in repair_user

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
    assert '"narration"' in expand_user
    assert script.title in expand_user


def test_instantiate_every_script_template() -> None:
    schema = script_templates.render_json_schema_instructions()
    assert '"title"' in schema
    assert '"narration"' in schema
    assert dumps_schema(script_templates.EDUCATIONAL_SCRIPT_JSON_SCHEMA) in schema
    assert _fields(script_templates.JSON_SCHEMA_INSTRUCTIONS) == {"schema_json"}

    common = {
        "title": "T",
        "language": "en",
        "target_duration_sec": 150,
        "word_budget": 350,
        "sections_text": "body {with} braces",
        "concepts_text": "(none)",
        "json_schema_instructions": schema,
    }
    for name in ("TOPIC_USER", "SCRIPT_USER", "PDF_USER"):
        rendered = format_prompt(getattr(script_templates, name), **common)
        assert "T" in rendered
        assert '"narration"' in rendered

    for name in ("TOPIC_SYSTEM", "SCRIPT_SYSTEM", "PDF_SYSTEM", "EXPAND_SYSTEM"):
        text = getattr(script_templates, name)
        assert isinstance(text, str) and text.strip()
        assert _fields(text) == set()

    repair = format_prompt(
        script_templates.REPAIR_USER,
        previous_response='{"a": 1}',
        json_schema_instructions=schema,
    )
    assert '{"a": 1}' in repair

    expand = format_prompt(
        script_templates.EXPAND_USER,
        current_duration_sec=40,
        current_words=90,
        target_duration_sec=180,
        word_budget=420,
        script_json=json.dumps({"title": "X", "nested": {"y": 2}}, indent=2),
        json_schema_instructions=schema,
    )
    assert '"nested"' in expand
    assert '"title"' in expand


def test_instantiate_every_section_template() -> None:
    schema = section_templates.render_json_schema_instructions(target_words=42)
    assert '"narration"' in schema
    assert "42" in schema
    assert _fields(section_templates.JSON_SCHEMA_INSTRUCTIONS) == {
        "schema_json",
        "target_words",
    }

    assert section_templates.SYSTEM.strip()
    assert _fields(section_templates.SYSTEM) == set()

    user = format_prompt(
        section_templates.USER,
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
    assert '"narration"' in user

    repair = format_prompt(
        section_templates.REPAIR_USER,
        target_words=42,
        previous_response='{"narration": "x", "summary": "y"}',
        json_schema_instructions=schema,
    )
    assert "42" in repair
    assert '"narration"' in repair


def test_instantiate_every_single_script_template() -> None:
    schema = single_script_templates.render_json_schema_instructions(
        total_target_words=350,
        target_duration_sec=150,
    )
    assert '"title"' in schema
    assert '"narration"' in schema
    assert "350" in schema
    assert _fields(single_script_templates.JSON_SCHEMA_INSTRUCTIONS) == {
        "schema_json",
        "total_target_words",
        "target_duration_sec",
    }

    assert single_script_templates.SYSTEM.strip()
    assert _fields(single_script_templates.SYSTEM) == set()

    user = format_prompt(
        single_script_templates.USER,
        title="Linear Search",
        language="en",
        target_duration_sec=150,
        total_target_words=350,
        learning_objectives="- Explain linear search",
        key_concepts="Linear Search",
        outline_sections="Section 1:\n  id: section-1",
        json_schema_instructions=schema,
    )
    assert "Linear Search" in user
    assert '"narration"' in user

    repair = format_prompt(
        single_script_templates.REPAIR_USER,
        previous_response='{"title": "x", "sections": []}',
        json_schema_instructions=schema,
    )
    assert '"title"' in repair


def test_instantiate_every_outline_template() -> None:
    schema = outline_templates.render_json_schema_instructions()
    assert '"learning_objective"' in schema
    assert _fields(outline_templates.JSON_SCHEMA_INSTRUCTIONS) == {"schema_json"}

    assert outline_templates.SYSTEM.strip()
    assert _fields(outline_templates.SYSTEM) == set()

    user = format_prompt(
        outline_templates.USER,
        title="Linear Search",
        language="en",
        target_duration_sec=150,
        total_target_words=350,
        section_count=10,
        sections_text='Material with {"json": true} braces',
        json_schema_instructions=schema,
    )
    assert "Linear Search" in user
    assert '"key_concepts"' in user

    repair = format_prompt(
        outline_templates.REPAIR_USER,
        previous_response="{}",
        json_schema_instructions=schema,
    )
    assert '"learning_objective"' in repair


def test_instantiate_every_quality_template() -> None:
    assert quality_templates.SYSTEM.strip()
    assert _fields(quality_templates.SYSTEM) == set()
    assert _fields(quality_templates.USER) == {
        "action",
        "title",
        "learning_objective",
        "target_words",
        "actual_words",
        "validation_failures",
        "previous_section_summary",
        "next_section_title",
        "original_narration",
        "schema_json",
    }

    user = quality_templates.render_user(
        action=RepairAction.EXPAND.value,
        title="Intro",
        learning_objective="Explain the idea",
        target_words=40,
        actual_words=2,
        validation_failures="- too short",
        previous_section_summary="(none)",
        next_section_title="Next",
        original_narration="Too short. {not_a_field}",
    )
    assert '"narration"' in user
    assert "expand_section" in user
    assert "Actual spoken words: 2" in user
    assert "{not_a_field}" in user  # values are not re-scanned


def test_format_prompt_missing_field_raises_clear_keyerror() -> None:
    with pytest.raises(KeyError, match="missing field"):
        format_prompt("Hello {name}", wrong="x")


def test_dumps_schema_roundtrip() -> None:
    schema = {"narration": "<string>", "nested": {"a": 1}}
    text = dumps_schema(schema)
    assert json.loads(text) == schema
