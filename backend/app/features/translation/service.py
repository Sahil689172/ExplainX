"""TranslationService — English narration → hi/te with on-disk cache."""

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
from app.features.translation.indictrans import (
    TranslationFailedError,
    translate_english_to,
)

logger = get_logger(__name__)

SUPPORTED_LANGS = ("en", "hi", "te")


class TranslationService:
    """MVP offline translation with artifacts/translations/{lang}.txt caching."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = ProjectRepository(session)
        self._fs = ProjectFilesystem(settings)
        self._narration_store = NarrationArtifactStore(self._fs)
        self._quality_store = QualityArtifactStore(self._fs)

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

        Always maintains ``artifacts/translations/en.txt``. Reuses ``hi.txt`` /
        ``te.txt`` when present (cache HIT).
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
            self._log_result(language="en", cache="HIT", elapsed_sec=None, saved=None)
            return english

        target_path = self.translation_path(project_id, code)
        if target_path.is_file() and target_path.stat().st_size > 0:
            text = target_path.read_text(encoding="utf-8").strip()
            self._log_result(language=code, cache="HIT", elapsed_sec=None, saved=None)
            return text

        started = time.perf_counter()
        translated = translate_english_to(
            english,
            target_lang=code,
        )
        elapsed = time.perf_counter() - started
        if not translated.strip():
            raise TranslationFailedError(
                "Translation produced empty output.",
                details={"language": code},
            )

        target_path.write_text(translated, encoding="utf-8")
        rel = f"translations/{code}.txt"
        self._log_result(
            language=code,
            cache="MISS",
            elapsed_sec=elapsed,
            saved=rel,
        )
        logger.info(
            "Translation saved",
            extra={
                "event": "translation_saved",
                "project_id": project_id,
                "language": code,
                "path": str(target_path),
                "elapsed_sec": round(elapsed, 3),
            },
        )
        return translated

    @staticmethod
    def _log_result(
        *,
        language: str,
        cache: str,
        elapsed_sec: float | None,
        saved: str | None,
    ) -> None:
        print("[Translation]", flush=True)
        print(f"Language : {language}", flush=True)
        print(f"Cache : {cache}", flush=True)
        if cache == "MISS" and elapsed_sec is not None:
            print(f"Translation Time : {elapsed_sec:.1f} sec", flush=True)
        if saved:
            print("Saved :", flush=True)
            print(saved, flush=True)
