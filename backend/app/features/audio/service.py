"""AudioService — load narration, translate if needed, synthesize with Piper."""

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
from app.features.narration.store import NarrationArtifactStore
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.script.store import ScriptArtifactStore
from app.features.translation.service import TranslationService

logger = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[4]


class AudioService:
    """MVP speech generation: narration → (optional translate) → artifacts/audio.wav."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._narration_store = NarrationArtifactStore(self._fs)
        self._script_store = ScriptArtifactStore(self._fs)
        self._translation = TranslationService(session, settings)

    def resolve_language(self, project_id: str, lang: str | None = None) -> str:
        """Resolve language: CLI --lang → EducationalScript.language → DEFAULT_LANGUAGE."""
        if lang and lang.strip():
            return lang.strip().lower()[:2]

        if self._script_store.has_script(project_id):
            script_lang = (self._script_store.read(project_id).language or "").strip()
            if script_lang:
                if "-" in script_lang:
                    script_lang = script_lang.split("-", 1)[0]
                return script_lang.lower()[:2]

        return (self._settings.default_language or "en").strip().lower()[:2]

    def generate(self, project_id: str, *, lang: str | None = None) -> Path:
        """Load narration, translate if needed, write ``artifacts/audio.wav``."""
        validate_project_id(project_id)
        if self._repo.get(project_id) is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )

        # Ensure narration exists (also used as English fallback by TranslationService).
        self._narration_store.read(project_id)

        language = self.resolve_language(project_id, lang)
        speaking_text = self._translation.ensure_translated(project_id, language)

        voices_dir = resolve_voices_dir(
            self._settings.piper_voices_dir,
            repo_root=_REPO_ROOT,
        )
        voice = discover_voice(voices_dir, language)
        log_audio_selection(language=voice.language, voice=voice.name)

        executable = resolve_piper_executable(
            self._settings.piper_executable,
            repo_root=_REPO_ROOT,
        )
        output_wav = self._fs.project_root(project_id) / "artifacts" / "audio.wav"
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
