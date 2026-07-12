# ExplainX — Development Roadmap

**Document Status:** Canonical Build Roadmap  
**Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Product Versions Crosswalk:** Constitution V1–V5  
**Companions:** All files under `docs/` especially  
`[PROJECT_CONSTITUTION.md](./PROJECT_CONSTITUTION.md)` ·  
`[DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)` ·  
`[FOLDER_STRUCTURE.md](./FOLDER_STRUCTURE.md)` ·  
`[SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)`  

> **Purpose:** Enable any developer to build ExplainX **from scratch** in a sane order.  
> Each phase lists objective, deliverables, dependencies, success criteria, and future extensions.  
> Do not skip foundational phases to “jump to video.” Deterministic engines before LLM spectacle.

---



## Table of Contents

1. [How to Use This Roadmap](#1-how-to-use-this-roadmap)
2. [Roadmap Overview Diagram](#2-roadmap-overview-diagram)
3. [Phase 0 — Architecture](#phase-0--architecture)
4. [Phase 1 — Core Infrastructure](#phase-1--core-infrastructure)
5. [Phase 2 — Document Intelligence](#phase-2--document-intelligence)
6. [Phase 3 — Knowledge Intelligence](#phase-3--knowledge-intelligence)
7. [Phase 4 — Content Intelligence](#phase-4--content-intelligence)
8. [Phase 5 — Presentation Engine](#phase-5--presentation-engine)
9. [Phase 6 — Animation Engine](#phase-6--animation-engine)
10. [Phase 7 — Multilingual Engine](#phase-7--multilingual-engine)
11. [Phase 8 — Rendering Engine](#phase-8--rendering-engine)
12. [Phase 9 — Frontend](#phase-9--frontend)
13. [Phase 10 — Optimization](#phase-10--optimization)
14. [Phase 11 — Testing](#phase-11--testing)
15. [Phase 12 — Documentation](#phase-12--documentation)
16. [Recommended Parallel Tracks](#16-recommended-parallel-tracks)
17. [Product Version Crosswalk](#17-product-version-crosswalk)
18. [From-Scratch Build Checklist](#18-from-scratch-build-checklist)
19. [Risk Register](#19-risk-register)

---



## 1. How to Use This Roadmap



### 1.1 Rules

1. Complete **success criteria** before treating a phase as done.
2. Honor **dependencies** — later phases assume earlier artifacts exist.
3. Prefer **fixtures** to unblock engines before agents are smart.
4. Update specs when contracts change (Definition of Done).
5. Cursor prompts should cite the **current phase** + relevant docs.



### 1.2 Phase Status Legend (for planning boards)


| Status        | Meaning               |
| ------------- | --------------------- |
| `NOT STARTED` | No implementation     |
| `IN PROGRESS` | Active development    |
| `BLOCKED`     | Waiting on dependency |
| `DONE`        | Success criteria met  |




### 1.3 Note on Phase 11 & 12

Testing and documentation run **continuously**, but each has a hardening phase so quality is not deferred forever.

---



## 2. Roadmap Overview Diagram

```
Phase 0  Architecture
    │
    ▼
Phase 1  Core Infrastructure
    │
    ├──────────────────────┐
    ▼                      ▼
Phase 2  Document     Phase 5  Presentation Engine (can start with fixtures)
Intelligence               │
    ▼                      │
Phase 3  Knowledge         │
Intelligence               │
    ▼                      │
Phase 4  Content ──────────┤  (feeds DSL compile)
Intelligence               │
    │                      ▼
    │                 Phase 6  Animation Engine
    │                      │
    ▼                      │
Phase 7  Multilingual      │
Engine (can overlap)       │
    │                      ▼
    └──────────────► Phase 8  Rendering Engine
                           │
                           ▼
                     Phase 9  Frontend (UI can start earlier against stubs)
                           │
                           ▼
                     Phase 10 Optimization
                           │
                           ▼
                     Phase 11 Testing (hardening)
                           │
                           ▼
                     Phase 12 Documentation (release-ready)
```

---



## Phase 0 — Architecture



### Objective

Establish the permanent product and engineering specifications so implementation does not invent architecture ad hoc.

### Deliverables

- `docs/PROJECT_CONSTITUTION.md`  
- `docs/SYSTEM_ARCHITECTURE.md`  
- `docs/PRESENTATION_DSL.md`  
- `docs/AGENT_SPECIFICATIONS.md`  
- `docs/DATABASE_DESIGN.md`  
- `docs/API_SPECIFICATION.md`  
- `docs/FOLDER_STRUCTURE.md`  
- `docs/DEVELOPMENT_GUIDE.md`  
- `docs/CODING_STANDARDS.md`  
- `docs/ROADMAP.md` (this file)  
- ADR process under `docs/ADRs/`



### Dependencies

- None (starting point)



### Success Criteria

- [ ] Specs exist and are internally consistent on isolation rules (agents, DSL, renderer)  
- [ ] Folder dependency direction agreed  
- [ ] V1 constraints (offline, free, hardware) documented  
- [ ] Team (or solo developer) accepts docs as source of truth  



### Future Extensions

- Additional ADRs as decisions arise  
- OpenAPI/JSON Schema mirrors of DSL & API  
- Threat model doc for networked V5

---



## Phase 1 — Core Infrastructure



### Objective

Stand up the runnable skeleton: repo layout, config, logging, DB, storage ports, API health, job shell — without full intelligence.

### Deliverables

- Repository skeleton per `FOLDER_STRUCTURE.md`  
- Backend boot (`FastAPI`), settings, DI, logging, error middleware  
- SQLite schema + migrations for core tables (`projects`, `render_jobs`, `job_stages`, …)  
- Repositories + filesystem project store (`data/projects/...`)  
- Ports with **fake** adapters (LLM/TTS/renderer fakes)  
- API: health, doctor, projects CRUD, jobs list/get stubs  
- `.gitignore` for `data/`; `.env.example`  
- Basic CI: lint + empty/unit smoke



### Dependencies

- Phase 0 architecture docs



### Success Criteria

- [ ] API starts locally and passes `/health` and `/system/doctor` (with clear not-ready flags)  
- [ ] Can create/get/list/delete a project in SQLite  
- [ ] Project directory created on disk  
- [ ] Job row can be inserted and polled with stub statuses  
- [ ] No model weights required for this phase  



### Future Extensions

- Postgres adapter behind same repositories  
- Split API vs worker processes  
- Auth middleware for networked mode

---



## Phase 2 — Document Intelligence



### Objective

Ingest source inputs and produce clean, structured text ready for knowledge extraction.

### Deliverables

- Upload API (`POST /projects/{id}/documents`, topic source)  
- **Parser Agent** (PDF/DOCX/TXT/MD/Topic)  
- **Cleaning Agent**  
- **Structure Agent**  
- Artifacts: `raw_document`, `clean_document`, `document_structure`  
- Orchestrator nodes for these stages + checkpoints  
- Fixtures: sample MD/TXT documents  
- Contract tests with no LLM or deterministic parsing only



### Dependencies

- Phase 1 (storage, jobs, API)



### Success Criteria

- [ ] Upload MD/TXT (and best-effort PDF/DOCX) produces non-empty clean text artifact  
- [ ] Structure artifact has at least one section tree  
- [ ] Job progress shows `reading_document` coarse stage  
- [ ] Failures return stable error codes (`PARSER_*`, `CLEAN_*`)  
- [ ] Resume skips completed parse/clean when hashes match  



### Future Extensions

- OCR plugin for scanned PDFs  
- Table-aware parsing  
- Bibliography/footnote channels

---



## Phase 3 — Knowledge Intelligence



### Objective

Turn structured documents into teachable concepts, classifications, difficulty, and explanation strategy.

### Deliverables

- **Knowledge Agent**  
- **Topic Classification Agent**  
- **Difficulty Agent**  
- **Explanation Strategy Agent**  
- Artifacts: `knowledge_model`, `topic_labels`, `difficulty_profile`, `explanation_plan`  
- LLM port wired to Ollama (Qwen2.5 3B) with strict JSON validation + repair retries  
- Contract tests with mocked LLM + one optional manual integration test



### Dependencies

- Phase 2 document artifacts  
- Local Ollama available for real runs (mocks for CI)



### Success Criteria

- [ ] Sample educational MD yields ≥1 validated concept  
- [ ] Topic + difficulty + strategy artifacts validate against schemas  
- [ ] Invalid LLM JSON triggers bounded repair then clear failure  
- [ ] Caching by input hash + agent version works  
- [ ] No agent calls another agent directly  



### Future Extensions

- Knowledge graph visualization for debug UI  
- Curriculum taxonomy packs  
- Cross-project concept reuse

---

## Phase 3.7 — Teaching Outline Service

### Objective

Insert a lesson-plan stage between RawContent and EducationalScript so narration
is planned before it is written.

### Pipeline

```
RawContent → TeachingOutline → EducationalScript
```

### Deliverables

- `TeachingOutline` + outline `TeachingSection` schemas (no narration)
- `TeachingOutlineService`, `OutlineGenerator`, Placeholder + Ollama generators
- `OutlineValidator` (8–12 sections; word budget at 140 WPM)
- Artifact: `artifacts/teaching_outline.json`
- ADR-0009

### Non-goals

- No new HTTP APIs  
- No Scene Planning  
- No narration inside the outline

### Success Criteria

- [x] Outline has 8–12 sections with id, title, learning_objective, target_words, key_concepts  
- [x] Total `target_words` matches duration × 140 WPM (±2)  
- [x] Script generation persists `teaching_outline.json` before EducationalScript  

---

## Phase 3.8 — Section Generation Engine

### Objective

Generate EducationalScript from TeachingOutline **one section at a time**, then merge.

### Pipeline

```
TeachingOutline → SectionGenerationService → EducationalScript
```

### Deliverables

- `SectionGenerationService`, `SectionGenerator`, Placeholder + Ollama generators
- `SectionMerger`, `SectionValidator`
- Artifacts: `artifacts/section_outputs/section_XX.json` + `educational_script.json`
- ADR-0010

### Rules

- Never generate the full script in one LLM call
- Each call receives title, objective, target_words, concepts, previous summary, next title
- EducationalScript schema unchanged

### Success Criteria

- [x] Independent per-section narration generation  
- [x] Merged EducationalScript validates in the V1 band  
- [x] Section outputs persisted under `artifacts/section_outputs/`  

---

## Phase 3.9 — Quality Assurance Engine

### Objective

Approve EducationalScript before downstream use: metrics → validate → targeted repair.

MVP priority: **stable end-to-end pipeline** over strict 2–3 minute duration accuracy.

### Pipeline

```
EducationalScript → ScriptMetricsCalculator → QualityAssuranceService → Approved EducationalScript
```

### Deliverables

- `QualityAssuranceService`, `ScriptRepairService`, `RepairGenerator`
- Placeholder + Ollama repair generators
- `QualityReport` + artifacts: `quality_report.json`, `approved_script.json`, `repair_log.json`
- ADR-0011

### MVP validation

Hard requirements:

- Estimated duration ≥ 60s and ≤ 300s (configurable)
- At least one teaching section; no empty narration; no duplicate section IDs

Not hard-gated:

- Per-section `target_words` (prompt guidance only)
- Total word count bands (metrics reporting only)

### Repair triggers (MVP)

Repair only when:

- Total duration &lt; 60s
- Empty sections
- Missing sections

Do not repair solely for `target_words` drift.

### Rules

- Never fake metrics; recalculate after every repair
- Never regenerate the entire script — repair affected sections only
- Max 2 repair attempts; then structured `SCRIPT_QUALITY_FAILED`
- No API / Scene Planning changes

### Success Criteria

- [x] PASS returns `status=ready` approved script  
- [x] Scripts under 60s are expanded via section repair  
- [x] QA artifacts persisted under `artifacts/`  
- [x] `target_words` drift does not fail the pipeline  

---



## Phase 4 — Content Intelligence



### Objective

Produce learner-facing narrative content: script, scenes, and catalog metadata.

### Deliverables

- **Script Agent**  
- **Scene Planner**  
- **Metadata Agent**  
- Artifacts: `narration_script`, `scene_plan`, `project_metadata`  
- API endpoints: generate script/scenes; GET script/scenes  
- Coverage validation (beats assigned; outline coverage checks)



### Dependencies

- Phase 3 knowledge plane artifacts



### Success Criteria

- [ ] Script contains TTS-friendly beats with unique IDs  
- [ ] Every beat maps to exactly one scene  
- [ ] Metadata title/description/tags populated  
- [ ] Generate endpoints return `202` + job progress  
- [ ] Contract tests pass with fake LLM  



### Future Extensions

- Style presets (teacher/documentary)  
- Quiz/recap scene modes  
- Automatic split/merge from measured audio durations

---



## Phase 5 — Presentation Engine



### Objective

Compile visual plans into the Presentation DSL and scene graph using diagram-first primitives (SVG/icons/shapes) — still without requiring generative images.

### Deliverables

- DSL Pydantic models + validators (`PRESENTATION_DSL.md`)  
- **Visual Planning Agent**  
- **Layout Planner**  
- **Theme Planner**  
- **Asset Agent**  
- `engines/presentation` compiler (procedural arrays, arrows, graphs, process flows, etc.)  
- Theme packs: NotebookLM, Whiteboard, Corporate, Minimal, Comic, Dark  
- Asset resolution against `/assets` packs  
- API: generate presentation; GET presentation DSL  
- Golden DSL fixtures for Binary Search / Photosynthesis / Networking



### Dependencies

- Phase 4 scene plan (for full path)  
- **Can start earlier** with hand-written scene/visual fixtures to unblock compiler



### Success Criteria

- [ ] Valid `presentation.dsl.json` compiled for sample scenes  
- [ ] Diagram primitives renderable in scene graph without AI images  
- [ ] Theme switch changes tokens without rewriting pedagogy props  
- [ ] DSL validation errors are actionable  
- [ ] Presentation engine does not import agents  



### Future Extensions

- Watercolor / Anime themes  
- Domain procedural compilers  
- Plugin `image` kind (V3)

---



## Phase 6 — Animation Engine



### Objective

Add pedagogical motion and camera framing, then bind an absolute timeline.

### Deliverables

- **Animation Agent**  
- **Camera Agent**  
- **Timeline Agent**  
- Engines: `animation/`, `camera/`, `timeline/`  
- DSL sections: `animations`, `camera`, `timeline`  
- API: generate timeline  
- Unit tests for easing, keyframes, bind rules  
- Golden timeline fixtures



### Dependencies

- Phase 5 compiled DSL  
- Voice durations preferred for final bind (see Phase 7); can bind with hints earlier for engine tests



### Success Criteria

- [ ] Scene-relative animations promote to absolute clips correctly  
- [ ] No overlapping scene clips; fps matches canvas  
- [ ] Camera limits enforced  
- [ ] `duration.resolved_sec` populated when audio present  
- [ ] Timeline Agent invokes engine — renderer still unused or optional  



### Future Extensions

- Theme motion packs  
- Word-level caption tracks  
- Cinematic camera presets

---



## Phase 7 — Multilingual Engine



### Objective

Enable local translation, TTS narration, and subtitles so videos are spoken and accessible offline.

### Deliverables

- **Translation Agent** (IndicTrans2; skip when languages equal)  
- **Voice Agent** (Piper TTS)  
- **Subtitle Agent** (SRT/VTT; optional Whisper.cpp alignment)  
- DSL updates: `voice`, `subtitles`  
- API: generate narration/subtitles; download audio/subs  
- Voice/language catalog endpoints  
- Memory policy: do not load translation + LLM + whisper simultaneously without need



### Dependencies

- Phase 4 script (required)  
- Phase 6 can finalize bind after voice durations (iteration loop)  
- Piper voices installed under `data/models`



### Success Criteria

- [ ] Per-beat audio files with measured `duration_sec`  
- [ ] Subtitles cues satisfy `end > start` and export files exist  
- [ ] Translation path works for at least one configured non-English target (or clearly gated as optional)  
- [ ] Timeline re-bind succeeds using real audio durations  
- [ ] Failures use `VOICE_*` / `SUBTITLE_*` / `TRANSLATE_*` codes  



### Future Extensions

- More language pairs and voice packs  
- Dual-language subtitles  
- Glossary-constrained translation

---



## Phase 8 — Rendering Engine



### Objective

Rasterize the bound presentation timeline into MP4 (plus thumbnail), mux audio, and assemble exports — **without calling AI**.

### Deliverables

- `engines/render` frame composer + quality profiles  
- FFmpeg adapter  
- **Rendering Agent** (façade only)  
- **Output Manager** / export package  
- API: render, export, download video/thumb/zip/manifest  
- Pause/cancel behavior around chunk boundaries (best effort)  
- Fixture path: golden DSL+timeline+silent/beep audio → MP4 in CI-optional job



### Dependencies

- Phase 5 DSL  
- Phase 6 timeline  
- Phase 7 audio/subs for full product path  
- FFmpeg installed



### Success Criteria

- [ ] Render-ready checklist enforced  
- [ ] MP4 + thumbnail produced for sample project  
- [ ] Export manifest lists video, audio, subs, metadata  
- [ ] Renderer never imports/calls agents or LLM port  
- [ ] Encode failure leaves DSL/timeline intact for retry  



### Future Extensions

- Hardware encoders (QSV/Iris Xe)  
- Cloud render plugin (V4)  
- Chunked distributed frames

---



## Phase 9 — Frontend



### Objective

Deliver a usable local operator UI for create → generate → monitor → download.

### Deliverables

- Next.js app under `apps/web`  
- Project library, create/upload, settings  
- Job progress UX (coarse stages)  
- Actions: generate, render, pause/resume/cancel  
- Export/download flows  
- Theme/voice/language selectors  
- Typed API client matching `API_SPECIFICATION.md`  
- Doctor/readiness banner when models missing



### Dependencies

- Phase 1 API minimum (UI stubs)  
- Phases 2–8 for full product loop (progressive enablement)



### Success Criteria

- [ ] User can go from topic/document to downloadable MP4 using UI only  
- [ ] UI never talks to Ollama/Piper directly  
- [ ] Error toasts show stable messages from API envelope  
- [ ] Polling does not freeze the UI  
- [ ] Responsive enough for desktop laptop use  



### Future Extensions

- DSL debug inspector (dev mode)  
- Collaborative presence (V5)  
- Desktop shell (Tauri/Electron)

---



## Phase 10 — Optimization



### Objective

Make the V1 path reliable on constrained hardware: memory, cache, resume, and encode performance.

### Deliverables

- Artifact cache keyed by hashes + versions  
- Resume from checkpoints across all stages  
- Model load/unload policy  
- Draft vs standard quality profiles tuned  
- DB/query indexes verified  
- Progress percent heuristics improved  
- Disk GC for temp frames  
- Performance notes measured on target-class machine



### Dependencies

- Phases 1–9 functional path



### Success Criteria

- [ ] Theme-only change does not regenerate knowledge unnecessarily  
- [ ] Voice-only change rebinds timeline + re-renders without full knowledge regen  
- [ ] Single active heavy job enforced by default  
- [ ] Doctor reports memory/disk warnings usefully  
- [ ] Sample 3-minute 720p path completes on 16GB-class machine without crash  



### Future Extensions

- Parallel TTS workers with caps  
- Smarter scene chunk encoding  
- Remote cache (later)

---



## Phase 11 — Testing



### Objective

Institutionalize quality gates so regressions cannot silently break DSL, agents, or render.

### Deliverables

- Unit suite for engines  
- Contract suite for agents (mocked ports)  
- API integration suite  
- Golden DSL/timeline fixtures CI-checked  
- Optional Playwright smoke for critical UI  
- Boundary import linter (`agents` ↛ each other; `render` ↛ `agents`)  
- Nightly/manual full offline pipeline job documented  
- Coverage of critical paths reported



### Dependencies

- Code from Phases 1–10 (testing starts earlier; this phase hardens)



### Success Criteria

- [ ] CI blocks merge on lint/type/unit/contract failures  
- [ ] Golden fixtures fail CI on unintentional diffs  
- [ ] At least one full offline sample path documented and periodically run  
- [ ] Flake rate acceptable; quarantine policy exists  
- [ ] Architecture boundary tests exist for critical forbidden imports  



### Future Extensions

- Visual regression screenshots of composed frames  
- Property-based tests for timeline binder  
- Load tests for API job queue

---



## Phase 12 — Documentation



### Objective

Make ExplainX approachable for new contributors and operators: runbooks, changelog, and release docs.

### Deliverables

- Root `README.md` with install/run/doctor/models instructions  
- Keep canonical `docs/*` in sync with shipped behavior  
- `CHANGELOG.md`  
- Contributor quickstart linking Development Guide + Coding Standards  
- Operator runbook: backup/restore per `DATABASE_DESIGN.md`  
- Release notes template  
- Optional diagram exports under `docs/diagrams/`



### Dependencies

- Ongoing from Phase 0; finalize for each release



### Success Criteria

- [ ] New developer can set up from README without tribal knowledge  
- [ ] Specs match implemented contracts (no known drift)  
- [ ] Release checklist references docs explicitly  
- [ ] Model download steps verified offline after install  



### Future Extensions

- Public developer portal  
- Auto-generated OpenAPI UI  
- Localized docs

---



## 16. Recommended Parallel Tracks

A small team can parallelize carefully:


| Track A (Backend core)      | Track B (Deterministic media)    | Track C (UI)                |
| --------------------------- | -------------------------------- | --------------------------- |
| Phase 1 → 2 → 3 → 4         | Phase 5 → 6 → 8 (fixtures first) | Phase 9 against API stubs   |
| Phase 7 after script exists | Integrate when agents ready      | Enable buttons as jobs land |


**Integration rule:** merge only behind working contracts; fake adapters keep CI green.

---



## 17. Product Version Crosswalk


| Product Version (Constitution)   | Roadmap Phases Primarily Involved                               |
| -------------------------------- | --------------------------------------------------------------- |
| **V1** Offline educational video | Phases 0–12 (core complete through optimization + hardening)    |
| **V2** Better themes & plugins   | Extend Phase 5 themes + plugin registry (Phase 1 plugins table) |
| **V3** Optional image generation | Phase 5 plugin visual backend; Asset Agent extensions           |
| **V4** Cloud rendering           | Phase 8 cloud adapter; API flags; privacy warnings              |
| **V5** Collaborative editing     | Phase 9 collab UI + API auth/ACL + DB sharing                   |


---



## 18. From-Scratch Build Checklist

Use this as a literal build order:

1. [ ] Read all Phase 0 docs
2. [ ] Scaffold repo (`FOLDER_STRUCTURE`)
3. [ ] Core infra: config, DB, API projects/jobs
4. [ ] Document intelligence agents + upload
5. [ ] Knowledge intelligence agents + Ollama port
6. [ ] Script/scenes/metadata agents
7. [ ] DSL models + presentation engine + themes/assets
8. [ ] Animation/camera/timeline engines + agents
9. [ ] Translation/voice/subtitles
10. [ ] Rendering + export
11. [ ] Frontend operator UI
12. [ ] Caching, resume, hardware hardening
13. [ ] CI/testing gates
14. [ ] README + changelog + release

**First celebrated milestone:** fixture DSL → MP4 with **no LLM**.  
**Second:** markdown topic → MP4 offline end-to-end.

---



## 19. Risk Register


| Risk                           | Phase | Mitigation                                  |
| ------------------------------ | ----- | ------------------------------------------- |
| LLM JSON unreliability         | 3–5   | Strict schemas, repair retries, templates   |
| RAM exhaustion on 16GB         | 7–10  | Sequential model loads, draft encodes       |
| PDF extraction poor            | 2     | Warnings, MD/TXT first-class, OCR later     |
| Scope creep (generative video) | all   | Constitution: presentation engine, not Sora |
| Doc drift                      | 12    | DoD requires doc updates with contracts     |
| Over-parallel jobs             | 10    | Default concurrency 1                       |


---



## Closing Statement

This roadmap turns ExplainX from a vision into a build sequence:

```
Architecture → Infrastructure → Documents → Knowledge → Content
    → Presentation → Animation → Multilingual → Render
    → Frontend → Optimize → Test → Document
```

Any developer can start at Phase 0, proceed in order (with the fixture-based parallel track for engines), and ship an offline presentation-to-video product without losing architectural integrity.

---

*End of ROADMAP.md*  
*ExplainX Engineering — Build the Spine First. Then Put Flesh on the Frames.*