# ExplainX — Project Constitution

**Document Status:** Canonical Architecture Reference  
**Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Classification:** Internal Engineering Design Document  

> **Authority:** This document is the permanent architectural source of truth for ExplainX.  
> All design decisions, implementation plans, Cursor prompts, pull requests, and reviews MUST align with this constitution.  
> When conflict arises between informal discussion and this document, **this document wins** until it is deliberately amended.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision & Positioning](#2-product-vision--positioning)
3. [What ExplainX Is — and Is Not](#3-what-explainx-is--and-is-not)
4. [Core Philosophy](#4-core-philosophy)
5. [System Constraints](#5-system-constraints)
6. [High-Level Architecture](#6-high-level-architecture)
7. [End-to-End Pipeline](#7-end-to-end-pipeline)
8. [Presentation DSL — The Central Language](#8-presentation-dsl--the-central-language)
9. [Multi-Agent System](#9-multi-agent-system)
10. [Visual Generation Strategy](#10-visual-generation-strategy)
11. [Theme System](#11-theme-system)
12. [Animation & Camera Engines](#12-animation--camera-engines)
13. [Rendering & Export System](#13-rendering--export-system)
14. [Primary Feature Specifications](#14-primary-feature-specifications)
15. [Plugin System](#15-plugin-system)
16. [Technology Stack](#16-technology-stack)
17. [Data Model & Persistence](#17-data-model--persistence)
18. [Expected Folder Structure](#18-expected-folder-structure)
19. [Development Philosophy & Engineering Standards](#19-development-philosophy--engineering-standards)
20. [Interface Contracts & Communication Rules](#20-interface-contracts--communication-rules)
21. [Error Handling, Logging & Observability](#21-error-handling-logging--observability)
22. [Testing Strategy](#22-testing-strategy)
23. [Security & Privacy](#23-security--privacy)
24. [Performance Budgets](#24-performance-budgets)
25. [Future Roadmap](#25-future-roadmap)
26. [Amendment Process](#26-amendment-process)
27. [Glossary](#27-glossary)
28. [Appendix: Architecture Diagrams](#28-appendix-architecture-diagrams)

---

## 1. Executive Summary

ExplainX is an **offline-first AI Presentation-to-Video Engine** that converts educational content into professional animated explainer videos.

The user experience is deliberately simple:

1. Upload a document (or enter a topic).
2. Configure language, theme, voice, and difficulty.
3. Receive an MP4 video plus narration, subtitles, thumbnail, metadata, and a saved project.

Internally, ExplainX never asks the user to design slides. It extracts knowledge, writes narration, plans scenes, compiles a **Presentation DSL**, builds an animation timeline, and renders video — entirely on the user's machine.

This constitution defines:

- Product boundaries and non-goals  
- Modular multi-agent architecture  
- Presentation DSL as the system lingua franca  
- Visual strategy (SVG / icons / diagrams first; generative images later as optional plugins)  
- Offline, free, CPU-compatible constraints  
- Engineering standards for production-quality software  

**No application code is implied by this document alone.** Implementation begins only after this constitution is accepted as the project baseline.

---

## 2. Product Vision & Positioning

### 2.1 Vision Statement

> ExplainX turns any educational document or topic into a clear, narrated, animated explainer video — without cloud APIs, without paid models, and without the user ever touching a slide editor.

### 2.2 Target Users

| Persona | Need | ExplainX Value |
|---------|------|----------------|
| Students | Understand dense textbooks | Topic → short explainer |
| Teachers | Create lesson videos | Document → classroom-ready MP4 |
| Self-learners | Offline study aids | Local, private, free generation |
| Content creators (education niche) | Fast explainer drafts | Structured scenes + voice + subtitles |
| Institutions with air-gapped labs | No cloud dependency | 100% offline pipeline |

### 2.3 Value Proposition

| Dimension | Promise |
|-----------|---------|
| Privacy | Content never leaves the device |
| Cost | Zero paid APIs; free models and assets |
| Quality | Structured explanation, not random video |
| Control | Themes, languages, difficulty, saved projects |
| Reliability | Deterministic pipeline stages with typed contracts |

### 2.4 Success Criteria (Product)

A Version 1 success looks like:

- User uploads a PDF on a constrained Windows laptop.
- Pipeline completes offline end-to-end.
- Output includes MP4, narration audio, subtitle file, thumbnail, metadata JSON, and a reloadable project.
- Video feels like a designed explainer presentation, not AI noise or stock-slideshow collage.

---

## 3. What ExplainX Is — and Is Not

### 3.1 What ExplainX Is

ExplainX is a **Presentation-to-Video Engine**.

Internally it always builds:

```
Document → Knowledge → Narration → Scenes → Presentation DSL → Timeline → Rendered MP4
```

The intermediate presentation is a first-class artifact of the system. The user never sees it as an interactive slide deck; they only receive the rendered video and related exports.

### 3.2 What ExplainX Is Not

| Not This | Why |
|----------|-----|
| Sora / Veo / Runway-style AI video | Those synthesize pixels frame-by-frame from prompts. ExplainX synthesizes **structured presentations** and renders them. |
| Generic “AI video generator” | Output is explanatory animation of concepts, not cinematic footage. |
| Slide editor product (PowerPoint clone) | Presentation exists for machines, not for manual editing in V1. |
| Cloud SaaS model marketplace | Offline-first, no paid APIs. |
| Image-generation-first tool | Visuals are predominantly SVG, icons, shapes, charts, and diagrams. |

### 3.3 Critical Product Rule

```
RULE: The user uploads a document and receives an MP4.
      The internal presentation is never the primary UI surface in V1.
```

Future versions may expose limited project inspection or collaborative editing (see Roadmap). Those features must not redefine the core identity of ExplainX as a presentation-to-video engine.

---

## 4. Core Philosophy

### 4.1 Architecture First

ExplainX is **not** a hackathon prototype. Architecture precedes code. Modules, contracts, and agent boundaries are designed before implementation.

### 4.2 Modular Multi-Agent Design

Every AI capability is an **independent agent** with:

- A single primary responsibility  
- Typed JSON inputs and outputs  
- No side-channel mutation of other agents’ artifacts  
- Explicit ownership of its output schema  

### 4.3 Presentation DSL as Central Language

After scene planning and visual planning, all downstream systems speak **Presentation DSL**:

- Animation Engine consumes DSL  
- Camera Engine consumes DSL + camera plan  
- Renderer consumes compiled timeline derived from DSL  
- Themes decorate DSL without rewriting semantic content  

### 4.4 Composition Over Monoliths

Prefer:

- Small agents + orchestrator (LangGraph)  
- Pure transforms where possible  
- Dependency injection for engines (TTS, LLM, renderer backends)  

Avoid:

- God-services that parse + narrate + render  
- Agents that “fix up” previous stages by rewriting unrelated fields  
- Hidden shared mutable state between agents  

### 4.5 Design Principles (SOLID-aligned)

| Principle | Application |
|-----------|-------------|
| Single Responsibility | One agent = one job |
| Open/Closed | Plugins extend without modifying core agents |
| Liskov Substitution | Renderer backends / TTS backends interchangeable behind interfaces |
| Interface Segregation | Narrow JSON contracts per agent |
| Dependency Inversion | Agents depend on abstractions (LLM port, TTS port), not concrete vendors |

### 4.6 Quality Attributes

Ordered priorities for V1:

1. Correctness of explanation structure  
2. Offline reliability  
3. Deterministic contracts and validation  
4. Memory/CPU fit on target hardware  
5. Visual clarity of diagrams  
6. Extensibility via plugins  

---

## 5. System Constraints

### 5.1 Non-Negotiable Constraints

| Constraint | Requirement |
|------------|-------------|
| Cost | 100% free software and models for core path |
| Network | Fully usable offline after model/asset install |
| APIs | No paid cloud AI APIs in the core product |
| Hardware | Must run on Intel i7-1255U, 16GB RAM, Intel Iris Xe |
| OS (primary) | Windows (first-class) |
| Compute | CPU-compatible; GPU optional, never required |
| Privacy | User documents processed locally by default |

### 5.2 Target Hardware Profile

```
CPU:     Intel Core i7-1255U (or equivalent)
RAM:     16 GB
GPU:     Intel Iris Xe (optional acceleration only)
Storage: SSD recommended for models + project cache
OS:      Windows 10/11
```

### 5.3 Model Footprint Guidance

| Component | Expected Role | Footprint Intent |
|-----------|---------------|------------------|
| Qwen2.5 3B (via Ollama) | Local LLM reasoning | Fit within 16GB with room for OS + app |
| IndicTrans2 | Local translation | Loaded on demand when translating |
| Piper TTS | Local speech synthesis | Lightweight CPU voices |
| Whisper.cpp | Optional alignment / ASR utilities | Used carefully; not for every frame |

### 5.4 Forbidden Dependencies (Core Path)

- Paid OpenAI / Anthropic / Google generative APIs  
- Cloud-only rendering farms (until Version 4 optional path)  
- Proprietary asset packs that block redistribution  
- Any agent that requires internet at runtime for core generation  

Internet may be used only for:

- Initial download of free models/assets (installer phase)  
- Optional future cloud rendering (explicit opt-in, Version 4+)  

---

## 6. High-Level Architecture

### 6.1 Layered System View

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER (UI)                         │
│                    Next.js · React · Tailwind · Framer Motion           │
│         Upload · Project Status · Settings · Preview · Export Download  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS / local API
┌───────────────────────────────────▼─────────────────────────────────────┐
│                         APPLICATION LAYER (API)                         │
│                              FastAPI · Python                           │
│              Auth-less local session · Job queue · Project CRUD         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                      ORCHESTRATION LAYER (LangGraph)                    │
│                     Multi-agent pipeline graph + state                  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐
│  Knowledge Plane │    │  Presentation    │    │  Media Plane         │
│  Parse → Clean → │    │  DSL Plane       │    │  Voice · Subtitles · │
│  Structure → Know│    │  Layout · Theme  │    │  Timeline · Render   │
│  Script · Scenes │    │  Assets · Anim   │    │  Export · Thumbnail  │
└──────────────────┘    └──────────────────┘    └──────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                         INFRASTRUCTURE LAYER                            │
│     SQLite · Filesystem Project Store · Ollama · Piper · FFmpeg         │
│              Logging · Validation · Plugin Registry                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Runtime Topology

ExplainX runs as a **local application stack**:

1. **Frontend** — Next.js desktop/web UI served locally  
2. **Backend** — FastAPI process on localhost  
3. **Model servers** — Ollama (and other local binaries) as managed subprocesses or system services  
4. **Workers** — Pipeline jobs executed via orchestrator; long jobs are asynchronous  

### 6.3 Ownership Boundaries

| Layer | Owns | Must Not Own |
|-------|------|--------------|
| UI | UX, progress, settings, downloads | Agent logic, DSL semantics |
| API | Jobs, persistence, validation entry | Scene animation math |
| Orchestrator | Agent order, retries, state machine | Theme pixel details |
| Agents | Their JSON transform | Direct FFmpeg invocation (except Rendering Agent) |
| Engines | Reusable non-AI libraries (layout, anim, camera, render) | LLM prompting |

**Important:** Agents may *call* engines. Engines must remain LLM-agnostic where possible.

---

## 7. End-to-End Pipeline

### 7.1 Canonical Pipeline Flow

```
┌────────────┐
│  Document  │  PDF / DOCX / TXT / MD / Topic
│  or Topic  │
└─────┬──────┘
      ▼
┌────────────┐
│   Parser   │  Raw structured text + assets refs
└─────┬──────┘
      ▼
┌────────────┐
│  Cleaning  │  Normalized plain content
└─────┬──────┘
      ▼
┌────────────┐
│ Structure  │  Sections, hierarchy, units
└─────┬──────┘
      ▼
┌────────────┐
│ Knowledge  │  Concepts, facts, relations
└─────┬──────┘
      ▼
┌────────────────────┐
│ Topic Classification│  Domain tags
└─────────┬──────────┘
          ▼
┌────────────┐
│ Difficulty │  Audience level
└─────┬──────┘
      ▼
┌─────────────────────┐
│ Explanation Strategy│  Pedagogical approach
└──────────┬──────────┘
           ▼
┌────────────┐
│   Script   │  Narration script + beats
└─────┬──────┘
      ▼
┌──────────────┐
│ Scene Planner│  Scene list + learning goals
└──────┬───────┘
       ▼
┌──────────────┐
│   Metadata   │  Title, tags, duration estimate
└──────┬───────┘
       ▼
┌────────────────┐
│ Visual Planning│  HOW to explain visually (diagram recipes)
└──────┬─────────┘
       ▼
┌──────────────┐
│ Layout Planner│  Spatial composition
└──────┬───────┘
       ▼
┌──────────────┐
│ Theme Planner│  Theme tokens applied
└──────┬───────┘
       ▼
┌────────────┐
│   Assets   │  Icons/SVG/charts resolved
└─────┬──────┘
      ▼
┌─────────────────┐
│ Presentation DSL│  ★ Central artifact
└─────┬───────────┘
      ▼
┌────────────┐
│ Animation  │  Motion intents → keyframes
└─────┬──────┘
      ▼
┌────────────┐
│   Camera   │  Shots, pans, zooms
└─────┬──────┘
      ▼
┌─────────────────┐
│ Animation Timeline│  Absolute timeline
└─────┬───────────┘
      ▼
┌────────────┐     ┌────────────┐     ┌────────────┐
│   Voice    │     │ Translation│     │  Subtitles │
│   (TTS)    │     │ (optional) │     │            │
└─────┬──────┘     └─────┬──────┘     └─────┬──────┘
      └────────────┬─────┴──────────────────┘
                   ▼
┌────────────┐
│ Rendering  │  Frames + mux → MP4
└─────┬──────┘
      ▼
┌────────────┐
│   Export   │  MP4 · audio · SRT/VTT · thumb · metadata · project
└─────┬──────┘
      ▼
┌────────────────┐
│ Project Manager│  Persist / resume / version project
└────────────────┘
```

### 7.2 User-Visible vs Internal Artifacts

| Artifact | User-visible? | Purpose |
|----------|---------------|---------|
| Source document | Yes (upload) | Input |
| Knowledge graph / concepts | No (V1) | Reasoning intermediate |
| Narration script | Optional export later | Voice + subtitles source |
| Presentation DSL | No (V1) | Machine presentation |
| Animation timeline | No | Render input |
| MP4 | Yes | Primary output |
| Subtitles | Yes | Accessibility / learning |
| Thumbnail | Yes | Library preview |
| Metadata JSON | Yes | Cataloging |
| Saved project | Yes | Resume / regenerate |

### 7.3 Pipeline Invariants

1. Every stage validates its output schema before the next stage starts.  
2. No stage mutates a previous stage’s stored artifact in place; it produces a new artifact or annotated copy.  
3. Failures are attributed to a stage with structured error codes.  
4. Re-runs may reuse cached upstream artifacts when inputs and agent versions match.  

---

## 8. Presentation DSL — The Central Language

### 8.1 Role

The Presentation DSL is the **semantic + visual intermediate representation** of the internal presentation.

It is:

- Human-auditable (JSON)  
- Theme-agnostic at the semantic layer  
- Consumable by Animation, Camera, and Rendering agents/engines  
- Versioned (`dsl_version`)  

### 8.2 Design Goals

| Goal | Description |
|------|-------------|
| Completeness | Enough to render a full explainer without re-querying the LLM |
| Stability | Downstream engines should rarely need LLM calls |
| Diffability | JSON diffs show what changed between regenerations |
| Extensibility | Unknown node types ignored safely or rejected by version gates |

### 8.3 Conceptual Schema (Illustrative)

> Exact schemas will live in typed Pydantic / Zod models during implementation. The following is the constitutional shape.

```json
{
  "dsl_version": "1.0",
  "project_id": "uuid",
  "meta": {
    "title": "Binary Search Explained",
    "language": "en",
    "theme_id": "notebooklm",
    "target_duration_sec": 180,
    "difficulty": "intermediate"
  },
  "scenes": [
    {
      "id": "scene_01",
      "purpose": "Introduce sorted array and search goal",
      "narration_ref": "nar_01",
      "duration_hint_sec": 20,
      "layout": {
        "type": "split_diagram",
        "regions": ["title", "main_stage", "caption"]
      },
      "elements": [
        {
          "id": "arr",
          "kind": "array",
          "props": { "values": [2, 5, 8, 12, 16, 23, 38], "sorted": true },
          "style_tokens": ["emphasis-neutral"]
        },
        {
          "id": "ptr_low",
          "kind": "pointer",
          "props": { "label": "low", "target": "arr[0]" }
        }
      ],
      "visual_recipe": {
        "strategy": "algorithm_trace",
        "steps": ["show_array", "highlight_bounds", "compare_mid", "narrow_range"]
      },
      "animations": [],
      "camera": { "preset": "focus_stage", "keyframes": [] }
    }
  ],
  "assets": [],
  "theme": { "id": "notebooklm", "tokens": {} },
  "timeline_bindings": []
}
```

### 8.4 Element Kind Catalog (V1 Intent)

| Kind | Typical Use |
|------|-------------|
| `text` | Titles, labels, captions |
| `shape` | Rect, circle, ellipse, line |
| `icon` | Lucide / Heroicons / OpenMoji references |
| `arrow` | Directional relationships |
| `array` / `list` | CS teaching structures |
| `tree` / `graph` | Hierarchical / network concepts |
| `chart` | Bar / line / pie for quantitative ideas |
| `equation` | Lightweight math display (SVG/text) |
| `group` | Nested composition |
| `callout` | Short pedagogical notes (used sparingly) |
| `image` | Optional plugin-provided bitmap (not core default) |

### 8.5 DSL Rules

1. Semantic meaning lives in `kind` + `props`, not in theme colors.  
2. Themes map `style_tokens` → concrete colors/fonts.  
3. Animation Agent adds motion to elements; it does not invent new pedagogical content.  
4. Camera Agent frames existing elements; it does not add new concepts.  
5. Rendering Agent is a consumer, not an author, of DSL meaning.  

---

## 9. Multi-Agent System

### 9.1 Orchestration Model

Agents are nodes in a **LangGraph** state machine. Shared state is a typed `PipelineState` object. Agents read declared inputs and write declared outputs only.

```
RULE: Agents communicate ONLY through structured JSON (validated schemas).
RULE: No agent may directly mutate another agent's output object in shared memory.
      Downstream agents produce NEW artifacts that REFERENCE upstream IDs.
```

### 9.2 Agent Catalog Overview

| Agent | Plane | Primary Output |
|-------|-------|----------------|
| Parser Agent | Knowledge | RawDocument |
| Cleaning Agent | Knowledge | CleanDocument |
| Structure Agent | Knowledge | DocumentStructure |
| Knowledge Agent | Knowledge | KnowledgeModel |
| Topic Classification Agent | Knowledge | TopicLabels |
| Difficulty Agent | Knowledge | DifficultyProfile |
| Explanation Strategy Agent | Knowledge | ExplanationPlan |
| Script Agent | Narrative | NarrationScript |
| Scene Planner | Narrative | ScenePlan |
| Metadata Agent | Narrative | ProjectMetadata |
| Visual Planning Agent | Presentation | VisualPlan |
| Layout Planner | Presentation | LayoutPlan |
| Theme Planner | Presentation | ThemeApplication |
| Asset Agent | Presentation | AssetManifest |
| Animation Agent | Motion | AnimationPlan |
| Camera Agent | Motion | CameraPlan |
| Translation Agent | Media | TranslatedArtifacts |
| Voice Agent | Media | AudioTracks |
| Subtitle Agent | Media | SubtitleDocuments |
| Rendering Agent | Media | RenderedMedia |
| Project Manager Agent | Control | ProjectRecord |

---

### 9.3 Parser Agent

**Purpose**  
Ingest source files or topic strings and extract raw textual (and optional embedded) content without interpreting pedagogy.

**Inputs**
- Source type: `pdf` | `docx` | `txt` | `md` | `topic`
- File path or topic string
- Locale hints (optional)

**Outputs**
```json
{
  "raw_document_id": "...",
  "source_type": "pdf",
  "pages_or_sections": [{ "id": "...", "text": "...", "order": 1 }],
  "warnings": [],
  "extraction_stats": { "char_count": 0, "page_count": 0 }
}
```

**Responsibilities**
- Format-specific parsing  
- Preserve reading order where possible  
- Record extraction warnings (scanned PDF with no text, etc.)  

**Future Improvements**
- OCR for scanned PDFs (optional local plugin)  
- Table structure preservation  
- Citation / footnote extraction  

---

### 9.4 Cleaning Agent

**Purpose**  
Normalize noisy extracted text into clean instructional content.

**Inputs**
- `RawDocument`

**Outputs**
```json
{
  "clean_document_id": "...",
  "text": "...",
  "removed_artifacts": ["headers", "page_numbers"],
  "normalization": { "unicode": true, "whitespace": true }
}
```

**Responsibilities**
- Strip repeated headers/footers  
- Normalize whitespace and unicode  
- Remove non-instructional junk when confidently detected  
- Preserve technical tokens (code, formulas markers)  

**Future Improvements**
- Domain-specific cleaners (legal vs CS textbooks)  
- Deduplication of repeated boilerplate  

---

### 9.5 Structure Agent

**Purpose**  
Recover hierarchical document structure for teaching units.

**Inputs**
- `CleanDocument`

**Outputs**
```json
{
  "structure_id": "...",
  "title_guess": "...",
  "sections": [
    { "id": "s1", "heading": "...", "level": 1, "children": [], "text_span": [0, 120] }
  ]
}
```

**Responsibilities**
- Heading detection  
- Section segmentation  
- Ordering and nesting  
- Identify candidates for scene boundaries  

**Future Improvements**
- Multi-document course structure  
- Learning-objective tagging per section  

---

### 9.6 Knowledge Agent

**Purpose**  
Extract teachable concepts, definitions, relationships, and examples.

**Inputs**
- `CleanDocument` + `DocumentStructure`

**Outputs**
```json
{
  "knowledge_id": "...",
  "concepts": [{ "id": "c1", "name": "Binary Search", "definition": "...", "prerequisites": [] }],
  "relations": [{ "from": "c1", "to": "c2", "type": "uses" }],
  "examples": [],
  "misconceptions": []
}
```

**Responsibilities**
- Concept inventory  
- Prerequisite links  
- Example and counterexample capture  
- Fact vs explanation separation  

**Future Improvements**
- Lightweight knowledge graph visualization for debugging  
- Cross-project concept reuse  

---

### 9.7 Topic Classification Agent

**Purpose**  
Classify domain and subtopics to guide visuals, metaphors, and theme defaults.

**Inputs**
- `KnowledgeModel` (+ optional user topic override)

**Outputs**
```json
{
  "topic_id": "...",
  "primary_domain": "computer_science",
  "subtopics": ["algorithms", "searching"],
  "confidence": 0.86
}
```

**Responsibilities**
- Domain labeling  
- Subtopic tags  
- Confidence scoring  

**Future Improvements**
- Multi-label hierarchical taxonomy  
- Curriculum alignment tags (e.g., school grade frameworks)  

---

### 9.8 Difficulty Agent

**Purpose**  
Estimate audience difficulty and adjust explanation depth.

**Inputs**
- Knowledge + topic labels + optional user preference

**Outputs**
```json
{
  "difficulty_id": "...",
  "level": "beginner" | "intermediate" | "advanced",
  "assumed_prerequisites": [],
  "depth_policy": { "definitions_first": true, "formula_density": "low" }
}
```

**Responsibilities**
- Level assignment  
- Depth policy for Script / Scene agents  
- Flag overly dense source material  

**Future Improvements**
- Adaptive difficulty per scene  
- User pretest-driven profiles  

---

### 9.9 Explanation Strategy Agent

**Purpose**  
Choose pedagogical strategy before scripting.

**Inputs**
- Knowledge + difficulty + topic labels

**Outputs**
```json
{
  "strategy_id": "...",
  "approach": "worked_example" | "concept_then_example" | "compare_contrast" | "process_flow" | "story_hook",
  "outline": ["hook", "core_idea", "steps", "recap"],
  "constraints": { "max_scenes": 12 }
}
```

**Responsibilities**
- Select explanation pattern  
- Produce high-level outline  
- Bound scene count / duration  

**Future Improvements**
- Strategy ensembles  
- A/B strategy scoring with offline heuristics  

---

### 9.10 Script Agent

**Purpose**  
Write the narration script aligned to strategy and knowledge.

**Inputs**
- ExplanationPlan + KnowledgeModel + DifficultyProfile + language

**Outputs**
```json
{
  "script_id": "...",
  "language": "en",
  "beats": [
    { "id": "nar_01", "text": "...", "scene_hint": "intro", "approx_sec": 12 }
  ],
  "glossary_terms": []
}
```

**Responsibilities**
- Clear spoken narration  
- Beat segmentation for scenes  
- Avoid unspeakable formatting  
- Keep sentences TTS-friendly  

**Future Improvements**
- Style presets (teacher, documentary, playful)  
- Automatic pacing optimization from TTS durations  

---

### 9.11 Scene Planner

**Purpose**  
Partition the script into scenes with learning goals.

**Inputs**
- NarrationScript + ExplanationPlan + KnowledgeModel

**Outputs**
```json
{
  "scene_plan_id": "...",
  "scenes": [
    {
      "id": "scene_01",
      "goal": "Define binary search preconditions",
      "narration_beat_ids": ["nar_01"],
      "must_include_concepts": ["c1"]
    }
  ]
}
```

**Responsibilities**
- Scene boundaries  
- Concept coverage checks  
- Avoid overcrowded scenes  
- Ensure intro/recap when strategy requires  

**Future Improvements**
- Automatic scene merge/split based on duration  
- Quiz-question scene inserts (optional mode)  

---

### 9.12 Metadata Agent

**Purpose**  
Produce project-level metadata for library, export, and search.

**Inputs**
- Topic labels + script + scene plan + user settings

**Outputs**
```json
{
  "title": "Binary Search Explained",
  "description": "...",
  "tags": ["algorithms", "search"],
  "language": "en",
  "estimated_duration_sec": 180,
  "thumbnail_prompt_notes": "array with mid pointer"
}
```

**Responsibilities**
- Title/description generation  
- Tagging  
- Duration estimation  
- Export metadata package  

**Future Improvements**
- SEO-like educational metadata schemas  
- Chapter markers for long videos  

---

### 9.13 Visual Planning Agent

**Purpose**  
Decide **HOW** each concept should be explained visually — the most important creative planning step before layout.

**Inputs**
- ScenePlan + KnowledgeModel + TopicLabels

**Outputs**
```json
{
  "visual_plan_id": "...",
  "scenes": [
    {
      "scene_id": "scene_01",
      "explanation_mode": "algorithm_trace",
      "primitives": ["array", "pointers", "highlight", "comparison", "arrows"],
      "forbidden": ["photoreal_human", "decorative_noise"],
      "steps": ["show_sorted_array", "set_bounds", "compare_mid", "halve_space"]
    }
  ]
}
```

**Responsibilities**
- Choose visual explanation mode per scene  
- Specify diagram primitives (not bitmaps)  
- Sequence visual steps matching narration  
- Prefer SVG/icon/shape vocabularies  

**Future Improvements**
- Learned visual templates per domain  
- Optional generative image plugin hooks (V3)  

**See also:** [Section 10 — Visual Generation Strategy](#10-visual-generation-strategy)

---

### 9.14 Layout Planner

**Purpose**  
Convert visual plans into spatial layouts and element skeletons.

**Inputs**
- VisualPlan + ScenePlan

**Outputs**
```json
{
  "layout_plan_id": "...",
  "scenes": [
    {
      "scene_id": "scene_01",
      "canvas": { "aspect": "16:9", "safe_margins": true },
      "regions": { "title": {...}, "stage": {...}, "caption": {...} },
      "elements": [{ "id": "arr", "kind": "array", "bbox_hint": [...] }]
    }
  ]
}
```

**Responsibilities**
- Region allocation  
- Element placement hints  
- Collision avoidance policies  
- Accessibility sizing minima  

**Future Improvements**
- Auto-layout solvers  
- RTL layout packs  

---

### 9.15 Theme Planner

**Purpose**  
Apply a selected theme’s tokens without changing pedagogical content.

**Inputs**
- LayoutPlan + user `theme_id`

**Outputs**
```json
{
  "theme_application_id": "...",
  "theme_id": "notebooklm",
  "tokens": { "bg": "...", "fg": "...", "accent": "...", "font_display": "...", "font_body": "..." },
  "per_element_style_tokens": { "arr": ["emphasis-neutral"] }
}
```

**Responsibilities**
- Resolve theme pack  
- Map semantic style tokens  
- Validate contrast where feasible  
- Keep semantic props untouched  

**Future Improvements**
- User theme packs  
- Watercolor / Anime packs (roadmap themes)  

---

### 9.16 Asset Agent

**Purpose**  
Resolve concrete assets (icons, SVG diagrams, charts) required by layouts.

**Inputs**
- LayoutPlan + VisualPlan + ThemeApplication

**Outputs**
```json
{
  "asset_manifest_id": "...",
  "assets": [
    { "id": "icon_sun", "type": "svg", "source": "openmoji", "key": "sun", "path": "..." }
  ],
  "missing": []
}
```

**Responsibilities**
- Map abstract needs → local asset libraries  
- Prefer Lucide / Heroicons / OpenMoji / Undraw  
- Generate simple SVG procedurally when no icon fits  
- Record missing assets for fallbacks  

**Future Improvements**
- Procedural diagram compilers per domain  
- Optional AI image plugin resolution (V3)  

---

### 9.17 Animation Agent

**Purpose**  
Attach motion intents and keyframes to DSL elements.

**Inputs**
- Presentation DSL draft (layout+assets+theme) + VisualPlan steps + narration timing hints

**Outputs**
```json
{
  "animation_plan_id": "...",
  "clips": [
    {
      "element_id": "ptr_mid",
      "preset": "move_to",
      "easing": "ease_in_out",
      "t": [0.2, 0.45],
      "params": { "to": "arr[3]" }
    }
  ]
}
```

**Responsibilities**
- Translate visual steps into animations  
- Keep motion pedagogical (not decorative spam)  
- Sync approximate timing to narration beats  

**Future Improvements**
- Physics-lite transitions  
- Emphasis detection from script prosody  

---

### 9.18 Camera Agent

**Purpose**  
Plan camera moves (pan/zoom/focus) across the stage.

**Inputs**
- DSL + AnimationPlan + Scene goals

**Outputs**
```json
{
  "camera_plan_id": "...",
  "shots": [
    { "scene_id": "scene_01", "type": "zoom_to", "target": "arr", "t": [0.0, 0.2] }
  ]
}
```

**Responsibilities**
- Framing for clarity  
- Avoid motion sickness (limits on speed/zoom)  
- Focus attention on active teaching elements  

**Future Improvements**
- Cinematic presets per theme  
- Multi-focus cutaways for complex diagrams  

---

### 9.19 Translation Agent

**Purpose**  
Local translation of script/subtitles/metadata using IndicTrans2 (and future local models).

**Inputs**
- NarrationScript / Metadata / Subtitles + target language

**Outputs**
```json
{
  "translation_id": "...",
  "source_lang": "en",
  "target_lang": "hi",
  "units": [{ "ref": "nar_01", "text": "..." }]
}
```

**Responsibilities**
- Translate user-selected fields  
- Preserve technical terms when configured  
- Produce parallel language packs in project  

**Future Improvements**
- More language pairs  
- Glossary-constrained decoding  

---

### 9.20 Voice Agent

**Purpose**  
Synthesize narration audio with Piper TTS (local).

**Inputs**
- (Translated) NarrationScript + voice profile + pacing settings

**Outputs**
```json
{
  "audio_id": "...",
  "tracks": [
    { "beat_id": "nar_01", "path": "audio/nar_01.wav", "duration_sec": 11.4 }
  ],
  "voice_id": "en_US-lessac-medium"
}
```

**Responsibilities**
- TTS generation  
- Per-beat audio files + concatenated master  
- Accurate durations for timeline alignment  

**Future Improvements**
- Multi-speaker modes  
- Emotion / emphasis controls within free voice limits  

---

### 9.21 Subtitle Agent

**Purpose**  
Generate timed subtitles from script + audio durations (and optional Whisper.cpp alignment).

**Inputs**
- Narration beats + audio durations (+ optional alignment)

**Outputs**
```json
{
  "subtitle_id": "...",
  "formats": ["srt", "vtt"],
  "cues": [{ "start": 0.0, "end": 2.1, "text": "..." }]
}
```

**Responsibilities**
- Cue segmentation for readability  
- Timing alignment  
- Export SRT/VTT  
- Burn-in optional flag for renderer  

**Future Improvements**
- Word-level karaoke captions  
- Dual-language subtitles  

---

### 9.22 Rendering Agent

**Purpose**  
Rasterize animated presentation frames and mux final media with FFmpeg / MoviePy / OpenCV as appropriate.

**Inputs**
- Final Presentation DSL + Animation Timeline + Audio + Subtitles + export settings

**Outputs**
```json
{
  "render_id": "...",
  "mp4_path": "export/video.mp4",
  "thumbnail_path": "export/thumb.jpg",
  "logs": []
}
```

**Responsibilities**
- Frame rendering  
- Audio muxing  
- Thumbnail capture  
- Resource-aware encoding on CPU / Iris Xe when available  

**Future Improvements**
- Hardware encoder auto-detect  
- Cloud render backend plugin (V4)  

---

### 9.23 Project Manager Agent

**Purpose**  
Own project lifecycle: create, persist, resume, invalidate caches, export package.

**Inputs**
- User actions + all stage artifacts

**Outputs**
```json
{
  "project_id": "...",
  "status": "draft" | "running" | "failed" | "completed",
  "artifact_index": {},
  "versions": []
}
```

**Responsibilities**
- Project CRUD  
- Artifact indexing on disk + SQLite pointers  
- Resume from last successful stage  
- Coordinate cancellation  

**Future Improvements**
- Project templates  
- Collaborative locks (V5)  

---

## 10. Visual Generation Strategy

### 10.1 Constitutional Rule

```
RULE: ExplainX MUST NOT rely on AI image generation for every scene.
      Visual Planning decides HOW a concept is explained.
      Most visuals are composed from SVG, icons, shapes, charts, arrows, and diagrams.
      Image generation is a future OPTIONAL plugin, not a core dependency.
```

### 10.2 Why Diagram-First

Educational clarity comes from **structured visual rhetoric**:

- Highlight the active element  
- Show relationships with arrows  
- Animate state changes over time  
- Label parts explicitly  

Generative images often fail at:

- Consistent iconography across scenes  
- Precise algorithmic state  
- Readable labels  
- Offline cost/latency budgets  

### 10.3 Visual Explanation Patterns

#### Example A — Binary Search

```
Binary Search
    ↓
Sorted Array (cells)
    ↓
Highlight bounds (low/high)
    ↓
Comparison at mid
    ↓
Arrow / pointer movement
    ↓
Animate range narrowing
```

Primitives: `array`, `pointer`, `highlight`, `comparison_badge`, `arrow`

#### Example B — Photosynthesis

```
Photosynthesis
    ↓
Sun icon
    ↓
Leaf diagram
    ↓
Water + CO₂ inputs
    ↓
Arrows into chloroplast region
    ↓
Labels (glucose, O₂)
    ↓
Process animation
```

Primitives: `icon`, `shape`, `arrow`, `label`, `process_flow`

#### Example C — Networking

```
Networking
    ↓
Client node
    ↓
Server node
    ↓
Packet tokens
    ↓
Path arrows
    ↓
Animate request/response
```

Primitives: `node`, `edge`, `token`, `arrow`, `sequence`

### 10.4 Visual Mode Taxonomy

| Mode | Best For | Core Primitives |
|------|----------|-----------------|
| `algorithm_trace` | CS algorithms | arrays, trees, pointers, highlights |
| `process_flow` | Biology/chem processes | stages, arrows, resource icons |
| `system_diagram` | Networks/architecture | nodes, edges, packets |
| `compare_contrast` | Tradeoffs | dual panels, markers |
| `definition_card` | Short concepts | title, icon, 3 bullets max |
| `chart_explain` | Quantitative ideas | chart + callout labels |
| `equation_walkthrough` | Math | equation parts reveal |

### 10.5 Asset Priority Order

When resolving visuals, Asset Agent MUST follow:

1. Procedural SVG from props (arrays, graphs, charts)  
2. Curated icon packs (Lucide, Heroicons, OpenMoji)  
3. Illustration packs (Undraw) when metaphor helps  
4. Simple geometric fallback  
5. **Only if plugin enabled:** generative image  

### 10.6 Anti-Patterns (Forbidden in Core)

- One unique AI image per scene as the default  
- Decorative backgrounds that reduce text contrast  
- Unlabeled abstract art for technical topics  
- Inconsistent character styles across scenes without a theme system  

---

## 11. Theme System

### 11.1 Purpose

Themes control **look and feel**, not pedagogy. A theme may change:

- Color tokens  
- Typography  
- Stroke styles  
- Icon set preference  
- Transition defaults  
- Background treatments  

A theme must **not** change:

- Concept inventory  
- Narration meaning  
- Scene learning goals  

### 11.2 Supported Themes

| Theme ID | Character | Notes |
|----------|-----------|-------|
| `notebooklm` | Clean study-note aesthetic | V1 priority |
| `whiteboard` | Marker / board feel | Strong for classrooms |
| `corporate` | Neutral professional | Business training |
| `minimal` | Sparse, high clarity | Dense topics |
| `comic` | Panel-like playful | Younger audiences |
| `dark` | Dark stage, careful contrast | Low-light viewing |
| `watercolor` | Soft illustrative (Future) | Roadmap |
| `anime` | Stylized motion language (Future) | Roadmap |

### 11.3 Theme Pack Contract

```json
{
  "id": "notebooklm",
  "version": "1.0",
  "fonts": { "display": "...", "body": "..." },
  "colors": { "bg": "...", "fg": "...", "accent": "...", "muted": "...", "danger": "..." },
  "strokes": { "weight": 2, "corner": 8 },
  "motion": { "default_easing": "ease_in_out", "emphasis_scale": 1.04 },
  "icon_preference": ["lucide", "heroicons"],
  "background": { "type": "subtle_paper" }
}
```

### 11.4 Theme Selection Rules

1. User selection wins when valid.  
2. Else Topic Classification may suggest a default.  
3. Contrast validation should warn (not hard-fail) on risky combinations.  

---

## 12. Animation & Camera Engines

### 12.1 Animation Engine

**Role:** Compile AnimationPlan + DSL into deterministic keyframes.

**Capabilities (V1)**
- Fade / slide / scale in-out  
- Highlight pulses  
- Pointer moves  
- Path follows for packets/tokens  
- Staggered list reveals  

**Non-goals (V1)**
- Full physics simulations  
- Character skeletal animation  

### 12.2 Camera Engine

**Role:** Compile CameraPlan into view transforms over the canvas.

**Capabilities (V1)**
- Static framing  
- Zoom-to-element  
- Pan between regions  
- Soft cuts between scenes  

**Safety Limits**
- Max zoom speed  
- Max pan speed  
- Minimum hold time on teaching focus  

### 12.3 Timeline Compiler

After animation + camera + audio durations are known:

```
Presentation DSL
 + AnimationPlan
 + CameraPlan
 + Audio durations
 → Animation Timeline (absolute timestamps)
 → Renderer
```

The timeline is the **renderable truth**. Re-encoding should not require re-running LLM agents if timeline and assets are unchanged.

---

## 13. Rendering & Export System

### 13.1 Rendering Pipeline

```
Timeline → Frame Generator → Encoder (FFmpeg) → Mux Audio → Optional Subtitle Burn-in → MP4
```

Components:

- **MoviePy** / custom frame composer for sequencing  
- **OpenCV** for image ops where useful  
- **FFmpeg** for robust encoding and muxing  

### 13.2 Export Package (V1)

| File | Description |
|------|-------------|
| `video.mp4` | Primary deliverable |
| `narration.wav` / `.mp3` | Full narration track |
| `subtitles.srt` | SubRip captions |
| `subtitles.vtt` | WebVTT captions |
| `thumbnail.jpg` | Preview image |
| `metadata.json` | Title, tags, duration, theme, languages |
| `project.explainx` / project dir | Saved project for reload |

### 13.3 Export Settings

- Resolution presets: `1280x720` (default on constrained hardware), `1920x1080` optional  
- FPS: 30 default  
- Bitrate: quality profiles `draft` / `standard` / `high`  
- Subtitle mode: external only | burned-in  

---

## 14. Primary Feature Specifications

### 14.1 Offline Execution

- After installation of models/assets, generation works with network disabled.  
- Orchestrator must not call remote endpoints in core path.  
- Feature flags gate any future online capabilities.

### 14.2 Multi-Agent Architecture

- Implemented as LangGraph nodes with typed state.  
- Each agent versioned; cache keys include agent version + input hash.

### 14.3 Local LLM

- Provider: Ollama  
- Default model: Qwen2.5 3B  
- Used for language-heavy agents (knowledge, script, planning)  
- Prompts stored as versioned templates, not inline magic strings scattered in code

### 14.4 Local Translation

- IndicTrans2 for supported Indian language pairs (expand over time)  
- Translation Agent is optional in pipeline when target language equals source

### 14.5 Local TTS

- Piper TTS voices  
- Voice catalog stored locally  
- Duration measurement feeds timeline compiler

### 14.6 Subtitle Generation

- Derived from script + timings  
- Optional Whisper.cpp alignment for improved sync  
- Always export sidecar files even if burn-in disabled

### 14.7 Scene Planning

- Converts pedagogical outline into scene list  
- Enforces coverage of key concepts  
- Emits scene goals consumed by Visual Planning

### 14.8 Presentation Generation

- Compiles Layout + Theme + Assets into Presentation DSL  
- DSL is persisted as a project artifact

### 14.9 Animation Engine

- See Section 12.1  

### 14.10 Camera Engine

- See Section 12.2  

### 14.11 Rendering Engine

- See Section 13  

### 14.12 Export System

- Packages all outputs; supports re-export without full regen when possible

### 14.13 Theme System

- See Section 11  

### 14.14 Plugin System

- See Section 15  

---

## 15. Plugin System

### 15.1 Goals

Allow extension without forking core agents:

- New themes  
- New asset packs  
- Optional image generation  
- Optional OCR  
- Optional cloud render (later)  

### 15.2 Plugin Types

| Type | Examples |
|------|----------|
| `theme` | Watercolor, Anime |
| `asset_pack` | Domain icon sets |
| `visual_backend` | Generative images (V3) |
| `translator` | Additional local models |
| `tts_voice_pack` | Extra Piper voices |
| `renderer` | Cloud renderer (V4) |
| `importer` | Extra document formats |

### 15.3 Plugin Contract (Conceptual)

```json
{
  "id": "plugin.example",
  "version": "1.0.0",
  "type": "theme",
  "entry": "explainx_plugin_example:register",
  "permissions": ["read_project_artifacts"],
  "offline": true
}
```

### 15.4 Safety Rules

1. Plugins cannot silently replace core pipeline stages without user enablement.  
2. Core must run with zero plugins installed.  
3. Plugin failures degrade gracefully to core fallbacks.  

---

## 16. Technology Stack

### 16.1 Frontend

| Technology | Role |
|------------|------|
| Next.js | App framework / routing |
| React | UI components |
| Tailwind CSS | Styling |
| Framer Motion | UI motion (not video engine) |
| TypeScript | Typed UI and shared DTOs where applicable |

### 16.2 Backend

| Technology | Role |
|------------|------|
| FastAPI | Local API |
| Python | Agent/engine implementation language |
| LangGraph | Multi-agent orchestration |
| SQLite | Project index, job state, settings |
| MoviePy | Composition helpers |
| FFmpeg | Encoding / muxing |
| OpenCV | Image processing utilities |

### 16.3 AI / Local Models

| Technology | Role |
|------------|------|
| Ollama | Local LLM runtime |
| Qwen2.5 3B | Default reasoning model |
| IndicTrans2 | Local translation |
| Piper TTS | Local narration |
| Whisper.cpp | Optional alignment / ASR utilities |

### 16.4 Assets

| Pack | Role |
|------|------|
| Lucide | UI + diagram icons |
| Heroicons | Alternate iconography |
| OpenMoji | Emoji-style educational icons |
| Undraw | Optional illustrative scenes |

### 16.5 Stack Rules

1. Prefer libraries that run offline.  
2. Pin versions for reproducibility.  
3. Isolate native binaries (FFmpeg, Ollama, Piper) behind adapter ports.  

---

## 17. Data Model & Persistence

### 17.1 Storage Layout (Logical)

```
projects/
  {project_id}/
    source/
    artifacts/
      raw_document.json
      clean_document.json
      structure.json
      knowledge.json
      script.json
      scene_plan.json
      visual_plan.json
      presentation.dsl.json
      animation_plan.json
      camera_plan.json
      timeline.json
      audio/
      subtitles/
      render/
    export/
    logs/
    project.json
```

### 17.2 SQLite Responsibilities

- Project registry  
- Job queue / status  
- Settings  
- Cache index (input hash → artifact path)  
- Plugin enablement  

### 17.3 Immutability Convention

Upstream artifacts are treated as immutable snapshots. Regeneration creates new artifact versions rather than silent overwrites when auditability is required (implementation may soft-overwrite draft stages, but IDs/versions must remain traceable).

---

## 18. Expected Folder Structure

> This is the **target repository structure**. Creating these directories/files in code is out of scope for this constitution-only task; this section is the blueprint.

```
ExplainX/
├── docs/
│   ├── PROJECT_CONSTITUTION.md          # ← this document
│   ├── ADRs/                            # Architecture Decision Records
│   ├── api/                             # API specs
│   └── schemas/                         # JSON schema mirrors (optional)
│
├── apps/
│   ├── web/                             # Next.js frontend
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── styles/
│   │   ├── public/
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── api/                             # FastAPI backend (or packages/api)
│
├── packages/                            # Shared libs (if monorepo)
│   ├── shared-types/                    # Cross-language DTOs / OpenAPI
│   └── config/                          # Shared ESLint/TS configs
│
├── backend/                             # Python backend root (canonical)
│   ├── pyproject.toml
│   ├── README.md
│   ├── app/
│   │   ├── main.py                      # FastAPI entry
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── projects.py
│   │   │   │   ├── jobs.py
│   │   │   │   ├── exports.py
│   │   │   │   └── settings.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   ├── errors.py
│   │   │   └── di.py                    # dependency injection
│   │   ├── models/                      # Pydantic schemas
│   │   │   ├── pipeline_state.py
│   │   │   ├── documents.py
│   │   │   ├── knowledge.py
│   │   │   ├── script.py
│   │   │   ├── scenes.py
│   │   │   ├── presentation_dsl.py
│   │   │   ├── animation.py
│   │   │   ├── camera.py
│   │   │   ├── media.py
│   │   │   └── project.py
│   │   ├── agents/
│   │   │   ├── base.py
│   │   │   ├── parser_agent.py
│   │   │   ├── cleaning_agent.py
│   │   │   ├── structure_agent.py
│   │   │   ├── knowledge_agent.py
│   │   │   ├── topic_classification_agent.py
│   │   │   ├── difficulty_agent.py
│   │   │   ├── explanation_strategy_agent.py
│   │   │   ├── script_agent.py
│   │   │   ├── scene_planner_agent.py
│   │   │   ├── metadata_agent.py
│   │   │   ├── visual_planning_agent.py
│   │   │   ├── layout_planner_agent.py
│   │   │   ├── theme_planner_agent.py
│   │   │   ├── asset_agent.py
│   │   │   ├── animation_agent.py
│   │   │   ├── camera_agent.py
│   │   │   ├── translation_agent.py
│   │   │   ├── voice_agent.py
│   │   │   ├── subtitle_agent.py
│   │   │   ├── rendering_agent.py
│   │   │   └── project_manager_agent.py
│   │   ├── orchestration/
│   │   │   ├── graph.py                 # LangGraph definition
│   │   │   ├── nodes.py
│   │   │   ├── checkpoints.py
│   │   │   └── cache.py
│   │   ├── engines/
│   │   │   ├── animation/
│   │   │   ├── camera/
│   │   │   ├── layout/
│   │   │   ├── timeline/
│   │   │   └── render/
│   │   ├── ports/                       # interfaces / protocols
│   │   │   ├── llm.py
│   │   │   ├── tts.py
│   │   │   ├── translator.py
│   │   │   ├── renderer.py
│   │   │   └── storage.py
│   │   ├── adapters/                    # concrete implementations
│   │   │   ├── ollama_llm.py
│   │   │   ├── piper_tts.py
│   │   │   ├── indictrans2.py
│   │   │   ├── whisper_cpp.py
│   │   │   ├── ffmpeg_renderer.py
│   │   │   └── sqlite_storage.py
│   │   ├── themes/
│   │   │   ├── notebooklm/
│   │   │   ├── whiteboard/
│   │   │   ├── corporate/
│   │   │   ├── minimal/
│   │   │   ├── comic/
│   │   │   └── dark/
│   │   ├── assets/
│   │   │   ├── icons/
│   │   │   ├── illustrations/
│   │   │   └── templates/
│   │   ├── plugins/
│   │   │   ├── registry.py
│   │   │   ├── loader.py
│   │   │   └── api.py
│   │   ├── services/
│   │   │   ├── project_service.py
│   │   │   ├── export_service.py
│   │   │   └── job_service.py
│   │   └── db/
│   │       ├── session.py
│   │       ├── schema.sql
│   │       └── migrations/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── agents/
│   │   ├── engines/
│   │   └── fixtures/
│   └── scripts/
│       ├── download_models.py
│       └── doctor.py                    # environment health check
│
├── assets/                              # large binary asset packs (git-lfs or download)
│   ├── openmoji/
│   ├── undraw/
│   └── fonts/
│
├── data/                                # local runtime data (gitignored)
│   ├── projects/
│   ├── models/
│   └── cache/
│
├── tools/
│   ├── lint/
│   └── codegen/
│
├── .env.example
├── .gitignore
├── README.md
├── LICENSE                              # prefer permissive free license for core
└── docker/                              # optional; not required for V1 offline desktop path
```

---

## 19. Development Philosophy & Engineering Standards

### 19.1 Enterprise, Not Prototype

ExplainX must feel like enterprise software:

- Explicit contracts  
- Predictable failures  
- Observable pipelines  
- Documented decisions (ADRs)  
- Testable modules  

### 19.2 Module Quality Bar

Every module must exhibit:

| Requirement | Meaning |
|-------------|---------|
| Single Responsibility | One reason to change |
| Low Coupling | Minimal hard dependencies |
| High Cohesion | Related logic stays together |
| Reusable Components | Engines usable outside agents |
| Clear Interfaces | Ports/adapters |
| Dependency Injection | Swappable LLM/TTS/renderer |
| Typed Models | Pydantic / TypeScript types |
| Proper Logging | Structured logs with stage IDs |
| Validation | Schema validation at boundaries |
| Testing | Unit + contract + golden fixtures |

### 19.3 Code Organization Rules (for future implementation)

1. Agents contain prompting + I/O mapping; heavy logic lives in engines/services.  
2. No circular imports between agents.  
3. No direct filesystem writes inside pure planning agents — use storage ports.  
4. Secrets/config via environment + settings object; never hardcode machine paths.  
5. Public functions type-annotated.  

### 19.4 Prompt Engineering Rules

1. Prompts are versioned templates.  
2. Prompts request JSON only for agent outputs.  
3. Outputs validated; on failure, bounded retry with repair prompt.  
4. Temperature and decoding params documented per agent.  

### 19.5 Definition of Done (Feature)

A feature is done when:

- Schema/contracts updated  
- Constitution section referenced or amended if architecture changes  
- Unit tests + at least one integration path  
- Logs and error codes defined  
- Offline behavior verified on target-class hardware when relevant  

---

## 20. Interface Contracts & Communication Rules

### 20.1 Communication Rules

| Rule ID | Statement |
|---------|-----------|
| C1 | Agents communicate only via structured JSON artifacts |
| C2 | No agent may directly modify another agent’s output artifact |
| C3 | Downstream agents may reference upstream IDs, not rewrite upstream semantics |
| C4 | Orchestrator owns execution order, retries, and cancellation |
| C5 | Presentation DSL is the hub for visual/motion/render stages |
| C6 | Engines are deterministic given the same inputs |

### 20.2 Versioning

- `dsl_version` for Presentation DSL  
- `agent_version` per agent implementation  
- Cache invalidation when versions change  

### 20.3 Example Boundary Violation (Forbidden)

```
# FORBIDDEN mental model
visual_agent.output.scenes[0].narration = "new text"  # mutates Script Agent territory
```

```
# REQUIRED mental model
new_artifact = layout_agent.run(visual_plan_ref=..., scene_plan_ref=...)
```

---

## 21. Error Handling, Logging & Observability

### 21.1 Error Model

```json
{
  "error_code": "AGENT_VALIDATION_FAILED",
  "stage": "script_agent",
  "message": "Output failed schema validation",
  "retriable": true,
  "details": {}
}
```

### 21.2 Logging Requirements

Every stage log must include:

- `project_id`  
- `job_id`  
- `stage`  
- `duration_ms`  
- `status`  

Prefer structured JSON logs for backend.

### 21.3 User-Facing Status

UI shows coarse stages:

1. Reading document  
2. Understanding content  
3. Writing narration  
4. Designing visuals  
5. Generating voice  
6. Rendering video  

Internal agent names may appear in advanced/debug mode only.

---

## 22. Testing Strategy

### 22.1 Test Pyramid

| Layer | Focus |
|-------|-------|
| Unit | Engines, pure transforms, schema validators |
| Agent contract | Fixture in → schema-valid out (LLM mocked) |
| Integration | Mini pipeline on sample docs |
| Golden | DSL/timeline snapshots for diagram scenes |
| System | Offline full run on sample project (nightly/manual on target hardware) |

### 22.2 Fixture Policy

Keep small educational fixtures:

- Binary search one-pager  
- Photosynthesis short MD  
- Client-server networking blurb  

### 22.3 Determinism

Where randomness exists (LLM), tests mock the LLM port. Engines/timeline/render path should be deterministic.

---

## 23. Security & Privacy

1. Local-first processing of user documents.  
2. No telemetry of document contents by default.  
3. Plugin permissions explicitly granted.  
4. Path traversal protections on project file access.  
5. Treat uploaded files as untrusted (size limits, type checks).  

---

## 24. Performance Budgets

### 24.1 Hardware Reality

On i7-1255U + 16GB RAM:

- Prefer 720p draft renders for iteration  
- Stream/unload models when switching major stages if memory pressure is high  
- Avoid loading IndicTrans2 + LLM + Whisper simultaneously unless necessary  

### 24.2 Soft Targets (V1 Guidance)

| Stage | Soft Target |
|-------|-------------|
| Short MD topic (≤1 page) to script | Minutes, not hours |
| Full 3-minute video render (720p) | Accept longer CPU encode times; show progress |
| UI responsiveness | Status polling must not freeze UI |

Exact numeric SLOs will be set after first prototype benchmarks; this constitution mandates **progress feedback** and **cancellability** rather than fake real-time promises.

---

## 25. Future Roadmap

### Version 1 — Offline Educational Video Generation

- Full offline pipeline  
- Core agents  
- Presentation DSL  
- Diagram-first visuals  
- Themes: NotebookLM, Whiteboard, Corporate, Minimal, Comic, Dark  
- Export package (MP4, narration, subtitles, thumbnail, metadata, project)  

### Version 2 — Better Themes & Plugin Architecture

- Hardened plugin registry  
- Theme authoring docs  
- Improved motion packs  
- Better asset procedural compilers  

### Version 3 — Optional Image Generation Plugins

- Visual backend plugins  
- Still diagram-first by default  
- Generative images only when user enables plugin and Visual Planning selects `image` primitive  

### Version 4 — Cloud Rendering

- Optional cloud renderer plugin for faster encodes  
- Core remains offline-capable  
- Explicit opt-in; privacy warnings  

### Version 5 — Collaborative Editing

- Multi-user project sessions  
- Limited presentation inspection/editing surfaces  
- Conflict-safe artifact versioning  

---

## 26. Amendment Process

1. Propose change via ADR in `docs/ADRs/`.  
2. Update this constitution with version bump (`1.x` minor for additive; `2.0` for breaking philosophy changes).  
3. Note migration impact on DSL and agents.  
4. Do not silently diverge in code.  

---

## 27. Glossary

| Term | Definition |
|------|------------|
| Presentation DSL | JSON intermediate language describing the internal presentation |
| Agent | Single-responsibility pipeline component with JSON I/O |
| Engine | Deterministic library used by agents (animation, camera, render) |
| Visual Recipe | Plan for how a concept is shown with diagram primitives |
| Timeline | Absolute-time compilation of animations, camera, and audio |
| Offline-first | Core path works without network after local setup |
| Plugin | Optional extension pack with explicit permissions |

---

## 28. Appendix: Architecture Diagrams

### 28.1 Context Diagram

```
                 ┌──────────────────┐
                 │  Local User (UI) │
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │     ExplainX     │
                 │  (Local Stack)   │
                 └────────┬─────────┘
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
   ┌────────────┐  ┌────────────┐  ┌──────────────┐
   │ Ollama LLM │  │ Piper TTS  │  │ FFmpeg Stack │
   └────────────┘  └────────────┘  └──────────────┘
          │               │                │
          └───────────────┴────────────────┘
                          │
                 ┌────────▼─────────┐
                 │ SQLite + Project │
                 │    Filesystem    │
                 └──────────────────┘
```

### 28.2 Agent Dependency (Simplified)

```
Parser → Cleaning → Structure → Knowledge → Topic → Difficulty → Strategy
                                                              ↓
                                                           Script
                                                              ↓
                                                         Scene Planner
                                                              ↓
                                                          Metadata
                                                              ↓
                                                      Visual Planning
                                                              ↓
                                                      Layout → Theme → Assets
                                                              ↓
                                                      Presentation DSL
                                                              ↓
                                                      Animation → Camera
                                                              ↓
                                         Translation? → Voice → Subtitles
                                                              ↓
                                                           Rendering
                                                              ↓
                                                      Project Manager / Export
```

### 28.3 Decision Table — When to Use Which Visual Mode

| Content Signal | Preferred Mode | Avoid |
|----------------|----------------|-------|
| Stepwise algorithm | `algorithm_trace` | Single static poster image |
| Biological process | `process_flow` | Unrelated stock photos |
| Request/response systems | `system_diagram` | Abstract gradient art |
| Definition-heavy intro | `definition_card` | Overcrowded diagrams |
| Numeric comparison | `chart_explain` | Unlabeled decorative charts |

---

## Closing Statement

ExplainX is a **presentation-to-video engine**, not a generative video model.

Its competitive advantage is a disciplined pipeline:

**Document → Knowledge → Narration → Scenes → Presentation DSL → Animation Timeline → MP4**

…executed **offline**, with **modular agents**, **diagram-first visuals**, and **enterprise engineering standards**.

All future implementation work must treat this document as the constitution of the system.

---

*End of PROJECT_CONSTITUTION.md*  
*ExplainX Engineering — Architecture First. Code Second.*
