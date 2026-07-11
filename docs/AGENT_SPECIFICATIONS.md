# ExplainX — Agent Specifications

**Document Status:** Canonical Multi-Agent Specification  
**Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Companions:**  
[`PROJECT_CONSTITUTION.md`](./PROJECT_CONSTITUTION.md) ·  
[`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md) ·  
[`PRESENTATION_DSL.md`](./PRESENTATION_DSL.md)  

> **Authority:** This document defines every agent in ExplainX: purpose, contracts, validation, failures, dependencies, and evolution rules.  
> Implementation must match these specifications. When informal discussion conflicts with this document, **this document wins** until amended via ADR.

---

## Table of Contents

1. [Purpose of This Document](#1-purpose-of-this-document)
2. [Agent System Overview](#2-agent-system-overview)
3. [How Agents Communicate](#3-how-agents-communicate)
4. [Why Agents Are Isolated](#4-why-agents-are-isolated)
5. [Agent Lifecycle](#5-agent-lifecycle)
6. [Retry Strategies](#6-retry-strategies)
7. [Logging Requirements](#7-logging-requirements)
8. [Shared Conventions](#8-shared-conventions)
9. [Agent Catalog](#9-agent-catalog)
10. [Pipeline Ordering & Parallelism](#10-pipeline-ordering--parallelism)
11. [Adding New Agents in Future Versions](#11-adding-new-agents-in-future-versions)
12. [Agent × DSL Interaction Matrix](#12-agent--dsl-interaction-matrix)
13. [Error Code Registry (Agents)](#13-error-code-registry-agents)
14. [Appendix: Minimal I/O Skeletons](#14-appendix-minimal-io-skeletons)

---

## 1. Purpose of This Document

ExplainX is a multi-agent system. Intelligence is deliberately split so that:

- each capability has one owner  
- contracts are typed JSON  
- failures are stage-local  
- caching and resume are possible  
- the renderer never needs to call an LLM  

This specification is the **engineering handbook** for every agent that will exist in the LangGraph orchestrator.

**No application code is defined here** — only behavior, contracts, and rules.

---

## 2. Agent System Overview

### 2.1 Definition of an Agent

An **agent** is a single-responsibility pipeline worker that:

1. Reads declared input artifacts (and/or project config)  
2. Performs one coherent job (often LLM-assisted, sometimes deterministic)  
3. Emits a validated output artifact  
4. Never mutates another agent’s output in place  

Agents may call **engines** (Presentation, Animation, Rendering) and **ports** (LLM, TTS, Translator, Storage). Engines are not agents.

### 2.2 Agent Roster (v1.0)

| # | Agent | Plane |
|---|-------|-------|
| 1 | Parser Agent | Knowledge |
| 2 | Cleaning Agent | Knowledge |
| 3 | Structure Agent | Knowledge |
| 4 | Knowledge Agent | Knowledge |
| 5 | Topic Classification Agent | Knowledge |
| 6 | Difficulty Agent | Knowledge |
| 7 | Explanation Strategy Agent | Knowledge |
| 8 | Script Agent | Narrative |
| 9 | Scene Planner | Narrative |
| 10 | Metadata Agent | Narrative / Catalog |
| 11 | Visual Planning Agent | Presentation |
| 12 | Layout Planner | Presentation |
| 13 | Theme Planner | Presentation |
| 14 | Asset Agent | Presentation |
| 15 | Animation Agent | Motion |
| 16 | Timeline Agent | Motion |
| 17 | Camera Agent | Motion |
| 18 | Translation Agent | Media |
| 19 | Voice Agent | Media |
| 20 | Subtitle Agent | Media |
| 21 | Rendering Agent | Media |
| 22 | Project Manager Agent | Control |

### 2.3 Orchestrator Relationship

```
API / Job Service
        │
        ▼
Agent Orchestrator (LangGraph)
        │
        ├── invokes agents in graph order
        ├── validates outputs
        ├── checkpoints artifacts
        ├── applies retries
        └── emits progress + logs
```

The orchestrator owns **when** agents run.  
Each agent owns **how** its transform is performed.

---

## 3. How Agents Communicate

### 3.1 Constitutional Communication Rules

| Rule ID | Rule |
|---------|------|
| C1 | Agents communicate **only** through structured JSON artifacts |
| C2 | No agent may directly modify another agent’s output object |
| C3 | Downstream agents **reference** upstream IDs; they do not rewrite upstream semantics |
| C4 | Shared runtime state is `PipelineState` containing **references** (IDs/paths), not giant in-memory blobs by default |
| C5 | After visual compile, the **Presentation DSL** is the hub language for motion/media/render stages |
| C6 | Side effects (disk writes) go through the **Storage Port**, not ad-hoc file IO inside prompts |

### 3.2 Communication Pattern

```
Agent A                         Storage                      Agent B
  │                                │                            │
  │ write artifact_A.json          │                            │
  │───────────────────────────────►│                            │
  │ update PipelineState ref       │                            │
  │────────────────────────────────┼───────────────────────────►│
  │                                │ read artifact_A.json       │
  │                                │◄───────────────────────────│
  │                                │                            │
  │                                │◄──── write artifact_B.json │
```

### 3.3 Artifact Envelope (Normative Wrapper)

Every agent output SHOULD be stored with an envelope:

```json
{
  "artifact_type": "knowledge_model",
  "artifact_id": "km_01",
  "schema_version": "1.0",
  "producer_agent": "knowledge_agent",
  "producer_version": "1.0.0",
  "created_at": "2026-07-11T10:00:00Z",
  "input_hash": "sha256:...",
  "project_id": "...",
  "job_id": "...",
  "payload": { }
}
```

Validators check `schema_version` + `payload`.

### 3.4 What Agents Do *Not* Do for Communication

- No shared mutable Python objects across agent calls  
- No hidden global “scratchpad” for pedagogy  
- No renderer callbacks into Script/Knowledge agents  
- No direct agent-to-agent function calls bypassing the orchestrator (except pure engine calls)

---

## 4. Why Agents Are Isolated

### 4.1 Motivations

| Benefit | Explanation |
|---------|-------------|
| **Single Responsibility** | A subtitle bug does not require touching knowledge extraction |
| **Testability** | Mock LLM/TTS ports; assert schema only |
| **Caching** | Theme change does not invalidate Knowledge artifacts |
| **Resume** | Failed render resumes from last checkpoint |
| **Security** | Render workers need no LLM credentials |
| **Clarity** | Ownership of fields in Presentation DSL is explicit |
| **Parallel evolution** | Replace Voice backend without rewriting Scene Planner |

### 4.2 Isolation Boundaries

```
┌─────────────────┐     JSON artifact      ┌─────────────────┐
│   Agent A       │ ──────────────────────► │   Agent B       │
│  private memory │     (immutable snap)    │  private memory │
└─────────────────┘                         └─────────────────┘
```

If Agent B needs a correction to Agent A’s content, it must either:

1. request orchestrator-level **re-run** of Agent A with feedback, or  
2. emit a **new** artifact that adapts A’s output without mutating A’s file  

Silent in-place mutation is forbidden.

### 4.3 Isolation vs Engines

Agents **may** call engines. Engines are deterministic libraries. Calling `PresentationEngine.compile(...)` does not violate isolation because the engine does not own pipeline identity — the agent (or orchestrator hook) still writes the resulting artifact through Storage.

---

## 5. Agent Lifecycle

Every agent instance execution follows the same lifecycle.

### 5.1 Lifecycle State Machine

```
scheduled
   │
   ▼
loading_inputs
   │
   ▼
validating_inputs
   │
   ├─ fail ──► failed (non-retriable or after retries)
   ▼
running
   │
   ├─ cancel ─► cancelled
   ▼
validating_outputs
   │
   ├─ fail ──► repairing (optional) ──► validating_outputs
   │                 │
   │                 └─► failed
   ▼
persisting
   │
   ▼
checkpointed
   │
   ▼
succeeded
```

### 5.2 Lifecycle Phases (Detail)

| Phase | Responsibilities |
|-------|------------------|
| **scheduled** | Orchestrator selects node; job shows fine_stage |
| **loading_inputs** | Resolve artifact refs from Storage; load config |
| **validating_inputs** | Ensure required inputs exist and pass schema |
| **running** | Core work (LLM call, deterministic transform, engine call) |
| **validating_outputs** | Schema + semantic checks for this agent |
| **repairing** | Optional bounded repair prompt / fixup |
| **persisting** | Write envelope + payload via Storage Port |
| **checkpointed** | Orchestrator records stage success + hashes |
| **succeeded** | Node complete; next nodes may run |
| **failed** | Error code recorded; job may stop or branch |
| **cancelled** | Cooperative stop; partial writes discarded or marked incomplete |

### 5.3 Idempotency

Given the same:

- input artifact hashes  
- agent version  
- relevant config hash  

an agent SHOULD return a **cache hit** and skip `running`, still emitting lifecycle logs (`cache_hit=true`).

### 5.4 Timeouts

Each agent declares a soft timeout (guidance). On timeout:

1. Attempt cooperative cancel  
2. Mark `AGENT_TIMEOUT`  
3. Apply retry policy if retriable  

---

## 6. Retry Strategies

### 6.1 Retry Classes

| Class | Meaning | Typical cases |
|-------|---------|---------------|
| **R0 None** | Do not retry | Validation of user input, missing source file |
| **R1 Repair** | Re-ask model to fix JSON / schema | LLM schema drift |
| **R2 Transient** | Retry same call | Ollama busy, file lock, temporary OOM recover |
| **R3 Degraded** | Retry with safer settings | Smaller context, lower temperature, draft quality |
| **R4 Upstream** | Fail and request upstream re-run | Missing concept that script requires |

### 6.2 Default Policy (v1.0 Guidance)

| Situation | Policy |
|-----------|--------|
| JSON parse / schema failure (LLM) | R1 up to **2** repair attempts |
| Empty required fields | R1 once, then fail |
| Model server unavailable | R2 with exponential backoff (e.g., 2s, 5s, 10s), max 3 |
| TTS synthesis glitch | R2 max 2 per beat |
| Render encode failure | R3 once to `draft` profile **only if** user/config allows; else fail |
| Semantic nonsense detected by validator | R1 once; else fail (do not infinite-loop) |
| Cancelled | No retry |

### 6.3 Repair Prompt Rules

When repairing:

1. Feed validator error messages (not the whole constitution)  
2. Require JSON-only response  
3. Do not silently change unrelated fields  
4. Log `repair_attempt` count  

### 6.4 What Retries Must Not Do

- Skip validation after a “successful” parse of wrong types  
- Mutate upstream artifacts to make downstream “pass”  
- Hide failures by inventing empty scenes  

---

## 7. Logging Requirements

### 7.1 Mandatory Log Events per Agent Run

| Event | When |
|-------|------|
| `agent_started` | Enter `running` |
| `agent_cache_hit` | Skip due to cache |
| `agent_input_validated` | Inputs OK |
| `agent_output_validated` | Outputs OK |
| `agent_repair_attempt` | Repair loop |
| `agent_retry` | Transient retry |
| `agent_succeeded` | Checkpointed |
| `agent_failed` | Terminal failure |
| `agent_cancelled` | Cancel path |

### 7.2 Required Structured Fields

```json
{
  "ts": "ISO-8601",
  "level": "INFO",
  "component": "agent_layer",
  "agent": "script_agent",
  "agent_version": "1.0.0",
  "project_id": "...",
  "job_id": "...",
  "stage": "script_agent",
  "event": "agent_succeeded",
  "duration_ms": 12040,
  "cache_hit": false,
  "repair_attempt": 0,
  "error_code": null,
  "input_hash": "sha256:...",
  "output_artifact_id": "script_01"
}
```

### 7.3 Privacy

- Default: do not log full document bodies or full narration  
- Log counts, hashes, IDs, truncated error snippets  
- Debug mode (explicit) may log truncated payloads  

### 7.4 Progress Mapping

Agents expose a `coarse_stage` for UI:

| Coarse Stage | Agents (examples) |
|--------------|-------------------|
| `reading_document` | Parser, Cleaning, Structure |
| `understanding_content` | Knowledge, Topic, Difficulty, Strategy |
| `writing_narration` | Script, Scene Planner, Metadata |
| `designing_visuals` | Visual, Layout, Theme, Asset (+ DSL compile) |
| `generating_motion` | Animation, Camera, Timeline |
| `generating_voice` | Translation, Voice, Subtitle |
| `rendering_video` | Rendering |
| `finalizing_project` | Project Manager / Output assembly |

---

## 8. Shared Conventions

### 8.1 Naming

- Agent module/node names: `snake_case` + `_agent` where applicable  
- Artifact types: `snake_case`  
- IDs: `^[a-z][a-z0-9_]*$` for non-UUID logical IDs; UUIDs for projects/jobs  

### 8.2 Version Field

Every agent has `agent_version` (semver). Cache keys include it.

### 8.3 Dependency Injection

Agents depend on ports:

- `LLMPort`  
- `TTSPort`  
- `TranslatorPort`  
- `StoragePort`  
- `PresentationEngine` / `AnimationEngine` / `RenderEngine` as needed  

### 8.4 Common Input: Pipeline Context

All agents receive (conceptually):

```json
{
  "project_id": "...",
  "job_id": "...",
  "config": {
    "language": "en",
    "target_language": "en",
    "theme_id": "notebooklm",
    "voice_id": "en_US-lessac-medium",
    "difficulty_override": null,
    "export": { "resolution": "1280x720", "fps": 30, "quality": "standard" }
  },
  "artifacts": { }
}
```

---

## 9. Agent Catalog

---

### 9.1 Parser Agent

#### Purpose
Ingest a source document or topic string and extract raw textual content (and basic structural crumbs) without pedagogical interpretation.

#### Responsibilities
- Detect/accept source type: PDF, DOCX, TXT, Markdown, Topic  
- Extract text in reading order where possible  
- Record page/section spans when available  
- Emit extraction warnings (empty PDF, encrypted, etc.)  
- Never “explain” or summarize beyond extraction  

#### Inputs
| Name | Type | Required |
|------|------|----------|
| `source.type` | enum | yes |
| `source.path` or `source.topic` | string | yes |
| `config.language` hint | string | no |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `raw_document` | Pages/sections of raw text + stats + warnings |

#### Validation
- At least one non-empty text unit OR typed failure `PARSER_EMPTY_CONTENT`  
- `source_type` matches actual parser used  
- Character count ≥ 0; warnings array present  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Unsupported type | `PARSER_UNSUPPORTED_TYPE` (R0) |
| File missing | `PARSER_FILE_NOT_FOUND` (R0) |
| Empty extract | `PARSER_EMPTY_CONTENT` (R0; user must provide better source or OCR plugin later) |
| Partial extract | Succeed with warnings |

#### Dependencies
- Storage Port  
- Format parsers (PDF/DOCX/MD libraries)  
- No LLM required in v1 core  

#### Future Improvements
- OCR plugin for scanned PDFs  
- Table/formula extraction fidelity  
- Citation and footnote channels  

---

### 9.2 Cleaning Agent

#### Purpose
Normalize raw extracted text into clean instructional content suitable for structure and knowledge extraction.

#### Responsibilities
- Strip repeated headers/footers/page numbers when confidently detected  
- Unicode and whitespace normalization  
- Remove obvious boilerplate  
- Preserve code tokens and technical strings  
- Record what was removed (categories, not always full text)  

#### Inputs
| Name | Required |
|------|----------|
| `raw_document` | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `clean_document` | Normalized text + normalization report |

#### Validation
- `text` non-empty if raw was non-empty  
- Normalization flags object present  
- Must not shrink content to empty without error  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Empty after clean | `CLEAN_EMPTY` (R0/R4 consider parser) |
| Over-stripping heuristic tripwire | Warning + keep safer variant |

#### Dependencies
- Storage Port  
- Optional light rules engine  
- LLM optional (v1 prefer deterministic rules)  

#### Future Improvements
- Domain-specific cleaners  
- Deduplication across chapters  

---

### 9.3 Structure Agent

#### Purpose
Recover hierarchical document structure: titles, sections, and candidate teaching units.

#### Responsibilities
- Heading detection / section segmentation  
- Nesting levels  
- Ordered section tree  
- Provide span references into clean text  

#### Inputs
| Name | Required |
|------|----------|
| `clean_document` | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `document_structure` | Tree of sections + title guess |

#### Validation
- Sections array present (may be single synthetic section)  
- Levels ≥ 1  
- Orders unique  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| LLM structure JSON invalid | R1 repair ×2 |
| No headings found | Succeed with one root section wrapping all text |

#### Dependencies
- LLM Port (optional/hybrid)  
- Storage Port  

#### Future Improvements
- Multi-doc course structures  
- Learning-objective tagging per section  

---

### 9.4 Knowledge Agent

#### Purpose
Extract teachable concepts, definitions, relations, examples, and misconceptions from structured content.

#### Responsibilities
- Build concept inventory  
- Capture definitions and examples  
- Relation edges (prerequisite, uses, part-of, contrasts-with)  
- Separate facts from explanatory notes  
- Stay faithful to source (no unchecked hallucination of critical facts)  

#### Inputs
| Name | Required |
|------|----------|
| `clean_document` | yes |
| `document_structure` | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `knowledge_model` | Concepts, relations, examples, misconceptions |

#### Validation
- ≥ 1 concept for non-trivial docs (else warning for tiny topics)  
- Concept IDs unique  
- Relations reference existing concept IDs  
- Definitions non-empty strings when present  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Schema invalid | R1 ×2 |
| Zero concepts on long doc | `KNOWLEDGE_EMPTY` fail |
| Low-confidence mass hallucination heuristics | Warning; optional R1 |

#### Dependencies
- LLM Port (primary)  
- Storage Port  

#### Future Improvements
- Lightweight knowledge graph export  
- Cross-project concept reuse  
- Citation back to section spans  

---

### 9.5 Topic Classification Agent

#### Purpose
Classify domain and subtopics to guide visuals, metaphors, defaults, and metadata tags.

#### Responsibilities
- Assign `primary_domain`  
- Assign `subtopics[]`  
- Provide confidence score  
- Suggest default theme hint (non-binding)  

#### Inputs
| Name | Required |
|------|----------|
| `knowledge_model` | yes |
| user topic override | no |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `topic_labels` | Domain, subtopics, confidence, theme_hint? |

#### Validation
- `primary_domain` non-empty  
- `confidence` in `[0,1]`  
- Subtopics array present  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Schema invalid | R1 ×2 |
| Low confidence | Succeed with `general` + warning |

#### Dependencies
- LLM Port  
- Storage Port  

#### Future Improvements
- Hierarchical taxonomy  
- Curriculum alignment tags  

---

### 9.6 Difficulty Agent

#### Purpose
Estimate audience difficulty and emit a depth policy for scripting and scene density.

#### Responsibilities
- Assign `beginner` \| `intermediate` \| `advanced`  
- Honor user override when provided  
- Emit depth policy (definitions-first, formula density, etc.)  
- List assumed prerequisites  

#### Inputs
| Name | Required |
|------|----------|
| `knowledge_model` | yes |
| `topic_labels` | yes |
| `config.difficulty_override` | no |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `difficulty_profile` | Level + depth_policy + prerequisites |

#### Validation
- Level enum valid  
- `depth_policy` object present  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Schema invalid | R1 ×1 then default `intermediate` with warning (policy choice) OR fail — **normative v1: fail after R1** if no override |

If user override present, agent may short-circuit to that level without LLM.

#### Dependencies
- LLM Port (when no override)  
- Storage Port  

#### Future Improvements
- Per-scene difficulty  
- Pretest-driven profiles  

---

### 9.7 Explanation Strategy Agent

#### Purpose
Choose the pedagogical approach and high-level outline before scripting.

#### Responsibilities
- Select approach (`worked_example`, `concept_then_example`, `compare_contrast`, `process_flow`, `story_hook`, …)  
- Produce outline beats  
- Bound max scenes / target duration constraints  

#### Inputs
| Name | Required |
|------|----------|
| `knowledge_model` | yes |
| `topic_labels` | yes |
| `difficulty_profile` | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `explanation_plan` | Approach, outline, constraints |

#### Validation
- `approach` in allowed enum  
- `outline` non-empty  
- `constraints.max_scenes` ≥ 1  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Schema invalid | R1 ×2 |
| Outline empty | fail `STRATEGY_EMPTY` |

#### Dependencies
- LLM Port  
- Storage Port  

#### Future Improvements
- Strategy ensembles / scoring  
- Domain-specific strategy templates  

---

### 9.8 Script Agent

#### Purpose
Write spoken narration aligned to knowledge, difficulty, and explanation strategy.

#### Responsibilities
- Produce TTS-friendly beats  
- Cover outline points  
- Avoid unspeakable formatting  
- Keep sentences clear and age-appropriate per difficulty  
- Attach scene hints per beat  

#### Inputs
| Name | Required |
|------|----------|
| `explanation_plan` | yes |
| `knowledge_model` | yes |
| `difficulty_profile` | yes |
| `config.language` | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `narration_script` | Beats with text, approx_sec, scene_hint, glossary |

#### Validation
- ≥ 1 beat  
- Each beat has non-empty `text` and unique `id`  
- No markdown tables / raw HTML in text  
- Approximate total duration within soft bounds (warning if extreme)  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Schema invalid | R1 ×2 |
| Unspeakable content patterns | R1 with cleaner instructions |
| Severely incomplete coverage vs outline | R1 once, else fail `SCRIPT_COVERAGE` |

#### Dependencies
- LLM Port  
- Storage Port  

#### Future Improvements
- Style presets (teacher, documentary)  
- Auto-adjust after Voice durations known (feedback loop via orchestrator)  

---

### 9.9 Scene Planner

#### Purpose
Partition narration into scenes with explicit learning goals and concept coverage.

#### Responsibilities
- Create ordered scenes  
- Map narration beat IDs → scenes  
- Assign scene goals  
- Enforce max scene constraints from strategy  
- Ensure intro/recap when strategy requires  

#### Inputs
| Name | Required |
|------|----------|
| `narration_script` | yes |
| `explanation_plan` | yes |
| `knowledge_model` | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `scene_plan` | Scenes with goals, beat IDs, must-include concepts |

#### Validation
- Every narration beat assigned to exactly one scene  
- Scene IDs unique; order contiguous  
- Non-empty goals  
- Concept IDs reference knowledge model when listed  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Unassigned beats | R1 ×2 |
| Too many scenes | R1 to merge; else fail |
| Empty scenes | fail |

#### Dependencies
- LLM Port (primary)  
- Storage Port  

#### Future Improvements
- Auto split/merge from measured audio durations  
- Optional quiz scenes  

---

### 9.10 Metadata Agent

#### Purpose
Produce project catalog metadata for UI library, export package, and search.

#### Responsibilities
- Title, description, tags  
- Duration estimate  
- Thumbnail guidance notes  
- Educational objectives summary  
- Write/update Presentation DSL `metadata` section when DSL exists  

#### Inputs
| Name | Required |
|------|----------|
| `topic_labels` | yes |
| `narration_script` | yes |
| `scene_plan` | yes |
| `difficulty_profile` | yes |
| user title override | no |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `project_metadata` | Metadata object |
| Optional DSL patch | `metadata` |

#### Validation
- Title non-empty ≤ 120 chars  
- Description non-empty  
- Tags array present  
- `estimated_duration_sec` > 0  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Schema invalid | R1 ×1 then heuristic title from topic (warning) allowed for metadata only |

#### Dependencies
- LLM Port  
- Storage Port  
- Optional DSL read/write  

#### Future Improvements
- Chapter markers  
- SEO-like educational schema packs  

---

### 9.11 Visual Planning Agent

#### Purpose
Decide **how** each scene should be explained visually using diagram-first primitives (not generative video).

#### Responsibilities
- Assign `visual_mode` per scene  
- List primitives (array, arrows, icons, …)  
- Ordered visual steps aligned to narration  
- Forbid decorative noise / photoreal defaults  
- Emit recipes consumed by Layout / Presentation Engine  

#### Inputs
| Name | Required |
|------|----------|
| `scene_plan` | yes |
| `knowledge_model` | yes |
| `topic_labels` | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `visual_plan` | Per-scene mode, primitives, steps, forbidden patterns |

#### Validation
- Every scene_id from scene_plan present  
- `visual_mode` in DSL enum  
- `primitives` non-empty  
- Steps non-empty for non-definition modes (warning otherwise)  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Schema invalid | R1 ×2 |
| Image-generation-only plan without plugin | reject / R1 to diagram plan |

#### Dependencies
- LLM Port  
- Storage Port  
- Constitution visual strategy rules  

#### Future Improvements
- Domain template library  
- Optional generative image plugin hooks (V3)  

---

### 9.12 Layout Planner

#### Purpose
Convert visual plans into spatial layouts and object skeletons with canvas-normalized transforms.

#### Responsibilities
- Choose layout preset / regions  
- Place object stubs (`kind`, `transform`, `z_index`)  
- Avoid overlapping critical labels  
- Respect safe margins  
- Hand off to Presentation Engine for DSL compile  

#### Inputs
| Name | Required |
|------|----------|
| `visual_plan` | yes |
| `scene_plan` | yes |
| canvas config | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `layout_plan` | Regions + element skeletons per scene |

#### Validation
- All transforms in `[0,1]` ranges (with allowed edge tolerance)  
- Region IDs valid  
- Object IDs unique per scene  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Overcrowding | R1 simplify; else warning + best effort |
| Schema invalid | R1 ×2 |

#### Dependencies
- LLM Port and/or deterministic layout heuristics  
- Presentation Engine  
- Storage Port  

#### Future Improvements
- Auto-layout solvers  
- RTL packs  

---

### 9.13 Theme Planner

#### Purpose
Apply a theme pack’s tokens to the presentation without changing pedagogy.

#### Responsibilities
- Resolve `theme_id` (user > suggestion > default)  
- Load theme tokens  
- Assign `style_tokens` on objects  
- Write DSL `theme` section  
- Warn on contrast issues when detectable  

#### Inputs
| Name | Required |
|------|----------|
| `layout_plan` or DSL draft | yes |
| `config.theme_id` | yes |
| `topic_labels.theme_hint` | no |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `theme_application` | Theme id + tokens + per-object style tokens |
| DSL `theme` update | yes |

#### Validation
- Theme exists on disk/registry  
- Required token keys present  
- Does not alter object pedagogical props  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Missing theme | fallback `minimal` + warning (R3 degraded) |
| Invalid tokens | fail `THEME_INVALID` |

#### Dependencies
- Theme registry  
- Storage Port  
- Presentation Engine (token apply)  

#### Future Improvements
- User-authored themes  
- Watercolor / Anime packs  

---

### 9.14 Asset Agent

#### Purpose
Resolve concrete assets (icons, SVG, illustrations, procedural generators) required by layouts/visual plans.

#### Responsibilities
- Map primitives → asset packs (Lucide, Heroicons, OpenMoji, Undraw)  
- Create procedural asset entries (arrays, charts)  
- Record missing assets and fallbacks  
- Write DSL `assets` and object `asset_id` links  

#### Inputs
| Name | Required |
|------|----------|
| `visual_plan` | yes |
| `layout_plan` / DSL objects | yes |
| `theme_application` | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `asset_manifest` | Assets + missing[] + fallbacks |
| DSL `assets` update | yes |

#### Validation
- Every `icon`/`image` object has resolvable `asset_id` OR fallback shape  
- File-backed paths exist when marked resolved  
- Procedural assets include generator name  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Asset missing | geometric/icon fallback + warning |
| Pack not installed | `ASSET_PACK_MISSING` (R0 until doctor installs) |

#### Dependencies
- Asset packs on disk  
- Storage Port  
- Optional plugin visual backends (future)  

#### Future Improvements
- Domain procedural compilers  
- Generative image plugin resolution (V3)  

---

### 9.15 Animation Agent

#### Purpose
Attach pedagogical motion intents to scene objects (fade, highlight, move, path follow, etc.).

#### Responsibilities
- Translate visual steps → `animations[]` presets  
- Keep motion purposeful (no spam)  
- Optionally anchor to narration beat IDs  
- Write DSL `scenes[].animations`  
- Respect theme motion defaults  

#### Inputs
| Name | Required |
|------|----------|
| Presentation DSL (`compiled`) | yes |
| `visual_plan` | yes |
| `narration_script` | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `animation_plan` | Clips/presets |
| DSL animations section | yes |

#### Validation
- Targets exist  
- `t[0] ≤ t[1]`  
- Presets known or plugin-registered  
- No animation invents new objects |

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Schema invalid | R1 ×2 |
| Missing target | fail or drop clip with warning (normative: fail if step-critical) |

#### Dependencies
- LLM Port (planning) + deterministic validation  
- Presentation DSL  
- Storage Port  

#### Future Improvements
- Prosody-driven emphasis  
- Theme-specific motion packs  

---

### 9.16 Timeline Agent

#### Purpose
Compile scene durations, animations, camera keyframes, and media timings into an absolute **Animation Timeline** that the renderer can consume. Own timeline bind semantics.

> **Note:** In system architecture, timeline compilation is an Animation Engine responsibility. The **Timeline Agent** is the agent-facing orchestrated node that invokes the Animation Engine, validates bind results, and writes the timeline artifact / DSL timeline section.

#### Responsibilities
- Resolve scene `duration` modes (`from_narration`, `fixed`, `max_of`, …)  
- Promote scene-relative animation/camera times to absolute clips  
- Build tracks: scene, animation, camera, audio, subtitle, transition  
- Insert markers at scene boundaries  
- Set `timeline.status` to `bound`  
- Advance DSL/project status toward `timeline_bound`  
- Ensure `metadata.actual_duration_sec` matches total duration when bound  

#### Inputs
| Name | Required |
|------|----------|
| Presentation DSL with animations/camera | yes |
| `voice` durations (if voice enabled) | yes if voice.enabled |
| `subtitles` cues (optional at bind; may bind later) | no |
| export fps | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `timeline` | Absolute timeline JSON |
| DSL `timeline` section / `$ref` | yes |
| Updated scene `duration.resolved_sec` | yes |

#### Validation
- No overlapping scene clips  
- `fps` matches canvas  
- All referenced IDs resolve  
- `duration_sec ≥` last clip end  
- Voice beats covered if enabled  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Missing voice durations | fail `TIMELINE_MISSING_AUDIO` (R4: run Voice first) |
| Non-deterministic engine error | R2 ×1 |
| Validation fail | fail with details (R0) |

#### Dependencies
- Animation Engine (required)  
- Storage Port  
- DSL schema  

#### Future Improvements
- Word-level caption alignment tracks  
- Chapter track export  
- Parallel clip packing optimizations  

---

### 9.17 Camera Agent

#### Purpose
Plan camera framing and motion (pan/zoom/focus) to direct attention without adding new pedagogical content.

#### Responsibilities
- Set initial camera transform per scene  
- Add keyframes toward focus objects  
- Enforce safety limits (max zoom/pan speed)  
- Write DSL `scenes[].camera`  

#### Inputs
| Name | Required |
|------|----------|
| Presentation DSL | yes |
| `animation_plan` (optional but recommended) | no |
| `visual_plan` / scene goals | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `camera_plan` | Shots/keyframes |
| DSL camera sections | yes |

#### Validation
- Zoom within limits  
- Focus object IDs exist when specified  
- Keyframe times valid  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Schema invalid | R1 ×2 |
| Unsafe motion | clamp + warning (R3 degraded) or fail if unclamped required |

#### Dependencies
- LLM Port optional; heuristics preferred for safety  
- Storage Port  
- DSL  

#### Future Improvements
- Cinematic theme presets  
- Multi-cut focus for complex diagrams  

**Ordering note:** Camera Agent typically runs **before** Timeline Agent so absolute camera clips can be bound. If camera runs after provisional timeline, Timeline Agent must re-bind (orchestrator edge).

---

### 9.18 Translation Agent

#### Purpose
Locally translate narration, metadata text, and subtitle source strings into the target language using IndicTrans2 (and future local models).

#### Responsibilities
- Translate selected units when `target_language != source_language`  
- Preserve technical terms per glossary policy  
- Emit parallel language pack artifacts  
- Update DSL voice/subtitle/metadata strings carefully  

#### Inputs
| Name | Required |
|------|----------|
| `narration_script` / DSL voice texts | yes |
| `project_metadata` | no |
| `config.target_language` | yes |
| glossary | no |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `translated_artifacts` | Parallel texts by ref ID |
| Updated DSL strings | when applicable |

#### Validation
- Every input unit has translation when enabled  
- Language codes BCP-47  
- No empty translations  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Model missing | `TRANSLATE_MODEL_MISSING` (R0) |
| Partial batch fail | R2 ×2 on failed units; else fail |
| Same language | no-op success |

#### Dependencies
- Translator Port (IndicTrans2)  
- Storage Port  

#### Future Improvements
- More language pairs  
- Glossary-constrained decoding  
- Dual-language subtitle tracks  

---

### 9.19 Voice Agent

#### Purpose
Synthesize narration audio locally with Piper TTS and measure durations for timeline binding.

#### Responsibilities
- Generate per-beat audio files  
- Optionally concatenate master track  
- Measure `duration_sec`  
- Write DSL `voice` paths/durations  
- Apply speaking rate settings  

#### Inputs
| Name | Required |
|------|----------|
| Narration beats (translated if needed) | yes |
| `config.voice_id` | yes |
| speaking_rate | no |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `audio_tracks` | Paths + durations |
| DSL `voice` update | yes |

#### Validation
- Each enabled beat has file path + duration > 0  
- Voice ID exists locally  
- Sample rate recorded when known  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Voice missing | `VOICE_NOT_FOUND` (R0) |
| Synth fail one beat | R2 ×2 on that beat |
| Empty text | fail `VOICE_EMPTY_TEXT` |

#### Dependencies
- TTS Port (Piper)  
- Storage Port  

#### Future Improvements
- Multi-speaker modes  
- Emphasis controls within free voices  
- Streaming synth for long scripts  

---

### 9.20 Subtitle Agent

#### Purpose
Create timed subtitles from narration text and audio timings (optional Whisper.cpp alignment).

#### Responsibilities
- Segment text into readable cues  
- Align to beat start/end (and optional word alignment)  
- Emit SRT/VTT paths  
- Write DSL `subtitles`  
- Honor burn-in flag as metadata for renderer (does not itself burn in)  

#### Inputs
| Name | Required |
|------|----------|
| Voice beats + durations | yes if subtitles enabled |
| Narration texts | yes |
| alignment mode | no |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `subtitle_documents` | Cues + file paths |
| DSL `subtitles` update | yes |

#### Validation
- `end_sec > start_sec`  
- No overlapping cues on same track (warning/error policy: error if overlap > 20ms)  
- Formats requested are emitted  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Missing audio timings | fail `SUBTITLE_MISSING_AUDIO` |
| Alignment tool fail | fallback to even split within beat + warning |
| Schema invalid | R1 (if LLM used) else fail |

#### Dependencies
- Storage Port  
- Optional Whisper.cpp adapter  
- Voice artifacts  

#### Future Improvements
- Karaoke word highlighting  
- Dual-language cues  

---

### 9.21 Rendering Agent

#### Purpose
Invoke the Rendering Engine to rasterize the bound timeline into MP4 (plus thumbnail), muxing audio and optionally burning subtitles. **Does not call LLMs.**

#### Responsibilities
- Verify render-ready checklist (DSL + timeline + media)  
- Call Rendering Engine with export settings  
- Produce MP4 + thumbnail paths  
- Capture encoder logs/metrics  
- Update metadata thumbnail path  
- Never invent scenes or call planning agents  

#### Inputs
| Name | Required |
|------|----------|
| Presentation DSL `render_ready` | yes |
| Bound timeline | yes |
| Audio paths if voice enabled | yes |
| Subtitles if burn-in | conditional |
| export settings | yes |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `rendered_media` | mp4_path, thumbnail_path, probe metadata |
| Optional metadata path updates | yes |

#### Validation (Precondition Gate)
- DSL validation clean of errors  
- Timeline bound  
- Assets resolved  
- fps/resolution consistent  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Incomplete inputs | `RENDER_INPUT_INCOMPLETE` (R0) |
| Encoder fail | `RENDER_ENCODE_FAILED` (+ optional R3 draft if allowed) |
| Disk full | `STORAGE_DISK_FULL` (R0) |

#### Dependencies
- Rendering Engine (MoviePy/OpenCV/FFmpeg)  
- Storage / Output Manager  
- **No LLM Port** |

#### Future Improvements
- Hardware encoder auto-detect  
- Cloud render plugin (V4)  
- Chunked scene rendering for memory  

---

### 9.22 Project Manager Agent

#### Purpose
Own project lifecycle control: create/update project records, coordinate status, assemble export package references, support resume/cancel, and finalize completion.

#### Responsibilities
- Maintain `ProjectRecord` status  
- Index artifacts  
- Trigger Output Manager export manifest  
- Support resume from checkpoint  
- Apply cancellation  
- Record versions used  
- Finalize job success/failure  

#### Inputs
| Name | Required |
|------|----------|
| User/project commands | yes |
| Stage artifacts / job state | yes |
| Render outputs (for finalize) | conditional |

#### Outputs
| Artifact | Description |
|----------|-------------|
| `project_record` | Status, artifact index, versions |
| `export_manifest` | Files list for download package |

#### Validation
- Status transitions legal (`draft→running→completed/failed/cancelled`)  
- Completed jobs have required export files present  
- Artifact index paths resolve  

#### Failure Handling
| Failure | Handling |
|---------|----------|
| Missing exports on complete | refuse completed; mark failed `PROJECT_EXPORT_INCOMPLETE` |
| Corrupt index | rebuild from filesystem scan + warning |

#### Dependencies
- Storage Port / SQLite  
- Output Manager service  
- Orchestrator checkpoints  

#### Future Improvements
- Project templates  
- Collaborative locks (V5)  
- Snapshot/branch of DSL versions  

---

## 10. Pipeline Ordering & Parallelism

### 10.1 Canonical Order

```
Parser
 → Cleaning
 → Structure
 → Knowledge
 → Topic Classification
 → Difficulty
 → Explanation Strategy
 → Script
 → Scene Planner
 → Metadata                 ─┐
 → Visual Planning           │ may partially overlap Metadata
 → Layout Planner            │ after Visual inputs ready
 → Theme Planner
 → Asset Agent
 → (Presentation Engine compile hook)
 → Animation Agent
 → Camera Agent
 → Translation Agent?       ─┐
 → Voice Agent               │ language branch
 → Subtitle Agent           ─┘
 → Timeline Agent
 → Rendering Agent
 → Project Manager finalize
```

### 10.2 Hard Dependencies

| Agent | Must wait for |
|-------|----------------|
| Voice | Script (+ Translation if needed) |
| Subtitle | Voice durations |
| Timeline | Animations + Camera + Voice (if enabled) |
| Rendering | Timeline bound + assets resolved |
| Asset | Layout skeletons / object list |

### 10.3 Safe Parallelism (Optional)

- Metadata ∥ early Visual Planning (both after Scene Planner)  
- Per-beat TTS inside Voice Agent (worker pool, capped)  

Default on 16GB machines: **conservative sequential** graph with limited TTS concurrency.

---

## 11. Adding New Agents in Future Versions

### 11.1 When to Add an Agent

Add a new agent when a capability:

- has a distinct responsibility  
- needs its own schema  
- may fail/retry independently  
- might be cached independently  

Do **not** add an agent for trivial pure functions — use an engine/util instead.

### 11.2 Checklist for New Agents

1. **ADR** describing motivation and placement in graph  
2. Update this document with full section (Purpose → Future)  
3. Define `artifact_type` + `schema_version`  
4. Declare inputs/outputs and validation IDs  
5. Declare retry class defaults  
6. Declare logging `coarse_stage` mapping  
7. Declare DSL read/write rights (if any)  
8. Add orchestrator node + edges  
9. Add contract tests with fixtures + mocked ports  
10. Bump `graph_version`  

### 11.3 Extension Patterns

| Pattern | Example |
|---------|---------|
| Optional pre-parser | OCR Agent (plugin) before Cleaning |
| Optional mid-visual | ImageGen Planning Agent (V3 plugin) |
| Optional post-timeline | Loudness Normalize Agent |
| Replaceable media | Alternate TTS Agent behind same Voice contract |

### 11.4 Compatibility Rules

- New agents must not break old artifact schemas without version bump  
- Prefer additive optional outputs  
- Plugins that introduce agents must be disable-able; core graph runs without them  

### 11.5 Anti-Patterns for New Agents

- “SuperAgent” that scripts + lays out + renders  
- Agents that mutate upstream artifacts in place  
- Agents that require cloud APIs in core path  
- Agents that bypass Presentation DSL to feed the renderer  

---

## 12. Agent × DSL Interaction Matrix

| Agent | DSL Read | DSL Write | Sections Touched |
|-------|----------|-----------|------------------|
| Parser → Strategy | No | No | — |
| Script | No | No | — (feeds voice later) |
| Scene Planner | No | No | — |
| Metadata | Yes | Yes | `metadata` |
| Visual Planning | No | No | — |
| Layout Planner | Yes | Via engine | `scenes.layout`, object transforms |
| Theme Planner | Yes | Yes | `theme`, `style_tokens` |
| Asset Agent | Yes | Yes | `assets`, `asset_id`s |
| Animation Agent | Yes | Yes | `scenes.animations` |
| Camera Agent | Yes | Yes | `scenes.camera` |
| Timeline Agent | Yes | Yes | `timeline`, `duration.resolved_sec`, status |
| Translation | Yes | Yes | texts in voice/subtitles/metadata |
| Voice | Yes | Yes | `voice` |
| Subtitle | Yes | Yes | `subtitles` |
| Rendering | Yes | Thumbnail path only | `metadata.thumbnail.path` |
| Project Manager | Yes | Status/index | `project` lifecycle fields |

---

## 13. Error Code Registry (Agents)

| Code | Agent / Stage | Retriable |
|------|---------------|-----------|
| `PARSER_UNSUPPORTED_TYPE` | Parser | no |
| `PARSER_FILE_NOT_FOUND` | Parser | no |
| `PARSER_EMPTY_CONTENT` | Parser | no |
| `CLEAN_EMPTY` | Cleaning | no |
| `KNOWLEDGE_EMPTY` | Knowledge | no |
| `STRATEGY_EMPTY` | Strategy | no |
| `SCRIPT_COVERAGE` | Script | after repair, no |
| `THEME_INVALID` | Theme | no |
| `ASSET_PACK_MISSING` | Asset | no |
| `TRANSLATE_MODEL_MISSING` | Translation | no |
| `VOICE_NOT_FOUND` | Voice | no |
| `VOICE_EMPTY_TEXT` | Voice | no |
| `SUBTITLE_MISSING_AUDIO` | Subtitle | no |
| `TIMELINE_MISSING_AUDIO` | Timeline | no |
| `RENDER_INPUT_INCOMPLETE` | Rendering | no |
| `RENDER_ENCODE_FAILED` | Rendering | maybe (R3) |
| `PROJECT_EXPORT_INCOMPLETE` | Project Manager | no |
| `AGENT_VALIDATION_FAILED` | Any | repair |
| `AGENT_TIMEOUT` | Any | transient |
| `AGENT_CANCELLED` | Any | no |

---

## 14. Appendix: Minimal I/O Skeletons

Illustrative payloads (not full schemas). Official visual fields live in `PRESENTATION_DSL.md`.

### 14.1 Knowledge Model (skeleton)

```json
{
  "artifact_type": "knowledge_model",
  "schema_version": "1.0",
  "payload": {
    "concepts": [{ "id": "c1", "name": "", "definition": "", "prerequisites": [] }],
    "relations": [{ "from": "c1", "to": "c2", "type": "uses" }],
    "examples": [],
    "misconceptions": []
  }
}
```

### 14.2 Narration Script (skeleton)

```json
{
  "artifact_type": "narration_script",
  "schema_version": "1.0",
  "payload": {
    "language": "en",
    "beats": [
      { "id": "nar_01", "text": "", "scene_hint": "intro", "approx_sec": 8 }
    ]
  }
}
```

### 14.3 Visual Plan (skeleton)

```json
{
  "artifact_type": "visual_plan",
  "schema_version": "1.0",
  "payload": {
    "scenes": [
      {
        "scene_id": "scene_01",
        "visual_mode": "algorithm_trace",
        "primitives": ["array", "pointer", "highlight", "arrow"],
        "steps": ["show_array", "compare_mid", "narrow_range"],
        "forbidden": ["photoreal_human", "decorative_noise"]
      }
    ]
  }
}
```

### 14.4 Timeline Artifact (skeleton)

```json
{
  "artifact_type": "timeline",
  "schema_version": "1.0",
  "payload": {
    "version": "1.0",
    "fps": 30,
    "duration_sec": 42.5,
    "status": "bound",
    "tracks": [],
    "markers": []
  }
}
```

---

## Closing Statement

ExplainX agents are **isolated specialists** connected by **JSON artifacts**, sequenced by an orchestrator, and disciplined by validation, retries, and logs.

```
Plan in agents.
Record in artifacts.
Speak DSL.
Render without AI.
```

Any future capability that deserves independent failure domains, caching, or ownership should be specified here **before** it is implemented.

---

*End of AGENT_SPECIFICATIONS.md*  
*ExplainX Engineering — One Job per Agent. One Contract per Boundary.*
