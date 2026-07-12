"""Developer CLI helpers — thin wrappers around existing backend services."""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import TextIO

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.enums import SourceType
from app.core.errors import ExplainXError
from app.core.logging import get_logger, setup_logging
from app.core.paths import ensure_runtime_directories
from app.db import session as db_session
from app.db.bootstrap import init_database
from app.features.input.pdf_extract import (
    PDF_MAX_BYTES,
    SCRIPT_MAX_LEN,
    SCRIPT_MIN_LEN,
    TOPIC_MAX_LEN,
    TOPIC_MIN_LEN,
)
from app.features.input.schemas import ScriptSourceRequest, TopicSourceRequest
from app.features.input.service import InputService
from app.features.projects.filesystem import ProjectFilesystem
from app.features.projects.schemas import ProjectCreateRequest
from app.features.projects.service import ProjectService
from app.features.script.ollama.client import OllamaClient
from app.features.script.schemas import EducationalScript
from app.features.script.service import ContentIntelligenceService
from app.features.script.store import ScriptArtifactStore

logger = get_logger(__name__)

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_APP_ERROR = 2
EXIT_UNEXPECTED = 3


def _log(msg: str, *, file: TextIO = sys.stderr) -> None:
    print(msg, file=file, flush=True)


def bootstrap(*, settings: Settings | None = None) -> Settings:
    """Initialize settings, logging, directories, and database (same sequence as app.main)."""
    try:
        cfg = settings or get_settings()
        setup_logging(cfg)
        ensure_runtime_directories(cfg)
        init_database()
        # init_database → get_engine() binds SessionLocal on the session module.
        db_session.get_engine()
        if db_session.SessionLocal is None:
            raise RuntimeError(
                "CLI initialization failed: SessionLocal is None after init_database()"
            )
        return cfg
    except Exception as exc:
        _log(f"CLI initialization failed: {exc}")
        traceback.print_exc()
        raise


def _session() -> Session:
    """Return a SQLAlchemy session from the shared SessionLocal factory."""
    db_session.get_engine()
    factory = db_session.SessionLocal
    if factory is None:
        raise RuntimeError(
            "CLI initialization failed: SessionLocal is unavailable "
            "(call bootstrap() before creating services)"
        )
    return factory()


def _truncate_title(value: str, *, fallback: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        cleaned = fallback
    return cleaned[:120]


def create_or_load_project(
    session: Session,
    settings: Settings,
    *,
    source_type: SourceType,
    title: str,
    source_topic: str | None,
    project_id: str | None,
) -> str:
    """Create a new project or verify an existing one exists."""
    projects = ProjectService(session, settings)
    if project_id:
        _log(f"[1/4] Loading project {project_id} …")
        detail = projects.get(project_id)
        _log(f"      Loaded: {detail.title}")
        return detail.project_id

    _log("[1/4] Creating project …")
    payload = ProjectCreateRequest(
        title=title,
        source_type=source_type,
        source_topic=source_topic,
        theme_id="notebooklm",
        source_language_code="en",
        target_language_code="en",
    )
    detail = projects.create(payload)
    _log(f"      Created project_id={detail.project_id}")
    return detail.project_id


def ingest_topic(
    session: Session,
    settings: Settings,
    project_id: str,
    topic: str,
) -> None:
    _log("[2/4] Ingesting topic source …")
    InputService(session, settings).ingest_topic(
        project_id,
        TopicSourceRequest(topic=topic, replace=True, language_hint="en"),
    )
    _log("      RawContent saved.")


def ingest_script_file(
    session: Session,
    settings: Settings,
    project_id: str,
    script_path: Path,
    *,
    title: str | None,
) -> None:
    _log(f"[2/4] Ingesting script from {script_path} …")
    text = script_path.read_text(encoding="utf-8")
    InputService(session, settings).ingest_script(
        project_id,
        ScriptSourceRequest(
            script=text,
            title=title,
            replace=True,
            language_hint="en",
        ),
    )
    _log("      RawContent saved.")


def ingest_pdf_file(
    session: Session,
    settings: Settings,
    project_id: str,
    pdf_path: Path,
) -> None:
    _log(f"[2/4] Ingesting PDF from {pdf_path} …")
    data = pdf_path.read_bytes()
    InputService(session, settings).ingest_pdf(
        project_id,
        filename=pdf_path.name,
        data=data,
        replace=True,
        language_hint="en",
    )
    _log("      RawContent saved.")


def _print_missing_model(model: str, installed: list[str]) -> None:
    _log("--------------------------------------------------")
    _log("")
    _log("Configured model:")
    _log("")
    _log(model)
    _log("")
    _log("Installed models:")
    _log("")
    if installed:
        for name in installed:
            _log(name)
    else:
        _log("(none)")
    _log("")
    _log("Suggested fix:")
    _log("")
    _log(f"ollama pull {model}")
    _log("")
    _log("or update OLLAMA_MODEL inside .env")
    _log("")
    _log("--------------------------------------------------")


def verify_ollama(settings: Settings) -> None:
    """Ensure Ollama is reachable and the configured model exists before generation."""
    if settings.is_testing or not settings.ollama_enabled:
        return

    client = OllamaClient.from_settings(settings)
    _log(
        f"[ollama] Checking {client.base_url} for model {client.model} …"
    )
    try:
        client.ensure_ready()
    except ExplainXError as exc:
        if exc.code == "OLLAMA_MODEL_MISSING":
            installed = list((exc.details or {}).get("installed_models") or [])
            _print_missing_model(client.model, installed)
        raise
    _log(f"[ollama] Ready ({client.model}).")


def generate_script(
    session: Session,
    settings: Settings,
    project_id: str,
) -> EducationalScript:
    _log("[3/4] Generating EducationalScript (V1 2–3 min) …")
    verify_ollama(settings)
    script = ContentIntelligenceService(session, settings).generate_script(project_id)
    _log("      EducationalScript generated.")
    return script


def print_summary(
    settings: Settings,
    project_id: str,
    script: EducationalScript,
) -> None:
    _log("[4/4] Summary")
    fs = ProjectFilesystem(settings)
    store = ScriptArtifactStore(fs)
    artifacts = store.artifacts_dir(project_id)
    print()
    print("=== ExplainX CLI Summary ===")
    print(f"project_id:              {project_id}")
    print(f"title:                   {script.title}")
    print(f"source_type:             {script.source_type.value}")
    print(f"status:                  {script.status}")
    print(f"language:                {script.language}")
    print(f"target_duration_sec:     {script.target_duration_sec}")
    print(f"estimated_duration_sec:  {script.estimated_duration_sec}")
    print(f"estimated_word_count:    {script.estimated_word_count}")
    print(f"estimated_scene_count:   {script.estimated_scene_count}")
    print(f"teaching_sections:       {len(script.teaching_sections)}")
    print(f"key_concepts:            {len(script.key_concepts)}")
    print(f"learning_objectives:     {len(script.learning_objectives)}")
    print(f"summary:                 {script.summary[:200]}")
    print()
    print("Artifacts:")
    print(f"  {artifacts / 'educational_script.json'}")
    print(f"  {artifacts / 'educational_script.md'}")
    print(f"  {artifacts / 'script_metrics.json'}")
    print(f"  {artifacts / 'v1' / 'raw_content.json'} (if present)")
    print(f"Project root: {fs.project_root(project_id)}")
    print()


def validate_topic(topic: str) -> str:
    cleaned = topic.strip()
    if len(cleaned) < TOPIC_MIN_LEN or len(cleaned) > TOPIC_MAX_LEN:
        raise ValidationAppErrorLike(
            f"Topic length must be between {TOPIC_MIN_LEN} and {TOPIC_MAX_LEN} characters "
            f"(got {len(cleaned)})."
        )
    return cleaned


def validate_script_path(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    if not path.is_file():
        raise ValidationAppErrorLike(f"Script file not found: {path}")
    if path.suffix.lower() not in {".txt", ".md", ".text"}:
        # Allow any text-like file; still read as UTF-8.
        _log(f"Warning: unusual script extension {path.suffix!r}; reading as UTF-8 text.")
    text = path.read_text(encoding="utf-8")
    length = len(text.strip())
    if length < SCRIPT_MIN_LEN or length > SCRIPT_MAX_LEN:
        raise ValidationAppErrorLike(
            f"Script length must be between {SCRIPT_MIN_LEN} and {SCRIPT_MAX_LEN} characters "
            f"(got {length})."
        )
    return path


def validate_pdf_path(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    if not path.is_file():
        raise ValidationAppErrorLike(f"PDF file not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValidationAppErrorLike(f"Expected a .pdf file, got: {path.name}")
    size = path.stat().st_size
    if size <= 0:
        raise ValidationAppErrorLike("PDF file is empty.")
    if size > PDF_MAX_BYTES:
        raise ValidationAppErrorLike(
            f"PDF exceeds {PDF_MAX_BYTES} bytes (got {size})."
        )
    return path


class ValidationAppErrorLike(ValueError):
    """CLI-side validation error (maps to exit code 1)."""


def run_pipeline(
    *,
    mode: str,
    value: str,
    project_id: str | None = None,
    title: str | None = None,
    settings: Settings | None = None,
) -> EducationalScript:
    """Execute topic|script|pdf → EducationalScript via existing services."""
    cfg = bootstrap(settings=settings)
    session = _session()
    try:
        if mode == "topic":
            topic = validate_topic(value)
            resolved_title = _truncate_title(title or topic, fallback="CLI Topic Project")
            pid = create_or_load_project(
                session,
                cfg,
                source_type=SourceType.TOPIC,
                title=resolved_title,
                source_topic=topic,
                project_id=project_id,
            )
            ingest_topic(session, cfg, pid, topic)
        elif mode == "script":
            script_path = validate_script_path(value)
            resolved_title = _truncate_title(
                title or script_path.stem,
                fallback="CLI Script Project",
            )
            pid = create_or_load_project(
                session,
                cfg,
                source_type=SourceType.SCRIPT,
                title=resolved_title,
                source_topic=resolved_title,
                project_id=project_id,
            )
            ingest_script_file(
                session,
                cfg,
                pid,
                script_path,
                title=resolved_title,
            )
        elif mode == "pdf":
            pdf_path = validate_pdf_path(value)
            resolved_title = _truncate_title(
                title or pdf_path.stem,
                fallback="CLI PDF Project",
            )
            pid = create_or_load_project(
                session,
                cfg,
                source_type=SourceType.PDF,
                title=resolved_title,
                source_topic=None,
                project_id=project_id,
            )
            ingest_pdf_file(session, cfg, pid, pdf_path)
        else:
            raise ValidationAppErrorLike(f"Unknown mode: {mode}")

        script = generate_script(session, cfg, pid)
        print_summary(cfg, pid, script)
        return script
    finally:
        session.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description=(
            "ExplainX Developer CLI — generate a V1 EducationalScript "
            "without the frontend (thin wrapper around backend services)."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--project-id",
            default=None,
            help="Reuse an existing project id instead of creating a new one.",
        )
        p.add_argument(
            "--title",
            default=None,
            help="Optional project title (defaults from topic/filename).",
        )

    topic = sub.add_parser("topic", help="Generate script from a topic string")
    topic.add_argument("topic", help="Teaching topic (3–500 characters)")
    add_common(topic)

    script = sub.add_parser("script", help="Generate script from a text file")
    script.add_argument("path", help="Path to .txt / .md script file")
    add_common(script)

    pdf = sub.add_parser("pdf", help="Generate script from a PDF file")
    pdf.add_argument("path", help="Path to .pdf file (≤25 MB, ≤30 pages)")
    add_common(pdf)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "topic":
            run_pipeline(
                mode="topic",
                value=args.topic,
                project_id=args.project_id,
                title=args.title,
            )
        elif args.command == "script":
            run_pipeline(
                mode="script",
                value=args.path,
                project_id=args.project_id,
                title=args.title,
            )
        elif args.command == "pdf":
            run_pipeline(
                mode="pdf",
                value=args.path,
                project_id=args.project_id,
                title=args.title,
            )
        else:
            parser.error(f"Unknown command: {args.command}")
        return EXIT_OK
    except ValidationAppErrorLike as exc:
        _log(f"Validation error: {exc}")
        return EXIT_USAGE
    except ExplainXError as exc:
        if exc.code != "OLLAMA_MODEL_MISSING":
            _log(f"Error [{exc.code}]: {exc.message}")
            if exc.details:
                _log(f"Details: {exc.details}")
        return EXIT_APP_ERROR
    except KeyboardInterrupt:
        _log("Interrupted.")
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001
        _log(f"Unexpected error: {exc}")
        traceback.print_exc()
        logger.exception("cli_unexpected_error")
        return EXIT_UNEXPECTED
