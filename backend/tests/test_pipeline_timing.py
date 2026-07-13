"""Smoke tests for pipeline timing helpers."""

from __future__ import annotations

from app.shared.pipeline_timing import pipeline_timing_scope, timed_step


def test_pipeline_timing_emits_bracket_lines(capsys) -> None:
    with pipeline_timing_scope(project_id="p1") as timer:
        with timed_step("Narration"):
            with timed_step("Ollama"):
                pass
        with timed_step("SceneBuilder"):
            pass
        with timed_step("QualityAssurance"):
            with timed_step("Validator"):
                pass
            with timed_step("Repair 1"):
                pass

    labels = [label for label, _ in timer.steps]
    assert "Narration" in labels
    assert "Ollama" in labels
    assert "SceneBuilder" in labels
    assert "QualityAssurance" in labels
    assert "Validator" in labels
    assert "Repair 1" in labels

    out = capsys.readouterr().out
    assert "[Narration]" in out
    assert "[SceneBuilder]" in out
    assert "[QualityAssurance]" in out
    assert "TOTAL:" in out
