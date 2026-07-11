# ExplainX — Folder Structure

**Document Status:** Canonical Repository Layout Reference  
**Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Companions:**  
[`PROJECT_CONSTITUTION.md`](./PROJECT_CONSTITUTION.md) ·  
[`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md) ·  
[`AGENT_SPECIFICATIONS.md`](./AGENT_SPECIFICATIONS.md) ·  
[`PRESENTATION_DSL.md`](./PRESENTATION_DSL.md) ·  
[`DATABASE_DESIGN.md`](./DATABASE_DESIGN.md) ·  
[`API_SPECIFICATION.md`](./API_SPECIFICATION.md)  

> **Authority:** This document defines the **final target folder structure** for ExplainX.  
> New code and Cursor prompts MUST place files according to these rules.  
> If a feature has no home here, amend this document (via ADR) before inventing a new top-level tree.

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Repository Topology at a Glance](#2-repository-topology-at-a-glance)
3. [Complete Tree](#3-complete-tree)
4. [Top-Level Folders](#4-top-level-folders)
5. [Frontend (`apps/web`)](#5-frontend-appsweb)
6. [Backend (`backend`)](#6-backend-backend)
7. [Agents Module](#7-agents-module)
8. [Presentation Engine](#8-presentation-engine)
9. [Animation Engine](#9-animation-engine)
10. [Rendering Engine](#10-rendering-engine)
11. [Assets](#11-assets)
12. [Models](#12-models)
13. [Outputs & Projects (Runtime Data)](#13-outputs--projects-runtime-data)
14. [Tests](#14-tests)
15. [Documentation](#15-documentation)
16. [Dependency Rules](#16-dependency-rules)
17. [What Should Never Happen](#17-what-should-never-happen)
18. [Import / Boundary Enforcement](#18-import--boundary-enforcement)
19. [Future Scalability](#19-future-scalability)
20. [Onboarding Map: Where Do I Put X?](#20-onboarding-map-where-do-i-put-x)
21. [Appendix: Module Responsibility Matrix](#21-appendix-module-responsibility-matrix)

---

## 1. Purpose

A production codebase needs a structure that:

- mirrors the layered architecture  
- makes illegal dependencies obvious  
- keeps AI agents, engines, and UI separable  
- separates **source** from **runtime data** (projects, models, outputs)  
- scales to plugins, cloud workers, and monorepo packages later  

This document is the map of that structure.

---

## 2. Repository Topology at a Glance

```
ExplainX/                          ← repository root (source of truth)
├── apps/web/                      ← Frontend (Next.js)
├── backend/                       ← Backend (FastAPI + agents + engines)
├── packages/                      ← Optional shared packages (types/config)
├── assets/                        ← Bundled free visual assets (source-controlled or LFS)
├── docs/                          ← Architecture & product documentation
├── tools/                         ← Dev/lint/codegen/doctor helpers
├── data/                          ← RUNTIME (gitignored): DB, projects, outputs, local models
├── tests/                         ← Cross-cutting / e2e fixtures (optional top-level)
└── scripts/                       ← Install, download-models, release helpers
```

**Critical split:**

| Tree | Committed? | Purpose |
|------|------------|---------|
| `apps/`, `backend/`, `docs/`, `assets/` | Yes (mostly) | Product source |
| `data/` | No | User projects, DB, caches, downloaded models |
| `backend/tests/`, `apps/web` tests | Yes | Automated tests |

---

## 3. Complete Tree

```
ExplainX/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── package.json                      # optional workspace root
├── pnpm-workspace.yaml               # optional
│
├── docs/
│   ├── PROJECT_CONSTITUTION.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── PRESENTATION_DSL.md
│   ├── AGENT_SPECIFICATIONS.md
│   ├── DATABASE_DESIGN.md
│   ├── API_SPECIFICATION.md
│   ├── FOLDER_STRUCTURE.md           # ← this file
│   ├── ADRs/
│   │   └── .gitkeep
│   ├── schemas/                      # JSON Schema mirrors of DSL/API (optional)
│   └── diagrams/                     # exported architecture diagrams (optional)
│
├── apps/
│   └── web/                          # Next.js frontend
│       ├── package.json
│       ├── tsconfig.json
│       ├── next.config.ts
│       ├── tailwind.config.ts
│       ├── public/
│       ├── app/                      # App Router
│       ├── components/
│       ├── features/
│       ├── lib/
│       ├── styles/
│       ├── hooks/
│       ├── types/
│       └── tests/
│
├── packages/                         # shared monorepo libs (optional V1, recommended)
│   ├── shared-types/                 # OpenAPI-generated or hand DTOs
│   └── eslint-config/
│
├── backend/
│   ├── pyproject.toml
│   ├── README.md
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI entry
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/                   # Pydantic / domain schemas (not ML weights)
│   │   ├── db/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── orchestration/
│   │   ├── agents/
│   │   ├── engines/
│   │   ├── ports/
│   │   ├── adapters/
│   │   ├── themes/
│   │   ├── plugins/
│   │   └── workers/
│   ├── tests/
│   └── scripts/
│
├── assets/                           # visual packs shipped with product
│   ├── icons/
│   │   ├── lucide/
│   │   ├── heroicons/
│   │   └── openmoji/
│   ├── illustrations/
│   │   └── undraw/
│   ├── fonts/
│   └── templates/                    # SVG diagram templates
│
├── tools/
│   ├── lint/
│   ├── codegen/
│   └── check_boundaries.py           # import boundary linter (future)
│
├── scripts/
│   ├── download_models.md            # instructions (or .py later)
│   └── doctor.md
│
└── data/                             # GITIGNORED runtime root
    ├── explainx.db
    ├── projects/
    ├── outputs/                      # optional global output mirror
    ├── models/
    ├── cache/
    ├── logs/
    └── backups/
```

---

## 4. Top-Level Folders

| Folder | Why it exists |
|--------|----------------|
| `apps/` | Hosts user-facing applications; keeps UI deployable/versionable separately from Python |
| `backend/` | All server-side generation, orchestration, persistence adapters |
| `packages/` | Shared contracts without circular app imports |
| `assets/` | Free, redistributable visual resources for diagram-first rendering |
| `docs/` | Permanent engineering constitution and specs |
| `tools/` | Developer automation; not production runtime |
| `scripts/` | Operator/setup entrypoints |
| `data/` | Mutable runtime state isolated from source control |

---

## 5. Frontend (`apps/web`)

### 5.1 Purpose

Provide the operator UI: upload, configure, monitor jobs, download exports.  
**Frontend never loads Ollama, Piper, or FFmpeg directly.**

### 5.2 Folder Map

```
apps/web/
├── app/                         # Next.js routes (pages)
│   ├── layout.tsx
│   ├── page.tsx                 # library / home
│   ├── projects/
│   │   ├── page.tsx
│   │   └── [projectId]/
│   │       ├── page.tsx
│   │       └── export/page.tsx
│   ├── settings/page.tsx
│   └── api/                     # ONLY BFF proxies if needed — prefer direct backend calls
├── components/                  # shared presentational UI
│   ├── ui/
│   ├── layout/
│   └── feedback/                # toasts, progress
├── features/                    # feature-sliced UI modules
│   ├── projects/
│   ├── upload/
│   ├── jobs/
│   ├── export/
│   └── settings/
├── lib/
│   ├── api/                     # typed API client for /api/v1
│   ├── config.ts
│   └── utils/
├── hooks/
├── styles/
├── types/                       # UI types; prefer packages/shared-types
├── public/                      # static images for UI chrome (not video assets)
└── tests/
```

### 5.3 Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `app/` | Routing & page composition |
| `components/` | Reusable UI primitives |
| `features/` | Domain UI (project list, job progress) |
| `lib/api/` | HTTP client to FastAPI only |
| `hooks/` | Client state/effects around API |

### 5.4 Why These Folders Exist

- **`features/`** prevents a dump of unrelated components  
- **`lib/api/`** centralizes endpoint contracts from `API_SPECIFICATION.md`  
- **`public/`** stays small; educational media lives in backend `data/projects`  

### 5.5 Frontend Dependency Rules

**Allowed to import:**

- other `apps/web` modules  
- `packages/shared-types`  

**Forbidden:**

- `backend/**`  
- direct filesystem project paths  
- model runtimes  
- Presentation DSL compilers  

---

## 6. Backend (`backend`)

### 6.1 Purpose

Host the API, orchestrator, agents, engines, ports/adapters, and DB access.

### 6.2 Tree (Detailed)

```
backend/
├── pyproject.toml
├── app/
│   ├── main.py
│   │
│   ├── api/                              # API Layer
│   │   ├── router.py
│   │   ├── deps.py                       # DI for routes
│   │   ├── middleware/
│   │   │   ├── request_id.py
│   │   │   └── error_handler.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── projects.py
│   │       ├── documents.py
│   │       ├── generate.py
│   │       ├── jobs.py
│   │       ├── render.py
│   │       ├── export.py
│   │       ├── themes.py
│   │       ├── voices.py
│   │       ├── languages.py
│   │       ├── settings.py
│   │       └── plugins.py
│   │
│   ├── core/                             # cross-cutting app core
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── errors.py
│   │   ├── enums.py
│   │   └── di.py                         # composition root
│   │
│   ├── models/                           # Pydantic schemas / domain DTOs
│   │   ├── api/                          # request/response models
│   │   ├── artifacts/                    # agent artifact schemas
│   │   ├── dsl/                          # Presentation DSL models
│   │   ├── jobs.py
│   │   └── project.py
│   │
│   ├── db/
│   │   ├── session.py
│   │   ├── schema.sql
│   │   └── migrations/
│   │
│   ├── repositories/                     # Storage Port implementations (SQL)
│   │   ├── project_repository.py
│   │   ├── job_repository.py
│   │   ├── scene_repository.py
│   │   ├── asset_repository.py
│   │   └── ...
│   │
│   ├── services/                         # application services (use-cases)
│   │   ├── project_service.py
│   │   ├── job_service.py
│   │   ├── export_service.py
│   │   ├── output_manager.py
│   │   └── doctor_service.py
│   │
│   ├── orchestration/                    # LangGraph wiring
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── nodes.py
│   │   ├── checkpoints.py
│   │   └── cache.py
│   │
│   ├── agents/                           # Agent Layer (see §7)
│   │
│   ├── engines/                          # Deterministic engines (see §8–10)
│   │   ├── presentation/
│   │   ├── animation/
│   │   ├── camera/
│   │   ├── timeline/
│   │   └── render/
│   │
│   ├── ports/                            # interfaces / protocols
│   │   ├── llm.py
│   │   ├── tts.py
│   │   ├── translator.py
│   │   ├── renderer.py
│   │   ├── storage.py
│   │   └── clock.py
│   │
│   ├── adapters/                         # concrete backends
│   │   ├── ollama_llm.py
│   │   ├── piper_tts.py
│   │   ├── indictrans2.py
│   │   ├── whisper_cpp.py
│   │   ├── ffmpeg_renderer.py
│   │   ├── sqlite_storage.py
│   │   └── fs_project_store.py
│   │
│   ├── themes/                           # theme packs (code + tokens)
│   │   ├── notebooklm/
│   │   ├── whiteboard/
│   │   ├── corporate/
│   │   ├── minimal/
│   │   ├── comic/
│   │   └── dark/
│   │
│   ├── plugins/
│   │   ├── registry.py
│   │   ├── loader.py
│   │   ├── api.py
│   │   └── bundled/                      # optional sample plugins
│   │
│   └── workers/
│       ├── pipeline_worker.py
│       └── render_worker.py
│
├── tests/                                # backend tests (see §14)
└── scripts/
    ├── download_models.py
    └── seed_themes.py
```

### 6.3 Why Backend Subfolders Exist

| Folder | Why |
|--------|-----|
| `api/` | HTTP boundary only; thin handlers |
| `services/` | Use-cases / transactions; orchestrates repos + jobs |
| `orchestration/` | Graph topology, not agent internals |
| `agents/` | One folder per agent responsibility |
| `engines/` | Deterministic, LLM-free core where possible |
| `ports/` | Swappable dependencies (SQLite→Postgres, Piper→other TTS) |
| `adapters/` | Side-effecting integrations |
| `repositories/` | SQL/FS persistence details |
| `themes/` | Theme packs versioned with backend |
| `plugins/` | Extension loading without core forks |
| `workers/` | Async process entrypoints |

### 6.4 Naming Clarification: `app/models`

In backend code, **`models/` means Pydantic/domain schemas**, not ML weight files.  
ML weights live under runtime `data/models/` (§12).

---

## 7. Agents Module

### 7.1 Path

```
backend/app/agents/
├── __init__.py
├── base.py                      # shared Agent protocol, lifecycle helpers
├── registry.py                  # agent name → callable
├── parser_agent.py
├── cleaning_agent.py
├── structure_agent.py
├── knowledge_agent.py
├── topic_classification_agent.py
├── difficulty_agent.py
├── explanation_strategy_agent.py
├── script_agent.py
├── scene_planner_agent.py
├── metadata_agent.py
├── visual_planning_agent.py
├── layout_planner_agent.py
├── theme_planner_agent.py
├── asset_agent.py
├── animation_agent.py
├── camera_agent.py
├── timeline_agent.py
├── translation_agent.py
├── voice_agent.py
├── subtitle_agent.py
├── rendering_agent.py
├── project_manager_agent.py
└── prompts/                     # versioned prompt templates
    ├── knowledge_v1.md
    ├── script_v1.md
    └── ...
```

### 7.2 Why This Folder Exists

- Makes the multi-agent system discoverable  
- Keeps prompts versioned beside agents  
- Prevents prompts from being buried in engines  

### 7.3 Agent Module Rules

| Rule | Detail |
|------|--------|
| One primary file per agent | Extra helpers allowed as `agents/_lib/...` if shared carefully |
| No agent-to-agent imports for invocation | Orchestrator calls agents |
| May call engines & ports | Via DI, not global singletons |
| Read/write artifacts via Storage Port | No ad-hoc absolute paths |

### 7.4 Optional Subpack for Shared Agent Utils

```
backend/app/agents/_lib/
├── json_repair.py
├── validators.py
└── hashing.py
```

`_lib` must not import specific agents (avoid cycles).

---

## 8. Presentation Engine

### 8.1 Path

```
backend/app/engines/presentation/
├── __init__.py
├── compiler.py                  # plans → Presentation DSL
├── scene_graph.py               # scene graph build
├── layout_math.py
├── theme_apply.py
├── procedural/                  # array/chart/graph SVG builders
│   ├── arrays.py
│   ├── charts.py
│   ├── graphs.py
│   └── orbits.py
└── validate_dsl.py
```

### 8.2 Why It Exists

Centralizes deterministic compilation of the official language (`PRESENTATION_DSL.md`).  
LLM planning stays in agents; geometry/token application stays here.

### 8.3 Dependencies

**May use:** DSL schemas (`app/models/dsl`), themes, asset path resolvers (via ports)  
**Must not use:** Ollama, agent modules, FastAPI routes  

---

## 9. Animation Engine

### 9.1 Path

```
backend/app/engines/animation/
├── __init__.py
├── presets.py                   # fade, move_to, highlight_set, ...
├── keyframes.py
├── easing.py
└── compile_motion.py

backend/app/engines/camera/
├── __init__.py
├── framing.py
├── limits.py
└── compile_camera.py

backend/app/engines/timeline/
├── __init__.py
├── binder.py                    # absolute timeline bind
├── tracks.py
└── validate_timeline.py
```

### 9.2 Why Split `animation` / `camera` / `timeline`

- Different reasons to change  
- Timeline Agent calls `timeline` binder  
- Animation/Camera agents produce plans consumed by these engines  

### 9.3 Dependencies

**May use:** DSL models, pure math  
**Must not use:** agents, LLM ports, FFmpeg  

---

## 10. Rendering Engine

### 10.1 Path

```
backend/app/engines/render/
├── __init__.py
├── frame_composer.py            # rasterize scene graph @ time t
├── encoder.py                   # FFmpeg interface wrapper used by adapter
├── thumbnail.py
├── mux.py
└── quality_profiles.py
```

### 10.2 Why It Exists

Pixels and encode settings live here. The **Rendering Agent** is a thin façade that validates render-ready inputs and calls this engine via ports/adapters.

### 10.3 Dependencies

**May use:** bound timeline + DSL + resolved asset files  
**Must not use:** agents, LLM, script regeneration  

Adapter `adapters/ffmpeg_renderer.py` owns process calls to FFmpeg.

---

## 11. Assets

### 11.1 Source Assets (`/assets`)

```
assets/
├── icons/
│   ├── lucide/
│   ├── heroicons/
│   └── openmoji/
├── illustrations/
│   └── undraw/
├── fonts/
└── templates/
```

| Folder | Why |
|--------|-----|
| `icons/` | Diagram-first iconography |
| `illustrations/` | Occasional metaphor support (Undraw) |
| `fonts/` | Theme font files (license-clean) |
| `templates/` | Reusable SVG scaffolds |

### 11.2 Runtime Resolved Assets

Project-specific resolved copies or generated procedural SVGs may appear under:

```
data/projects/{project_id}/artifacts/vN/assets/
```

### 11.3 Rules

- Prefer referencing pack keys + hashing over duplicating entire packs per project  
- No paid asset packs in core  
- Generative images (future plugins) write under project artifacts, not `/assets`

---

## 12. Models

### 12.1 Runtime Models Root

```
data/models/                     # GITIGNORED
├── ollama/                      # or rely on Ollama's default store; document path in settings
├── piper/
│   └── voices/
├── indictrans2/
└── whispercpp/
```

### 12.2 Why Models Are Outside `backend/`

| Reason | Detail |
|--------|--------|
| Size | Multi-GB; must not live in git |
| Machine-specific | Paths differ per install |
| Offline install step | `scripts/download_models` populates this tree |
| Security/privacy | User-local artifacts |

### 12.3 What Is in Repo Instead

- Adapter code (`adapters/ollama_llm.py`)  
- Version pins / recommended tags in docs & settings defaults  
- Doctor checks that validate presence  

**Never** commit weight binaries into `backend/app/models` (that folder is for Pydantic schemas).

---

## 13. Outputs & Projects (Runtime Data)

### 13.1 Projects

```
data/projects/{project_id}/
├── source/
├── artifacts/
│   └── v{N}/
│       ├── raw_document.json
│       ├── clean_document.json
│       ├── knowledge.json
│       ├── script.json
│       ├── scene_plan.json
│       ├── visual_plan.json
│       ├── presentation.dsl.json
│       ├── animation_plan.json
│       ├── camera_plan.json
│       ├── timeline.json
│       ├── audio/
│       ├── subtitles/
│       └── assets/
├── export/
│   ├── video.mp4
│   ├── narration.wav
│   ├── subtitles.srt
│   ├── subtitles.vtt
│   ├── thumb.jpg
│   ├── metadata.json
│   └── package.zip
├── logs/
└── project.json                  # optional debug mirror
```

### 13.2 Outputs

| Location | Role |
|----------|------|
| `data/projects/.../export/` | **Canonical** per-project outputs |
| `data/outputs/` | Optional global shortcut/mirror for tooling — not required |

### 13.3 Why Runtime Data Is Separated

- Clean git status  
- Easy backup (`DATABASE_DESIGN.md`)  
- Multiple checkouts can share one `EXPLAINX_DATA_ROOT`  

### 13.4 Database File

```
data/explainx.db
```

Configured via settings; never stored under `apps/web`.

---

## 14. Tests

### 14.1 Backend Tests

```
backend/tests/
├── unit/
│   ├── engines/
│   ├── repositories/
│   └── services/
├── agents/
│   ├── test_script_agent_contract.py
│   └── ...                      # LLM mocked
├── integration/
│   ├── test_pipeline_tiny_md.py
│   └── test_api_projects.py
├── golden/
│   ├── dsl/
│   └── timelines/
└── fixtures/
    ├── documents/
    │   ├── binary_search.md
    │   ├── photosynthesis.md
    │   └── networking.md
    └── dsl/
```

### 14.2 Frontend Tests

```
apps/web/tests/
├── unit/
└── e2e/                         # optional Playwright
```

### 14.3 Why Tests Mirror Architecture

- Engine tests do not need Ollama  
- Agent contract tests assert JSON schemas  
- Golden DSL tests lock renderer inputs  

### 14.4 Rule

Fixtures for educational samples live in `tests/fixtures`, not in `data/projects` (runtime).

---

## 15. Documentation

```
docs/
├── PROJECT_CONSTITUTION.md
├── SYSTEM_ARCHITECTURE.md
├── PRESENTATION_DSL.md
├── AGENT_SPECIFICATIONS.md
├── DATABASE_DESIGN.md
├── API_SPECIFICATION.md
├── FOLDER_STRUCTURE.md
├── ADRs/
├── schemas/
└── diagrams/
```

| Item | Why |
|------|-----|
| Specs at docs root | Discoverable permanent references |
| `ADRs/` | Record architectural decisions & amendments |
| `schemas/` | Optional machine-readable DSL/API schemas |
| `diagrams/` | Exported visuals for onboarding |

**Rule:** Do not put architecture docs only in chat history — update `docs/`.

---

## 16. Dependency Rules

### 16.1 Layer Dependency Direction

```
apps/web
   │  (HTTP only)
   ▼
backend/app/api
   ▼
backend/app/services
   ▼
backend/app/orchestration ──► backend/app/agents
   │                              │
   │                              ├► ports
   │                              └► engines
   ▼
repositories / adapters
   ▼
SQLite + filesystem (data/)
```

### 16.2 Allowed Dependency Matrix

| From ↓ \ To → | api | services | orchestration | agents | engines | ports | adapters | repositories | web |
|---------------|-----|----------|---------------|--------|---------|-------|----------|--------------|-----|
| **web** | via HTTP | — | — | — | — | — | — | — | self |
| **api** | self | yes | no* | no | no | yes (deps) | no | no | no |
| **services** | no | self | yes | no | no | yes | no | yes | no |
| **orchestration** | no | limited | self | yes | yes | yes | no | yes | no |
| **agents** | no | no | no | self/`_lib` | yes | yes | no | no** | no |
| **engines** | no | no | no | no | self | yes (narrow) | no | no | no |
| **adapters** | no | no | no | no | maybe | implements | self | maybe | no |
| **repositories** | no | no | no | no | no | implements storage | no | self | no |

\* API should not import graph internals deeply; call `JobService.start...`.  
\*\* Agents use Storage **Port**, not repositories directly (preferred).

### 16.3 Composition Root

Only `backend/app/core/di.py` (and `main.py` / workers) wire adapters into ports.

---

## 17. What Should Never Happen

These are **hard architectural prohibitions**. Violations fail review.

### 17.1 Agent Isolation

| Never | Why |
|-------|-----|
| Agents directly calling other agents | Breaks orchestration, retries, isolation |
| Agents mutating another agent's artifact in place | Breaks caching & audit trail |
| Shared mutable global pedagogy state | Hidden coupling |

**Correct:** Orchestrator sequences agents; artifacts pass through storage/state refs.

### 17.2 Renderer Purity

| Never | Why |
|-------|-----|
| Rendering engine talking to AI agents | Non-deterministic, untestable, offline-hostile |
| Renderer inventing scenes when DSL incomplete | Hides upstream bugs |
| FFmpeg invoked from Script/Knowledge agents | Wrong layer |

**Correct:** Renderer consumes Presentation DSL + Timeline + media paths only.

### 17.3 Frontend Boundaries

| Never | Why |
|-------|-----|
| Frontend directly accessing models (Ollama/Piper) | Bypasses jobs, security, progress, logging |
| Frontend reading `data/projects` via FS APIs | Breaks packaging; use export endpoints |
| Frontend importing backend Python | Impossible/wrong; use HTTP |

### 17.4 DSL & Engines

| Never | Why |
|-------|-----|
| Engines importing `agents.*` | Cycle & layer violation |
| Putting Presentation DSL compile logic in API routes | Unreusable, untested |
| Storing MP4s inside `apps/web/public` as the pipeline output | Wrong lifetime & size |

### 17.5 Repository Hygiene

| Never | Why |
|-------|-----|
| Committing `data/projects`, DB, or model weights | Repo bloat & privacy risk |
| Creating random top-level `misc/`, `newcode/`, `temp_agents/` | Structure entropy |
| Duplicating theme packs in three places without registry | Drift |

### 17.6 Plugin Safety

| Never | Why |
|-------|-----|
| Plugins patching core agents silently | Unreviewable behavior |
| Core requiring a plugin to render a basic diagram | Breaks offline core promise |

---

## 18. Import / Boundary Enforcement

### 18.1 Recommended Enforcement (Future Implementation)

- Python: `import-linter` or custom `tools/check_boundaries.py` in CI  
- TypeScript: ESLint `no-restricted-imports` blocking `backend`  

### 18.2 Example Forbidden Import Patterns

```text
FORBIDDEN: backend.app.engines.render → backend.app.agents
FORBIDDEN: backend.app.agents.script_agent → backend.app.agents.scene_planner_agent
FORBIDDEN: apps.web → backend.app
FORBIDDEN: backend.app.api.routes → backend.app.adapters.ollama_llm  (use DI)
```

---

## 19. Future Scalability

### 19.1 Monorepo Growth

```
apps/
  web/
  desktop/                 # future Tauri/Electron shell
  admin/                   # future

backend/                   # may split later into:
  # services kept until pain appears

packages/
  shared-types/
  dsl-schema/
  api-client/
```

### 19.2 Worker Split

```
backend/app/workers/
  pipeline_worker.py       # agents + engines (CPU)
  render_worker.py         # encode-only

# Future separate deployables:
apps/worker-pipeline/
apps/worker-render/
```

Same folders’ **code modules** move behind package boundaries without changing agent contracts.

### 19.3 Plugin Packages

```
plugins/
  explainx-plugin-flux/
  explainx-plugin-watercolor-theme/
```

Loaded via `backend/app/plugins`; may live outside core repo.

### 19.4 Cloud Rendering (V4)

Add adapter:

```
backend/app/adapters/cloud_renderer.py
```

No need to move DSL out of `engines/presentation`.  
Export a timeline bundle from `data/projects/...` to remote render; results return to `export/`.

### 19.5 PostgreSQL

Replace:

```
adapters/sqlite_storage.py
```

with:

```
adapters/postgres_storage.py
```

Repositories keep the same interfaces; folder layout unchanged.

### 19.6 Collaborative Editing (V5)

Possible additions:

```
backend/app/services/collab_service.py
apps/web/features/collab/
```

Still no frontend→model calls; still no renderer→agent calls.

### 19.7 Scalability Principle

> Scale by **adding adapters, workers, and packages**, not by breaking folder dependency direction.

---

## 20. Onboarding Map: Where Do I Put X?

| If you are building… | Put it in… |
|----------------------|------------|
| A new page/button | `apps/web/features/...` + `app/` route |
| A new REST endpoint | `backend/app/api/routes/` + service method |
| A new agent | `backend/app/agents/` + orchestration edge + `AGENT_SPECIFICATIONS.md` |
| Diagram geometry | `backend/app/engines/presentation/` |
| Motion preset | `backend/app/engines/animation/` |
| Encode profile | `backend/app/engines/render/` |
| DB query | `backend/app/repositories/` |
| Ollama call | `backend/app/adapters/ollama_llm.py` via `ports/llm.py` |
| Theme pack | `backend/app/themes/{id}/` + DB seed |
| Icon pack files | `/assets/icons/...` |
| User project MP4 | `data/projects/{id}/export/` |
| Architecture change | `docs/` + `docs/ADRs/` |
| Contract test for agent | `backend/tests/agents/` |
| Golden DSL fixture | `backend/tests/golden/dsl/` |

---

## 21. Appendix: Module Responsibility Matrix

| Module path | Layer | Owns | Does not own |
|-------------|-------|------|--------------|
| `apps/web` | Presentation | UX | AI, render |
| `backend/app/api` | API | HTTP contract | Business deep logic |
| `backend/app/services` | Application | Use-cases, jobs | Pixel math |
| `backend/app/orchestration` | Control | Graph, checkpoints | Theme tokens |
| `backend/app/agents` | Agent | Planning transforms | FFmpeg |
| `backend/app/engines/presentation` | Engine | DSL compile | Prompts |
| `backend/app/engines/animation` | Engine | Motion compile | TTS |
| `backend/app/engines/timeline` | Engine | Absolute bind | LLM |
| `backend/app/engines/render` | Engine | Frames/encode | Scene pedagogy |
| `backend/app/ports` | Interface | Contracts | Implementations |
| `backend/app/adapters` | Infrastructure | External tools | Domain rules |
| `backend/app/repositories` | Infrastructure | Persistence | Agent prompts |
| `assets/` | Resources | Visual packs | Projects |
| `data/` | Runtime | DB/projects/models/outputs | Source code |
| `docs/` | Knowledge | Specs | Runtime |

---

## Closing Statement

ExplainX’s folder structure is the **physical embodiment** of its architecture:

```
UI → API → Services → Orchestrator → Agents → Engines
                         │              │
                         └──── Ports ───┴──► Adapters → Data
```

Keep runtime data in `data/`.  
Keep intelligence in `agents/`.  
Keep determinism in `engines/`.  
Keep the frontend on HTTP.  
Keep the renderer on the Presentation DSL.

If a change fights this tree, the change is probably in the wrong layer.

---

*End of FOLDER_STRUCTURE.md*  
*ExplainX Engineering — Put Everything in Its Place. Keep the Edges Clean.*
