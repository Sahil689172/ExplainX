# ExplainX — Technology Stack

**Document Status:** Canonical Technology Selection Reference  
**Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Companions:**  
[`PROJECT_CONSTITUTION.md`](./PROJECT_CONSTITUTION.md) ·  
[`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md) ·  
[`FOLDER_STRUCTURE.md`](./FOLDER_STRUCTURE.md) ·  
[`RISK_ANALYSIS.md`](./RISK_ANALYSIS.md)  

> **Authority:** This document records **what** technologies ExplainX uses and **why**.  
> Swapping a technology requires an ADR and an update here. Core constraints remain: **100% free**, **offline**, **CPU-compatible** on the target Windows laptop class.

---

## Table of Contents

1. [Stack Principles](#1-stack-principles)
2. [Hardware Compatibility](#2-hardware-compatibility)
3. [Frontend](#3-frontend)
4. [Backend](#4-backend)
5. [Database](#5-database)
6. [Orchestration](#6-orchestration)
7. [LLM](#7-llm)
8. [Translation](#8-translation)
9. [Voice Generation](#9-voice-generation)
10. [Subtitle Generation](#10-subtitle-generation)
11. [Presentation, SVG Assets, Icons & Charts](#11-presentation-svg-assets-icons--charts)
12. [Animation](#12-animation)
13. [Rendering](#13-rendering)
14. [Testing](#14-testing)
15. [Development Tools](#15-development-tools)
16. [Stack Integration Map](#16-stack-integration-map)
17. [Technology Decision Summary Table](#17-technology-decision-summary-table)

---

## 1. Stack Principles

| Principle | Implication |
|-----------|-------------|
| Free | No paid APIs or proprietary runtimes required for core |
| Offline-first | After install, generation works without network |
| CPU-first | GPU optional; Iris Xe may help encode, never required |
| Ports & adapters | Concrete tools are swappable behind interfaces |
| Diagram-first visuals | Prefer SVG/icons over generative images |
| Local trust | Stack runs on localhost for V1 |

---

## 2. Hardware Compatibility

### 2.1 Target Profile (Normative)

| Resource | Requirement |
|----------|-------------|
| CPU | Intel Core i7-1255U (or equivalent modern dual/quad-class laptop CPU) |
| RAM | 16 GB |
| GPU | Intel Iris Xe Graphics (optional acceleration) |
| OS | Windows 10/11 (first-class) |
| Storage | SSD strongly recommended for models + project cache |

### 2.2 Compatibility Rules

1. Default model: **Qwen2.5 3B** via Ollama — sized for 16GB with OS + app headroom.  
2. Do not require CUDA or discrete GPU for V1.  
3. Prefer 720p draft encodes during iteration.  
4. Avoid loading LLM + IndicTrans2 + Whisper simultaneously.  
5. Default concurrency: **one** heavy pipeline job.  
6. Doctor must report missing FFmpeg/Ollama/Piper clearly.

### 2.3 What “Works on Target Hardware” Means

- Completes a short educational markdown → MP4 path offline without OOM kill  
- UI remains responsive while jobs run  
- Failures are recoverable via resume/retry  

Exact wall-clock times vary; progress UX is mandatory.

---

## 3. Frontend

### 3.1 Next.js

| | |
|--|--|
| **Purpose** | App framework for local operator UI (routing, SSR/CSR as needed) |
| **Advantages** | Mature React meta-framework; file routing; strong TS DX; easy localhost deploy |
| **Limitations** | Heavier than a pure Vite SPA; App Router complexity |
| **Future replacements** | Vite + React Router if Next is overkill for pure desktop shell |
| **Alternative options** | Remix, Nuxt (wrong language), plain React CRA (legacy) |
| **Integration points** | Talks only to FastAPI `/api/v1`; no direct model access |

### 3.2 React

| | |
|--|--|
| **Purpose** | Component model for UI |
| **Advantages** | Ecosystem, hiring familiarity, works with Next |
| **Limitations** | Footguns around client state if unstructured |
| **Future replacements** | Unlikely in V1–V2 |
| **Alternative options** | Svelte, Vue, Solid |
| **Integration points** | `apps/web` features, hooks, API client |

### 3.3 TypeScript

| | |
|--|--|
| **Purpose** | Typed frontend (and shared DTO alignment) |
| **Advantages** | Safer refactors; matches API contracts |
| **Limitations** | Build config overhead |
| **Future replacements** | None planned |
| **Alternative options** | JS (rejected for standards) |
| **Integration points** | `packages/shared-types`, API client types |

### 3.4 Tailwind CSS

| | |
|--|--|
| **Purpose** | Utility-first styling |
| **Advantages** | Fast UI iteration; consistent spacing; small runtime |
| **Limitations** | Class verbosity; design discipline still required |
| **Future replacements** | CSS Modules + design tokens if preferred later |
| **Alternative options** | plain CSS, styled-components, MUI (avoid heavy kits unless needed) |
| **Integration points** | `apps/web` styles/components |

### 3.5 Framer Motion

| | |
|--|--|
| **Purpose** | **UI** motion only (not video engine) |
| **Advantages** | Polished transitions for progress/pages |
| **Limitations** | Irrelevant to MP4 pipeline; can be overused |
| **Future replacements** | CSS transitions only |
| **Alternative options** | Motion One, CSS |
| **Integration points** | Frontend feedback/layout animations |

---

## 4. Backend

### 4.1 Python

| | |
|--|--|
| **Purpose** | Primary language for agents, engines, media tooling |
| **Advantages** | Best ecosystem for ML/TTS/FFmpeg wrappers; rapid agent iteration |
| **Limitations** | GIL for CPU-bound threads; packaging native deps on Windows |
| **Future replacements** | Mixed: keep Python for AI/media; optional Rust/Go workers later |
| **Alternative options** | Node-only stack (weaker media/AI local tooling) |
| **Integration points** | Entire `backend/` |

### 4.2 FastAPI

| | |
|--|--|
| **Purpose** | Local HTTP API (control plane) |
| **Advantages** | Native Pydantic validation; OpenAPI; async support; excellent DX |
| **Limitations** | Not a full job queue system by itself |
| **Future replacements** | Same role with Litestar/Starlette if needed |
| **Alternative options** | Flask, Django Ninja, gRPC-only (worse for web UI) |
| **Integration points** | `backend/app/api` ↔ Next.js; services; jobs |

### 4.3 Pydantic

| | |
|--|--|
| **Purpose** | Typed request/artifact/DSL validation |
| **Advantages** | Strict schemas; JSON-friendly; FastAPI-native |
| **Limitations** | Heavy models can be verbose |
| **Future replacements** | msgspec for ultra-hot paths (optional) |
| **Alternative options** | dataclasses + JSON Schema, attrs |
| **Integration points** | API models, agent envelopes, DSL models |

---

## 5. Database

### 5.1 SQLite (V1)

| | |
|--|--|
| **Purpose** | Projects, jobs, indexes, settings registry |
| **Advantages** | Zero ops; single file; offline; perfect for desktop; WAL mode |
| **Limitations** | Write concurrency; not ideal for multi-writer cloud SaaS |
| **Future replacements** | **PostgreSQL** via Storage Port (same repositories) |
| **Alternative options** | DuckDB (analytics), LiteFS, MySQL |
| **Integration points** | Repositories; `data/explainx.db`; see `DATABASE_DESIGN.md` |

### 5.2 Filesystem Project Store

| | |
|--|--|
| **Purpose** | DSL, timelines, audio, MP4, stage JSON |
| **Advantages** | Natural for large artifacts; easy backup of project folders |
| **Limitations** | Path management; not transactional with DB without care |
| **Future replacements** | S3-compatible object storage for cloud mode |
| **Alternative options** | Store blobs in SQLite (rejected for large media) |
| **Integration points** | `data/projects/{id}/`; Output Manager |

---

## 6. Orchestration

### 6.1 LangGraph

| | |
|--|--|
| **Purpose** | Multi-agent state machine / pipeline graph |
| **Advantages** | Explicit nodes/edges; checkpoint-friendly; fits agent isolation |
| **Limitations** | Evolving APIs; learning curve; avoid over-graphing simple ETL |
| **Future replacements** | Custom orchestrator; Temporal for distributed workers (later) |
| **Alternative options** | Plain Python FSM, Prefect, Airflow (heavy), LangChain LCEL alone |
| **Integration points** | `backend/app/orchestration`; agents as nodes; job checkpoints |

---

## 7. LLM

### 7.1 Ollama

| | |
|--|--|
| **Purpose** | Local LLM runtime |
| **Advantages** | Simple local model management; offline after pull; Windows support |
| **Limitations** | RAM pressure; model quality vs size tradeoff |
| **Future replacements** | llama.cpp server, LM Studio, vLLM-local (if hardware grows) |
| **Alternative options** | Direct llama.cpp, GPT4All |
| **Integration points** | `adapters/ollama_llm.py` via `LLMPort` |

### 7.2 Qwen2.5 3B

| | |
|--|--|
| **Purpose** | Default reasoning model for agents (knowledge, script, planning) |
| **Advantages** | Fits 16GB-class machines; capable JSON-ish instruction following for size; free |
| **Limitations** | Hallucinations; weaker than large cloud models; context limits |
| **Future replacements** | Larger Qwen/Llama when user has more RAM; selectable model setting |
| **Alternative options** | Llama 3.2 3B, Phi-3/4 mini, Gemma small — evaluate quality vs RAM |
| **Integration points** | Knowledge/Content/Visual planning agents; never the renderer |

---

## 8. Translation

### 8.1 IndicTrans2

| | |
|--|--|
| **Purpose** | Local translation (esp. Indian language pairs) |
| **Advantages** | Offline; free research models; strong regional coverage intent |
| **Limitations** | Model size/RAM; quality varies by pair; packaging complexity |
| **Future replacements** | Additional local NLLB/M2M models; plugin translators |
| **Alternative options** | Argos Translate, MarianMT, cloud MT (rejected for core) |
| **Integration points** | `TranslatorPort` → Translation Agent; optional pipeline stage |

---

## 9. Voice Generation

### 9.1 Piper TTS

| | |
|--|--|
| **Purpose** | Local neural TTS for narration |
| **Advantages** | Fast on CPU; offline; free voices; good enough for education |
| **Limitations** | Less expressive than premium cloud voices; voice catalog limited |
| **Future replacements** | Other local TTS (Coqui, MMS-TTS) via `TTSPort` |
| **Alternative options** | eSpeak (robotic), cloud TTS (rejected for core) |
| **Integration points** | Voice Agent; audio paths in DSL; timeline durations |

---

## 10. Subtitle Generation

### 10.1 Script + Timing Alignment (Core)

| | |
|--|--|
| **Purpose** | Build SRT/VTT from narration beats + measured audio durations |
| **Advantages** | Deterministic; no extra model required |
| **Limitations** | Phrase boundaries may be coarse |
| **Future replacements** | Richer linguistic segmentation |
| **Alternative options** | Manual captions only (rejected) |
| **Integration points** | Subtitle Agent; export package; optional burn-in |

### 10.2 Whisper.cpp (Optional Alignment)

| | |
|--|--|
| **Purpose** | Optional forced alignment / ASR assist for better cue timing |
| **Advantages** | Local; improves sync when enabled |
| **Limitations** | Extra RAM/CPU; slower; not needed for every job |
| **Future replacements** | Other local aligners |
| **Alternative options** | Whisper (Python) heavier; cloud ASR (rejected for core) |
| **Integration points** | Optional path in Subtitle Agent; doctor feature flag |

---

## 11. Presentation, SVG Assets, Icons & Charts

### 11.1 Procedural SVG / Scene Graph (In-Engine)

| | |
|--|--|
| **Purpose** | Generate arrays, arrows, graphs, orbits, process diagrams from DSL props |
| **Advantages** | Deterministic; educationally precise; offline; tiny vs images |
| **Limitations** | Authoring compilers takes engineering effort |
| **Future replacements** | Richer domain compilers; optional Skia drawing |
| **Alternative options** | AI images per scene (rejected as default) |
| **Integration points** | Presentation Engine; Asset Agent `procedural` type |

### 11.2 Lucide

| | |
|--|--|
| **Purpose** | Icon pack for UI + diagrams |
| **Advantages** | Clean SVG; free license; consistent style |
| **Limitations** | Not emoji-like; limited metaphor set |
| **Future replacements** | Additional packs |
| **Alternative options** | Feather, Phosphor |
| **Integration points** | `/assets/icons/lucide`; Asset Agent; web UI |

### 11.3 Heroicons

| | |
|--|--|
| **Purpose** | Alternate iconography |
| **Advantages** | Free; familiar; solid/outline variants |
| **Limitations** | Overlap with Lucide |
| **Future replacements** | — |
| **Alternative options** | Tabler Icons |
| **Integration points** | Theme `icon_preference`; Asset Agent |

### 11.4 OpenMoji

| | |
|--|--|
| **Purpose** | Educational emoji-style icons (sun, leaf, earth, etc.) |
| **Advantages** | Free; expressive for science metaphors; SVG |
| **Limitations** | Style may clash with corporate themes; large pack size |
| **Future replacements** | Subset packaging to reduce disk |
| **Alternative options** | Twemoji (license check), Noto Emoji |
| **Integration points** | Photosynthesis/solar-type scenes; Asset Agent |

### 11.5 Undraw

| | |
|--|--|
| **Purpose** | Optional illustrations for metaphors (not every scene) |
| **Advantages** | Free illustrations; lighter than generative AI |
| **Limitations** | Generic; not precise for algorithms |
| **Future replacements** | Custom illustration packs |
| **Alternative options** | Humaaans, Storyset (license verify) |
| **Integration points** | Asset Agent rare path; still diagram-first |

### 11.6 Charts

| | |
|--|--|
| **Purpose** | Bar/line/pie for `chart_explain` visual mode |
| **Advantages** | Quantitative clarity |
| **Limitations** | Need careful labeling/contrast |
| **Primary approach** | Procedural SVG in Presentation Engine (preferred for offline render) |
| **Alternative options** | Matplotlib (Python) for raster charts; Apache ECharts (UI only — not in MP4 unless exported) |
| **Future replacements** | Vega-Lite compile-to-SVG |
| **Integration points** | DSL `chart` kind; render frame composer |

**Note:** Charting libraries that assume browser DOM must not be required inside headless render unless adapted.

---

## 12. Animation

### 12.1 Custom Animation / Timeline Engines (Python)

| | |
|--|--|
| **Purpose** | Compile pedagogical motion + camera + absolute timeline from DSL |
| **Advantages** | Full control; deterministic; no browser dependency in worker |
| **Limitations** | Must build presets (fade, move, highlight, path follow) |
| **Future replacements** | Embed a lightweight scene runtime if beneficial |
| **Alternative options** | Remotion (React/video — heavier Node pipeline), Manim (great math, less general product fit), GSAP (browser-oriented) |
| **Integration points** | Animation/Camera/Timeline agents + engines; feeds renderer |

### 12.2 Why Not Remotion/Manim as Core

| Tool | Why not core V1 |
|------|-----------------|
| Remotion | Node/React encode path duplicates stack; RAM complexity |
| Manim | Excellent math animations; weaker as general multi-domain product IR |
| Browser record | Fragile headless; harder offline job control |

ExplainX keeps **Presentation DSL → Python engines → FFmpeg** as the spine.

---

## 13. Rendering

### 13.1 FFmpeg

| | |
|--|--|
| **Purpose** | Encode, mux audio, final MP4 packaging |
| **Advantages** | Industry standard; free; offline; flexible codecs |
| **Limitations** | CLI complexity; Windows distribution must be licensed/documented carefully (use full build from trusted source) |
| **Future replacements** | Still FFmpeg under adapters; cloud encode later |
| **Alternative options** | GStreamer, Media Foundation (Windows-specific) |
| **Integration points** | `ffmpeg_renderer` adapter; Rendering Engine; Output Manager |

### 13.2 MoviePy

| | |
|--|--|
| **Purpose** | Composition helpers for clips/sequencing in Python |
| **Advantages** | Productive Python API over media ops |
| **Limitations** | Performance overhead; version quirks; still relies on FFmpeg |
| **Future replacements** | Direct FFmpeg filter graphs; PyAV |
| **Alternative options** | PyAV, ffmpeg-python only |
| **Integration points** | Render engine composition helpers |

### 13.3 OpenCV

| | |
|--|--|
| **Purpose** | Image ops, frame utilities, optional processing |
| **Advantages** | Battle-tested; CPU-friendly; free |
| **Limitations** | Not a full animation authoring tool |
| **Future replacements** | Pillow-only for simple ops if OpenCV too heavy |
| **Alternative options** | Pillow, scikit-image |
| **Integration points** | Frame composer helpers; thumbnails |

### 13.4 Hardware Encoding (Optional)

| | |
|--|--|
| **Purpose** | Faster encode via Iris Xe / QSV when available |
| **Advantages** | Speed on target GPU |
| **Limitations** | Driver variance; quality differences; must fallback to CPU x264 |
| **Future replacements** | NVENC on machines that have it |
| **Alternative options** | Always software x264 (default safe path) |
| **Integration points** | Quality profiles; doctor capability detect |

---

## 14. Testing

| Technology | Purpose | Advantages | Limitations | Future replacements | Alternatives | Integration points |
|------------|---------|------------|-------------|---------------------|--------------|--------------------|
| **pytest** | Python tests | Fixtures, parametrize, ecosystem | — | — | unittest | `backend/tests` |
| **pytest** mocks / fakes | Port fakes | Isolation from Ollama | Discipline required | — | unittest.mock | Agent contract tests |
| **Golden JSON fixtures** | DSL/timeline lock | Catches IR drift | Manual review on change | Visual frame goldens | Snapshots libs | `tests/golden` |
| **Playwright** (optional) | UI e2e | Real browser flows | Slower CI | Cypress | — | `apps/web/tests/e2e` |
| **ESLint / Ruff / Prettier** | Static quality | Consistency | Noise if misconfigured | — | flake8/black | CI |
| **import-linter** (planned) | Architecture boundaries | Enforces isolation | Setup cost | Custom checker | grimp | CI |

---

## 15. Development Tools

| Technology | Purpose | Advantages | Limitations | Future replacements | Alternatives | Integration points |
|------------|---------|------------|-------------|---------------------|--------------|--------------------|
| **Git** | Version control | Universal | — | — | — | Branch strategy |
| **uv / poetry / pip-tools** (pick one) | Python deps | Reproducible locks | Team must standardize | — | raw pip | `pyproject.toml` |
| **pnpm / npm** | JS deps | Lockfiles | — | — | yarn | `apps/web` |
| **Ollama CLI** | Model pull/run | Simple | Separate install | Bundled runtime | LM Studio | Doctor |
| **Cursor / VS Code** | IDE | AI-assisted coding within specs | Can invent architecture if unconstrained | — | — | Follow `DEVELOPMENT_GUIDE` |
| **OpenAPI generator** (optional) | TS client from API | Contract sync | Drift if not gated | Hand types | orval, openapi-typescript | `packages/shared-types` |
| **Alembic** (or SQL migrations) | DB migrations | Ordered upgrades | — | — | custom SQL runner | `backend/app/db/migrations` |
| **FFmpeg build** | Native binary | Required for render | Must document install | Bundled in installer later | — | Doctor PATH check |

---

## 16. Stack Integration Map

```
┌──────────────── Frontend ────────────────┐
│ Next.js · React · TS · Tailwind · FM     │
└───────────────────┬──────────────────────┘
                    │ HTTP /api/v1
┌───────────────────▼──────────────────────┐
│ FastAPI · Pydantic · Services · LangGraph│
└─┬─────────┬─────────┬─────────┬──────────┘
  │         │         │         │
  ▼         ▼         ▼         ▼
Ollama    Piper   IndicTrans2  Whisper.cpp
Qwen2.5   TTS     (optional)   (optional)
  │         │         │         │
  └─────────┴──── Agents ───────┘
                    │
                    ▼
        Presentation Engine (SVG/icons/charts)
                    │
                    ▼
        Animation · Camera · Timeline Engines
                    │
                    ▼
        OpenCV/MoviePy helpers → FFmpeg → MP4
                    │
                    ▼
        SQLite + Filesystem (data/)
```

---

## 17. Technology Decision Summary Table

| Layer | Choice | Why selected |
|-------|--------|--------------|
| Frontend | Next.js + React + TS + Tailwind | Productive local UI, typed contracts |
| UI motion | Framer Motion | Polish without touching video IR |
| Backend | Python + FastAPI | AI/media ecosystem + typed API |
| Orchestration | LangGraph | Explicit multi-agent pipeline |
| DB | SQLite → Postgres later | Offline desktop now; scale later |
| LLM | Ollama + Qwen2.5 3B | Free, local, RAM-fit |
| Translation | IndicTrans2 | Free local MT |
| Voice | Piper | Free CPU TTS |
| Subtitles | Beat timing + optional Whisper.cpp | Offline captions |
| Visuals | Procedural SVG + Lucide/Heroicons/OpenMoji/Undraw | Diagram-first education |
| Animation | Custom Python engines | Deterministic DSL-driven motion |
| Render | FFmpeg + MoviePy + OpenCV | Reliable MP4 offline |
| Tests | pytest + goldens (+ Playwright optional) | Contract + IR stability |

---

## Closing Statement

ExplainX’s stack is chosen for a single mission:

> Run a free, offline, presentation-to-video engine on a mid-range Windows laptop — with swappable adapters when the future demands more.

Every technology must earn its place against **cost, offline capability, RAM, and architectural isolation**.

---

*End of TECH_STACK.md*  
*ExplainX Engineering — Free. Local. Replaceable Behind Ports.*
