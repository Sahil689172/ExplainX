"""Tests for narration pipeline stage timing."""

from __future__ import annotations

import sys

from app.features.narration.timing import (
    NarrationPipelineTimer,
    narration_timing_scope,
    time_stage,
)


def test_narration_timing_report_format(capsys: sys.stdout) -> None:
    with narration_timing_scope() as timer:
        timer.prompt_build_sec = 0.01
        timer.http_request_sec = 0.0
        timer.first_token_sec = 1.2
        timer.generation_sec = 51.3
        timer.parsing_sec = 0.02
        timer.validation_sec = 0.03
        timer.artifact_write_sec = 0.01
        timer.set_prompt_size(system="sys", prompt="user prompt")
        timer.set_response_size("narration text")

    captured = capsys.readouterr().out
    assert "[Timing]" in captured
    assert "Prompt Build .......... 0.01 sec" in captured
    assert "First Token ........... 1.20 sec" in captured
    assert "Generation ............ 51.30 sec" in captured
    assert "Prompt size ..........." in captured
    assert "Response size ........." in captured


def test_time_stage_accumulates_validation() -> None:
    timer = NarrationPipelineTimer()
    from app.features.narration import timing as timing_mod

    token = timing_mod._narration_timer.set(timer)
    try:
        with time_stage("validation_sec", accumulate=True):
            pass
        with time_stage("validation_sec", accumulate=True):
            pass
        assert timer.validation_sec >= 0.0
    finally:
        timing_mod._narration_timer.reset(token)
