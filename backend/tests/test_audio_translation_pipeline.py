"""Tests for AudioService language resolution (no Piper invocation)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.features.audio.service import AudioService


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_root=str(tmp_path),
        env="testing",
        ollama_enabled=False,
        piper_voices_dir=str(tmp_path / "piper"),
        piper_executable="piper",
    )


def test_resolve_language_uses_project_target() -> None:
    service = AudioService(MagicMock(), _settings(Path(".")))
    service._repo.get = MagicMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(target_language_code="hi")
    )
    assert service.resolve_language("11111111-1111-1111-1111-111111111111") == "hi"


def test_resolve_language_cli_override_wins() -> None:
    service = AudioService(MagicMock(), _settings(Path(".")))
    service._repo.get = MagicMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(target_language_code="hi")
    )
    assert (
        service.resolve_language(
            "11111111-1111-1111-1111-111111111111", lang="te"
        )
        == "te"
    )


def test_generate_uses_translation_then_piper(tmp_path: Path) -> None:
    project_id = "11111111-1111-1111-1111-111111111111"
    settings = _settings(tmp_path)
    out = tmp_path / "out.wav"
    out.write_bytes(b"RIFF")

    service = AudioService(MagicMock(), settings)
    service._repo.get = MagicMock(return_value=object())  # type: ignore[method-assign]
    service._translation.ensure_translated = MagicMock(  # type: ignore[method-assign]
        return_value="English narration text for speech."
    )

    fake_voice = SimpleNamespace(
        language="hi",
        name="hi_IN-pratham-medium",
        model_path=tmp_path / "hi.onnx",
        config_path=None,
    )
    with (
        patch("app.features.audio.service.resolve_voices_dir", return_value=tmp_path),
        patch("app.features.audio.service.discover_voice", return_value=fake_voice),
        patch("app.features.audio.service.log_audio_selection"),
        patch("app.features.audio.service.resolve_piper_executable", return_value="piper"),
        patch("app.features.audio.service.synthesize_wav", return_value=out) as synth,
        patch.object(
            service._fs,
            "project_root",
            return_value=tmp_path / "projects" / project_id,
        ),
    ):
        path = service.generate(project_id, lang="hi")

    service._translation.ensure_translated.assert_called_once_with(project_id, "hi")
    synth.assert_called_once()
    assert path == out
    assert synth.call_args.kwargs["output_wav"].name == "audio_hi.wav"
