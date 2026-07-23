"""Unit tests for the pipeline adapter (script → scene plans)."""

from __future__ import annotations

from app.services.visual_intelligence.pipeline_adapter import (
    plan_script,
    plan_script_as_dicts,
    script_to_scene_inputs,
)
from app.services.visual_intelligence.schemas import VisualType

_SCRIPT = {
    "title": "Photosynthesis",
    "learning_objectives": ["Explain the process", "Explain the chart of outputs"],
    "teaching_sections": [
        {
            "id": "section-1",
            "title": "The Process",
            "narration": "Step by step, the process converts light in stages.",
            "concept_tags": ["process", "stages"],
            "estimated_duration_sec": 8.0,
        },
        {
            "id": "section-2",
            "title": "The Data",
            "narration": "A chart shows the percentage of glucose produced over time.",
            "concept_tags": ["chart", "data"],
            "estimated_duration_sec": 6.0,
        },
    ],
}


def test_script_to_scene_inputs_maps_fields():
    scenes = script_to_scene_inputs(_SCRIPT)
    assert [s.scene_id for s in scenes] == ["section-1", "section-2"]
    assert scenes[0].learning_objective == "Explain the process"
    assert scenes[0].duration_hint_sec == 8.0
    assert "process" in scenes[0].keywords


def test_plan_script_returns_plans():
    plans = plan_script(_SCRIPT)
    assert len(plans) == 2
    assert plans[0].intent.visual_type == VisualType.FLOWCHART
    assert plans[1].intent.visual_type == VisualType.CHART
    # Duration hint flows through to the intent.
    assert plans[0].intent.estimated_duration == 8.0


def test_plan_script_as_dicts_is_json_ready():
    dicts = plan_script_as_dicts(_SCRIPT)
    assert len(dicts) == 2
    assert dicts[0]["intent"]["visual_type"] == "flowchart"
    assert "illustration_path" in dicts[0]["layered_scene"]


def test_adapter_handles_empty_script():
    assert script_to_scene_inputs({"teaching_sections": []}) == []
    assert plan_script({"teaching_sections": []}) == []
