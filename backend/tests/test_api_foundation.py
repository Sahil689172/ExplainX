"""Unit tests for Phase 1.3 API foundation."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_unversioned_and_v1(client: TestClient) -> None:
    for path in ("/health", "/api/v1/health"):
        response = client.get(path)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "ok"
        assert body["meta"]["api_version"] == "v1"
        assert "X-Request-Id" in response.headers
        assert response.headers.get("X-ExplainX-Api-Version") == "1"


def test_system_info_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["app_name"] == "ExplainX"
    assert data["api_version"] == "v1"
    assert "features" in data
    assert data["features"]["projects"] is True
    assert data["features"]["agents"] is False


def test_system_modules_lists_stubs(client: TestClient) -> None:
    response = client.get("/api/v1/system/modules")
    assert response.status_code == 200
    items = {item["name"]: item for item in response.json()["data"]["items"]}
    assert items["projects"]["available"] is True
    assert items["documents"]["status"] == "stub"
    assert items["rendering"]["available"] is False


def test_settings_public_read(client: TestClient) -> None:
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["app_name"] == "ExplainX"
    assert "cors_origins" in data
    assert "data_root" in data


def test_settings_patch_is_stub(client: TestClient) -> None:
    response = client.patch("/api/v1/settings", json={"note": "noop"})
    assert response.status_code == 501
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "not_implemented"


def test_documents_stub_routes(client: TestClient) -> None:
    listed = client.get("/api/v1/documents")
    assert listed.status_code == 200
    assert listed.json()["data"]["module"] == "documents"

    upload = client.post("/api/v1/documents")
    assert upload.status_code == 501

    detail = client.get("/api/v1/documents/doc-1")
    assert detail.status_code == 501


def test_agents_stub_routes(client: TestClient) -> None:
    catalog = client.get("/api/v1/agents")
    assert catalog.status_code == 200
    assert "planned_agents" in catalog.json()["data"]

    run = client.post("/api/v1/agents/run")
    assert run.status_code == 501

    status = client.get("/api/v1/agents/parser_agent/status")
    assert status.status_code == 501


def test_rendering_stub_routes(client: TestClient) -> None:
    status = client.get("/api/v1/rendering/status")
    assert status.status_code == 200
    assert status.json()["data"]["module"] == "rendering"

    create = client.post("/api/v1/rendering/jobs")
    assert create.status_code == 501

    job = client.get("/api/v1/rendering/jobs/job-1")
    assert job.status_code == 501


def test_validation_error_envelope(client: TestClient) -> None:
    # Projects create requires a body; empty/invalid triggers 422 envelope
    response = client.post("/api/v1/projects", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "fields" in body["error"]["details"]
    assert "request_id" in body["meta"]


def test_not_found_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


def test_payload_too_large_middleware() -> None:
    """Reject oversized Content-Length before the route runs."""
    import asyncio

    from app.api.middleware.validation import RequestValidationMiddleware

    async def inner_app(scope, receive, send):  # type: ignore[no-untyped-def]
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = RequestValidationMiddleware(inner_app, max_body_bytes=1024)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"content-length", b"2048"),
            (b"content-type", b"application/json"),
        ],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "state": {},
    }

    messages: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    asyncio.run(middleware(scope, receive, send))
    start = next(m for m in messages if m["type"] == "http.response.start")
    assert start["status"] == 413
    body_msg = next(m for m in messages if m["type"] == "http.response.body")
    assert b"PAYLOAD_TOO_LARGE" in body_msg["body"]



def test_openapi_docs_available_in_debug(client: TestClient) -> None:
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    schema = openapi.json()
    assert schema["info"]["title"].startswith("ExplainX")
    assert "x-explainx-api-version" in schema["info"]
    paths = schema["paths"]
    assert "/api/v1/system/info" in paths
    assert "/api/v1/documents" in paths
    assert "/api/v1/agents" in paths
    assert "/api/v1/rendering/status" in paths
    assert "/api/v1/settings" in paths


def test_request_id_propagates_from_client(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-Id": "test-req-123"})
    assert response.headers["X-Request-Id"] == "test-req-123"
    assert response.json()["meta"]["request_id"] == "test-req-123"


def test_projects_router_still_mounted(client: TestClient) -> None:
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert response.json()["success"] is True
