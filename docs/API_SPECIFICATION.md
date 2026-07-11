# ExplainX — API Specification

**Document Status:** Canonical HTTP API Contract  
**API Version Defined Herein:** `v1`  
**Document Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Style:** REST-ish JSON over HTTP (local-first)  
**Companions:**  
[`PROJECT_CONSTITUTION.md`](./PROJECT_CONSTITUTION.md) ·  
[`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md) ·  
[`AGENT_SPECIFICATIONS.md`](./AGENT_SPECIFICATIONS.md) ·  
[`DATABASE_DESIGN.md`](./DATABASE_DESIGN.md) ·  
[`PRESENTATION_DSL.md`](./PRESENTATION_DSL.md)  

> **Authority:** This document defines every HTTP endpoint ExplainX will expose.  
> Frontend and future clients MUST program against this contract.  
> Do not invent undocumented routes in implementation without amending this specification.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Base URL & Environments](#2-base-url--environments)
3. [API Versioning](#3-api-versioning)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [Common Conventions](#5-common-conventions)
6. [Standard Response Format](#6-standard-response-format)
7. [Error Handling](#7-error-handling)
8. [Asynchronous Jobs & Rendering](#8-asynchronous-jobs--rendering)
9. [Endpoint Catalog](#9-endpoint-catalog)
10. [Health & System](#10-health--system)
11. [Projects](#11-projects)
12. [Documents / Upload](#12-documents--upload)
13. [Generation Pipeline Controls](#13-generation-pipeline-controls)
14. [Narration, Subtitles & Media Artifacts](#14-narration-subtitles--media-artifacts)
15. [Render Lifecycle](#15-render-lifecycle)
16. [Export & Download](#16-export--download)
17. [Themes, Voices & Languages](#17-themes-voices--languages)
18. [Settings & Plugins](#18-settings--plugins)
19. [Webhooks / Events (Optional Future)](#19-webhooks--events-optional-future)
20. [Rate Limits & Concurrency](#20-rate-limits--concurrency)
21. [OpenAPI Alignment](#21-openapi-alignment)
22. [Appendix: Enumerations](#22-appendix-enumerations)
23. [Appendix: Complete Route Index](#23-appendix-complete-route-index)

---

## 1. Overview

ExplainX exposes a **local application API** (FastAPI) consumed primarily by the Next.js frontend.

The API is a **control plane**:

- create/manage projects  
- upload sources  
- start/pause/resume/cancel generation & render jobs  
- poll progress  
- download exports  

Heavy AI/rendering work runs **asynchronously** in workers. Clients do not block on multi-minute renders inside a single HTTP request (except optional short sync utilities).

### 1.1 Design Principles

| Principle | Meaning |
|-----------|---------|
| Resource-oriented | Projects, jobs, exports are first-class resources |
| Async by default | Generation/render return `202 Accepted` + job id |
| Typed JSON | Request/response schemas validated |
| Idempotent starts | Optional idempotency keys for job creation |
| Local-first auth | V1: trusted localhost; later token/session |
| Stable errors | Machine-readable `error.code` |

---

## 2. Base URL & Environments

| Environment | Base URL (typical) |
|-------------|--------------------|
| Local V1 | `http://127.0.0.1:8000/api/v1` |
| Future networked | `https://{host}/api/v1` |

All routes below are relative to `/api/v1` unless noted.

Content types:

- JSON requests: `Content-Type: application/json`  
- Uploads: `multipart/form-data`  
- Downloads: appropriate binary content types  

---

## 3. API Versioning

### 3.1 URI Versioning (Normative)

ExplainX uses **URI path versioning**:

```
/api/v1/...
/api/v2/...   # future breaking redesign
```

### 3.2 What Constitutes a Breaking Change

| Change | Bump |
|--------|------|
| Remove/rename field or endpoint | MAJOR (`v2`) |
| Change field meaning/type | MAJOR |
| Add optional field / new endpoint | MINOR (stay on `v1`, document bump `1.x`) |
| Add new error code | MINOR |
| Tighten validation that rejects previously accepted bad input | MINOR (document migration) |

### 3.3 Headers

| Header | Purpose |
|--------|---------|
| `Accept: application/json` | Preferred |
| `X-ExplainX-Api-Version: 1` | Optional explicit version echo |
| `X-Idempotency-Key: <string>` | Optional for job-creating POSTs |

Responses MAY echo:

```http
X-ExplainX-Api-Version: 1
```

### 3.4 Deprecation Policy

Deprecated endpoints remain for at least one MAJOR cycle, returning header:

```http
Deprecation: true
Sunset: <ISO-8601 date>
Link: </api/v2/...>; rel="successor-version"
```

---

## 4. Authentication & Authorization

### 4.1 Version 1 (Local Desktop)

| Requirement | V1 Behavior |
|-------------|-------------|
| Authentication | **None required** for loopback clients |
| Authorization | Filesystem jail under storage root; no cross-user model |
| Binding | API SHOULD listen on `127.0.0.1` by default |

### 4.2 Future (Networked / Collaborative V5)

| Mechanism | Use |
|-----------|-----|
| Bearer access token | `Authorization: Bearer <token>` |
| Session cookie | Optional web session |
| Project ACLs | Owner/editor/viewer |

### 4.3 Per-Endpoint Auth Field

Each endpoint documents:

- **V1:** `None (localhost trust)`  
- **Future:** `Bearer` / `Project ACL` when applicable  

Unless stated otherwise, assume V1 localhost trust.

### 4.4 CSRF / CORS

- Local Next.js origin allowlisted  
- Credentials mode documented when sessions appear  
- Mutating requests from non-allowlisted origins rejected in networked mode  

---

## 5. Common Conventions

### 5.1 IDs

- UUIDs as strings for `project_id`, `job_id`, `video_id`, etc.  
- Logical IDs (`scene_id`, `beat_id`) are snake_case strings  

### 5.2 Timestamps

ISO-8601 UTC strings, e.g. `2026-07-11T10:15:30Z`.

### 5.3 Pagination

List endpoints support:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | integer | 20 | Max 100 |
| `cursor` | string | null | Opaque cursor |
| `sort` | string | `updated_at:desc` | |

Response includes `page.next_cursor`.

### 5.4 Partial Success

Pipeline jobs may complete with warnings. Warnings appear in job/project payloads; HTTP status still `200`/`202` as appropriate.

---

## 6. Standard Response Format

### 6.1 Success Envelope

All JSON success responses use:

```json
{
  "success": true,
  "data": { },
  "meta": {
    "request_id": "req_...",
    "api_version": "v1",
    "timestamp": "2026-07-11T10:15:30Z"
  }
}
```

List responses:

```json
{
  "success": true,
  "data": {
    "items": [ ],
    "page": {
      "limit": 20,
      "next_cursor": null,
      "total_estimate": 12
    }
  },
  "meta": { "request_id": "req_...", "api_version": "v1", "timestamp": "..." }
}
```

### 6.2 Accepted (Async) Envelope

```json
{
  "success": true,
  "data": {
    "job_id": "uuid",
    "project_id": "uuid",
    "status": "queued",
    "poll_url": "/api/v1/jobs/{job_id}",
    "progress_url": "/api/v1/jobs/{job_id}/progress"
  },
  "meta": { "request_id": "req_...", "api_version": "v1", "timestamp": "..." }
}
```

### 6.3 Binary Responses

File downloads omit the JSON envelope and stream bytes with:

```http
Content-Type: video/mp4
Content-Disposition: attachment; filename="video.mp4"
X-Request-Id: req_...
```

---

## 7. Error Handling

### 7.1 Error Envelope

```json
{
  "success": false,
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "No project exists with the given id.",
    "details": {
      "project_id": "..."
    },
    "retriable": false,
    "docs_url": "https://local/docs/errors/PROJECT_NOT_FOUND"
  },
  "meta": {
    "request_id": "req_...",
    "api_version": "v1",
    "timestamp": "..."
  }
}
```

### 7.2 HTTP Status Mapping

| Status | When |
|--------|------|
| `400` | Validation / malformed JSON |
| `401` | Auth required (future) |
| `403` | Forbidden (future ACL / non-loopback lockdown) |
| `404` | Resource missing |
| `409` | Conflict (illegal state transition, duplicate idempotency with different body) |
| `413` | Upload too large |
| `415` | Unsupported media type |
| `422` | Semantic validation failed |
| `429` | Too many concurrent jobs |
| `500` | Unexpected server error |
| `503` | Dependency unavailable (Ollama/FFmpeg missing) |
| `202` | Async accepted (success path) |

### 7.3 Common Error Codes

| Code | Typical Status |
|------|----------------|
| `VALIDATION_ERROR` | 400/422 |
| `PROJECT_NOT_FOUND` | 404 |
| `JOB_NOT_FOUND` | 404 |
| `INVALID_STATE_TRANSITION` | 409 |
| `JOB_ALREADY_RUNNING` | 409 |
| `IDEMPOTENCY_CONFLICT` | 409 |
| `UPLOAD_TOO_LARGE` | 413 |
| `UNSUPPORTED_SOURCE_TYPE` | 415/422 |
| `MODEL_UNAVAILABLE` | 503 |
| `FFMPEG_UNAVAILABLE` | 503 |
| `STORAGE_DISK_FULL` | 500/507 if used |
| `INTERNAL_ERROR` | 500 |

Validation errors include field paths:

```json
"details": {
  "fields": [
    { "path": "theme_id", "message": "Unknown theme", "code": "UNKNOWN_THEME" }
  ]
}
```

---

## 8. Asynchronous Jobs & Rendering

### 8.1 Why Async

Full pipelines (parse → knowledge → DSL → TTS → encode) can take minutes on CPU-only hardware. The API therefore:

1. Accepts work with `202`  
2. Returns `job_id`  
3. Lets clients poll progress  
4. Supports pause / resume / cancel where safe  

### 8.2 Job Resource

Jobs are addressed at:

- `GET /jobs/{job_id}`  
- `GET /jobs/{job_id}/progress`  
- `POST /jobs/{job_id}/pause`  
- `POST /jobs/{job_id}/resume`  
- `POST /jobs/{job_id}/cancel`  

Pipeline stage triggers (`/projects/{id}/generate/...`) create jobs of various `job_type` values.

### 8.3 Progress Payload

```json
{
  "job_id": "...",
  "project_id": "...",
  "status": "running",
  "coarse_stage": "rendering_video",
  "fine_stage": "rendering_agent",
  "progress_percent": 72.5,
  "message": "Encoding H.264…",
  "stages": [
    { "name": "parser_agent", "status": "succeeded" },
    { "name": "rendering_agent", "status": "running" }
  ],
  "warnings": [],
  "error": null,
  "updated_at": "..."
}
```

### 8.4 Pause / Resume / Cancel Semantics

| Action | Allowed From | Effect |
|--------|--------------|--------|
| Pause | `running` | Cooperative pause after current stage checkpoint when possible |
| Resume | `paused` (and sometimes `failed` with resume flag) | Continue from checkpoint |
| Cancel | `queued` \| `running` \| `paused` | Terminal `cancelled`; artifacts retained |

**Note:** Pause during FFmpeg encode may only take effect between scene chunks; clients must tolerate delayed pause acknowledgment.

### 8.5 Idempotency

For `POST` endpoints that create jobs, clients MAY send:

```http
X-Idempotency-Key: create-job-binary-search-1
```

- Same key + same body → return original job (`200` or `202`)  
- Same key + different body → `409 IDEMPOTENCY_CONFLICT`  

---

## 9. Endpoint Catalog

Sections 10–18 specify each endpoint fully.

---

## 10. Health & System

### 10.1 Health Check

| | |
|--|--|
| **Purpose** | Liveness of API process |
| **Method** | `GET` |
| **Route** | `/health` |
| **Auth** | None |
| **Request Body** | None |
| **Response Body** | `{ "status": "ok", "uptime_sec": 123 }` inside `data` |
| **Status Codes** | `200` |
| **Validation** | None |
| **Errors** | Rare `500` |

Note: `/health` MAY live outside version mount as `/health` for probes; versioned alias `/api/v1/health` also allowed.

### 10.2 Doctor / Readiness

| | |
|--|--|
| **Purpose** | Check models, FFmpeg, disk, DB readiness |
| **Method** | `GET` |
| **Route** | `/system/doctor` |
| **Auth** | None (V1) |
| **Request Body** | None |
| **Response `data`** | |

```json
{
  "ready": false,
  "checks": [
    { "id": "sqlite", "ok": true },
    { "id": "ffmpeg", "ok": true },
    { "id": "ollama", "ok": false, "detail": "connection refused" },
    { "id": "piper", "ok": true },
    { "id": "disk_space", "ok": true, "free_gb": 42.1 }
  ]
}
```

| **Status Codes** | `200` always if API up; `ready` flag indicates usability |
| **Errors** | `500` on doctor crash |

---

## 11. Projects

### 11.1 Create Project

| | |
|--|--|
| **Purpose** | Create a new ExplainX project shell |
| **Method** | `POST` |
| **Route** | `/projects` |
| **Auth** | None (V1) |

**Request Body**

```json
{
  "title": "Binary Search Explained",
  "description": "Optional",
  "source_type": "topic",
  "source_topic": "Binary search algorithms",
  "theme_id": "notebooklm",
  "source_language_code": "en",
  "target_language_code": "en",
  "voice_id": "en_US-lessac-medium",
  "difficulty": "intermediate",
  "settings": {
    "export_width": 1280,
    "export_height": 720,
    "fps": 30,
    "quality_profile": "standard",
    "burn_in_subtitles": false,
    "subtitle_formats": ["srt", "vtt"],
    "speaking_rate": 1.0
  }
}
```

For file-based projects, create project first then upload (or use combined upload endpoint §12.2).

**Response `data`** (`201`)

```json
{
  "project_id": "uuid",
  "title": "Binary Search Explained",
  "status": "draft",
  "current_version_id": "uuid",
  "created_at": "...",
  "updated_at": "..."
}
```

| **Status Codes** | `201`, `400`, `422`, `503` |
| **Validation** | title required ≤120; theme/language exist; enums valid; dimensions >0 |
| **Errors** | `UNKNOWN_THEME`, `UNKNOWN_LANGUAGE`, `VALIDATION_ERROR` |

---

### 11.2 List Projects

| | |
|--|--|
| **Purpose** | List projects for library UI |
| **Method** | `GET` |
| **Route** | `/projects` |
| **Auth** | None (V1) |
| **Query** | `status`, `q`, `limit`, `cursor`, `sort` |
| **Request Body** | None |
| **Response** | Paginated project summaries |
| **Status Codes** | `200`, `400` |
| **Validation** | limit ≤100 |
| **Errors** | `VALIDATION_ERROR` |

**Summary item fields:** `project_id`, `title`, `status`, `theme_id`, `updated_at`, `thumbnail_url`, `actual_duration_sec`.

---

### 11.3 Get Project

| | |
|--|--|
| **Purpose** | Fetch full project detail including settings, metadata pointers, latest job summary |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}` |
| **Auth** | None (V1) |
| **Request Body** | None |

**Response `data`**

```json
{
  "project_id": "uuid",
  "title": "...",
  "description": "...",
  "status": "running",
  "source_type": "pdf",
  "source_path": "source/input.pdf",
  "theme_id": "notebooklm",
  "source_language_code": "en",
  "target_language_code": "en",
  "voice_id": "en_US-lessac-medium",
  "difficulty": "intermediate",
  "current_version_id": "uuid",
  "dsl_available": true,
  "timeline_available": false,
  "settings": { },
  "metadata": { },
  "latest_job": {
    "job_id": "uuid",
    "status": "running",
    "coarse_stage": "designing_visuals"
  },
  "primary_video_id": null,
  "created_at": "...",
  "updated_at": "..."
}
```

| **Status Codes** | `200`, `404` |
| **Validation** | `project_id` UUID |
| **Errors** | `PROJECT_NOT_FOUND` |

---

### 11.4 Update Project

| | |
|--|--|
| **Purpose** | Update mutable project fields/settings (may invalidate caches; does not auto-render) |
| **Method** | `PATCH` |
| **Route** | `/projects/{project_id}` |
| **Auth** | None (V1) |

**Request Body** (all optional)

```json
{
  "title": "New title",
  "description": "...",
  "theme_id": "dark",
  "voice_id": "...",
  "difficulty": "beginner",
  "target_language_code": "hi",
  "settings": {
    "quality_profile": "draft",
    "burn_in_subtitles": true
  }
}
```

| **Response** | Updated project (`200`) |
| **Status Codes** | `200`, `400`, `404`, `409`, `422` |
| **Validation** | Same as create for provided fields |
| **Errors** | `PROJECT_NOT_FOUND`, `INVALID_STATE_TRANSITION` if archived/deleted, `UNKNOWN_THEME` |

Changing theme/voice/language marks dirty stages; client should call appropriate generate endpoints.

---

### 11.5 Delete Project

| | |
|--|--|
| **Purpose** | Soft-delete (default) or hard-delete project and artifacts |
| **Method** | `DELETE` |
| **Route** | `/projects/{project_id}` |
| **Auth** | None (V1) |
| **Query** | `mode=soft\|hard` (default `soft`) |
| **Request Body** | None optional `{ "confirm": true }` required for `hard` |

| **Response `data`** | `{ "project_id": "...", "deleted": true, "mode": "soft" }` |
| **Status Codes** | `200`, `400`, `404`, `409` |
| **Validation** | hard requires confirm; cannot hard-delete while job running unless `force=true` |
| **Errors** | `PROJECT_NOT_FOUND`, `JOB_ALREADY_RUNNING`, `VALIDATION_ERROR` |

---

### 11.6 List Project Versions

| | |
|--|--|
| **Purpose** | List generation versions for a project |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/versions` |
| **Auth** | None (V1) |
| **Response** | Version summaries (`version_number`, `change_reason`, `status`, `created_at`) |
| **Status Codes** | `200`, `404` |
| **Errors** | `PROJECT_NOT_FOUND` |

---

### 11.7 Get Project Artifacts Index

| | |
|--|--|
| **Purpose** | List artifact pointers (DSL, knowledge, script, etc.) for current or specified version |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/artifacts` |
| **Query** | `version_id?` |
| **Response** | Artifact index entries with types, hashes, availability |
| **Status Codes** | `200`, `404` |
| **Errors** | `PROJECT_NOT_FOUND`, `VERSION_NOT_FOUND` |

---

## 12. Documents / Upload

### 12.1 Upload Document

| | |
|--|--|
| **Purpose** | Attach a source document to an existing project |
| **Method** | `POST` |
| **Route** | `/projects/{project_id}/documents` |
| **Auth** | None (V1) |
| **Content-Type** | `multipart/form-data` |

**Request Body (multipart)**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | yes | PDF/DOCX/TXT/MD |
| `replace` | boolean | no | Replace existing source (default false) |

**Response `data`** (`201`)

```json
{
  "project_id": "...",
  "source_type": "pdf",
  "source_path": "source/input.pdf",
  "source_hash": "sha256:...",
  "size_bytes": 1048576,
  "filename": "lesson.pdf"
}
```

| **Status Codes** | `201`, `400`, `404`, `409`, `413`, `415`, `422` |
| **Validation** | extension/MIME allowlist; max size (e.g. 50MB V1); project not immutable |
| **Errors** | `UNSUPPORTED_SOURCE_TYPE`, `UPLOAD_TOO_LARGE`, `PROJECT_NOT_FOUND`, `SOURCE_ALREADY_EXISTS` |

---

### 12.2 Create Project With Upload (Convenience)

| | |
|--|--|
| **Purpose** | Atomically create project + upload document |
| **Method** | `POST` |
| **Route** | `/projects/upload` |
| **Auth** | None (V1) |
| **Content-Type** | `multipart/form-data` |

**Fields:** `file` + JSON fields as string `payload` mirroring Create Project (without topic-only source).

| **Status Codes** | `201`, `400`, `413`, `415`, `422` |
| **Errors** | Same as create + upload |

---

### 12.3 Set Topic Source

| | |
|--|--|
| **Purpose** | Set/replace topic text source without file |
| **Method** | `PUT` |
| **Route** | `/projects/{project_id}/source/topic` |
| **Request Body** | `{ "topic": "Photosynthesis for grade 8" }` |
| **Response** | Updated source metadata |
| **Status Codes** | `200`, `400`, `404`, `422` |
| **Validation** | topic 3–500 chars |
| **Errors** | `VALIDATION_ERROR`, `PROJECT_NOT_FOUND` |

---

## 13. Generation Pipeline Controls

These endpoints enqueue **partial or full** pipeline jobs. All return **`202 Accepted`** with job envelope unless a sync dry-run query is used (`?sync=true` forbidden for heavy stages in V1).

Common validation:

- Project exists and not deleted  
- Required upstream artifacts present (or `force_from` provided)  
- Doctor dependencies available for requested stages  
- No conflicting running job unless `preempt` policy allows  

Common errors: `PROJECT_NOT_FOUND`, `MISSING_UPSTREAM_ARTIFACT`, `JOB_ALREADY_RUNNING`, `MODEL_UNAVAILABLE`, `VALIDATION_ERROR`.

---

### 13.1 Start Full Pipeline

| | |
|--|--|
| **Purpose** | Run end-to-end generation through render (default product action) |
| **Method** | `POST` |
| **Route** | `/projects/{project_id}/generate` |
| **Auth** | None (V1) |

**Request Body**

```json
{
  "mode": "full",
  "from_stage": null,
  "until_stage": null,
  "create_new_version": true,
  "change_reason": "full_regen",
  "options": {
    "skip_translation": true,
    "quality_profile": "standard"
  }
}
```

**Response** | `202` job envelope (`job_type=full_pipeline`)  
**Status Codes** | `202`, `400`, `404`, `409`, `422`, `429`, `503`  
**Validation** | Source present (file or topic); settings complete  
**Errors** | `SOURCE_REQUIRED`, `JOB_ALREADY_RUNNING`, `MODEL_UNAVAILABLE`, `FFMPEG_UNAVAILABLE`

---

### 13.2 Generate Script

| | |
|--|--|
| **Purpose** | Run pipeline through Script Agent (knowledge plane + script) |
| **Method** | `POST` |
| **Route** | `/projects/{project_id}/generate/script` |
| **Request Body** | |

```json
{
  "reuse_knowledge": true,
  "difficulty_override": null
}
```

| **Response** | `202` job (`job_type` includes script target) |
| **Status Codes** | `202`, `404`, `409`, `422`, `503` |
| **Validation** | Source available; if `reuse_knowledge` then knowledge artifact must exist or be regenerable |
| **Errors** | `MISSING_UPSTREAM_ARTIFACT`, `MODEL_UNAVAILABLE` |

On completion, clients may `GET /projects/{id}/script`.

---

### 13.3 Generate Scenes

| | |
|--|--|
| **Purpose** | Generate scene plan from script |
| **Method** | `POST` |
| **Route** | `/projects/{project_id}/generate/scenes` |
| **Request Body** | `{ "reuse_script": true, "max_scenes": 12 }` |
| **Response** | `202` job |
| **Status Codes** | `202`, `404`, `409`, `422`, `503` |
| **Validation** | Script artifact required if reuse; max_scenes ≥ 1 |
| **Errors** | `MISSING_UPSTREAM_ARTIFACT` (`narration_script`) |

---

### 13.4 Generate Presentation

| | |
|--|--|
| **Purpose** | Compile Presentation DSL (visual/layout/theme/assets + presentation engine) |
| **Method** | `POST` |
| **Route** | `/projects/{project_id}/generate/presentation` |
| **Request Body** | |

```json
{
  "theme_id": null,
  "reuse_scene_plan": true,
  "reuse_visual_plan": false
}
```

| **Response** | `202` job |
| **Status Codes** | `202`, `404`, `409`, `422`, `503` |
| **Validation** | Scene plan required; theme exists |
| **Errors** | `MISSING_UPSTREAM_ARTIFACT`, `UNKNOWN_THEME`, `ASSET_PACK_MISSING` |

On completion: DSL available via artifacts / download.

---

### 13.5 Generate Narration (Voice)

| | |
|--|--|
| **Purpose** | Synthesize TTS audio for script beats (Voice Agent) |
| **Method** | `POST` |
| **Route** | `/projects/{project_id}/generate/narration` |
| **Request Body** | |

```json
{
  "voice_id": null,
  "speaking_rate": 1.0,
  "translate_first": false
}
```

| **Response** | `202` job |
| **Status Codes** | `202`, `404`, `409`, `422`, `503` |
| **Validation** | Script exists; voice installed |
| **Errors** | `MISSING_UPSTREAM_ARTIFACT`, `VOICE_NOT_FOUND`, `TRANSLATE_MODEL_MISSING` |

Alias route (optional): `/projects/{project_id}/generate/voice`.

---

### 13.6 Generate Subtitles

| | |
|--|--|
| **Purpose** | Build timed subtitles from narration + audio durations |
| **Method** | `POST` |
| **Route** | `/projects/{project_id}/generate/subtitles` |
| **Request Body** | |

```json
{
  "formats": ["srt", "vtt"],
  "burn_in": false,
  "align_with_whisper": false
}
```

| **Response** | `202` job |
| **Status Codes** | `202`, `404`, `409`, `422`, `503` |
| **Validation** | formats subset of supported; narration audio durations required |
| **Errors** | `SUBTITLE_MISSING_AUDIO`, `MISSING_UPSTREAM_ARTIFACT` |

---

### 13.7 Generate Motion / Timeline

| | |
|--|--|
| **Purpose** | Run Animation + Camera + Timeline agents/engines to bind absolute timeline |
| **Method** | `POST` |
| **Route** | `/projects/{project_id}/generate/timeline` |
| **Request Body** | `{ "reuse_animations": false }` |
| **Response** | `202` job |
| **Status Codes** | `202`, `404`, `409`, `422` |
| **Validation** | DSL compiled; voice durations if voice enabled |
| **Errors** | `TIMELINE_MISSING_AUDIO`, `MISSING_UPSTREAM_ARTIFACT` |

---

### 13.8 Get Generated Script

| | |
|--|--|
| **Purpose** | Read narration script artifact |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/script` |
| **Response `data`** | Script JSON (beats, language) |
| **Status Codes** | `200`, `404` |
| **Errors** | `PROJECT_NOT_FOUND`, `ARTIFACT_NOT_FOUND` |

---

### 13.9 Get Scenes

| | |
|--|--|
| **Purpose** | Read scene plan / scene index |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/scenes` |
| **Query** | `version_id?` |
| **Response** | List of scenes (id, order, purpose, visual_mode, durations) |
| **Status Codes** | `200`, `404` |
| **Errors** | `PROJECT_NOT_FOUND`, `ARTIFACT_NOT_FOUND` |

---

### 13.10 Get Presentation DSL

| | |
|--|--|
| **Purpose** | Download/read compiled Presentation DSL JSON |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/presentation` |
| **Query** | `version_id?` |
| **Response** | DSL document (JSON envelope `data` or raw with `Accept` preference — normative: envelope with DSL in `data.dsl`) |
| **Status Codes** | `200`, `404` |
| **Errors** | `ARTIFACT_NOT_FOUND` |

---

## 14. Narration, Subtitles & Media Artifacts

### 14.1 List Narration Beats

| | |
|--|--|
| **Purpose** | List narration rows with timing/audio availability |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/narrations` |
| **Status Codes** | `200`, `404` |
| **Errors** | `PROJECT_NOT_FOUND` |

---

### 14.2 Get Narration Audio

| | |
|--|--|
| **Purpose** | Download a beat audio file |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/narrations/{beat_id}/audio` |
| **Response** | Binary audio |
| **Status Codes** | `200`, `404` |
| **Errors** | `ARTIFACT_NOT_FOUND` |

---

### 14.3 List / Download Subtitles

| | |
|--|--|
| **Purpose** | Download subtitle sidecar |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/subtitles/{format}` |
| **Path `format`** | `srt` \| `vtt` |
| **Response** | Text file |
| **Status Codes** | `200`, `404`, `422` |
| **Errors** | `ARTIFACT_NOT_FOUND`, `VALIDATION_ERROR` |

---

## 15. Render Lifecycle

### 15.1 Render Video

| | |
|--|--|
| **Purpose** | Enqueue Rendering Agent for MP4 (+ thumbnail) from bound timeline |
| **Method** | `POST` |
| **Route** | `/projects/{project_id}/render` |
| **Auth** | None (V1) |

**Request Body**

```json
{
  "quality_profile": "standard",
  "width": 1280,
  "height": 720,
  "burn_in_subtitles": false,
  "force": false
}
```

| **Response** | `202` job envelope (`job_type=render_only` or full render stage) |
| **Status Codes** | `202`, `404`, `409`, `422`, `429`, `503` |
| **Validation** | Timeline bound / render_ready; dimensions match aspect; FFmpeg present |
| **Errors** | `RENDER_INPUT_INCOMPLETE`, `FFMPEG_UNAVAILABLE`, `JOB_ALREADY_RUNNING` |

---

### 15.2 Get Render Progress

| | |
|--|--|
| **Purpose** | Poll coarse/fine progress for a job (render or full pipeline) |
| **Method** | `GET` |
| **Route** | `/jobs/{job_id}/progress` |
| **Auth** | None (V1) |
| **Request Body** | None |
| **Response `data`** | Progress payload (§8.3) |
| **Status Codes** | `200`, `404` |
| **Validation** | job_id UUID |
| **Errors** | `JOB_NOT_FOUND` |

**Alias:** `GET /projects/{project_id}/render/progress?job_id=` for UI convenience (must match project).

---

### 15.3 Get Job

| | |
|--|--|
| **Purpose** | Full job resource including stages and error details |
| **Method** | `GET` |
| **Route** | `/jobs/{job_id}` |
| **Response `data`** | Job record + stages[] |
| **Status Codes** | `200`, `404` |
| **Errors** | `JOB_NOT_FOUND` |

---

### 15.4 Pause Render / Job

| | |
|--|--|
| **Purpose** | Cooperatively pause a running job after checkpoint |
| **Method** | `POST` |
| **Route** | `/jobs/{job_id}/pause` |
| **Request Body** | `{ "reason": "user_requested" }` optional |
| **Response `data`** | `{ "job_id": "...", "status": "pausing"|"paused" }` |
| **Status Codes** | `200`, `404`, `409` |
| **Validation** | status must be `running` |
| **Errors** | `JOB_NOT_FOUND`, `INVALID_STATE_TRANSITION` |

**Alias:** `POST /projects/{project_id}/render/pause` with body `{ "job_id": "..." }`.

---

### 15.5 Resume Render / Job

| | |
|--|--|
| **Purpose** | Resume a paused job from last checkpoint |
| **Method** | `POST` |
| **Route** | `/jobs/{job_id}/resume` |
| **Request Body** | `{ "force_from_stage": null }` optional |
| **Response** | `202` or `200` with job status `queued`/`running` |
| **Status Codes** | `200`, `202`, `404`, `409`, `503` |
| **Validation** | status `paused` (or resumable `failed`) |
| **Errors** | `INVALID_STATE_TRANSITION`, `MODEL_UNAVAILABLE` |

**Alias:** `POST /projects/{project_id}/render/resume`.

---

### 15.6 Cancel Render / Job

| | |
|--|--|
| **Purpose** | Cancel queued/running/paused job |
| **Method** | `POST` |
| **Route** | `/jobs/{job_id}/cancel` |
| **Request Body** | `{ "reason": "user_cancelled" }` optional |
| **Response `data`** | `{ "job_id": "...", "status": "cancelled" }` |
| **Status Codes** | `200`, `404`, `409` |
| **Validation** | not already terminal completed |
| **Errors** | `INVALID_STATE_TRANSITION`, `JOB_NOT_FOUND` |

**Alias:** `POST /projects/{project_id}/render/cancel`.

---

### 15.7 List Jobs for Project

| | |
|--|--|
| **Purpose** | Job history for a project |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/jobs` |
| **Query** | `status?`, pagination |
| **Status Codes** | `200`, `404` |
| **Errors** | `PROJECT_NOT_FOUND` |

---

## 16. Export & Download

### 16.1 Export Video (Package)

| | |
|--|--|
| **Purpose** | Assemble/export package (MP4 + narration + subtitles + thumbnail + metadata + optional DSL) and return manifest; may enqueue if assembly needed |
| **Method** | `POST` |
| **Route** | `/projects/{project_id}/export` |
| **Request Body** | |

```json
{
  "include": ["video", "audio", "subtitles", "thumbnail", "metadata", "dsl"],
  "video_id": null,
  "as_zip": true
}
```

| **Response** | `200` with manifest + download URLs, or `202` if packaging job started |
| **Status Codes** | `200`, `202`, `404`, `409`, `422` |
| **Validation** | include subset valid; primary video ready |
| **Errors** | `PROJECT_EXPORT_INCOMPLETE`, `VIDEO_NOT_READY` |

---

### 16.2 Download Primary Video

| | |
|--|--|
| **Purpose** | Download MP4 |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/export/video` |
| **Query** | `video_id?` |
| **Response** | `video/mp4` bytes |
| **Status Codes** | `200`, `404` |
| **Errors** | `VIDEO_NOT_FOUND`, `PROJECT_NOT_FOUND` |

---

### 16.3 Download Thumbnail

| | |
|--|--|
| **Purpose** | Download thumbnail image |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/export/thumbnail` |
| **Response** | `image/jpeg` |
| **Status Codes** | `200`, `404` |
| **Errors** | `ARTIFACT_NOT_FOUND` |

---

### 16.4 Download Export ZIP

| | |
|--|--|
| **Purpose** | Download full export archive |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/export/zip` |
| **Response** | `application/zip` |
| **Status Codes** | `200`, `404`, `409` |
| **Errors** | `PROJECT_EXPORT_INCOMPLETE` |

---

### 16.5 Get Export Manifest

| | |
|--|--|
| **Purpose** | JSON manifest of export files and hashes |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/export/manifest` |
| **Response `data`** | `{ "files": [ { "role": "video", "path": "...", "hash": "...", "url": "..." } ] }` |
| **Status Codes** | `200`, `404` |
| **Errors** | `PROJECT_NOT_FOUND`, `PROJECT_EXPORT_INCOMPLETE` |

---

### 16.6 List Videos

| | |
|--|--|
| **Purpose** | List rendered videos for project/versions |
| **Method** | `GET` |
| **Route** | `/projects/{project_id}/videos` |
| **Status Codes** | `200`, `404` |
| **Errors** | `PROJECT_NOT_FOUND` |

---

## 17. Themes, Voices & Languages

### 17.1 List Themes

| | |
|--|--|
| **Purpose** | List available themes |
| **Method** | `GET` |
| **Route** | `/themes` |
| **Response** | Theme summaries |
| **Status Codes** | `200` |
| **Auth** | None |
| **Errors** | — |

---

### 17.2 Get Theme

| | |
|--|--|
| **Purpose** | Theme detail + token preview |
| **Method** | `GET` |
| **Route** | `/themes/{theme_id}` |
| **Status Codes** | `200`, `404` |
| **Errors** | `UNKNOWN_THEME` / `THEME_NOT_FOUND` |

---

### 17.3 List Voices

| | |
|--|--|
| **Purpose** | List installed Piper voices |
| **Method** | `GET` |
| **Route** | `/voices` |
| **Query** | `language_code?` |
| **Status Codes** | `200` |
| **Errors** | — |

---

### 17.4 List Languages

| | |
|--|--|
| **Purpose** | List supported languages and capabilities |
| **Method** | `GET` |
| **Route** | `/languages` |
| **Status Codes** | `200` |
| **Errors** | — |

---

## 18. Settings & Plugins

### 18.1 Get App Settings

| | |
|--|--|
| **Purpose** | Read non-secret global settings |
| **Method** | `GET` |
| **Route** | `/settings` |
| **Status Codes** | `200` |
| **Auth** | None (V1); future admin |
| **Errors** | — |

---

### 18.2 Update App Settings

| | |
|--|--|
| **Purpose** | Update global settings (model paths, concurrency) |
| **Method** | `PATCH` |
| **Route** | `/settings` |
| **Request Body** | Sparse key/value map |
| **Status Codes** | `200`, `400`, `422` |
| **Validation** | Known keys only; paths must stay in allowlisted roots |
| **Errors** | `VALIDATION_ERROR`, `PATH_NOT_ALLOWED` |

---

### 18.3 List Plugins

| | |
|--|--|
| **Purpose** | List installed plugins and enablement |
| **Method** | `GET` |
| **Route** | `/plugins` |
| **Status Codes** | `200` |

---

### 18.4 Enable / Disable Plugin

| | |
|--|--|
| **Purpose** | Toggle plugin |
| **Method** | `POST` |
| **Route** | `/plugins/{plugin_id}/enable` or `/plugins/{plugin_id}/disable` |
| **Status Codes** | `200`, `404`, `409` |
| **Errors** | `PLUGIN_NOT_FOUND`, `PLUGIN_INCOMPATIBLE` |

---

## 19. Webhooks / Events (Optional Future)

V1 uses polling. Future networked deployments MAY offer:

| | |
|--|--|
| **Purpose** | Push job progress events |
| **Method** | `WS` or SSE |
| **Route** | `/ws/jobs/{job_id}` or `GET /jobs/{job_id}/events` (SSE) |
| **Auth** | Bearer (future) |
| **Notes** | Not required for local V1 |

---

## 20. Rate Limits & Concurrency

| Limit | V1 Default |
|-------|------------|
| Concurrent full_pipeline jobs | 1 |
| Concurrent render_only jobs | 1 |
| Upload size | 50 MB (configurable) |
| API requests/min (local) | Soft; not strictly required |

Exceeding concurrency → `429` with `JOB_CONCURRENCY_LIMIT`.

---

## 21. OpenAPI Alignment

Implementation SHOULD publish machine-readable OpenAPI 3.x at:

```
GET /api/v1/openapi.json
```

Human docs MAY be generated from OpenAPI, but **this markdown file remains the product authority** until an ADR says otherwise.

---

## 22. Appendix: Enumerations

### Project status
`draft` | `queued` | `running` | `completed` | `failed` | `cancelled` | `archived`

### Job status
`queued` | `running` | `pausing` | `paused` | `completed` | `failed` | `cancelled`

### Coarse stages
`reading_document` | `understanding_content` | `writing_narration` | `designing_visuals` | `generating_motion` | `generating_voice` | `rendering_video` | `finalizing_project`

### Quality profiles
`draft` | `standard` | `high`

### Source types
`pdf` | `docx` | `txt` | `md` | `topic`

---

## 23. Appendix: Complete Route Index

| Method | Route | Section |
|--------|-------|---------|
| GET | `/health` | 10.1 |
| GET | `/system/doctor` | 10.2 |
| POST | `/projects` | 11.1 |
| GET | `/projects` | 11.2 |
| GET | `/projects/{project_id}` | 11.3 |
| PATCH | `/projects/{project_id}` | 11.4 |
| DELETE | `/projects/{project_id}` | 11.5 |
| GET | `/projects/{project_id}/versions` | 11.6 |
| GET | `/projects/{project_id}/artifacts` | 11.7 |
| POST | `/projects/{project_id}/documents` | 12.1 |
| POST | `/projects/upload` | 12.2 |
| PUT | `/projects/{project_id}/source/topic` | 12.3 |
| POST | `/projects/{project_id}/generate` | 13.1 |
| POST | `/projects/{project_id}/generate/script` | 13.2 |
| POST | `/projects/{project_id}/generate/scenes` | 13.3 |
| POST | `/projects/{project_id}/generate/presentation` | 13.4 |
| POST | `/projects/{project_id}/generate/narration` | 13.5 |
| POST | `/projects/{project_id}/generate/subtitles` | 13.6 |
| POST | `/projects/{project_id}/generate/timeline` | 13.7 |
| GET | `/projects/{project_id}/script` | 13.8 |
| GET | `/projects/{project_id}/scenes` | 13.9 |
| GET | `/projects/{project_id}/presentation` | 13.10 |
| GET | `/projects/{project_id}/narrations` | 14.1 |
| GET | `/projects/{project_id}/narrations/{beat_id}/audio` | 14.2 |
| GET | `/projects/{project_id}/subtitles/{format}` | 14.3 |
| POST | `/projects/{project_id}/render` | 15.1 |
| GET | `/jobs/{job_id}/progress` | 15.2 |
| GET | `/jobs/{job_id}` | 15.3 |
| POST | `/jobs/{job_id}/pause` | 15.4 |
| POST | `/jobs/{job_id}/resume` | 15.5 |
| POST | `/jobs/{job_id}/cancel` | 15.6 |
| GET | `/projects/{project_id}/jobs` | 15.7 |
| POST | `/projects/{project_id}/export` | 16.1 |
| GET | `/projects/{project_id}/export/video` | 16.2 |
| GET | `/projects/{project_id}/export/thumbnail` | 16.3 |
| GET | `/projects/{project_id}/export/zip` | 16.4 |
| GET | `/projects/{project_id}/export/manifest` | 16.5 |
| GET | `/projects/{project_id}/videos` | 16.6 |
| GET | `/themes` | 17.1 |
| GET | `/themes/{theme_id}` | 17.2 |
| GET | `/voices` | 17.3 |
| GET | `/languages` | 17.4 |
| GET | `/settings` | 18.1 |
| PATCH | `/settings` | 18.2 |
| GET | `/plugins` | 18.3 |
| POST | `/plugins/{plugin_id}/enable` | 18.4 |
| POST | `/plugins/{plugin_id}/disable` | 18.4 |
| GET | `/openapi.json` | 21 |

**Aliases (non-normative convenience):**

- `GET /projects/{project_id}/render/progress`  
- `POST /projects/{project_id}/render/pause|resume|cancel`  
- `POST /projects/{project_id}/generate/voice` → narration  

---

## Closing Statement

The ExplainX API is a **versioned, envelope-based, async-first control plane** for an offline presentation-to-video engine.

Clients should:

1. Create/upload project sources  
2. Start generate/render jobs (`202`)  
3. Poll `/jobs/{id}/progress`  
4. Pause/resume/cancel as needed  
5. Download exports when artifacts are ready  

Agents and renderers remain behind the API — never exposed as ad-hoc HTTP to the model layer.

---

*End of API_SPECIFICATION.md*  
*ExplainX Engineering — Stable Contracts. Async Jobs. Local Trust.*
