"""AudioService — load narration, synthesize with Piper, save audio.wav."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.features.audio.piper import synthesize_wav
from app.features.narration.store import NarrationArtifactStore
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository

logger = get_logger(__name__)


class AudioService:
    """MVP speech generation: narration → artifacts/audio.wav."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._narration_store = NarrationArtifactStore(self._fs)

    def generate(self, project_id: str) -> Path:
        """Load narration and write ``artifacts/audio.wav``. Returns the WAV path."""
        validate_project_id(project_id)
        if self._repo.get(project_id) is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )

        narration = self._narration_store.read(project_id)
        output_wav = self._fs.project_root(project_id) / "artifacts" / "audio.wav"

        path = synthesize_wav(
            narration.text,
            executable=self._settings.piper_executable,
            model=self._settings.piper_model,
            output_wav=output_wav,
        )

        logger.info(
            "Speech audio saved",
            extra={
                "event": "audio_generated",
                "project_id": project_id,
                "path": str(path),
                "bytes": path.stat().st_size,
            },
        )
        return path
