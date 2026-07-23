"""Integration tests for the Visual Intelligence pipeline + REST surface.

Covers: topic input, PDF input, multiple-scene generation, legacy
compatibility, and invalid-input handling. No LLM calls, no image generation.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.services.visual_intelligence import VisualIntelligenceService

API = "/api/v1/visual-intelligence"


def _topic_script() -> dict[str, Any]:
    return {
        "script_id": "topic-script",
        "source_type": "topic",
        "learning_objectives": ["Understand HTTP", "Compare growth"],
        "teaching_sections": [
            {
                "id": "scene-1",
                "title": "How an HTTP request flows",
                "narration": "The browser sends a request to a server which "
                "processes each step in sequence and returns a response.",
                "concept_tags": ["http", "request", "flow", "process", "server"],
                "estimated_duration_sec": 8.0,
            },
            {
                "id": "scene-2",
                "title": "Comparing algorithm growth",
                "narration": "We compare linear versus quadratic growth on a "
                "chart to show how the curves diverge.",
                "concept_tags": ["chart", "graph", "compare", "data"],
                "estimated_duration_sec": 7.0,
            },
        ],
    }


def _pdf_script() -> dict[str, Any]:
    return {
        "script_id": "pdf-script",
        "source_type": "pdf",
        "teaching_sections": [
            {
                "id": "pdf-scene-1",
                "title": "The water cycle",
                "narration": "Water evaporates, condenses into clouds, and falls "
                "as rain — a cycle that repeats through distinct stages.",
                "concept_tags": ["cycle", "stages", "diagram", "process"],
                "estimated_duration_sec": 9.0,
            }
        ],
    }


# --------------------------------------------------------------------------- #
# Service-level integration
# --------------------------------------------------------------------------- #


def test_plan_topic_script_multiple_scenes() -> None:
    service = VisualIntelligenceService()
    plans = service.plan_script(_topic_script())

    assert len(plans) == 2
    for plan in plans:
        assert plan.scene_id
        assert plan.cache_key  # prospective cache key is populated
        assert plan.intent.estimated_duration > 0
        assert plan.strategy.primary_renderer is not None
        assert plan.layered_scene.ordered()  # at least one layer


def test_plan_pdf_script() -> None:
    service = VisualIntelligenceService()
    plans = service.plan_script(_pdf_script())

    assert len(plans) == 1
    plan = plans[0]
    assert plan.scene_id == "pdf-scene-1"
    assert plan.intent.visual_type is not None


def test_analyze_single_scene() -> None:
    service = VisualIntelligenceService()
    intent = service.analyze(
        {
            "scene_id": "s1",
            "title": "A flowchart of the login process",
            "narration": "The login flow moves step by step through validation.",
            "keywords": ["flow", "process", "step"],
        }
    )
    assert intent.scene_id == "s1"
    assert 0.0 <= intent.confidence <= 1.0


def test_legacy_compatibility_shapes() -> None:
    service = VisualIntelligenceService()
    plan = service.plan_script(_topic_script())[0]

    legacy = plan.layered_scene.to_legacy_dict()
    assert "illustration_path" in legacy
    assert "layers" in legacy

    timeline_scene = plan.to_timeline_scene()
    for key in ("scene_id", "title", "duration", "camera", "timeline"):
        assert key in timeline_scene
    assert "elements" in timeline_scene["timeline"]
    # gentle cinematic zoom stays within the rendering camera clamp
    assert 1.0 <= timeline_scene["camera"]["zoom"] <= 1.10


# --------------------------------------------------------------------------- #
# HTTP integration
# --------------------------------------------------------------------------- #


def test_health_endpoint(client: TestClient) -> None:
    response = client.get(f"{API}/health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "ok"
    assert data["llm_enabled"] is False
    assert data["image_generation"] is False
    assert data["renderer_count"] >= 1


def test_analyze_endpoint_topic(client: TestClient) -> None:
    response = client.post(
        f"{API}/analyze",
        json={
            "scenes": [
                {
                    "scene_id": "s1",
                    "title": "How an HTTP request flows",
                    "narration": "A request travels from client to server and back.",
                    "keywords": ["flow", "process"],
                }
            ]
        },
    )
    assert response.status_code == 200
    intents = response.json()["data"]["intents"]
    assert len(intents) == 1
    assert intents[0]["scene_id"] == "s1"


def test_plan_endpoint_with_script(client: TestClient) -> None:
    response = client.post(
        f"{API}/plan",
        json={"script": _topic_script(), "include_timeline": True},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source"] == "script"
    assert data["scene_count"] == 2
    assert len(data["scene_plans"]) == 2
    assert len(data["timeline_scenes"]) == 2
    assert data["scene_plans"][0]["cache_key"]


def test_plan_endpoint_with_scenes_no_timeline(client: TestClient) -> None:
    response = client.post(
        f"{API}/plan",
        json={
            "scenes": [{"scene_id": "only", "title": "A simple definition"}],
            "include_timeline": False,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source"] == "scenes"
    assert "timeline_scenes" not in data


def test_plan_endpoint_invalid_empty(client: TestClient) -> None:
    response = client.post(f"{API}/plan", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_analyze_endpoint_invalid_empty(client: TestClient) -> None:
    response = client.post(f"{API}/analyze", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_analyze_endpoint_rejects_unknown_field(client: TestClient) -> None:
    response = client.post(f"{API}/analyze", json={"bogus": 1})
    assert response.status_code == 422
