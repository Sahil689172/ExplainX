"""AudioService — translate (if needed) then synthesize with Piper."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.features.audio.piper import (
    discover_voice,
    log_audio_selection,
    resolve_piper_executable,
    resolve_voices_dir,
    synthesize_wav,
)
from app.features.audio.text_cleaner import clean_speech_text
from app.features.audio.voices import preferred_voice_stem
from app.features.narration.languages import (
    language_label,
    normalize_output_language,
)
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.translation.service import TranslationService

logger = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[4]


class AudioService:
    """Speech generation: English script → optional translation → Piper WAV."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._translation = TranslationService(session, settings)

    def resolve_language(self, project_id: str, lang: str | None = None) -> str:
        """Resolve output language: CLI override → project target → default."""
        if lang and lang.strip():
            return normalize_output_language(lang)

        project = self._repo.get(project_id)
        if project is not None:
            target = (getattr(project, "target_language_code", None) or "").strip()
            if target:
                return normalize_output_language(target)

        return normalize_output_language(self._settings.default_language or "en")

    def generate(self, project_id: str, *, lang: str | None = None) -> Path:
        """Ensure narration for the requested language, then write ``audio_<lang>.wav``."""
        validate_project_id(project_id)
        if self._repo.get(project_id) is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )

        language = self.resolve_language(project_id, lang)
        speaking_text = self._translation.ensure_translated(project_id, language)
        speaking_text = clean_speech_text(speaking_text)
        if not speaking_text.strip():
            raise NotFoundError(
                "Narration text for speech synthesis is empty.",
                code="NARRATION_NOT_FOUND",
                details={"project_id": project_id, "language": language},
            )

        voices_dir = resolve_voices_dir(
            self._settings.piper_voices_dir,
            repo_root=_REPO_ROOT,
        )
        preferred = preferred_voice_stem(language)
        voice = discover_voice(
            voices_dir,
            language,
            preferred_stem=preferred,
        )
        log_audio_selection(
            language=language_label(language),
            voice=voice.name,
        )

        executable = resolve_piper_executable(
            self._settings.piper_executable,
            repo_root=_REPO_ROOT,
        )
        output_wav = (
            self._fs.project_root(project_id) / "artifacts" / f"audio_{language}.wav"
        )
        path = synthesize_wav(
            speaking_text,
            executable=executable,
            model=str(voice.model_path),
            output_wav=output_wav,
            config=str(voice.config_path) if voice.config_path else None,
        )

        logger.info(
            "Speech audio saved",
            extra={
                "event": "audio_generated",
                "project_id": project_id,
                "path": str(path),
                "bytes": path.stat().st_size,
                "language": voice.language,
                "voice": voice.name,
            },
        )
        return path
