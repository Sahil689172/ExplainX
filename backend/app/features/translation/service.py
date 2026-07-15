"""TranslationService — English narration → hi with on-disk + in-memory Argos cache."""

from __future__ import annotations

import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.features.narration.store import NarrationArtifactStore
from app.features.projects.filesystem import ProjectFilesystem, validate_project_id
from app.features.projects.repository import ProjectRepository
from app.features.quality.store import QualityArtifactStore
from app.features.translation.argos import (
    TranslationFailedError,
    get_argos_engine,
)

logger = get_logger(__name__)

SUPPORTED_LANGS = ("en", "hi")

_REPO_ROOT = Path(__file__).resolve().parents[4]


class TranslationService:
    """Offline Argos translation with artifacts/translations/{lang}.txt caching."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._narration_store = NarrationArtifactStore(self._fs)
        self._quality_store = QualityArtifactStore(self._fs)

        models_dir = self._resolve_argos_models_dir()
        # Load installed languages + translation objects once per process.
        self._argos = get_argos_engine(models_dir=models_dir)

    def _resolve_argos_models_dir(self) -> Path:
        configured = getattr(self._settings, "argos_models_dir", None) or "data/models/argos"
        path = Path(str(configured))
        if not path.is_absolute():
            path = _REPO_ROOT / path
        return path.resolve()

    def translations_dir(self, project_id: str) -> Path:
        return self._fs.project_root(project_id) / "artifacts" / "translations"

    def translation_path(self, project_id: str, lang: str) -> Path:
        return self.translations_dir(project_id) / f"{lang}.txt"

    def load_english_source(self, project_id: str) -> str:
        """Prefer approved script narration; fall back to continuous narration."""
        approved_path = self._quality_store.approved_script_path(project_id)
        if approved_path.is_file():
            script = self._quality_store.read_approved(project_id)
            text = (script.full_text or "").strip()
            if text:
                return text

        narration = self._narration_store.read(project_id)
        text = (narration.text or "").strip()
        if not text:
            raise NotFoundError(
                "No English narration text available to translate.",
                code="NARRATION_NOT_FOUND",
                details={"project_id": project_id},
            )
        return text

    def ensure_translated(self, project_id: str, lang: str) -> str:
        """Return text for ``lang``, translating from English when needed.

        Always maintains ``artifacts/translations/en.txt``. Reuses ``hi.txt``
        when present (artifact cache HIT).
        """
        validate_project_id(project_id)
        if self._repo.get(project_id) is None:
            raise NotFoundError(
                "No project exists with the given id.",
                code="PROJECT_NOT_FOUND",
                details={"project_id": project_id},
            )

        code = (lang or "en").strip().lower()[:2]
        if code not in SUPPORTED_LANGS:
            raise ValidationAppError(
                f"Unsupported language for translation: {lang!r}.",
                code="LANGUAGE_NOT_SUPPORTED",
                details={"language": lang, "supported_languages": list(SUPPORTED_LANGS)},
            )

        out_dir = self.translations_dir(project_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        en_path = self.translation_path(project_id, "en")
        if en_path.is_file() and en_path.stat().st_size > 0:
            english = en_path.read_text(encoding="utf-8").strip()
        else:
            english = self.load_english_source(project_id)
            en_path.write_text(english, encoding="utf-8")

        if code == "en":
            self._log_argos(source="en", target="en", elapsed_sec=0.0)
            return english

        target_path = self.translation_path(project_id, code)
        if target_path.is_file() and target_path.stat().st_size > 0:
            text = target_path.read_text(encoding="utf-8").strip()
            self._log_argos(source="en", target=code, elapsed_sec=0.0)
            return text

        started = time.perf_counter()
        translated = self._argos.translate(english, target_lang=code)
        elapsed = time.perf_counter() - started
        if not translated.strip():
            raise TranslationFailedError(
                "Translation produced empty output.",
                details={"language": code},
            )

        target_path.write_text(translated, encoding="utf-8")
        self._log_argos(source="en", target=code, elapsed_sec=elapsed)
        logger.info(
            "Translation saved",
            extra={
                "event": "translation_saved",
                "project_id": project_id,
                "language": code,
                "path": str(target_path),
                "elapsed_sec": round(elapsed, 3),
                "provider": "Argos",
            },
        )
        return translated

    @staticmethod
    def _log_argos(*, source: str, target: str, elapsed_sec: float) -> None:
        print("[Translation]", flush=True)
        print("Provider : Argos", flush=True)
        print(f"Source : {source}", flush=True)
        print(f"Target : {target}", flush=True)
        print(f"Time : {elapsed_sec:.2f} sec", flush=True)
