"""Tests for the ExplainX developer CLI (thin service wrapper)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cli import dev_cli
from app.cli.dev_cli import (
    EXIT_APP_ERROR,
    EXIT_OK,
    EXIT_USAGE,
    main,
    validate_pdf_path,
    validate_script_path,
    validate_topic,
)
from app.cli.dev_cli import ValidationAppErrorLike
from app.db import session as db_session


def test_cli_startup_initializes_session_local(_test_env: Path) -> None:
    """CLI bootstrap must bind SessionLocal like app.main before services run."""
    db_session.reset_db_engine()
    assert db_session.SessionLocal is None

    cfg = dev_cli.bootstrap()
    assert cfg is not None
    assert db_session.SessionLocal is not None

    session = dev_cli._session()
    try:
        assert session.bind is not None
        assert session.bind is db_session.get_engine()
    finally:
        session.close()


def test_validate_topic_ok() -> None:
    assert validate_topic("  Binary search  ") == "Binary search"


def test_validate_topic_too_short() -> None:
    with pytest.raises(ValidationAppErrorLike):
        validate_topic("ab")


def test_validate_script_path(tmp_path: Path) -> None:
    path = tmp_path / "lesson.txt"
    path.write_text("Welcome students. Today we study sorting carefully.", encoding="utf-8")
    assert validate_script_path(str(path)) == path.resolve()


def test_validate_script_path_missing(tmp_path: Path) -> None:
    with pytest.raises(ValidationAppErrorLike):
        validate_script_path(str(tmp_path / "missing.txt"))


def test_validate_pdf_extension(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(ValidationAppErrorLike):
        validate_pdf_path(str(path))


def test_cli_topic_end_to_end(_test_env: Path) -> None:
    code = main(["topic", "Hash tables for beginners"])
    assert code == EXIT_OK

    projects = list((_test_env / "projects").iterdir())
    assert len(projects) == 1
    artifacts = projects[0] / "artifacts"
    assert (artifacts / "educational_script.json").is_file()
    assert (artifacts / "educational_script.md").is_file()
    assert (artifacts / "script_metrics.json").is_file()
    assert (artifacts / "v1" / "raw_content.json").is_file()


def test_cli_script_file_end_to_end(_test_env: Path, tmp_path: Path) -> None:
    script_file = tmp_path / "custom.txt"
    script_file.write_text(
        "Hello class. We will study recursion with clear examples today.",
        encoding="utf-8",
    )
    code = main(["script", str(script_file), "--title", "Recursion Lesson"])
    assert code == EXIT_OK
    projects = list((_test_env / "projects").iterdir())
    assert len(projects) == 1
    assert (projects[0] / "artifacts" / "educational_script.json").is_file()


def test_cli_usage_error_for_short_topic(_test_env: Path) -> None:
    code = main(["topic", "x"])
    assert code == EXIT_USAGE


def test_cli_missing_script_file(_test_env: Path, tmp_path: Path) -> None:
    code = main(["script", str(tmp_path / "nope.txt")])
    assert code == EXIT_USAGE


def test_cli_duplicate_topic_creates_separate_projects(_test_env: Path) -> None:
    assert main(["topic", "Hashing for beginners"]) == EXIT_OK
    assert main(["topic", "Hashing for beginners"]) == EXIT_OK
    projects = list((_test_env / "projects").iterdir())
    assert len(projects) == 2
    ids = {p.name for p in projects}
    assert len(ids) == 2
    for root in projects:
        assert (root / "artifacts" / "educational_script.json").is_file()
        assert (root / "artifacts" / "v1" / "raw_content.json").is_file()


def test_cli_reuse_project_by_title(_test_env: Path) -> None:
    assert main(["topic", "Hashing for beginners"]) == EXIT_OK
    first_id = next(p.name for p in (_test_env / "projects").iterdir())
    assert (
        main(["topic", "Hashing for beginners", "--reuse-project"]) == EXIT_OK
    )
    projects = list((_test_env / "projects").iterdir())
    assert len(projects) == 1
    assert projects[0].name == first_id


def test_cli_load_existing_project(_test_env: Path) -> None:
    assert main(["topic", "First topic about graphs"]) == EXIT_OK
    project_id = next(p.name for p in (_test_env / "projects").iterdir())
    code = main(
        [
            "topic",
            "Second topic about trees and traversal",
            "--project-id",
            project_id,
        ]
    )
    assert code == EXIT_OK
    # Still a single project directory (reused).
    assert len(list((_test_env / "projects").iterdir())) == 1


def test_cli_unknown_project(_test_env: Path) -> None:
    code = main(
        [
            "topic",
            "Valid topic text here",
            "--project-id",
            "11111111-1111-1111-1111-111111111111",
        ]
    )
    assert code == EXIT_APP_ERROR


def test_cli_topic_audio_flag_invokes_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_run_topic_with_audio(**kwargs: object) -> Path:
        called.update(kwargs)
        return Path("artifacts/audio_hi.wav")

    monkeypatch.setattr(dev_cli, "run_topic_with_audio", fake_run_topic_with_audio)
    code = main(["topic", "Photosynthesis for beginners here", "--lang", "hi", "--audio"])
    assert code == EXIT_OK
    assert called["topic"] == "Photosynthesis for beginners here"
    assert called["language"] == "hi"


def test_cli_generate_command_invokes_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_run_topic_with_audio(**kwargs: object) -> Path:
        called.update(kwargs)
        return Path("artifacts/audio_en.wav")

    monkeypatch.setattr(dev_cli, "run_topic_with_audio", fake_run_topic_with_audio)
    code = main(["generate", "Photosynthesis for beginners here", "--lang", "en"])
    assert code == EXIT_OK
    assert called["language"] == "en"


def test_cli_topic_without_audio_does_not_orchestrate(
    monkeypatch: pytest.MonkeyPatch, _test_env: Path
) -> None:
    orchestrated = {"hit": False}

    def boom(**_kwargs: object) -> Path:
        orchestrated["hit"] = True
        return Path("x")

    monkeypatch.setattr(dev_cli, "run_topic_with_audio", boom)
    code = main(["topic", "Hash tables for beginners"])
    assert code == EXIT_OK
    assert orchestrated["hit"] is False
