"""Health endpoint smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_envelope(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert "request_id" in body["meta"]
    assert "X-Request-Id" in response.headers


def test_health_v1_alias(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_doctor_foundation_ready(client: TestClient) -> None:
    response = client.get("/system/doctor")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "checks" in body["data"]
    assert body["data"]["ready"] is True
