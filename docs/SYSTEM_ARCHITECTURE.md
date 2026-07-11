# ExplainX — System Architecture

**Document Status:** Canonical Software Architecture Reference  
**Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Companion Document:** [`docs/PROJECT_CONSTITUTION.md`](./PROJECT_CONSTITUTION.md)  
**Audience:** Engineers, architects, and future contributors  

> **Authority:** This document describes *how* ExplainX is structured as a software system.  
> The constitution defines *what* the product is and the agent/product rules.  
> If product philosophy conflicts with informal discussion, the constitution wins.  
> If component interaction or layering conflicts with informal discussion, **this document wins** until amended.

---

## Table of Contents

1. [Purpose of This Document](#1-purpose-of-this-document)
2. [Architectural Thesis](#2-architectural-thesis)
3. [Why ExplainX Is an AI Presentation Engine](#3-why-explainx-is-an-ai-presentation-engine)
4. [System Context](#4-system-context)
5. [Complete Architecture Diagram](#5-complete-architecture-diagram)
6. [System Layers](#6-system-layers)
7. [Component Responsibilities](#7-component-responsibilities)
8. [Data Flow](#8-data-flow)
9. [Cross-Cutting Runtime Model](#9-cross-cutting-runtime-model)
10. [Design Principles](#10-design-principles)
11. [Interface & Contract Architecture](#11-interface--contract-architecture)
12. [Failure Recovery](#12-failure-recovery)
13. [Logging Architecture](#13-logging-architecture)
14. [Performance Architecture](#14-performance-architecture)
15. [Scalability](#15-scalability)
16. [Security & Isolation Boundaries](#16-security--isolation-boundaries)
17. [Deployment Topology](#17-deployment-topology)
18. [Developer Onboarding Map](#18-developer-onboarding-map)
19. [Architecture Decision Summary](#19-architecture-decision-summary)
20. [Appendix: Sequence & State Diagrams](#20-appendix-sequence--state-diagrams)

---

## 1. Purpose of This Document

This document is the **software engineering view** of ExplainX.

A new developer should be able to answer all of the following after reading it:

- What are the logical layers and how do they depend on each other?
- Where does AI end and deterministic rendering begin?
- How does a PDF become an MP4?
- Which component owns Presentation DSL, timelines, audio, and storage?
- How do we test, cache, recover, log, and later scale?

This is **architecture only**. It does not implement application code.

---

## 2. Architectural Thesis

ExplainX is built on one irreversible architectural bet:

> **Language models plan and explain. Deterministic engines compose and render.**

That bet produces a pipeline of durable intermediate artifacts:

```
Document
   ↓
Knowledge
   ↓
Presentation DSL
   ↓
Scene Graph
   ↓
Animation Timeline
   ↓
Renderer
   ↓
Video
```

### 2.1 Implications

| Concern | Architectural Consequence |
|---------|---------------------------|
| Maintainability | Failures localize to one stage/artifact |
| Testing | Engines tested without LLMs; agents tested with mocked ports |
| Scalability | Later swap render backends without rewriting knowledge agents |
| Performance | Cache upstream artifacts; only re-run dirty stages |
| Offline execution | Local models + local binaries; no cloud required for core path |

### 2.2 Relationship to the Constitution

| Document | Answers |
|----------|---------|
| `PROJECT_CONSTITUTION.md` | Product vision, agent catalog, constraints, themes, roadmap |
| `SYSTEM_ARCHITECTURE.md` | Layers, interactions, runtime, recovery, logging, performance, scale |

Agents listed in the constitution are **logical workers inside the Agent Layer**. Engines listed here are **deterministic subsystems** that agents call through ports.

---

## 3. Why ExplainX Is an AI Presentation Engine

### 3.1 Not a Traditional AI Video Generator

Traditional AI video systems (Sora-like, Veo-like, diffusion video) typically:

- Map a prompt → latent video frames  
- Optimize for cinematic plausibility  
- Lack stable intermediate teaching structure  
- Are expensive, cloud-heavy, and hard to debug scene-by-scene  
- Struggle with precise labels, algorithmic state, and consistent iconography  

ExplainX deliberately rejects that model for education.

### 3.2 What ExplainX Actually Is

ExplainX is an **AI Presentation Engine** that:

1. Extracts teachable knowledge from documents/topics  
2. Writes narration and scene plans  
3. Compiles an internal **Presentation DSL** (never shown as a slide UI in V1)  
4. Builds a **scene graph** of diagram primitives (SVG, icons, shapes, charts, arrows)  
5. Compiles an **animation timeline** synchronized to local TTS  
6. Renders that timeline to MP4 with local tooling  

The user experience is “upload → get video.”  
The system reality is “AI builds a presentation; software renders it.”

### 3.3 Why This Architecture Is Superior for ExplainX’s Goals

#### Maintainability

- Each stage has typed JSON contracts.  
- A bad subtitle cue does not require regenerating knowledge extraction.  
- Theme changes do not require rewriting scripts.  
- Render bugs are isolated to the Rendering Engine.

#### Testing

- Presentation Engine / Animation Engine / Rendering Engine can be unit-tested with fixtures.  
- Agent tests mock LLM/TTS ports and assert schema validity.  
- Golden DSL and timeline snapshots detect visual regressions without pixel AI.

#### Scalability

- V1: local CPU render  
- Later: GPU encode, cloud render plugin, optional image backends  
- Agent layer remains stable while media backends evolve  

#### Performance

- Intermediate artifacts enable incremental recomputation.  
- Heavy models unload between stages under memory pressure.  
- Draft 720p renders support iteration on constrained hardware.

#### Offline Execution

- Ollama + Piper + local assets + FFmpeg form a closed loop.  
- No paid API in the core path.  
- Air-gapped classrooms remain first-class.

---

## 4. System Context

### 4.1 External Actors

| Actor | Interaction |
|-------|-------------|
| End user | Uploads content, configures job, downloads exports |
| Local model runtimes | Ollama, Piper, IndicTrans2, optional Whisper.cpp |
| Native media tools | FFmpeg, OpenCV-assisted ops |
| Filesystem | Project artifacts, exports, caches |
| SQLite | Registry, jobs, settings, cache index |

### 4.2 System Context Diagram

```
                         ┌────────────────────┐
                         │   Human Operator   │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ ExplainX Frontend  │
                         │     (Next.js)      │
                         └─────────┬──────────┘
                                   │ localhost API
                                   ▼
                         ┌────────────────────┐
                         │ ExplainX Backend   │
                         │     (FastAPI)      │
                         └─────────┬──────────┘
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
   ┌───────────────┐      ┌────────────────┐      ┌────────────────┐
   │ Local Models  │      │  Project Store │      │ Media Toolchain│
   │ Ollama/Piper/ │      │ FS + SQLite    │      │ FFmpeg/OpenCV  │
   │ IndicTrans2   │      │                │      │                │
   └───────────────┘      └────────────────┘      └────────────────┘
```

### 4.3 Trust Boundary

Everything inside the ExplainX local stack is trusted as “user’s machine.”  
Uploaded documents are **content-untrusted** (size/type validation, path safety) even though processing is local.

---

## 5. Complete Architecture Diagram

### 5.1 Primary Stack Diagram

```
                              USER
                                │
                                ▼
                        Frontend (Next.js)
                     React · Tailwind · Framer Motion
                                │
                                ▼
                        FastAPI Backend
                     Routes · Jobs · Validation
                                │
                                ▼
                       Agent Orchestrator
                           (LangGraph)
                                │
┌───────────────────────────────┴───────────────────────────────┐
│                        AGENT LAYER                            │
│                                                               │
│  Parser Agent                                                 │
│  Cleaning Agent                                               │
│  Structure Agent                                              │
│  Knowledge Agent                                              │
│  Topic Classification Agent                                   │
│  Difficulty Agent                                             │
│  Explanation Strategy Agent                                   │
│  Script Agent                                                 │
│  Scene Planner                                                │
│  Metadata Agent                                               │
│  Visual Planner                                               │
│  Layout Planner                                               │
│  Theme Planner                                                │
│  Asset Agent                                                  │
│  Animation Planner                                            │
│  Camera Agent                                                 │
│  Translation Agent                                            │
│  Voice Agent                                                  │
│  Subtitle Agent                                               │
│  Rendering Agent                                              │
│  Project Manager Agent                                        │
│                                                               │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
                     Presentation Engine
              DSL compile · Scene Graph · Themes · Assets
                                │
                                ▼
                       Animation Engine
                 Motion compile · Camera · Timeline
                                │
                                ▼
                       Rendering Engine
              Frames · Encode · Mux · Thumbnail
                                │
                                ▼
                          Final MP4
                    (+ audio, subs, metadata, project)
```

### 5.2 Layered Dependency Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                   1. Presentation Layer (UI)                 │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                        2. API Layer                          │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                       3. Agent Layer                         │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                   4. Presentation Engine                     │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                     5. Animation Engine                      │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                     6. Rendering Engine                      │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                      7. Storage Layer                        │
│         Filesystem · SQLite · Cache · Models · Assets        │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 Ports & Adapters (Hexagonal View)

```
                    ┌─────────────────────────────┐
                    │     Application Core        │
                    │  Orchestrator + Agents +    │
                    │  Engines (domain logic)     │
                    └──────────────┬──────────────┘
                                   │ ports
         ┌─────────────┬───────────┼───────────┬─────────────┐
         ▼             ▼           ▼           ▼             ▼
      LLM Port     TTS Port   Translate   Render Port   Storage Port
         │             │        Port           │             │
         ▼             ▼           ▼           ▼             ▼
      Ollama        Piper     IndicTrans2   FFmpeg       SQLite/FS
```

Core code depends on **ports** (interfaces).  
Adapters implement those ports with concrete local binaries/libraries.

---

## 6. System Layers

Each layer below is specified with:

- Purpose  
- Responsibilities  
- Technologies  
- Input  
- Output  
- Dependencies  
- Failure Handling  
- Future Scalability  

---

### 6.1 Presentation Layer

#### Purpose

Provide the human interface for project creation, configuration, progress, preview, and export download. It is an operator console for a local media factory — not the video renderer itself.

#### Responsibilities

- Document/topic upload UX  
- Theme, language, voice, difficulty, resolution settings  
- Job progress visualization (coarse pipeline stages)  
- Project library (list/resume/delete)  
- Download of MP4 and export package  
- Local settings (model paths, default theme, quality profile)  
- Accessibility of the UI itself (not burned-in video captions)

#### Technologies

- Next.js  
- React  
- TypeScript  
- Tailwind CSS  
- Framer Motion (UI motion only)

#### Input

- User actions (upload, configure, start, cancel, download)  
- API responses (project status, artifacts availability, errors)

#### Output

- HTTP/JSON requests to API Layer  
- User-visible status and downloads  

#### Dependencies

- API Layer only (no direct agent or engine calls)  
- Static public assets for UI chrome  

#### Failure Handling

- Network/API errors surfaced as recoverable toasts/banners  
- Polling backoff when backend busy  
- Disable start when validation fails client-side  
- Preserve form state on transient failures  
- Never pretend a render succeeded without confirmed export paths  

#### Future Scalability

- Optional remote API target (same contract) for cloud mode  
- Collaborative cursors/presence (V5) as UI extensions  
- Advanced debug inspector for DSL/timeline (dev mode)

---

### 6.2 API Layer

#### Purpose

Expose a stable, local application boundary between UI and the generation system. Own request validation, job lifecycle, authorization-of-local-resources (path safety), and orchestration triggers.

#### Responsibilities

- REST (or RPC-style) endpoints for projects, jobs, settings, exports  
- Input validation and content-type limits  
- Enqueue pipeline runs  
- Stream or poll job status  
- Map domain errors → HTTP error contracts  
- Bootstrap health checks (`doctor`: models present, FFmpeg present, disk space)

#### Technologies

- FastAPI  
- Pydantic request/response models  
- Python asyncio / background task or worker process  
- OpenAPI as the machine-readable contract for the frontend  

#### Input

- Multipart uploads / topic strings  
- Job configuration JSON  
- Project IDs and commands (start, cancel, export)

#### Output

- Job IDs and status payloads  
- Artifact download URLs/paths  
- Structured error responses  

#### Dependencies

- Agent Orchestrator (to run pipelines)  
- Storage Layer (persist projects/jobs)  
- Settings / dependency injection container  

#### Failure Handling

- Reject invalid payloads before enqueue  
- Idempotent job creation keys where possible  
- Persist failed job state with stage + error_code  
- Timeout policies for hung workers  
- Health endpoint distinguishes “API up” vs “models missing”

#### Future Scalability

- Split API gateway vs worker processes  
- Horizontal workers with shared project store (later)  
- AuthN for multi-user local/network deployments (V5)

---

### 6.3 Agent Layer

#### Purpose

Perform AI-assisted and rule-assisted **planning and transformation** stages that produce typed intermediate artifacts. Agents decide *what to teach* and *how to present it*; they do not rasterize final video frames (except the Rendering Agent, which *invokes* the Rendering Engine).

#### Responsibilities

- Execute constitution-defined agents as LangGraph nodes  
- Validate every agent output schema  
- Write immutable-ish artifacts via Storage Port  
- Call engines through ports when compiling DSL/timeline/media  
- Respect cache hits for unchanged upstream hashes  
- Emit structured stage logs and progress events  

#### Technologies

- LangGraph orchestration  
- Python agents  
- Ollama (Qwen2.5 3B) via LLM Port  
- IndicTrans2 / Piper / Whisper.cpp via respective ports  
- Pydantic models for contracts  

#### Input

- PipelineState (project config + artifact references)  
- Source document or topic  

#### Output

- Stage artifacts: knowledge, script, scene plan, visual plan, DSL refs, audio, subtitles, render refs  
- Updated job status  

#### Dependencies

- Presentation Engine (for DSL/scene graph compilation assistance)  
- Animation Engine (timeline compilation)  
- Rendering Engine (via Rendering Agent)  
- Storage Layer  
- Model adapters  

#### Failure Handling

- Schema validation failure → bounded repair retry → stage fail  
- Model unavailable → non-retriable until doctor/fix  
- Partial success preserved; resume from last good stage  
- Cancellation cooperative between nodes  

#### Future Scalability

- Replace individual agents without rewriting graph topology  
- Add optional plugin agents (OCR, image gen planners)  
- Parallelize independent branches (e.g., metadata alongside visual planning when contracts allow)

**Agent isolation rule:** Agents communicate only through structured JSON artifacts. No agent mutates another agent’s output in place.

---

### 6.4 Presentation Engine

#### Purpose

Compile planning outputs into the system’s central visual IR: **Presentation DSL** and an in-memory/on-disk **Scene Graph**. This is the heart of “AI Presentation Engine.”

#### Responsibilities

- Merge Layout + Theme + Assets into Presentation DSL  
- Build scene graph nodes from element kinds (`array`, `arrow`, `icon`, …)  
- Resolve style tokens through theme packs  
- Enforce canvas rules (16:9, safe margins, contrast warnings)  
- Provide deterministic geometry for procedural diagrams  
- Remain LLM-agnostic at the engine core  

#### Technologies

- Python engine modules  
- Theme pack JSON/YAML  
- SVG/icon resolution against asset libraries  
- Pure functions for layout math where possible  

#### Input

- ScenePlan  
- VisualPlan  
- LayoutPlan  
- ThemeApplication  
- AssetManifest  

#### Output

- `presentation.dsl.json`  
- Scene graph representation (may be embedded in DSL or sibling artifact)  
- Validation report (warnings/errors)

#### Dependencies

- Storage Layer (read plans, write DSL)  
- Assets catalog  
- Theme packs  
- Invoked by Layout/Theme/Asset-related agents and orchestrator hooks  

#### Failure Handling

- Missing asset → geometric/icon fallback  
- Invalid element props → reject scene with actionable error  
- Theme missing → fall back to `minimal` or configured default  
- Never invent pedagogical content; only compose what plans specify  

#### Future Scalability

- Richer procedural compilers per domain (CS, biology, networks)  
- Plugin visual backends attaching `image` nodes (V3)  
- RTL / localization-aware layout packs  

---

### 6.5 Animation Engine

#### Purpose

Turn static presentation structure into time-based motion and camera behavior, then compile an absolute **Animation Timeline** aligned to narration audio durations.

#### Responsibilities

- Interpret AnimationPlan / CameraPlan  
- Generate keyframes for elements and camera  
- Apply easing and pedagogical motion presets  
- Bind narration beat timings to scene clips  
- Emit timeline suitable for headless render  
- Enforce motion safety limits (max zoom/pan speeds)

#### Technologies

- Python timeline compiler  
- Deterministic math (no network)  
- Optional interpolation utilities  

#### Input

- Presentation DSL / Scene Graph  
- AnimationPlan  
- CameraPlan  
- Audio track durations  
- Export FPS / duration policies  

#### Output

- `timeline.json` (absolute timestamps, tracks, keyframes)  
- Derived per-scene clip manifests  

#### Dependencies

- Presentation Engine outputs  
- Voice Agent durations (via artifacts, not live coupling)  
- Storage Layer  

#### Failure Handling

- Missing duration → estimate from script heuristics, mark warning, or fail-closed based on policy  
- Overlapping illegal keyframes → validation error  
- Timeline compile must be deterministic for identical inputs  

#### Future Scalability

- Motion packs per theme  
- GPU-accelerated interpolation later (optional)  
- Word-level caption sync hooks  

---

### 6.6 Rendering Engine

#### Purpose

Rasterize the timeline into frames, encode video, mux audio, generate thumbnails, and optionally burn subtitles. This layer turns the presentation into the user-visible MP4.

#### Responsibilities

- Frame composition from scene graph + timeline  
- Encode via FFmpeg  
- Audio muxing  
- Thumbnail extraction  
- Quality profiles (`draft`, `standard`, `high`)  
- Resource-aware settings for Iris Xe / CPU-only  

#### Technologies

- MoviePy (composition helpers)  
- OpenCV (image ops)  
- FFmpeg (encode/mux)  
- Rendering Agent as the agent-facing façade  

#### Input

- Timeline  
- Presentation DSL / resolved assets  
- Audio files  
- Subtitle files + burn-in flag  
- Export settings (resolution, FPS, bitrate)

#### Output

- `video.mp4`  
- `thumbnail.jpg`  
- Render logs / metrics  
- Checksums / media probe metadata  

#### Dependencies

- Animation Engine timeline  
- Storage / Output Manager  
- Native FFmpeg availability  

#### Failure Handling

- Encode failure → retain frames or intermediate if configured; mark job failed with encoder stderr excerpt  
- Disk full → fail early with storage error  
- Partial MP4 cleaned up or quarantined  
- Retry encode with safer profile (`draft`) only if policy allows and user opted in  

#### Future Scalability

- Hardware encoders  
- Cloud render plugin (V4)  
- Distributed frame farms (far future)  
- Alternative backends without changing Agent Layer contracts  

---

### 6.7 Storage Layer

#### Purpose

Persist projects, artifacts, jobs, caches, models references, and exports. Provide durable truth for resume, debugging, and incremental regeneration.

#### Responsibilities

- Project directory layout management  
- SQLite registry for projects/jobs/settings/cache index  
- Atomic writes for JSON artifacts where feasible  
- Cache key lookup (input hash + agent/engine versions)  
- Model/asset path configuration  
- Garbage collection policies for temp frames  

#### Technologies

- Filesystem project store  
- SQLite  
- Hashing utilities  
- Optional future object storage adapter (cloud mode)

#### Input

- Artifact write requests from services/agents  
- Queries for project/job state  

#### Output

- Durable artifacts and DB rows  
- Resolved paths for downstream stages  

#### Dependencies

- Host filesystem permissions  
- Disk quota/space  

#### Failure Handling

- Write failures surface as storage errors (retriable if transient)  
- Corrupt JSON → mark artifact invalid; allow stage rerun  
- DB migration failures block startup via doctor  

#### Future Scalability

- Remote object store backend via Storage Port  
- Multi-user shared storage (V5)  
- Content-addressed artifact store for dedupe  

---

## 7. Component Responsibilities

This section maps named system components (as engineers refer to them day-to-day) onto layers.

### 7.1 Frontend

| Aspect | Detail |
|--------|--------|
| Layer | Presentation Layer |
| Owns | UX, client validation, progress display, downloads |
| Does not own | Agent prompts, DSL semantics, FFmpeg |
| Talks to | API Layer only |

### 7.2 Backend

| Aspect | Detail |
|--------|--------|
| Layer | API + application services host |
| Owns | Process lifetime, DI container, worker entrypoints |
| Contains | API Layer, Orchestrator, Agents, Engines adapters wiring |
| Does not own | Pixel UI |

### 7.3 API

| Aspect | Detail |
|--------|--------|
| Layer | API Layer |
| Owns | External contract stability |
| Guarantees | Versioned DTOs, authz of local paths, job control |
| Evolution | Additive fields preferred; breaking changes versioned |

### 7.4 Agent Layer

| Aspect | Detail |
|--------|--------|
| Layer | Agent Layer |
| Owns | AI/planning transforms and stage sequencing logic hooks |
| Guarantees | JSON contracts, isolation, resumability |
| Collaboration | Calls engines; never bypasses ports for side effects |

### 7.5 Presentation Engine

| Aspect | Detail |
|--------|--------|
| Layer | Presentation Engine |
| Owns | DSL compilation, scene graph, theme application mechanics |
| Guarantees | Deterministic composition from plans + assets |
| Non-goal | Inventing new teaching content |

### 7.6 Rendering Engine

| Aspect | Detail |
|--------|--------|
| Layer | Rendering Engine |
| Owns | Frames, encode, mux, thumbnails |
| Guarantees | Media outputs matching export settings |
| Non-goal | Changing narration or scene pedagogy |

### 7.7 Storage

| Aspect | Detail |
|--------|--------|
| Layer | Storage Layer |
| Owns | Durability and retrieval of artifacts |
| Guarantees | Path conventions, cache index integrity |
| Includes | Project directories + blob files |

### 7.8 Assets

| Aspect | Detail |
|--------|--------|
| Layer | Cross-cutting resource pack under Storage/Assets |
| Owns | Icons (Lucide/Heroicons/OpenMoji), Undraw, fonts, SVG templates |
| Consumed by | Asset Agent + Presentation Engine |
| Rule | Core path uses local free packs only |

### 7.9 Database

| Aspect | Detail |
|--------|--------|
| Layer | Storage Layer (SQLite) |
| Owns | Project registry, job queue/status, settings, cache index, plugin enablement |
| Does not store | Large media binaries (those stay on filesystem) |
| Guarantee | Source of truth for *pointers* and job state |

### 7.10 Models

| Aspect | Detail |
|--------|--------|
| Layer | Infrastructure adapters behind ports |
| Includes | Qwen2.5 3B via Ollama, IndicTrans2, Piper voices, Whisper.cpp |
| Owned operationally by | Installer/doctor scripts + settings |
| Rule | Loaded on demand; unload under memory pressure when possible |

### 7.11 Output Manager

| Aspect | Detail |
|--------|--------|
| Layer | Application service spanning Rendering + Storage |
| Owns | Final export package assembly |
| Produces | MP4, narration audio, SRT/VTT, thumbnail, metadata.json, saved project bundle |
| Guarantees | Export manifest listing all files + hashes |
| Failure mode | If any required artifact missing, export is incomplete and job not marked completed |

---

## 8. Data Flow

### 8.1 Upload → MP4 (End-to-End)

```
1. User uploads PDF/DOCX/TXT/MD or enters a Topic in Frontend
2. API validates and stores source under projects/{id}/source
3. API creates Job row (status=queued) in SQLite
4. Orchestrator starts LangGraph with PipelineState
5. Knowledge plane agents produce:
      RawDocument → CleanDocument → Structure → Knowledge
      → Topic → Difficulty → Explanation Strategy
6. Narrative plane agents produce:
      Script → Scene Plan → Metadata
7. Visual plane agents produce:
      Visual Plan → Layout → Theme → Asset Manifest
8. Presentation Engine compiles Presentation DSL + Scene Graph
9. Animation/Camera agents + Animation Engine produce Timeline
10. Optional Translation Agent adapts language artifacts
11. Voice Agent synthesizes audio; durations written back to artifacts
12. Subtitle Agent emits SRT/VTT (optional alignment)
13. Rendering Agent invokes Rendering Engine → MP4 + thumbnail
14. Output Manager assembles export package
15. Project Manager Agent finalizes ProjectRecord (status=completed)
16. Frontend polls status and enables downloads
```

### 8.2 Artifact Hand-off Table

| From | To | Artifact |
|------|----|----------|
| Parser | Cleaning | RawDocument |
| Cleaning | Structure | CleanDocument |
| Structure | Knowledge | DocumentStructure |
| Knowledge plane | Script | KnowledgeModel + plans |
| Script | Scene Planner | NarrationScript |
| Scene Planner | Visual Planner | ScenePlan |
| Visual/Layout/Theme/Assets | Presentation Engine | Plans + manifest |
| Presentation Engine | Animation Engine | Presentation DSL / Scene Graph |
| Animation Engine | Rendering Engine | Timeline |
| Voice/Subtitle | Rendering / Output Manager | Media sidecars |
| Rendering | Output Manager | MP4 + thumb |
| Output Manager | User | Export package |

### 8.3 Internal IR Progression (Constitutional Core)

```
Document
   ↓
Knowledge
   ↓
Presentation DSL
   ↓
Scene Graph
   ↓
Animation Timeline
   ↓
Renderer
   ↓
Video
```

### 8.4 Incremental Recompute Example

User changes **theme only**:

1. Invalidate ThemeApplication + DSL styling + timeline only if motion packs differ  
2. Reuse Knowledge, Script, ScenePlan, VisualPlan when hashes match  
3. Re-render  

User changes **voice only**:

1. Re-run Voice + Subtitle timing + Timeline retarget + Render  
2. Keep DSL geometry if unchanged  

This is a primary maintainability/performance benefit of staged IR.

---

## 9. Cross-Cutting Runtime Model

### 9.1 Job State Machine

```
queued → running → (stage_n) → completed
                 ↘ failed
                 ↘ cancelled
```

Substates may record `current_stage` for UI.

### 9.2 PipelineState (Conceptual)

```json
{
  "project_id": "...",
  "job_id": "...",
  "config": {
    "theme_id": "notebooklm",
    "language": "en",
    "voice_id": "...",
    "difficulty": "intermediate",
    "export": { "resolution": "1280x720", "fps": 30 }
  },
  "artifacts": {
    "knowledge_id": "...",
    "script_id": "...",
    "dsl_path": "...",
    "timeline_path": "...",
    "mp4_path": null
  },
  "versions": {
    "dsl_version": "1.0",
    "graph_version": "1.0"
  }
}
```

### 9.3 Control Plane vs Data Plane

| Plane | Components | Role |
|-------|------------|------|
| Control | API, Job Service, Orchestrator, Project Manager | When/what runs |
| Data | Artifacts, engines, media files | What is produced |

Keeping these separate prevents UI/API concerns from leaking into render math.

---

## 10. Design Principles

### 10.1 Single Responsibility Principle

Each agent and engine has one reason to change.

- Script Agent changes when narration policy changes.  
- Rendering Engine changes when encoding strategy changes.  
- Do not combine “write script + render video” in one module.

### 10.2 Low Coupling

- Frontend couples only to API contracts.  
- Agents couple to artifact schemas, not to each other’s internals.  
- Engines couple to DSL/timeline, not to Ollama prompts.

### 10.3 High Cohesion

- All timeline math lives in Animation Engine.  
- All theme token resolution lives with Presentation Engine/theme packs.  
- All job lifecycle transitions live in job/project services.

### 10.4 Dependency Injection

- LLM, TTS, Translator, Renderer, Storage are ports.  
- Adapters injected at composition root.  
- Tests inject fakes without patching globals.

### 10.5 Composition over Inheritance

- Prefer pipeline composition and strategy objects over deep class hierarchies.  
- Themes compose tokens; they do not subclass “VideoProject.”  
- Visual modes are selectable strategies, not subclasses of Agent.

### 10.6 Modularity

- Packages/folders mirror layers.  
- New format importers plug in without touching render.  
- New themes drop in as packs.

### 10.7 Offline First

- Core path assumes no network.  
- Online features are explicit plugins/flags.  
- Doctor checks verify local readiness.

### 10.8 Plugin Architecture

- Themes, asset packs, visual backends, renderers register via plugin API.  
- Core runs with zero plugins.  
- Plugin failure falls back to core behavior.

### 10.9 JSON Communication

- Agent I/O is structured JSON validated by schemas.  
- Artifacts are auditable and diffable.  
- No hidden binary protocol between agents.

### 10.10 Agent Isolation

- No shared mutable objects across agents.  
- Downstream produces new artifacts referencing upstream IDs.  
- Orchestrator owns retries and sequencing.

---

## 11. Interface & Contract Architecture

### 11.1 Contract Tiers

| Tier | Examples | Breaking Change Impact |
|------|----------|------------------------|
| Public API | `/projects`, `/jobs` | Frontend + external tools |
| Agent I/O | KnowledgeModel, ScenePlan | Graph nodes + caches |
| DSL | `presentation.dsl.json` | Presentation/Animation/Render |
| Timeline | `timeline.json` | Rendering Engine |
| Export Manifest | `metadata.json` + file list | Users + Output Manager |

### 11.2 Validation Points

1. API ingress  
2. Each agent egress  
3. Presentation Engine compile  
4. Timeline compile  
5. Export assembly  

Fail fast at the earliest boundary.

### 11.3 Compatibility Policy

- Additive JSON fields: preferred  
- Renames: require version bump + migration note in ADR  
- `dsl_version` gates renderer features  

---

## 12. Failure Recovery

### 12.1 Recovery Philosophy

> Prefer **resume** over **restart from zero**.  
> Prefer **preserve artifacts** over **delete on failure**.  
> Prefer **structured error codes** over opaque exceptions.

### 12.2 Layer-by-Layer Recovery

#### Presentation Layer

- On API timeout: retry poll with backoff  
- On failed job: show stage + message; offer “Retry from failed stage”  
- On download missing: refresh artifact list  

#### API Layer

- Validate before side effects  
- If worker crash: mark job failed; leave artifacts intact  
- Duplicate start requests: return existing running job when idempotency key matches  

#### Agent Layer

- Validation fail → repair retry (bounded, e.g., 1–2)  
- Non-retriable model errors → stop stage, persist error  
- Cancellation → checkpoint last successful artifact set  

#### Presentation Engine

- Asset miss → fallback primitive; warn  
- Hard schema break → fail stage; do not emit partial DSL unless marked `partial=true` for debug only  

#### Animation Engine

- Timing gaps → policy: estimate with warning or fail  
- Never silently desync audio/timeline without logging  

#### Rendering Engine

- Encoder fail → fail job; keep timeline/DSL  
- Allow re-encode without regenerating agents  
- Clean temp frames on failure after diagnostics retention window  

#### Storage Layer

- Disk full → refuse new writes early  
- Corrupt artifact → quarantine file; require stage rerun  
- SQLite locked → retry with backoff; then fail retriable  

### 12.3 Checkpointing

Orchestrator checkpoints after each successful stage:

```
checkpoint = {
  stage,
  artifact_ids,
  input_hashes,
  agent_versions,
  timestamp
}
```

Resume loads checkpoint and continues.

### 12.4 Dead Letter / Failed Jobs

Failed jobs retain:

- error_code  
- stage  
- stderr excerpts (render)  
- last checkpoint  

Operators can inspect artifacts for debugging without re-uploading sources.

---

## 13. Logging Architecture

### 13.1 Goals

- Reconstruct any job’s path from logs alone  
- Correlate UI job IDs with stage failures  
- Support performance analysis (stage durations, memory notes)  
- Avoid logging full private document text by default  

### 13.2 Log Levels

| Level | Use |
|-------|-----|
| DEBUG | Prompt sizes, cache hit details, geometry traces (dev) |
| INFO | Stage start/end, artifact written, job state transitions |
| WARNING | Fallbacks, contrast issues, estimated timings |
| ERROR | Stage failures, validation failures |
| CRITICAL | Storage corruption, unrecoverable process faults |

### 13.3 Required Fields (Structured Logs)

```json
{
  "ts": "ISO-8601",
  "level": "INFO",
  "project_id": "...",
  "job_id": "...",
  "stage": "script_agent",
  "event": "stage_completed",
  "duration_ms": 8422,
  "status": "ok",
  "error_code": null,
  "component": "agent_layer"
}
```

### 13.4 Log Channels

| Channel | Destination | Contents |
|---------|-------------|----------|
| app | `data/projects/{id}/logs/app.jsonl` | Stage lifecycle |
| render | `.../logs/render.log` | FFmpeg/MoviePy excerpts |
| api | process stdout/file | Request metrics |
| doctor | diagnostics | Environment health |

### 13.5 Privacy Rules

- Default: log hashes, counts, headings — not full source bodies  
- Debug mode (explicit): may log truncated snippets  
- Never exfiltrate logs to cloud in core product  

### 13.6 Progress Events

Orchestrator emits progress events consumed by API and pushed/polled to UI:

```json
{
  "job_id": "...",
  "coarse_stage": "designing_visuals",
  "fine_stage": "visual_planning_agent",
  "percent_estimate": 55
}
```

Percent is advisory; coarse stage is authoritative for UX copy.

---

## 14. Performance Architecture

### 14.1 Caching

**Cache key inputs:**

- Normalized source hash  
- Pipeline config hash (theme, language, voice, difficulty, export)  
- Agent version  
- Engine version  
- DSL version  

**Cache scope:**

| Artifact family | Cacheable |
|-----------------|-----------|
| Knowledge plane | Yes |
| Script/scenes | Yes |
| DSL | Yes |
| Audio | Yes (per voice) |
| Timeline | Yes |
| MP4 | Yes (per export settings) |

**Invalidation:** change in any key component for that stage and downstream.

### 14.2 Memory Management

Target profile: **16GB RAM**, CPU LLM.

Policies:

1. Load one heavy model family at a time when possible (LLM vs translation vs whisper).  
2. Explicit unload/release hooks after stage groups.  
3. Stream large PDFs page batches if needed.  
4. Prefer 720p draft for iteration.  
5. Delete temp frame directories after successful encode (configurable retention).  
6. Cap concurrency of jobs on a single machine (default: 1 active render).  

### 14.3 Scene Rendering

- Render scene-by-scene or clip-by-clip to bound peak memory.  
- Reuse decoded SVG/icon rasters within a scene.  
- Avoid holding entire full-length uncompressed frame buffers.  
- Thumbnail from a representative mid-scene frame after successful encode or during first pass.

### 14.4 Parallel Processing

Safe parallelism (V1 conservative):

| Candidate | Parallel? | Notes |
|-----------|-----------|-------|
| Multiple jobs | Optional, default off | RAM risk |
| Metadata + Visual Planning | Possible | If inputs ready and no write conflicts |
| Per-beat TTS | Possible | CPU-bound; limit workers |
| Frame encode chunks | Later | Complexity vs Iris Xe gains |
| LLM agents in parallel | Rare | Most are sequential dependencies |

**Rule:** Prefer correctness and memory safety over aggressive parallelism on the target laptop class.

### 14.5 Performance Budgets (Guidance)

Exact SLOs evolve with benchmarks; architecture mandates:

- Non-blocking UI while jobs run  
- Cancellable runs  
- Stage-level timing metrics always logged  
- Draft quality profile for faster feedback loops  

---

## 15. Scalability

ExplainX scales by **replacing adapters and adding plugins**, not by rewriting the knowledge→DSL core.

### 15.1 Cloud Rendering (Version 4)

```
Timeline + Assets Package → Cloud Renderer Plugin → MP4 download → Output Manager
```

- Core agents still local (or optionally remote later)  
- Privacy warning + explicit opt-in  
- Same timeline contract  

### 15.2 GPU Rendering

- Detect hardware encoders (QSV/NVENC/etc.) via renderer adapter  
- Fall back to CPU x264/x265  
- Iris Xe may help encode; still not required  

### 15.3 ComfyUI / Stable Diffusion / FLUX

These attach as **optional visual backend plugins (V3+)**:

- Visual Planning may emit an `image` primitive only when plugin enabled  
- Asset Agent delegates to plugin  
- Default path remains SVG/icons/diagrams  
- Offline plugin variants preferred; online variants flagged  

### 15.4 Video Plugins

- Alternate transition packs  
- Intro/outro bumpers  
- Specialty diagram animators  

Registered as motion/render plugins; timeline schema gains optional tracks gated by version.

### 15.5 Additional Languages

- Translation Agent + additional local models  
- Voice packs per language  
- Subtitle dual-track export  
- Layout packs for RTL when needed  

### 15.6 Collaborative Editing (Version 5)

- Multi-user control plane on shared project store  
- Conflict-safe artifact versioning  
- Limited human inspection of scenes/DSL  
- Still presentation-engine core; not a full PowerPoint clone unless product expands  

### 15.7 Scale-Out Mental Model

```
                 ┌──────────────┐
                 │ Control Plane│  API / Jobs / Auth
                 └──────┬───────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   Worker A         Worker B         Worker C
   (agents+engines) (agents+engines) (render-only)
        │               │               │
        └───────────────┴───────────────┘
                        │
                        ▼
                 Shared Storage
```

V1 collapses this to one machine; contracts allow future split.

---

## 16. Security & Isolation Boundaries

| Boundary | Rule |
|----------|------|
| UI → API | No direct FS access from browser beyond download endpoints |
| API → Storage | Canonical root jail for project paths |
| Plugins | Explicit permissions; default deny |
| Models | Local process; no document upload to third parties in core |
| Uploads | Size/type limits; treat as untrusted content |

---

## 17. Deployment Topology

### 17.1 V1 Local Topology

```
Windows Laptop
├── Next.js UI (localhost)
├── FastAPI backend (localhost)
├── Ollama service
├── Piper binaries/voices
├── FFmpeg
├── SQLite file
└── data/projects/...
```

### 17.2 Process Roles

| Process | Role |
|---------|------|
| Web | Presentation Layer |
| API | Control plane + may host worker |
| Worker (optional split) | Orchestrator + engines |
| Ollama | LLM inferences |

---

## 18. Developer Onboarding Map

If you are new:

1. Read `PROJECT_CONSTITUTION.md` for product/agent rules.  
2. Read this file for layer interactions.  
3. Trace one fixture topic through Data Flow §8.  
4. Locate ports/adapters for LLM/TTS/Render.  
5. Before coding a feature, identify:  
   - which layer owns it  
   - which artifact contracts change  
   - which tests (engine vs agent) apply  

**Rule of thumb:**

- Changing teaching content logic → Agent Layer  
- Changing diagram geometry → Presentation Engine  
- Changing motion → Animation Engine  
- Changing MP4 encoding → Rendering Engine  
- Changing buttons/pages → Presentation Layer  
- Changing endpoints → API Layer  

---

## 19. Architecture Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Video paradigm | Presentation→Render | Educational clarity, offline, testability |
| Agent I/O | JSON schemas | Isolation, diffability, validation |
| Central IR | Presentation DSL | Stable hub for visual/motion/render |
| Orchestration | LangGraph | Explicit state machine, resumability |
| UI stack | Next.js/React | Productive local operator UI |
| API | FastAPI | Typed Python alignment with AI stack |
| Persistence | SQLite + FS | Simple, local, adequate for V1 |
| Visuals | Diagram-first | Reliability over generative images |
| Extensibility | Ports + plugins | Scale features without core rewrites |

---

## 20. Appendix: Sequence & State Diagrams

### 20.1 Sequence — Happy Path

```
User    Frontend    API      Orchestrator    Agents/Engines    Storage
 │         │         │            │                │              │
 │ upload  │         │            │                │              │
 │────────►│ store   │            │                │              │
 │         │────────►│            │                │              │
 │         │         │ write src  │                │              │
 │         │         │───────────────────────────────────────────►│
 │         │         │ enqueue    │                │              │
 │         │         │───────────►│                │              │
 │         │         │            │ run stages     │              │
 │         │         │            │───────────────►│              │
 │         │         │            │ write artifacts│              │
 │         │         │            │                │─────────────►│
 │         │ poll    │            │                │              │
 │         │────────►│ status     │                │              │
 │         │◄────────│            │                │              │
 │ download│         │            │                │              │
 │────────►│────────►│ read export│                │              │
 │         │◄────────│◄───────────┴────────────────┴──────────────│
```

### 20.2 State — Job + Stage

```
[JOB queued]
    │
    ▼
[JOB running]
    │
    ├─ stage: parse ... render
    │    ├─ success → next stage
    │    ├─ fail → [JOB failed] (checkpoint kept)
    │    └─ cancel → [JOB cancelled]
    ▼
[JOB completed] → exports available
```

### 20.3 Why Layers Beat a Monolith (Summary Diagram)

```
Monolithic "AI video" prompt→pixels
          │
          ▼
    Hard to test, cache, or resume
    Hard to run offline cheaply
    Hard to guarantee teaching structure

ExplainX layered IR
          │
          ▼
    Test engines without LLMs
    Cache knowledge when theme changes
    Resume after render failure
    Swap renderer for cloud/GPU later
    Keep pedagogy consistent via DSL
```

---

## Closing Statement

ExplainX is architected as a **local, layered, artifact-centric AI Presentation Engine**.

The stack is intentionally boring where it must be reliable (engines, storage, encoding) and modular where it must be intelligent (agents). The Presentation DSL and Animation Timeline are the load-bearing beams between those worlds.

A developer who understands:

1. the seven system layers,  
2. the upload→MP4 data flow, and  
3. the ports/adapters boundary  

…understands how to extend ExplainX without violating its architecture.

---

*End of SYSTEM_ARCHITECTURE.md*  
*ExplainX Engineering — Layers, Contracts, and Deterministic Rendering.*
