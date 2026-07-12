"""Tests for the ExplainX developer CLI (thin service wrapper)."""

from __future__ import annotations

from pathlib import Path

import pytest

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
