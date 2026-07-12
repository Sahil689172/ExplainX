"""Tests for Phase 3 Content Intelligence API (aligned with Phase 3.6 schema)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.features.script.durations import V1_TARGET_DURATION_SEC


def _create_project(client: TestClient, title: str) -> str:
    response = client.post(
        "/api/v1/projects",
        json={
            "title": title,
            "source_type": "topic",
            "source_topic": "placeholder topic for create",
            "theme_id": "notebooklm",
            "source_language_code": "en",
            "target_language_code": "en",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["project_id"]


def test_api_generate_with_ignored_duration_preset(client: TestClient, _test_env) -> None:
    project_id = _create_project(client, "Phase3 Duration")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Hash tables for beginners", "replace": True},
    )
    assert ingest.status_code == 200, ingest.text

    created = client.post(
        f"/api/v1/projects/{project_id}/script",
        json={"target_duration": "3min"},
    )
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["target_duration_sec"] == V1_TARGET_DURATION_SEC
    assert data["metadata"]["processor"] == "topic_content_v1"
    assert data["status"] == "placeholder"
    assert len(data["teaching_sections"]) >= 1

    artifact = _test_env / "projects" / project_id / "artifacts" / "educational_script.json"
    assert artifact.is_file()


def test_api_rejects_nothing_for_legacy_duration_field(client: TestClient) -> None:
    """API still accepts legacy duration fields; V1 ignores them (no 422)."""
    project_id = _create_project(client, "Legacy Duration")
    client.put(
        f"/api/v1/projects/{project_id}/source/topic",
        json={"topic": "Valid topic text here", "replace": True},
    )
    response = client.post(
        f"/api/v1/projects/{project_id}/script",
        json={"target_duration": "2min"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["target_duration_sec"] == V1_TARGET_DURATION_SEC


def test_api_script_from_custom_script(client: TestClient) -> None:
    project_id = _create_project(client, "Custom Script Phase3")
    ingest = client.put(
        f"/api/v1/projects/{project_id}/source/script",
        json={
            "script": "Hello class. We will study sorting algorithms today.",
            "title": "Sorting",
            "replace": True,
        },
    )
    assert ingest.status_code == 200, ingest.text
    created = client.post(
        f"/api/v1/projects/{project_id}/script",
        json={"target_duration_sec": 90},
    )
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["source_type"] == "script"
    assert data["target_duration_sec"] == V1_TARGET_DURATION_SEC
    assert "Hello class" in " ".join(s["narration"] for s in data["teaching_sections"])
