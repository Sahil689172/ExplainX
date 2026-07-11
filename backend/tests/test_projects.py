"""Project lifecycle tests — Phase 1.2."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _create_payload(**overrides: object) -> dict:
    payload = {
        "title": "Binary Search Explained",
        "description": "A short CS explainer",
        "source_type": "topic",
        "source_topic": "Binary search",
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


def test_create_project(client: TestClient, _test_env: Path) -> None:
    response = client.post("/api/v1/projects", json=_create_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["title"] == "Binary Search Explained"
    assert data["status"] == "draft"
    assert data["current_phase"] == "foundation"
    assert data["dsl_version"] == "1.0"
    root = _test_env / "projects" / data["project_id"]
    assert root.exists()
    assert (root / "project.json").exists()
    assert (root / "assets").is_dir()
    assert (root / "export").is_dir()
    assert (root / "scenes").is_dir()
    assert (root / "audio").is_dir()
    assert (root / "subtitles").is_dir()
    assert (root / "generated").is_dir()
    assert (root / "logs").is_dir()
    assert (root / "temp").is_dir()


def test_duplicate_title_rejected(client: TestClient) -> None:
    assert client.post("/api/v1/projects", json=_create_payload()).status_code == 201
    response = client.post("/api/v1/projects", json=_create_payload())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_PROJECT"


def test_unknown_theme_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects",
        json=_create_payload(theme_id="not-a-theme"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNKNOWN_THEME"


def test_get_list_rename_save(client: TestClient) -> None:
    created = client.post("/api/v1/projects", json=_create_payload()).json()["data"]
    project_id = created["project_id"]

    got = client.get(f"/api/v1/projects/{project_id}")
    assert got.status_code == 200
    assert got.json()["data"]["project_id"] == project_id

    listed = client.get("/api/v1/projects", params={"q": "Binary"})
    assert listed.status_code == 200
    assert len(listed.json()["data"]["items"]) >= 1

    renamed = client.post(
        f"/api/v1/projects/{project_id}/rename",
        json={"title": "Binary Search v2"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["title"] == "Binary Search v2"

    saved = client.post(f"/api/v1/projects/{project_id}/save")
    assert saved.status_code == 200


def test_delete_soft(client: TestClient) -> None:
    created = client.post("/api/v1/projects", json=_create_payload(title="To Delete")).json()["data"]
    project_id = created["project_id"]
    deleted = client.delete(f"/api/v1/projects/{project_id}")
    assert deleted.status_code == 200
    assert deleted.json()["data"]["mode"] == "soft"
    assert client.get(f"/api/v1/projects/{project_id}").status_code == 404


def test_duplicate_project(client: TestClient) -> None:
    created = client.post("/api/v1/projects", json=_create_payload(title="Original")).json()["data"]
    dup = client.post(f"/api/v1/projects/{created['project_id']}/duplicate", json={})
    assert dup.status_code == 201
    assert dup.json()["data"]["title"] == "Original (Copy)"
    assert dup.json()["data"]["project_id"] != created["project_id"]


def test_archive_project(client: TestClient) -> None:
    created = client.post("/api/v1/projects", json=_create_payload(title="Archive Me")).json()[
        "data"
    ]
    archived = client.post(f"/api/v1/projects/{created['project_id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "archived"


def test_export_project(client: TestClient, _test_env: Path) -> None:
    created = client.post("/api/v1/projects", json=_create_payload(title="Export Me")).json()[
        "data"
    ]
    exported = client.post(f"/api/v1/projects/{created['project_id']}/export")
    assert exported.status_code == 200
    export_path = _test_env / exported.json()["data"]["export_path"]
    assert export_path.exists()


def test_topic_required_for_topic_source(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects",
        json=_create_payload(source_topic=None, title="Missing Topic"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SOURCE_REQUIRED"


def test_load_recovers_missing_folder(client: TestClient, _test_env: Path) -> None:
    created = client.post("/api/v1/projects", json=_create_payload(title="Repair Me")).json()[
        "data"
    ]
    project_id = created["project_id"]
    assets = _test_env / "projects" / project_id / "assets"
    assets.rmdir()
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    assert assets.is_dir()
