"""Developer CLI helpers — thin wrappers around existing backend services."""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.enums import SourceType
from app.core.errors import ExplainXError
from app.core.benchmark import BenchmarkTimer
from app.core.logging import get_logger, setup_logging
from app.core.paths import ensure_runtime_directories
from app.db import session as db_session
from app.db.bootstrap import init_database
from app.features.audio.service import AudioService
from app.features.audio.voices import preferred_voice_stem
from app.features.input.pdf_extract import (
    PDF_MAX_BYTES,
    SCRIPT_MAX_LEN,
    SCRIPT_MIN_LEN,
    TOPIC_MAX_LEN,
    TOPIC_MIN_LEN,
)
from app.features.input.schemas import ScriptSourceRequest, TopicSourceRequest
from app.features.input.service import InputService
from app.features.narration.languages import (
    SUPPORTED_NARRATION_LANGUAGES,
    language_label,
    normalize_narration_language,
)
from app.features.projects.filesystem import ProjectFilesystem
from app.features.projects.schemas import ProjectCreateRequest
from app.features.projects.service import ProjectService
from app.features.renderer.service import RenderService
from app.features.script.ollama.client import MODEL_NOT_INSTALLED, OllamaClient
from app.features.script.schemas import EducationalScript
from app.features.script.service import ContentIntelligenceService
from app.features.script.store import ScriptArtifactStore
from app.features.translation.service import TranslationService

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
    reuse_project: bool = False,
    language: str = "en",
) -> str:
    """Create a new project, or optionally reuse one with the same title."""
    output_lang = normalize_narration_language(language)
    projects = ProjectService(session, settings)
    if project_id:
        _log(f"[1/4] Loading project {project_id} …")
        detail = projects.get(project_id)
        _log(f"      Loaded: {detail.title}")
        return detail.project_id

    if reuse_project:
        existing = projects.find_by_title(title)
        if existing is not None:
            _log(f"[1/4] Reusing project with title {title!r} …")
            _log(f"      project_id={existing.project_id}")
            return existing.project_id

    _log("[1/4] Creating project …")
    payload = ProjectCreateRequest(
        title=title,
        source_type=source_type,
        source_topic=source_topic,
        theme_id="notebooklm",
        # Canonical script language is always English; --lang is output language.
        source_language_code="en",
        target_language_code=output_lang,
    )
    detail = projects.create(payload)
    _log("Created new project")
    _log(f"Title: {detail.title}")
    _log(f"Project ID: {detail.project_id}")
    _log(f"Requested output language: {output_lang}")
    return detail.project_id


def ingest_topic(
    session: Session,
    settings: Settings,
    project_id: str,
    topic: str,
    *,
    language: str = "en",
) -> None:
    # Script generation is always English; output language lives on the project.
    _ = normalize_narration_language(language)
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
    language: str = "en",
) -> None:
    _ = normalize_narration_language(language)
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
    *,
    language: str = "en",
) -> None:
    _ = normalize_narration_language(language)
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
    _log(model)
    _log("")
    _log("Installed models:")
    _log("")
    if installed:
        for name in installed:
            _log(f"- {name}")
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
    client.log_connection()
    try:
        client.ensure_ready()
    except ExplainXError as exc:
        if exc.code == MODEL_NOT_INSTALLED:
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


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Result of topic|script|pdf script generation."""

    project_id: str
    script: EducationalScript


def run_pipeline(
    *,
    mode: str,
    value: str,
    project_id: str | None = None,
    title: str | None = None,
    reuse_project: bool = False,
    language: str = "en",
    settings: Settings | None = None,
    benchmark: BenchmarkTimer | None = None,
) -> PipelineResult:
    """Execute topic|script|pdf → EducationalScript via existing services."""
    cfg = bootstrap(settings=settings)
    lang = normalize_narration_language(language)
    verify_ollama(cfg)
    owns_benchmark = benchmark is None
    bench = benchmark or BenchmarkTimer()
    if owns_benchmark:
        bench.start("total_pipeline")

    session = _session()
    try:
        if mode == "topic":
            topic = validate_topic(value)
            resolved_title = _truncate_title(title or topic, fallback="CLI Topic Project")
            bench.start("project_creation")
            pid = create_or_load_project(
                session,
                cfg,
                source_type=SourceType.TOPIC,
                title=resolved_title,
                source_topic=topic,
                project_id=project_id,
                reuse_project=reuse_project,
                language=lang,
            )
            bench.stop("project_creation")
            bench.start("ingestion")
            ingest_topic(session, cfg, pid, topic, language=lang)
            bench.stop("ingestion")
        elif mode == "script":
            script_path = validate_script_path(value)
            resolved_title = _truncate_title(
                title or script_path.stem,
                fallback="CLI Script Project",
            )
            bench.start("project_creation")
            pid = create_or_load_project(
                session,
                cfg,
                source_type=SourceType.SCRIPT,
                title=resolved_title,
                source_topic=resolved_title,
                project_id=project_id,
                reuse_project=reuse_project,
                language=lang,
            )
            bench.stop("project_creation")
            bench.start("ingestion")
            ingest_script_file(
                session,
                cfg,
                pid,
                script_path,
                title=resolved_title,
                language=lang,
            )
            bench.stop("ingestion")
        elif mode == "pdf":
            pdf_path = validate_pdf_path(value)
            resolved_title = _truncate_title(
                title or pdf_path.stem,
                fallback="CLI PDF Project",
            )
            bench.start("project_creation")
            pid = create_or_load_project(
                session,
                cfg,
                source_type=SourceType.PDF,
                title=resolved_title,
                source_topic=None,
                project_id=project_id,
                reuse_project=reuse_project,
                language=lang,
            )
            bench.stop("project_creation")
            bench.start("ingestion")
            ingest_pdf_file(session, cfg, pid, pdf_path, language=lang)
            bench.stop("ingestion")
        else:
            raise ValidationAppErrorLike(f"Unknown mode: {mode}")

        bench.start("script_generation")
        script = generate_script(session, cfg, pid)
        bench.stop("script_generation")
        print_summary(cfg, pid, script)

        if owns_benchmark:
            _finalize_benchmark(
                bench,
                settings=cfg,
                project_id=pid,
                language=lang,
                with_audio=False,
            )
        return PipelineResult(project_id=pid, script=script)
    finally:
        session.close()


def _finalize_benchmark(
    bench: BenchmarkTimer,
    *,
    settings: Settings,
    project_id: str,
    language: str,
    with_audio: bool,
) -> Path:
    """Attach metadata, stop total if needed, write JSON, print banner."""
    if bench.is_running("total_pipeline"):
        bench.stop("total_pipeline")

    voice = preferred_voice_stem(language) or ""
    bench.set_meta(
        language=language,
        llm_model=settings.ollama_model,
        tts_provider="Piper" if with_audio else "",
        voice=voice if with_audio else "",
    )
    if not with_audio:
        bench.record("translation", 0.0)
        bench.record("audio_generation", 0.0)

    fs = ProjectFilesystem(settings)
    path = fs.project_root(project_id) / "artifacts" / "benchmark.json"
    bench.save(path)
    print()
    bench.summary()
    print()
    return path


def _run_translation(
    project_id: str,
    lang: str,
    *,
    settings: Settings | None = None,
) -> float:
    """Call existing TranslationService; return elapsed seconds."""
    cfg = bootstrap(settings=settings)
    session = _session()
    try:
        started = time.perf_counter()
        TranslationService(session, cfg).ensure_translated(project_id, lang)
        return time.perf_counter() - started
    finally:
        session.close()


def _collect_artifact_paths(
    settings: Settings,
    project_id: str,
    *,
    language: str,
    audio_path: Path | None,
) -> list[Path]:
    """List generated artifacts that exist (CLI report only)."""
    fs = ProjectFilesystem(settings)
    artifacts = fs.project_root(project_id) / "artifacts"
    candidates = [
        artifacts / "educational_script.json",
        artifacts / "educational_script.md",
        artifacts / "narration.json",
        artifacts / "narration_en.txt",
        artifacts / "narration.txt",
        artifacts / "benchmark.json",
    ]
    if language != "en":
        candidates.append(artifacts / f"narration_{language}.txt")
    if audio_path is not None:
        candidates.append(audio_path)
    else:
        candidates.append(artifacts / f"audio_{language}.wav")

    seen: set[Path] = set()
    out: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        if path.is_file():
            seen.add(resolved)
            out.append(path)
    return out


def print_workflow_summary(
    *,
    settings: Settings,
    project_id: str,
    language: str,
    script_sec: float,
    translation_sec: float | None,
    audio_sec: float,
    total_sec: float,
    audio_path: Path,
) -> None:
    """Print one final convenience-workflow summary."""
    print()
    print("=== ExplainX Generate Summary ===")
    print(f"Project ID:              {project_id}")
    print(f"Requested language:      {language} ({language_label(language)})")
    print(f"Script generation time:  {script_sec:.2f} sec")
    if translation_sec is not None:
        print(f"Translation time:        {translation_sec:.2f} sec")
    else:
        print("Translation time:        n/a (English)")
    print(f"Audio generation time:   {audio_sec:.2f} sec")
    print(f"Total pipeline time:     {total_sec:.2f} sec")
    print()
    print("Generated artifacts:")
    for path in _collect_artifact_paths(
        settings, project_id, language=language, audio_path=audio_path
    ):
        print(f"  {path}")
    print()


def run_topic_with_audio(
    *,
    topic: str,
    project_id: str | None = None,
    title: str | None = None,
    reuse_project: bool = False,
    language: str = "en",
    settings: Settings | None = None,
) -> Path:
    """Orchestrate existing topic pipeline + AudioService (CLI convenience only)."""
    lang = normalize_narration_language(language)
    bench = BenchmarkTimer()
    bench.start("total_pipeline")

    result = run_pipeline(
        mode="topic",
        value=topic,
        project_id=project_id,
        title=title,
        reuse_project=reuse_project,
        language=lang,
        settings=settings,
        benchmark=bench,
    )
    pid = result.project_id
    script_sec = bench.elapsed("script_generation")

    translation_sec: float | None = None
    if lang != "en":
        _log("[audio] Translating narration for speech …")
        bench.start("translation")
        _run_translation(pid, lang, settings=settings)
        translation_sec = bench.stop("translation")
    else:
        bench.record("translation", 0.0)
        translation_sec = None

    _log("[audio] Generating speech …")
    bench.start("audio_generation")
    audio_path = run_audio(pid, lang=lang, settings=settings)
    audio_sec = bench.stop("audio_generation")

    cfg = bootstrap(settings=settings)
    _finalize_benchmark(
        bench,
        settings=cfg,
        project_id=pid,
        language=lang,
        with_audio=True,
    )
    total_sec = bench.elapsed("total_pipeline")
    print_workflow_summary(
        settings=cfg,
        project_id=pid,
        language=lang,
        script_sec=script_sec,
        translation_sec=translation_sec,
        audio_sec=audio_sec,
        total_sec=total_sec,
        audio_path=audio_path,
    )
    return audio_path


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
        p.add_argument(
            "--reuse-project",
            action="store_true",
            help=(
                "If a project with the same title already exists, reuse it. "
                "Default is always to create a new project (duplicate titles allowed)."
            ),
        )
        p.add_argument(
            "--lang",
            default="en",
            choices=list(SUPPORTED_NARRATION_LANGUAGES),
            help=(
                "Requested output language (en, hi, te). Default: en. "
                "Script generation is always English; language is used for "
                "translation + Piper during audio."
            ),
        )

    topic = sub.add_parser("topic", help="Generate script from a topic string")
    topic.add_argument("topic", help="Teaching topic (3–500 characters)")
    add_common(topic)
    topic.add_argument(
        "--audio",
        action="store_true",
        help="After script generation, also run AudioService (translate if needed).",
    )

    script = sub.add_parser("script", help="Generate script from a text file")
    script.add_argument("path", help="Path to .txt / .md script file")
    add_common(script)

    pdf = sub.add_parser("pdf", help="Generate script from a PDF file")
    pdf.add_argument("path", help="Path to .pdf file (≤25 MB, ≤30 pages)")
    add_common(pdf)

    generate = sub.add_parser(
        "generate",
        help="Convenience: topic pipeline + audio (same as: topic … --audio)",
    )
    generate.add_argument("topic", help="Teaching topic (3–500 characters)")
    add_common(generate)
    generate.add_argument(
        "--audio",
        action="store_true",
        help="Optional; generate always runs AudioService (accepted for compatibility).",
    )

    audio = sub.add_parser(
        "audio",
        help="Generate speech audio_<lang>.wav (translate if needed, then Piper)",
    )
    audio.add_argument("project_id", help="Project UUID with a narration artifact")
    audio.add_argument(
        "--lang",
        default=None,
        choices=list(SUPPORTED_NARRATION_LANGUAGES),
        help="Optional output-language override. Default: project target_language_code.",
    )

    render = sub.add_parser(
        "render",
        help="Render video.mp4 from a static project image (MVP)",
    )
    render.add_argument("project_id", help="Project UUID with a PNG/JPG in assets/")

    return parser


def run_render(
    project_id: str,
    *,
    settings: Settings | None = None,
) -> Path:
    """Generate artifacts/frames/ + video.mp4 for an existing project image."""
    cfg = bootstrap(settings=settings)
    session = _session()
    try:
        result = RenderService(session, cfg).render(project_id.strip())
        print()
        print("=== ExplainX Render Summary ===")
        print(f"Project ID:     {result.project_id}")
        print(f"Input image:    {result.input_image.name}")
        print(f"Frames:         {result.metadata.frame_count}")
        print(f"Resolution:     {result.metadata.resolution}")
        print(f"Render time:    {result.metadata.render_time:.2f} sec")
        print(f"Video:          {result.video_path}")
        print(f"Metadata:       {result.metadata_path}")
        print()
        return result.video_path
    finally:
        session.close()


def run_audio(
    project_id: str,
    *,
    lang: str | None = None,
    settings: Settings | None = None,
) -> Path:
    """Generate artifacts/audio_<lang>.wav for an existing project."""
    cfg = bootstrap(settings=settings)
    session = _session()
    try:
        print("Generating speech...", flush=True)
        path = AudioService(session, cfg).generate(project_id.strip(), lang=lang)
        print("Saved", flush=True)
        print(path.name, flush=True)
        return path
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "topic":
            if getattr(args, "audio", False):
                run_topic_with_audio(
                    topic=args.topic,
                    project_id=args.project_id,
                    title=args.title,
                    reuse_project=args.reuse_project,
                    language=args.lang,
                )
            else:
                run_pipeline(
                    mode="topic",
                    value=args.topic,
                    project_id=args.project_id,
                    title=args.title,
                    reuse_project=args.reuse_project,
                    language=args.lang,
                )
        elif args.command == "generate":
            run_topic_with_audio(
                topic=args.topic,
                project_id=args.project_id,
                title=args.title,
                reuse_project=args.reuse_project,
                language=args.lang,
            )
        elif args.command == "script":
            run_pipeline(
                mode="script",
                value=args.path,
                project_id=args.project_id,
                title=args.title,
                reuse_project=args.reuse_project,
                language=args.lang,
            )
        elif args.command == "pdf":
            run_pipeline(
                mode="pdf",
                value=args.path,
                project_id=args.project_id,
                title=args.title,
                reuse_project=args.reuse_project,
                language=args.lang,
            )
        elif args.command == "audio":
            run_audio(args.project_id, lang=args.lang)
        elif args.command == "render":
            run_render(args.project_id)
        else:
            parser.error(f"Unknown command: {args.command}")
        return EXIT_OK
    except ValidationAppErrorLike as exc:
        _log(f"Validation error: {exc}")
        return EXIT_USAGE
    except ExplainXError as exc:
        if exc.code != MODEL_NOT_INSTALLED:
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