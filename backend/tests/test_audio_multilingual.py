"""Tests for multilingual Piper voice discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import ValidationAppError
from app.features.audio.piper import SUPPORTED_LANGUAGES, discover_voice


def _make_voice_tree(root: Path) -> Path:
    voices = root / "piper"
    for lang, name in (
        ("en", "en_US-lessac-medium"),
        ("hi", "hi_IN-pratham-medium"),
        ("te", "te_IN-venkatesh-medium"),
    ):
        lang_dir = voices / lang
        lang_dir.mkdir(parents=True)
        onnx = lang_dir / f"{name}.onnx"
        onnx.write_bytes(b"onnx-placeholder")
        (lang_dir / f"{name}.onnx.json").write_text("{}", encoding="utf-8")
    return voices


def test_english_voice_loads(tmp_path: Path) -> None:
    voices = _make_voice_tree(tmp_path)
    voice = discover_voice(voices, "en")
    assert voice.language == "en"
    assert voice.name == "en_US-lessac-medium"
    assert voice.model_path.suffix == ".onnx"
    assert voice.config_path is not None
    assert voice.config_path.name.endswith(".onnx.json")


def test_hindi_voice_loads(tmp_path: Path) -> None:
    voices = _make_voice_tree(tmp_path)
    voice = discover_voice(voices, "hi")
    assert voice.language == "hi"
    assert voice.name == "hi_IN-pratham-medium"


def test_telugu_voice_loads(tmp_path: Path) -> None:
    voices = _make_voice_tree(tmp_path)
    voice = discover_voice(voices, "te")
    assert voice.language == "te"
    assert voice.name == "te_IN-venkatesh-medium"


def test_unsupported_language_raises(tmp_path: Path) -> None:
    voices = _make_voice_tree(tmp_path)
    with pytest.raises(ValidationAppError) as exc_info:
        discover_voice(voices, "fr")
    assert exc_info.value.code == "LANGUAGE_NOT_SUPPORTED"
    assert exc_info.value.details["supported_languages"] == list(SUPPORTED_LANGUAGES)


def test_missing_onnx_raises_voice_model_not_found(tmp_path: Path) -> None:
    voices = tmp_path / "piper"
    (voices / "en").mkdir(parents=True)
    with pytest.raises(ValidationAppError) as exc_info:
        discover_voice(voices, "en")
    assert exc_info.value.code == "VOICE_MODEL_NOT_FOUND"


def test_normalize_chrome_download_suffixes(tmp_path: Path) -> None:
    from app.features.audio.piper import normalize_voice_filenames

    lang = tmp_path / "en"
    lang.mkdir()
    (lang / "en_US-lessac-medium (1).onnx").write_bytes(b"onnx")
    (lang / "en_US-lessac-medium.onnx (1).json").write_text("{}", encoding="utf-8")

    normalize_voice_filenames(lang)

    assert (lang / "en_US-lessac-medium.onnx").is_file()
    assert (lang / "en_US-lessac-medium.onnx.json").is_file()
    assert not (lang / "en_US-lessac-medium (1).onnx").exists()
    assert not (lang / "en_US-lessac-medium.onnx (1).json").exists()

    voice = discover_voice(tmp_path, "en")
    assert voice.name == "en_US-lessac-medium"
    assert voice.config_path is not None
