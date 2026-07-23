"""Unit tests for the deterministic VisualIntentAnalyzer."""

from __future__ import annotations

from app.services.visual_intelligence.intent_analyzer import VisualIntentAnalyzer
from app.services.visual_intelligence.schemas import (
    Complexity,
    RendererType,
    SceneInput,
    VisualType,
)


def _scene(**kwargs) -> SceneInput:
    base = {"scene_id": "s1"}
    base.update(kwargs)
    return SceneInput(**base)


def test_flowchart_detected_from_process_keywords():
    analyzer = VisualIntentAnalyzer()
    intent = analyzer.analyze(
        _scene(
            title="How Photosynthesis Works",
            narration="First light is absorbed, then the process converts CO2 step by step.",
            keywords=["process", "steps"],
        )
    )
    assert intent.visual_type == VisualType.FLOWCHART
    assert intent.suggested_renderer == RendererType.MERMAID
    assert 0.0 <= intent.confidence <= 1.0
    assert intent.matched_keywords


def test_chart_detected_from_data_keywords():
    analyzer = VisualIntentAnalyzer()
    intent = analyzer.analyze(
        _scene(
            title="Global Temperatures",
            narration="The chart shows the percentage trend of data over decades.",
        )
    )
    assert intent.visual_type == VisualType.CHART
    assert intent.suggested_renderer == RendererType.MATPLOTLIB


def test_mathematical_uses_manim():
    analyzer = VisualIntentAnalyzer()
    intent = analyzer.analyze(
        _scene(
            title="The Pythagorean Theorem",
            narration="We prove the theorem using the equation and geometry of triangles.",
            educational_concepts=["theorem", "proof", "geometry"],
        )
    )
    assert intent.visual_type == VisualType.MATHEMATICAL
    assert intent.suggested_renderer == RendererType.MANIM
    # heavy type + 3 concepts → at least moderate
    assert intent.complexity in (Complexity.MODERATE, Complexity.COMPLEX)


def test_timeline_detected():
    analyzer = VisualIntentAnalyzer()
    intent = analyzer.analyze(
        _scene(
            title="History of Flight",
            narration="A timeline of milestones over time from 1903 onward.",
        )
    )
    assert intent.visual_type == VisualType.TIMELINE


def test_fallback_without_keywords_is_illustration():
    analyzer = VisualIntentAnalyzer()
    intent = analyzer.analyze(
        _scene(title="Something", narration="A gentle poetic musing about wonder.")
    )
    assert intent.visual_type in (VisualType.ILLUSTRATION, VisualType.TEXT_ONLY)
    assert intent.confidence >= 0.35


def test_empty_scene_is_text_only():
    analyzer = VisualIntentAnalyzer()
    intent = analyzer.analyze(_scene())
    assert intent.visual_type == VisualType.TEXT_ONLY


def test_duration_hint_respected():
    analyzer = VisualIntentAnalyzer()
    intent = analyzer.analyze(
        _scene(narration="process step step", keywords=["process"], duration_hint_sec=7.5)
    )
    assert intent.estimated_duration == 7.5


def test_determinism_same_input_same_output():
    analyzer = VisualIntentAnalyzer()
    scene = _scene(title="Process", narration="step by step process workflow", keywords=["process"])
    a = analyzer.analyze(scene)
    b = analyzer.analyze(scene)
    assert a.model_dump() == b.model_dump()


def test_analyze_many():
    analyzer = VisualIntentAnalyzer()
    intents = analyzer.analyze_many([_scene(scene_id="a", narration="chart data"), _scene(scene_id="b")])
    assert [i.scene_id for i in intents] == ["a", "b"]
