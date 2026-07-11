# ExplainX — Coding Standards

**Document Status:** Canonical Coding Standards  
**Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Audience:** Every developer and Cursor session before writing code  
**Companions:**  
[`DEVELOPMENT_GUIDE.md`](./DEVELOPMENT_GUIDE.md) ·  
[`FOLDER_STRUCTURE.md`](./FOLDER_STRUCTURE.md) ·  
[`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md) ·  
[`PRESENTATION_DSL.md`](./PRESENTATION_DSL.md) ·  
[`AGENT_SPECIFICATIONS.md`](./AGENT_SPECIFICATIONS.md) ·  
[`API_SPECIFICATION.md`](./API_SPECIFICATION.md)  

> **Authority:** If code style or structure conflicts with this document, change the code.  
> Architecture isolation rules in `FOLDER_STRUCTURE.md` / `SYSTEM_ARCHITECTURE.md` override any convenience shortcut.

---

## Table of Contents

1. [Guiding Principles](#1-guiding-principles)
2. [Python Style Guide](#2-python-style-guide)
3. [TypeScript Style Guide](#3-typescript-style-guide)
4. [Folder Naming](#4-folder-naming)
5. [File Naming](#5-file-naming)
6. [Class Naming](#6-class-naming)
7. [Function Naming](#7-function-naming)
8. [Variable Naming](#8-variable-naming)
9. [Comments](#9-comments)
10. [Documentation](#10-documentation)
11. [Logging](#11-logging)
12. [Error Handling](#12-error-handling)
13. [Validation](#13-validation)
14. [Configuration Management](#14-configuration-management)
15. [Dependency Injection](#15-dependency-injection)
16. [Testing Rules](#16-testing-rules)
17. [Performance Rules](#17-performance-rules)
18. [Architecture Rules](#18-architecture-rules)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Formatting & Tooling](#20-formatting--tooling)
21. [Security & Privacy Coding Rules](#21-security--privacy-coding-rules)

---

## 1. Guiding Principles

| Principle | Standard |
|-----------|----------|
| Clarity over cleverness | Prefer obvious code |
| Contracts over conventions alone | Types + validators at boundaries |
| Isolation over shortcuts | No illegal cross-layer calls |
| Small diffs | Change only what the task needs |
| Offline-first | No paid/cloud AI in core paths |
| Fail clearly | Stable error codes, structured logs |

**Before writing code, read:** the relevant architecture doc for your layer + this standards doc.

---

## 2. Python Style Guide

### 2.1 Language & Tooling

| Item | Standard |
|------|----------|
| Language | Python 3.11+ (document exact pin in `pyproject.toml`) |
| Type hints | Required on public functions/methods |
| Formatter | Ruff format or Black (pick one in repo setup; do not mix) |
| Linter | Ruff |
| Types | `mypy` or `pyright` in CI for `backend/app` |
| Tests | `pytest` |
| Packages | Absolute imports from `app....` inside backend |

### 2.2 Style Rules

1. Follow PEP 8 except where formatter disagrees (formatter wins).  
2. Max line length: **100** (formatter-enforced).  
3. Prefer `list[str]` / `dict[str, Any]` over `typing.List` on 3.11+.  
4. Use `pathlib.Path` for filesystem paths.  
5. No wildcard imports (`from x import *`).  
6. Keep functions focused; if > ~50 lines of mixed concerns, split.  
7. Agents return Pydantic models / typed dicts — not ad-hoc untyped dict soup at boundaries.  
8. Async: use `async def` for I/O-bound API/service edges; engines may stay sync unless proven otherwise. Do not mark sync CPU code async without reason.  
9. Avoid mutable default arguments.  
10. Datetimes in UTC; store ISO-8601 strings at persistence boundary as per DB design.

### 2.3 Pydantic / Schemas

- API request/response models live under `app/models/api/`.  
- Artifact schemas under `app/models/artifacts/`.  
- DSL models under `app/models/dsl/`.  
- Use `model_config` forbidding unexpected extras on **ingress** validation where strictness is required.  
- Include `schema_version` on artifact payloads.

### 2.4 Python Docstrings

Use concise docstrings on public modules/classes/functions:

```python
def bind_timeline(dsl: PresentationDSL, audio: VoiceArtifact) -> Timeline:
    """Compile absolute timeline tracks from DSL and measured audio durations."""
```

Do not restate the type signature in prose.

---

## 3. TypeScript Style Guide

### 3.1 Language & Tooling

| Item | Standard |
|------|----------|
| Language | TypeScript strict mode |
| Framework | Next.js App Router + React |
| Formatter | Prettier |
| Linter | ESLint (typescript-eslint) |
| Styling | Tailwind CSS |
| Motion (UI only) | Framer Motion |

### 3.2 Style Rules

1. `strict: true` in `tsconfig`.  
2. No `any` unless isolated and justified with comment; prefer `unknown` + narrow.  
3. Prefer `interface` for object shapes shared across files; `type` for unions/utilities.  
4. Components: function components only.  
5. Named exports preferred for reusable modules; default export OK for Next.js pages.  
6. Keep UI components presentational when possible; data fetching in features/hooks.  
7. API calls only through `lib/api` client — never raw scattered `fetch` with magic URLs.  
8. Match API envelope types from `API_SPECIFICATION.md`.  
9. Avoid premature `useMemo` / `useCallback` unless profiling or repo React Compiler guidance requires.  
10. Client vs server components: mark `"use client"` only when needed.

### 3.3 React Patterns

- Prefer controlled progressive enhancement of job polling with clear cancellation.  
- Handle loading, empty, and error states explicitly.  
- Do not encode business pipeline logic in the UI.

---

## 4. Folder Naming

| Rule | Example |
|------|---------|
| `snake_case` for Python packages/folders | `visual_planning_agent` lives in file; package `agents/` |
| `kebab-case` for frontend route segments if multiword | `app/projects/[projectId]/` |
| `snake_case` or short nouns for backend packages | `engines/presentation/` |
| Plural for collections | `routes/`, `repositories/`, `themes/` |
| No spaces, no uppercase folder names | avoid `My Agents/` |
| Runtime data never under source apps | use `data/` |

Follow `FOLDER_STRUCTURE.md` for placement. Do not invent top-level folders without ADR + doc update.

---

## 5. File Naming

### 5.1 Python

| Kind | Pattern | Example |
|------|---------|---------|
| Agent | `<name>_agent.py` | `script_agent.py` |
| Route module | plural resource | `projects.py` |
| Repository | `<entity>_repository.py` | `job_repository.py` |
| Service | `<domain>_service.py` | `export_service.py` |
| Adapter | `<vendor>_<capability>.py` | `piper_tts.py` |
| Test | `test_<unit>.py` | `test_timeline_binder.py` |
| Migration | timestamped id | `20260711_001_init_core.py` |

### 5.2 TypeScript

| Kind | Pattern | Example |
|------|---------|---------|
| Component | `PascalCase.tsx` | `JobProgress.tsx` |
| Hook | `useSomething.ts` | `useJobPolling.ts` |
| Util | `camelCase.ts` | `formatDuration.ts` |
| Feature folder | kebab or camel nouns | `features/jobs/` |
| Types | `*.types.ts` or colocated | `project.types.ts` |

### 5.3 Docs & Config

- Docs: `UPPER_SNAKE` for canonical specs already established (`PROJECT_CONSTITUTION.md`)  
- New ADRs: `ADR-0001-title-slug.md`  
- Env example: `.env.example`  

---

## 6. Class Naming

| Kind | Pattern | Example |
|------|---------|---------|
| Class | `PascalCase` | `PresentationCompiler` |
| Pydantic model | `PascalCase` | `NarrationScript` |
| Exception | `PascalCase` + `Error`/`Exception` | `RenderInputIncompleteError` |
| Abstract port/protocol | `PascalCase` noun | `LLMPort`, `StoragePort` |
| Agent class (if used) | `<Name>Agent` | `ScriptAgent` |
| Enum | `PascalCase` | `JobStatus` |
| Enum members | `UPPER_SNAKE` | `JobStatus.RUNNING` |

Avoid `Manager`, `Helper`, `Utils` classes that attract unrelated methods. Prefer named services/engines.

---

## 7. Function Naming

| Kind | Pattern | Example |
|------|---------|---------|
| Regular function/method | `snake_case` (Py) / `camelCase` (TS) | `bind_timeline` / `fetchProject` |
| Boolean returning | `is_` / `has_` / `can_` prefix | `is_render_ready` |
| Agent entry | `run` or `execute` | `ScriptAgent.run(state)` |
| Validators | `validate_<thing>` | `validate_dsl` |
| Factories | `create_<thing>` | `create_project` |
| Converters | `to_<x>` / `from_<x>` | `to_envelope` |
| Private | `_leading_underscore` (Py) | `_repair_json` |

Names should describe **outcome**, not implementation (`compile_scene_graph`, not `doStuff`).

---

## 8. Variable Naming

| Kind | Pattern | Example |
|------|---------|---------|
| Locals / vars | `snake_case` (Py) / `camelCase` (TS) | `project_id` / `projectId` |
| Constants | `UPPER_SNAKE` | `MAX_UPLOAD_BYTES` |
| IDs | explicit suffix | `project_id`, `job_id`, `beat_id` |
| Paths | `*_path` | `dsl_path` |
| Hashes | `*_hash` | `source_hash` |
| Booleans | affirmative | `cache_hit`, not `cache_not_miss` |
| Collections | plural | `scenes`, `beats` |

**Avoid:** single-letter names except short loop indices; opaque abbreviations (`tmp2`, `data1`).

**IDs across languages:** Python `project_id` ↔ JSON `project_id` ↔ TS `projectId` at the TS boundary only (map in client types).

---

## 9. Comments

### 9.1 When to Comment

- Non-obvious constraints (memory budget, motion safety limits)  
- Workarounds with link/ticket  
- Public protocol intent when name is insufficient  

### 9.2 When Not to Comment

- Restating the next line of code  
- Commented-out dead code (delete it)  
- Loud banners (`##### SECTION #####`)  

### 9.3 TODO Rules

```python
# TODO(EX-123): unload IndicTrans2 after translation stage to free RAM
```

No ownerless TODOs without ticket/context. Do not ship `FIXME` in `main` without issue link.

---

## 10. Documentation

| Change | Doc obligation |
|--------|----------------|
| New/changed API route | `API_SPECIFICATION.md` |
| New/changed agent | `AGENT_SPECIFICATIONS.md` |
| DSL change | `PRESENTATION_DSL.md` (+ version) |
| DB change | `DATABASE_DESIGN.md` + migration |
| Folder/layer change | `FOLDER_STRUCTURE.md` + ADR |
| Process change | `DEVELOPMENT_GUIDE.md` |
| Standards change | this file |

Module README files are optional; prefer canonical docs over scattered READMEs. Root `README.md` holds run instructions only.

Public Python modules and TS `lib/api` should stay aligned with specs — docs are not optional for contract changes.

---

## 11. Logging

### 11.1 Rules

1. Use the shared logging setup (`app/core/logging.py`) — no ad-hoc `print` in production paths.  
2. Prefer **structured** logs (JSON fields) on backend.  
3. Always include `request_id` / `project_id` / `job_id` when available.  
4. Agent lifecycle events per `AGENT_SPECIFICATIONS.md`.  
5. Default: do not log full document bodies or full narration text.  
6. Levels: DEBUG (dev detail), INFO (stage transitions), WARNING (fallbacks), ERROR (failures), CRITICAL (process integrity).  

### 11.2 Example Fields

`ts`, `level`, `component`, `event`, `project_id`, `job_id`, `stage`, `duration_ms`, `error_code`

### 11.3 Frontend Logging

- User-facing toasts for failures  
- `console` only in development; do not log PII  

---

## 12. Error Handling

### 12.1 Rules

1. Map domain failures to stable **error codes** (see API + agent specs).  
2. Raise typed domain errors in services/agents; translate to HTTP in API middleware.  
3. Never expose stack traces to clients in production responses.  
4. Do not swallow exceptions without logging.  
5. Retries follow agent retry classes (R0–R4); do not invent infinite loops.  
6. Partial success uses warnings arrays — do not pretend full success.  

### 12.2 HTTP Envelope

All JSON errors use the API error envelope (`success: false`, `error.code`, `error.message`, `error.details`, `meta.request_id`).

### 12.3 Forbidden Patterns

```python
# FORBIDDEN
except Exception:
    pass

# FORBIDDEN in renderer
call_script_agent_to_fix_missing_text()
```

---

## 13. Validation

| Boundary | Validate |
|----------|----------|
| API ingress | Pydantic request models |
| Agent egress | Artifact schema + semantic checks |
| DSL compile | `PRESENTATION_DSL` validation rules |
| Timeline bind | Track overlaps, fps match, durations |
| Render gate | Render-ready checklist |
| Upload | Type, size, path safety |

**Fail fast** at the earliest boundary.  
Do not trust LLM output without schema validation.  
Repair retries are bounded and logged.

---

## 14. Configuration Management

1. Use a single settings object (`app/core/config.py`) loaded from environment + `.env` (never commit secrets).  
2. Provide `.env.example` with safe defaults.  
3. Distinguish:  
   - **App config** (ports, data root, concurrency)  
   - **Project settings** (theme, voice, quality) stored in DB  
4. Paths must resolve under configured data roots (jail).  
5. Feature flags for experimental plugins/online features default **off**.  
6. No hardcoded machine-specific absolute paths in source.  

---

## 15. Dependency Injection

1. Define ports in `app/ports/`.  
2. Implement adapters in `app/adapters/`.  
3. Wire in `app/core/di.py` (composition root) and FastAPI `deps`.  
4. Agents/engines receive dependencies via constructor/parameters — not global imports of adapters.  
5. Tests inject fakes/mocks.  
6. Do not instantiate `OllamaLLM()` deep inside random helpers.

```text
Correct:  ScriptAgent(llm: LLMPort, storage: StoragePort)
Wrong:    from app.adapters.ollama_llm import OllamaLLM  # inside agent module body as hard dep
```

---

## 16. Testing Rules

1. New behavior requires tests appropriate to risk (`DEVELOPMENT_GUIDE.md` §9).  
2. Engines: deterministic unit tests; no network.  
3. Agents: contract tests with mocked `LLMPort` / `TTSPort`.  
4. API: integration tests for status codes + envelopes.  
5. Name tests after behavior: `test_bind_timeline_requires_audio_when_voice_enabled`.  
6. Fixtures in `backend/tests/fixtures/`; do not use real user `data/projects`.  
7. Golden files change only intentionally; explain in PR.  
8. Do not hit real Ollama in unit CI.  
9. Flaky tests are bugs — fix or quarantine with issue.  
10. Coverage is a guide, not a vanity metric; prefer critical-path coverage.

---

## 17. Performance Rules

1. Design for **16GB RAM** and CPU LLM.  
2. Default concurrency: one heavy pipeline job.  
3. Unload large models between stage groups when feasible.  
4. Prefer 720p draft for iteration encodes.  
5. Stream/write artifacts incrementally; avoid holding full frame buffers for entire video.  
6. Cache by input hash + agent/engine versions.  
7. No N+1 DB patterns in list endpoints — use explicit queries.  
8. Frontend: poll with backoff; do not hammer progress endpoints.  
9. Profile before micro-optimizing.  
10. Do not add parallelism that risks OOM on target hardware.

---

## 18. Architecture Rules

These are **non-negotiable** coding standards:

| ID | Rule |
|----|------|
| A1 | Agents communicate only via JSON artifacts / orchestrator state refs |
| A2 | Agents must not invoke other agents directly |
| A3 | Rendering consumes Presentation DSL + timeline + media only — never AI agents |
| A4 | Frontend talks only to `/api/v1` — never models or `data/` FS directly |
| A5 | Engines must not import `app.agents` |
| A6 | API routes stay thin — business logic in services |
| A7 | Presentation DSL is the visual/motion hub language |
| A8 | Core path remains offline and free of paid APIs |
| A9 | New top-level folders require ADR + `FOLDER_STRUCTURE` update |
| A10 | Dependency direction follows `FOLDER_STRUCTURE.md` matrix |

Violations are **blocking** on review.

---

## 19. Code Review Checklist

Reviewers and authors must verify:

### Correctness & Contracts
- [ ] Matches accepted specs / ADR  
- [ ] Schemas/API/DSL updated if needed  
- [ ] Validation present at boundaries  
- [ ] Error codes stable and documented  

### Architecture
- [ ] Correct layer/folder  
- [ ] No agent↔agent calls  
- [ ] Renderer AI-free  
- [ ] Frontend API-only  
- [ ] DI used for ports/adapters  

### Quality
- [ ] Naming matches this document  
- [ ] No secrets or `data/` artifacts committed  
- [ ] Logging adequate; no sensitive body dumps  
- [ ] Tests added/updated  
- [ ] Performance risk considered (RAM/CPU)  

### PR Hygiene
- [ ] Scope focused  
- [ ] Checklist in PR body  
- [ ] Clear summary of why  

---

## 20. Formatting & Tooling

| Area | Tool |
|------|------|
| Python format/lint | Ruff (or Black + Ruff) |
| Python types | mypy/pyright |
| TS format | Prettier |
| TS lint | ESLint |
| Pre-commit | Optional but recommended |
| CI | Lint + types + tests gate `main` |

Do not disable linters file-wide without justification. Prefer surgical ignores with comments.

---

## 21. Security & Privacy Coding Rules

1. Jail all project paths under storage root.  
2. Validate upload content types and sizes.  
3. Never commit `.env`, keys, user documents, or model weights.  
4. Plugins default deny; permissions explicit.  
5. Treat uploaded files as untrusted content.  
6. Do not send document contents to third-party APIs in core code.  

---

## Closing Statement

Coding standards keep ExplainX coherent as many agents and engines evolve.

```
Name clearly.
Validate boundaries.
Inject dependencies.
Log structure.
Respect layers.
Test what you change.
```

If a shortcut violates architecture rules, it is not a shortcut — it is technical debt.

---

*End of CODING_STANDARDS.md*  
*ExplainX Engineering — Same Rules. Every File.*
