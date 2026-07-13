# CURRENT_IMPLEMENTATION_ANALYSIS.md

**Document type:** Architecture audit (read-only)  
**Scope:** ExplainX backend (`backend/`) as implemented  
**Date:** 2026-07-13  
**Evidence run:** `python run.py topic "collateral damage"` → TOTAL **347.3 sec** (Intel i7 + `llama3:latest`)  
**Constraint:** No code was modified to produce this report.

---

## Executive Summary (one page)

### 1. How the current implementation actually works

`python run.py topic "…"` bootstraps settings/DB, creates a project, writes `RawContent` (no AI), then calls `ContentIntelligenceService.generate_script`. That orchestrator runs:

1. **TeachingOutlineService** — one Ollama call → lesson plan (`TeachingOutline`, 8–12 sections, no narration).  
2. **SingleScriptGenerationService** — one Ollama call → full narrations for all sections → `EducationalScript`.  
3. **QualityAssuranceService** — inspect + validate; optional **per-section** Ollama repair (only if hard failures); persist QA artifacts.  
4. Persist `educational_script.json` / metrics and set project phase to `content`.

APIs and schemas for `EducationalScript` / `TeachingOutline` are stable. Older paths (`OllamaContentGenerator`, `SectionGenerationService`) still exist in the tree but are **not** on the live CLI/API script path.

### 2. Why it currently takes ~6 minutes (this run: ~5.8 min)

| Stage | Wall time | Share of TOTAL |
|-------|-----------|----------------|
| Outline Ollama | **121.1 s** | **34.9%** |
| Single-script Ollama | **226.1 s** | **65.1%** |
| QA / validate / repair | **~0 s** | **~0%** |
| Project create + ingest | untimed, ≪1 s | ≈0% |

**Almost all runtime is two sequential CPU-bound Ollama `/api/generate` calls.** Nested `[Ollama]` lines are *inside* Outline/SingleScript, not extra additive work. The ~6-minute figure is local-model latency (prompt + long JSON completion), not Python orchestration.

### 3. Which components are well designed

- Protocol + factory pattern for generators (placeholder vs Ollama).  
- Outline = plan only; narration = separate pass.  
- QA validate → **targeted section repair** (not whole-script regen).  
- Shared `OllamaClient`, `prompt_format`, `pipeline_timing`.  
- Durable artifacts under `data/projects/<id>/artifacts/`.  
- Circular-import avoidance (quality ↛ section_generation; shared section types).

### 4. Which components should be redesigned (later)

- Dual script writers still in repo (`script/ollama`, `section_generation`) unused by the live path → cognitive load.  
- Nested timing (`[Ollama]` ≈ parent step) is confusing for ops.  
- Duplicate script copies (`educational_script.json` + `approved_script.json`).  
- Outline still ~2 minutes for a short JSON plan — prompt/model strategy, not Python.  
- Single-script call is huge (10 narrations) — main latency lever.

### 5. Which components should never be touched (without a deliberate ADR)

- Public HTTP API shapes.  
- `EducationalScript` / `TeachingOutline` Pydantic schemas.  
- DB schema / Alembic migrations for projects.  
- Offline Ollama boundary (`OllamaClient` contract).  
- QA gate semantics (approve only after validation; repair sections only).  
- Artifact root layout under `projects/<uuid>/`.

---

# 1. Current End-to-End Pipeline

Command: `python run.py topic "Binary Search"` (same path as `"collateral damage"`).

```
run.py
  └─ app.cli.dev_cli.main
       └─ run_pipeline(mode="topic")
            ├─ bootstrap()
            │    Settings, setup_logging, ensure_runtime_directories, init_database
            ├─ [1/4] create_or_load_project
            │    ProjectService.create(ProjectCreateRequest)
            │    → DB Project + ProjectFilesystem tree + project.json mirror
            ├─ [2/4] ingest_topic
            │    InputService.ingest_topic(TopicSourceRequest)
            │    → write source/topic.txt
            │    → InputRouter → TopicProcessor → RawContent
            │    → artifacts/v1/raw_content.json
            │    → project phase → document
            ├─ [3/4] generate_script
            │    verify_ollama → OllamaClient.ensure_ready (/api/tags)
            │    ContentIntelligenceService.generate_script
            │      pipeline_timing_scope
            │      ├─ read RawContent
            │      ├─ TeachingOutlineService.generate_outline
            │      │    OutlineGenerator (OllamaOutlineGenerator | Placeholder)
            │      │    apply_word_budget, OutlineValidator
            │      │    → teaching_outline.json
            │      ├─ SingleScriptGenerationService.generate_from_outline
            │      │    SingleScriptGenerator (Ollama | Placeholder)
            │      │    assemble_educational_script + metrics enrich
            │      ├─ enrich_script_with_metrics (ContentIntelligence)
            │      ├─ QualityAssuranceService.assure
            │      │    QualityInspector → ScriptValidator
            │      │    [optional] ScriptRepairService → RepairGenerator (Ollama)
            │      │    → quality_report.json, approved_script.json, repair_log.json
            │      ├─ ScriptMetricsCalculator.compute
            │      ├─ ScriptArtifactStore.write
            │      │    → educational_script.json, .md, script_metrics.json
            │      └─ project.current_phase = content; commit
            └─ [4/4] print_summary
```

### Models / protocols on the hot path

| Layer | Type |
|-------|------|
| Schemas | `RawContent`, `TeachingOutline`, `EducationalScript`, `ScriptMetrics`, `QualityReport`, `RepairLog` |
| Protocols | `OutlineGenerator`, `SingleScriptGenerator`, `OllamaClientProtocol`, `RepairGenerator` |
| Services | `ProjectService`, `InputService`, `ContentIntelligenceService`, `TeachingOutlineService`, `SingleScriptGenerationService`, `QualityAssuranceService`, `ScriptRepairService` |
| Stores | `InputArtifactStore`, `OutlineArtifactStore`, `ScriptArtifactStore`, `QualityArtifactStore` |

**Not on hot path (dormant but present):** `SectionGenerationService`, `OllamaContentGenerator` / `create_content_generator`, presentation/rendering agents.

---

# 2. Call Graph

```
dev_cli.run_pipeline
  ├─ ProjectService.create | get
  ├─ InputService.ingest_topic
  │    ├─ InputArtifactStore.write_text_source
  │    ├─ InputRouter.route → TopicProcessor.process
  │    └─ InputArtifactStore.write_raw_content + ProjectRepository update
  └─ ContentIntelligenceService.generate_script
       ├─ InputArtifactStore.read_raw_content
       ├─ TeachingOutlineService.generate_outline
       │    ├─ InputArtifactStore.read_raw_content
       │    ├─ create_outline_generator → OllamaOutlineGenerator.generate
       │    │    └─ OllamaClient.generate  (+ optional JSON repair generate)
       │    │         └─ OutlineResponseParser.parse
       │    ├─ apply_word_budget
       │    ├─ OutlineValidator.validate
       │    └─ OutlineArtifactStore.write
       ├─ SingleScriptGenerationService.generate_from_outline
       │    └─ create_single_script_generator → OllamaSingleScriptGenerator.generate
       │         └─ OllamaClient.generate  (+ optional JSON repair generate)
       │              └─ SingleScriptResponseParser.parse
       │                   └─ assemble_educational_script → enrich_script_with_metrics
       ├─ enrich_script_with_metrics
       ├─ QualityAssuranceService.assure
       │    ├─ QualityInspector.inspect
       │    ├─ ScriptValidator.validate
       │    ├─ [fail] ScriptRepairService.repair / repair_sections
       │    │    └─ create_repair_generator → OllamaRepairGenerator.repair_section
       │    │         └─ OllamaClient.generate
       │    └─ QualityArtifactStore.write_report | write_approved | write_repair_log
       ├─ ScriptMetricsCalculator.compute
       ├─ ScriptArtifactStore.write
       └─ ProjectRepository commit (phase=content)
```

### Dependency injection (construction)

| Service | Depends on |
|---------|------------|
| `ContentIntelligenceService` | `TeachingOutlineService`, `SingleScriptGenerationService`, `QualityAssuranceService`, stores, `ScriptMetricsCalculator` |
| `TeachingOutlineService` | `OutlineGenerator` (factory), `OutlineValidator`, input/outline stores |
| `SingleScriptGenerationService` | `SingleScriptGenerator` (factory), outline store |
| `QualityAssuranceService` | `QualityInspector`, `ScriptRepairService`, `ScriptValidator`, QA store |
| `ScriptRepairService` | `RepairGenerator` (factory) |
| All Ollama generators | shared `OllamaClient` (`features/script/ollama/client.py`) |

---

# 3. Ollama Usage

Shared transport: `OllamaClient.generate` → `POST {base}/api/generate` (non-streaming), wrapped in `timed_step("Ollama")`.  
Preflight (CLI only): `ensure_ready` → `GET /api/tags` (not a generation call).

## 3.1 Live path — every generation request

### A. Outline (always once; +0–1 JSON repair)

| Field | Value |
|-------|--------|
| File | `app/features/outline/ollama/generator.py` |
| Class | `OllamaOutlineGenerator` |
| Function | `generate` |
| Templates | `outline/ollama/templates.py`: `SYSTEM`, `USER`, optional `REPAIR_USER` |
| Input | `RawContent` (title, language, topic/sections text ≤8k chars), target duration, word budget, section_count≈10 |
| Output | JSON → `TeachingOutline` (title, language, 8–12 sections with id/title/learning_objective/key_concepts) |
| Est. prompt size | ~1.5–4 KB (topic) / up to ~10 KB (long PDF text) |
| Est. response size | ~2–6 KB JSON (plan only) |
| Observed time | **121.1 s** |

### B. Single script (always once; +0–1 JSON repair)

| Field | Value |
|-------|--------|
| File | `app/features/single_script/ollama/generator.py` |
| Class | `OllamaSingleScriptGenerator` |
| Function | `generate` |
| Templates | `single_script/ollama/templates.py`: `SYSTEM`, `USER`, optional `REPAIR_USER` |
| Input | Full `TeachingOutline` (all section ids, titles, objectives, concepts, target_words) |
| Output | JSON `{title, sections[{id,title,objective,narration}]}` → assembled `EducationalScript` |
| Est. prompt size | ~3–8 KB |
| Est. response size | ~8–20 KB (≈300–420 words narration × 10 sections + JSON) |
| Observed time | **226.1 s** |

### C. Section repair (0–N; only if QA finds repairable hard issues)

| Field | Value |
|-------|--------|
| File | `app/features/quality/ollama/generator.py` |
| Class | `OllamaRepairGenerator` |
| Function | `repair_section` |
| Templates | `quality/ollama/templates.py`: `SYSTEM`, `USER` (`render_user`) |
| Input | One `SectionRepairRequest` (action, title, objective, target/actual words, failures, context, original narration) |
| Output | JSON `{narration}` for that section only |
| Est. prompt size | ~1–4 KB |
| Est. response size | ~0.5–2 KB |
| Observed time (collateral damage run) | **0** (no repair) |

Max repair attempts: `MAX_REPAIR_ATTEMPTS` (2) per failing section / script loop.

## 3.2 Dormant generators (not called by ContentIntelligence today)

| Class | File | Role |
|-------|------|------|
| `OllamaContentGenerator` | `script/ollama/generator.py` | Legacy full-script from RawContent (`TOPIC_*` / `SCRIPT_*` / `PDF_*` / expand) |
| `OllamaSectionGenerator` | `section_generation/ollama/generator.py` | Per-section narration (N calls) |

---

# 4. Pipeline Timing

### Measured (generation scope only)

From the attached CLI run (`TOTAL: 347.3 sec`):

| Step | Seconds | % of TOTAL | Notes |
|------|---------|------------|--------|
| Project creation | ~0 (untimed) | ~0% | Outside `pipeline_timing_scope` |
| Ingestion | ~0 (untimed) | ~0% | Outside scope |
| Outline generation | **121.1** | **34.9%** | Dominated by nested `[Ollama] 121.1` |
| Single script generation | **226.1** | **65.1%** | Dominated by nested `[Ollama] 226.1` |
| Validation | **0.0** | **0.0%** | `[Validator]` inside QA |
| Repair | **0** | **0%** | No `[Repair N]` emitted |
| QA wall | **0.0** | **0.0%** | `[QualityAssurance]` |
| Persistence | ≪1 (untimed inside QA/script store) | ~0% | Atomic JSON writes |

**Important:** `[Ollama]` times are nested inside Outline/SingleScript. Do **not** sum Ollama + Outline + SingleScript — that would double-count. TOTAL ≈ Outline + SingleScript + QA.

### Why older docs said “6–8 minutes with 10–15 calls”

Previous architecture: 1 outline + N section calls. Current architecture: **2 generation calls** on success. Wall clock remains multi-minute because each call is still large on CPU `llama3:latest`, especially the single-script completion (~3.8 minutes alone).

---

# 5. Data Flow

```
Topic string
  ↓
source/topic.txt
  ↓
RawContent  →  artifacts/v1/raw_content.json
  ↓
TeachingOutline  →  artifacts/teaching_outline.json
  ↓
EducationalScript (draft status from LLM)
  ↓
ScriptMetricsCalculator (in-memory enrich)
  ↓
QualityAssuranceService
  ├─ QualityReport     → artifacts/quality_report.json
  ├─ RepairLog         → artifacts/repair_log.json
  └─ Approved script   → artifacts/approved_script.json  (status=ready)
  ↓
ScriptArtifactStore
  ├─ educational_script.json   (same approved payload)
  ├─ educational_script.md
  └─ script_metrics.json
```

### Absolute path pattern

```
{EXPLAINX_DATA_ROOT}/projects/{project_id}/
  project.json
  source/topic.txt
  artifacts/
    v1/raw_content.json
    teaching_outline.json
    educational_script.json
    educational_script.md
    script_metrics.json
    quality_report.json
    approved_script.json
    repair_log.json
```

Example from the audited run:

`C:\Users\hp\ExplainX\data\projects\905c89c6-1990-4e93-a840-4e701b1846d0\artifacts\`

---

# 6. Responsibility Analysis

| Service | Input | Output | Responsibility | Business logic? | Orchestration? | Keep? |
|---------|-------|--------|----------------|-----------------|----------------|-------|
| `ProjectService` | create/update DTOs | Project detail | CRUD, FS mirror, lifecycle | Yes (project domain) | Light | **Keep** |
| `InputService` | topic/script/pdf | `RawContent` | Validate, route processors, persist | Yes (ingestion) | Light | **Keep** |
| `TopicProcessor` | `ProcessorContext` | `RawContent` | Deterministic topic → sections | Yes | No | **Keep** |
| `ContentIntelligenceService` | `project_id` | Approved `EducationalScript` | End-to-end script pipeline | Thin | **Yes (main)** | **Keep** |
| `TeachingOutlineService` | `project_id` / RawContent | `TeachingOutline` | Plan generation + budget + validate + store | Yes | Medium | **Keep** |
| `SingleScriptGenerationService` | outline | `EducationalScript` | One-pass narration | Thin (delegates) | Light | **Keep** |
| `OllamaOutlineGenerator` | RawContent | TeachingOutline | LLM outline | Yes (AI adapter) | No | **Keep** |
| `OllamaSingleScriptGenerator` | TeachingOutline | EducationalScript | LLM full script | Yes (AI adapter) | No | **Keep** |
| `QualityAssuranceService` | script (+ raw/outline) | Approved script | Gate quality; drive repair | Yes | Medium | **Keep** |
| `ScriptRepairService` | findings / section errors | Patched script / SectionOutput | Targeted repairs only | Yes | Light | **Keep** |
| `ScriptMetricsCalculator` | script | metrics / enriched script | Deterministic WPM math | Yes | No | **Keep** |
| `SectionGenerationService` | outline | EducationalScript | Legacy N-section path | Yes | Medium | Keep for tests / remove later via ADR |
| `OllamaContentGenerator` | RawContent | EducationalScript | Legacy one-shot script | Yes | No | Dormant; do not expand |
| Presentation / Rendering / Agents | — | — | Later phases | — | — | Out of current script path |

---

# 7. Bottleneck Analysis

Ranked by estimated impact on wall-clock for topic → approved script on CPU:

| Rank | Bottleneck | Impact | Evidence |
|------|------------|--------|----------|
| 1 | **Single-script Ollama completion** (long JSON with 10 narrations) | **Very high** (~65%) | 226 s / 347 s |
| 2 | **Outline Ollama completion** | **High** (~35%) | 121 s / 347 s |
| 3 | **Sequential LLM stages** (outline must finish before script) | High (no overlap) | Architecture |
| 4 | Cold / CPU `llama3:latest` inference | High (amplifies 1–2) | Environment |
| 5 | Optional JSON-repair second generate | Medium (when parse fails) | Retry path |
| 6 | Optional QA section repairs (extra generates) | Medium-high when triggered | Not in this run |
| 7 | Duplicate persistence (`approved` + `educational_script`) | Low | I/O ≪1 s |
| 8 | Repeated `enrich_script_with_metrics` / inspect passes | Low | Pure Python |
| 9 | Prompt building / `json.dumps` schema injection | Negligible | Microseconds |
| 10 | Legacy dead code paths (section_generation) | Maintainability only | Not on hot path |

**Not significant today:** repeated per-section generation (removed from live path), project create, ingestion, validation CPU.

---

# 8. Dependency Graph

```
cli / routers
  → projects, input, script (ContentIntelligence), presentation, …
       → outline, single_script, quality
            → script.schemas, script.metrics, script.ollama.client
            → input.schemas / stores
            → projects.filesystem / repository
       → shared (prompt_format, pipeline_timing, section_*)
```

### Highlights

| Issue | Status |
|-------|--------|
| Circular quality ↔ section_generation | **Fixed** via shared types + `SectionAssurer` injection; quality does not import section_generation |
| `single_script` → `quality` | **None** (good) |
| All Ollama adapters → `script.ollama.client` | **Tight but intentional** shared client |
| `outline` → `script.durations` / processors.common | Mild cross-feature coupling |
| `ContentIntelligence` imports outline + single_script + quality | Acceptable orchestrator hub |
| Dependency inversion | Generators behind Protocols + factories — **good** |
| Dead package still imported by tests | `section_generation` — increases graph noise |

---

# 9. AI Architecture

### Prompt inventory (templates modules)

| Package | Templates | Active on CLI script path? |
|---------|-----------|----------------------------|
| `outline/ollama/templates` | SYSTEM, USER, REPAIR_USER, OUTLINE_JSON_SCHEMA | **Yes** |
| `single_script/ollama/templates` | SYSTEM, USER, REPAIR_USER, SINGLE_SCRIPT_JSON_SCHEMA | **Yes** |
| `quality/ollama/templates` | SYSTEM, USER, REPAIR_JSON_SCHEMA | **Yes (conditional)** |
| `section_generation/ollama/templates` | SYSTEM, USER, REPAIR_USER | No (dormant) |
| `script/ollama/templates` | TOPIC/SCRIPT/PDF/EXPAND/REPAIR families | No (dormant) |

### Hierarchy

```
SYSTEM (role)
  + USER (task + source/outline + schema_json)
  + optional REPAIR_USER (previous_response + schema)
```

All active templates inject schemas via `dumps_schema` / `format_prompt` (no raw JSON braces in template source).

### Retry / repair logic

| Kind | Trigger | Bound |
|------|---------|-------|
| JSON parse retry | Invalid LLM JSON | 1 repair generate per outline/script call |
| QA section repair | TOO_SHORT / EMPTY_SECTION (MVP) | ≤2 attempts; section-only |
| Whole-script regen | — | **Not used** by QA |

### JSON schemas (active)

1. Outline: title, language, sections[{id,title,learning_objective,key_concepts}]  
2. Single script: title, sections[{id,title,objective,narration}]  
3. Repair: {narration}

---

# 10. State Machine

Logical content states for the script pipeline (not all are distinct DB enums):

```
Created
  (ProjectStatus draft-ish; ProjectPhase foundation)
        ↓  ProjectService.create
Project Ready
        ↓  InputService.ingest_*
RawContent Ready
  (artifacts/v1/raw_content.json; phase → document)
        ↓  TeachingOutlineService.generate_outline
Outline Ready
  (teaching_outline.json; outline.status placeholder|draft|ready)
        ↓  SingleScriptGenerationService.generate_from_outline
Script Draft Ready
  (in-memory EducationalScript; status draft/placeholder)
        ↓  metrics enrich
Metrics Attached
        ↓  QualityAssuranceService.assure
QA Passed  OR  QA Failed (raise ValidationAppError)
        ↓  on pass
Approved
  (status=ready; approved_script.json + educational_script.json;
   project.current_phase = content)
```

### Transitions

| From | To | Trigger | Side effects |
|------|-----|---------|--------------|
| — | Created | `ProjectService.create` | DB row, dirs, `project.json` |
| Created | RawContent Ready | `InputService.ingest_topic` | `topic.txt`, `raw_content.json` |
| RawContent Ready | Outline Ready | `generate_outline` | Ollama outline, `teaching_outline.json` |
| Outline Ready | Script Draft Ready | `generate_from_outline` | Ollama single script |
| Script Draft Ready | QA Passed | `assure` success | QA artifacts, status=ready |
| Script Draft Ready | Failed | hard QA after max repair | report/log written; exception |
| QA Passed | Persisted API script | `ScriptArtifactStore.write` | educational_script + metrics |
| Any | Content phase | commit after success | `ProjectPhase.CONTENT` |

Note: `ProjectStatus` (draft/queued/running/…) is coarser and not finely stepped by the CLI topic flow today.

---

# 11. Current Folder Responsibilities

| Package | Responsibility |
|---------|----------------|
| `features/projects` | Project CRUD, FS jail, mirrors, import/export |
| `features/input` | Source ingest (topic/script/pdf), `RawContent`, processors, store |
| `features/outline` | Teaching outline generation, budget, validation, store |
| `features/single_script` | **Live** TeachingOutline → EducationalScript (one pass) |
| `features/section_generation` | **Legacy** per-section narration + merger + section_outputs store |
| `features/script` | Orchestrator (`ContentIntelligenceService`), schemas, metrics, validator, stores, shared `OllamaClient`, legacy content generator |
| `features/quality` | Inspector, QA service, repair, QA artifacts |
| `features/presentation` | Presentation plan (placeholder planner) — after script |
| `features/rendering` | Render stubs / later pipeline |
| `features/agents` | Agent router stubs |
| `features/settings` | App settings feature surface |
| `shared/` | Envelopes, health, prompt_format, pipeline_timing, section_output/validator |
| `cli/` | Developer CLI orchestration |
| `core/` | Config, errors, enums, logging, paths |
| `db/` | Engine, models, Alembic bootstrap |

---

# 12. Performance Recommendations

**No code changes in this audit.** Opportunities only:

| # | Opportunity | Est. time saved | Complexity | Risk |
|---|-------------|-----------------|------------|------|
| 1 | Faster / quantized model or GPU for Ollama | 50–80% of 347 s | Low (ops) | Low–med (quality) |
| 2 | Shrink single-script prompt/response (fewer sections, shorter caps, tighter schema) | 30–90 s | Med | Med (teaching quality) |
| 3 | Shorter outline (fixed 8 sections; smaller schema) | 20–60 s | Low | Low–med |
| 4 | Parallelize outline+something else | Limited (script needs outline) | High | High |
| 5 | Cache outlines by topic hash | Full 121 s on cache hit | Med | Low |
| 6 | Skip outline LLM for pure topics (template outline) | ~121 s | Med | Med (plan quality) |
| 7 | Stream generate / lower `num_predict` | 10–40% of LLM | Med | Med |
| 8 | Keep model warm (avoid reload between calls) | Variable | Low | Low |
| 9 | Merge outline+script into one LLM call | Removes one round-trip (~121 s) | High | High (schema/quality) |
| 10 | Remove duplicate approved/educational writes | ≪1 s | Low | Low |

Top practical levers: **(1) model/runtime**, **(2–3) smaller generations**, **(5–6) skip or cache outline**, **(9) single LLM call for entire lesson** if product accepts the quality tradeoff.

---

# 13. Architecture Score

| Dimension | Score (/10) | Rationale |
|-----------|-------------|-----------|
| Maintainability | **7** | Clear packages; legacy generators add noise |
| Extensibility | **8** | Protocols/factories; QA/outline/script separable |
| Testability | **8** | Placeholders, mockable `OllamaClientProtocol`, broad pytest suite |
| AI Pipeline | **7** | Sound outline→script→QA; dormant paths confuse the story |
| Performance | **4** | Correct structure for fewer calls; still ~6 min on CPU LLM |
| Separation of Concerns | **8** | Plan vs narration vs QA vs metrics well split |

**Overall:** ~**7/10** architecture with a **performance ceiling set by local LLM**, not by Python service design.

---

## Appendix A — Observed CLI timing (verbatim)

```
[Ollama] 121.1 sec
[Outline] 121.1 sec
[Ollama] 226.1 sec
[SingleScript] 226.1 sec
[Validator] 0.0 sec
[QualityAssurance] 0.0 sec
TOTAL: 347.3 sec
```

## Appendix B — Ollama call counts (happy path)

| Era | Generation calls |
|-----|------------------|
| Before single-pass | 1 outline + N sections (+ retries/repairs) ≈ **10–15+** |
| Current | **1 outline + 1 script** (+ 0–1 JSON repair each) (+ 0–N QA repairs) |

---

*End of audit. No source code was modified.*
