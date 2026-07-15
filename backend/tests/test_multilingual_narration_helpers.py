"""Tests for speech text cleaner and preferred voice mapping."""

from __future__ import annotations

from app.features.audio.text_cleaner import clean_speech_text
from app.features.audio.voices import PREFERRED_VOICES, preferred_voice_stem


def test_clean_speech_removes_markdown_without_rewriting() -> None:
    raw = "# Title\nHello **world** with `code` and ***noise***…"
    cleaned = clean_speech_text(raw)
    assert "#" not in cleaned
    assert "*" not in cleaned
    assert "`" not in cleaned
    assert "Hello" in cleaned
    assert "world" in cleaned


def test_preferred_voices_cover_en_hi_te() -> None:
    assert preferred_voice_stem("en") == "en_US-lessac-medium"
    assert preferred_voice_stem("hi") == "hi_IN-pratham-medium"
    assert preferred_voice_stem("te") == PREFERRED_VOICES["te"]
