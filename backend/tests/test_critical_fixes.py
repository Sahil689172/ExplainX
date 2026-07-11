"""Tests for Critical Phase 1.2 architecture fixes."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.core.config import get_settings
from app.core.errors import ValidationAppError
from app.db.session import get_engine
from app.models.api.projects import ProjectCreateRequest
from app.services.project_filesystem import ProjectFilesystem, validate_project_id
from app.services.project_service import ProjectService


def _create_payload(**overrides: object) -> dict:
    payload = {
        "title": "Critical Fix Project",
        "description": "test",
        "source_type": "topic",
        "source_topic": "Testing critical fixes",
        "theme_id": "notebooklm",
        "source_language_code": "en",
        "target_language_code": "en",
        "difficulty": "intermediate",
        "settings": {
            "export_width": 1280,
            "export_height": 720,
            "fps": 30,
            "quality_profile": "standard",
            "burn_in_subtitles": False,
            "subtitle_formats": ["srt", "vtt"],
            "speaking_rate": 1.0,
        },
    }
    payload.update(overrides)
    return payload


def test_schema_comes_from_alembic_not_create_all(client: TestClient) -> None:
    engine = get_engine()
    inspector = inspect(engine)
    assert inspector.has_table("projects")
    assert inspector.has_table("project_settings")
    assert inspector.has_table("themes")
    assert inspector.has_table("languages")
    assert inspector.has_table("alembic_version")
    with engine.connect() as conn:
        version = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
    assert version == "20260711_001"


def test_settings_patch_is_partial(client: TestClient) -> None:
    created = client.post(
        "/api/v1/projects",
        json=_create_payload(
            title="Partial Settings",
            settings={
                "export_width": 1280,
                "export_height": 720,
                "fps": 30,
                "quality_profile": "standard",
                "burn_in_subtitles": True,
                "subtitle_formats": ["srt", "vtt"],
                "speaking_rate": 1.25,
            },
        ),
    ).json()["data"]
    project_id = created["project_id"]

    patched = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"settings": {"quality_profile": "draft"}},
    )
    assert patched.status_code == 200
    settings = patched.json()["data"]["settings"]
    assert settings["quality_profile"] == "draft"
    assert settings["export_width"] == 1280
    assert settings["export_height"] == 720
    assert settings["burn_in_subtitles"] is True
    assert settings["speaking_rate"] == 1.25
    assert settings["subtitle_formats"] == ["srt", "vtt"]


def test_path_traversal_project_id_rejected(client: TestClient) -> None:
    # Non-UUID ids must be rejected by the service (HTTP envelope 422).
    response = client.get("/api/v1/projects/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    # Direct guards (URL normalization may turn encoded ../ into a different route).
    with pytest.raises(ValidationAppError):
        validate_project_id("..")
    with pytest.raises(ValidationAppError):
        validate_project_id("../../etc/passwd")
    with pytest.raises(ValidationAppError):
        validate_project_id("not-a-uuid")
    with pytest.raises(ValidationAppError):
        validate_project_id("../secrets")


def test_filesystem_jail_rejects_escape(_test_env: Path) -> None:
    fs = ProjectFilesystem(get_settings())
    with pytest.raises(ValidationAppError):
        fs.project_root("../outside")


def test_zip_slip_import_rejected(client: TestClient, _test_env: Path, tmp_path: Path) -> None:
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("../escaped.txt", "pwned")
        zf.writestr("project.json", '{"title": "Evil"}')

    with evil.open("rb") as handle:
        response = client.post(
            "/api/v1/projects/import",
            files={"file": ("evil.zip", handle, "application/zip")},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PROJECT_CORRUPTED"
    projects_root = _test_env / "projects"
    if projects_root.exists():
        for child in projects_root.iterdir():
            assert not (child / "escaped.txt").exists()


def test_oversized_zip_rejected(
    _test_env: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fs = ProjectFilesystem(get_settings())
    huge = tmp_path / "huge.zip"
    with zipfile.ZipFile(huge, "w") as zf:
        zf.writestr("project.json", '{"title": "Big"}')

    # Force any real zip to exceed the compressed-size gate.
    monkeypatch.setattr(
        "app.services.project_filesystem.MAX_IMPORT_ZIP_BYTES",
        10,
    )
    dest = fs.project_root("11111111-1111-1111-1111-111111111111")
    dest.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValidationAppError) as exc:
        fs.extract_zip_safe(huge, dest)
    assert exc.value.code == "PROJECT_CORRUPTED"


def test_create_failure_cleans_filesystem(
    _test_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: ProjectFilesystem, project_id: str, payload: dict) -> Path:  # type: ignore[type-arg]
        raise RuntimeError("mirror write failed")

    monkeypatch.setattr(ProjectFilesystem, "write_project_json", boom)

    # Use the module attribute — a direct import can bind None before get_engine().
    from app.db import session as db_session

    db_session.get_engine()
    assert db_session.SessionLocal is not None
    with db_session.SessionLocal() as session:
        service = ProjectService(session, get_settings())
        with pytest.raises(RuntimeError, match="mirror write failed"):
            service.create(ProjectCreateRequest(**_create_payload(title="Boom Create")))

    projects = list((_test_env / "projects").glob("*")) if (_test_env / "projects").exists() else []
    assert projects == []


def test_roundtrip_import_export_still_works(client: TestClient, _test_env: Path) -> None:
    created = client.post(
        "/api/v1/projects",
        json=_create_payload(title="Export Import Safe"),
    ).json()["data"]
    project_id = created["project_id"]
    exported = client.post(f"/api/v1/projects/{project_id}/export")
    assert exported.status_code == 200
    zip_rel = exported.json()["data"]["export_path"]
    zip_path = _test_env / zip_rel
    assert zip_path.exists()

    with zip_path.open("rb") as handle:
        imported = client.post(
            "/api/v1/projects/import",
            files={"file": ("pkg.zip", handle, "application/zip")},
            data={"title": "Imported Safe"},
        )
    assert imported.status_code == 200, imported.text
    assert imported.json()["data"]["title"] == "Imported Safe"
