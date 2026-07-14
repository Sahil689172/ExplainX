"""Tests for translation cache behavior (no real IndicTrans2 load)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.enums import SourceType
from app.core.timeutil import utc_now_iso
from app.features.narration.schemas import NarrationDocument
from app.features.narration.store import NarrationArtifactStore
from app.features.projects.filesystem import ProjectFilesystem
from app.features.translation.service import TranslationService


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_root=str(tmp_path),
        env="testing",
        ollama_enabled=False,
    )


def _seed_narration(tmp_path: Path, project_id: str, text: str) -> None:
    settings = _settings(tmp_path)
    fs = ProjectFilesystem(settings)
    root = fs.project_root(project_id)
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    narration = NarrationDocument(
        narration_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        project_id=project_id,
        content_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        source_type=SourceType.TOPIC,
        status="ready",
        title="Photosynthesis",
        language="en",
        text=text,
        target_duration_sec=150,
        warnings=[],
        metadata={},
        created_at=utc_now_iso(),
    )
    NarrationArtifactStore(fs).write(project_id, narration)


def test_en_skips_model_and_caches_en_txt(tmp_path: Path) -> None:
    project_id = "11111111-1111-1111-1111-111111111111"
    _seed_narration(tmp_path, project_id, "Plants make food using sunlight.")

    session = MagicMock()
    service = TranslationService(session, _settings(tmp_path))
    service._repo.get = MagicMock(return_value=object())  # type: ignore[method-assign]

    with patch(
        "app.features.translation.service.translate_english_to"
    ) as mock_tr:
        text = service.ensure_translated(project_id, "en")
        mock_tr.assert_not_called()

    assert text.startswith("Plants make food")
    en_path = tmp_path / "projects" / project_id / "artifacts" / "translations" / "en.txt"
    assert en_path.is_file()


def test_hi_cache_miss_then_hit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_id = "11111111-1111-1111-1111-111111111111"
    _seed_narration(tmp_path, project_id, "Plants make food using sunlight.")

    session = MagicMock()
    service = TranslationService(session, _settings(tmp_path))
    service._repo.get = MagicMock(return_value=object())  # type: ignore[method-assign]

    with patch(
        "app.features.translation.service.translate_english_to",
        return_value="पौधे सूर्य के प्रकाश का उपयोग करके भोजन बनाते हैं।",
    ) as mock_tr:
        first = service.ensure_translated(project_id, "hi")
        assert mock_tr.call_count == 1
        second = service.ensure_translated(project_id, "hi")
        assert mock_tr.call_count == 1

    assert first == second
    hi_path = tmp_path / "projects" / project_id / "artifacts" / "translations" / "hi.txt"
    assert hi_path.is_file()
    out = capsys.readouterr().out
    assert "Cache : MISS" in out
    assert "Cache : HIT" in out
