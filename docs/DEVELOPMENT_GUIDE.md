# ExplainX — Development Guide

**Document Status:** Canonical Engineering Workflow Reference  
**Version:** 1.0.0  
**Last Updated:** 2026-07-11  
**Companions:**  
[`PROJECT_CONSTITUTION.md`](./PROJECT_CONSTITUTION.md) ·  
[`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md) ·  
[`PRESENTATION_DSL.md`](./PRESENTATION_DSL.md) ·  
[`AGENT_SPECIFICATIONS.md`](./AGENT_SPECIFICATIONS.md) ·  
[`DATABASE_DESIGN.md`](./DATABASE_DESIGN.md) ·  
[`API_SPECIFICATION.md`](./API_SPECIFICATION.md) ·  
[`FOLDER_STRUCTURE.md`](./FOLDER_STRUCTURE.md)  

> **Authority:** This guide defines *how* ExplainX is developed day to day.  
> Architecture docs define *what* to build. This document defines process, quality gates, and Cursor usage.  
> When workflow conflicts with informal habit, **this guide wins** until amended via ADR.

---

## Table of Contents

1. [Development Philosophy](#1-development-philosophy)
2. [Architecture Workflow](#2-architecture-workflow)
3. [Branch Strategy](#3-branch-strategy)
4. [Commit Strategy](#4-commit-strategy)
5. [Module Development Order](#5-module-development-order)
6. [Coding Workflow](#6-coding-workflow)
7. [How to Add New Features](#7-how-to-add-new-features)
8. [Using Cursor AI](#8-using-cursor-ai)
9. [Testing Strategy](#9-testing-strategy)
10. [Review Strategy](#10-review-strategy)
11. [Dependency Management](#11-dependency-management)
12. [Release Process](#12-release-process)
13. [Project Milestones](#13-project-milestones)
14. [Definition of Done](#14-definition-of-done)
15. [Local Environment Expectations](#15-local-environment-expectations)
16. [Communication & Documentation Hygiene](#16-communication--documentation-hygiene)
17. [Appendix: PR Checklist](#17-appendix-pr-checklist)
18. [Appendix: Cursor Prompt Templates](#18-appendix-cursor-prompt-templates)

---

## 1. Development Philosophy

ExplainX is **not** a hackathon codebase.

| Principle | Practice |
|-----------|----------|
| Architecture first | Specs before modules; ADRs before breaking changes |
| Contracts over cleverness | JSON schemas, API envelope, DSL versioning |
| Isolation | Agents do not call agents; renderer does not call AI |
| Offline-first | No paid APIs in core; doctor checks for local deps |
| Incremental vertical slices | Prefer thin end-to-end paths over orphaned layers |
| Enterprise feel | Logging, validation, tests, reviewable PRs |

**Default mindset:** change the smallest layer that satisfies the requirement, prove it with tests, update docs if contracts moved.

---

## 2. Architecture Workflow

### 2.1 When Architecture Work Is Required

Do architecture work (docs + ADR) **before coding** when the change:

- adds/removes an agent  
- changes Presentation DSL fields or meaning  
- adds a DB table or breaks migrations  
- adds/renames public API endpoints  
- introduces a plugin type or cloud dependency  
- changes folder dependency direction  

### 2.2 Architecture Change Loop

```
1. Identify impacted specs (constitution / architecture / DSL / agents / DB / API / folders)
2. Draft or update ADR in docs/ADRs/
3. Update the relevant canonical doc(s)
4. Get review (even if solo: self-review against "What Should Never Happen")
5. Implement against the updated contracts
6. Add tests that lock the new contract
```

### 2.3 ADR Minimum Template

```markdown
# ADR-XXXX: Title

- Status: Proposed | Accepted | Superseded
- Date: YYYY-MM-DD
- Context
- Decision
- Consequences
- Docs updated
- Alternatives considered
```

### 2.4 Spec Precedence

If documents disagree temporarily during a change:

1. Accepted ADR for the change  
2. Updated canonical doc for that domain  
3. Older docs (must be brought in sync in the same PR when possible)  

---

## 3. Branch Strategy

### 3.1 Branch Types

| Branch | Purpose | Lifetime |
|--------|---------|----------|
| `main` | Stable, releasable line | Permanent |
| `develop` (optional) | Integration line if team prefers GitFlow | Permanent if used |
| `feature/<slug>` | New capability | Short |
| `fix/<slug>` | Bug fix | Short |
| `chore/<slug>` | Tooling, deps, docs-only | Short |
| `docs/<slug>` | Documentation amendments | Short |
| `release/<x.y.z>` | Release hardening | Short |
| `hotfix/<slug>` | Urgent fix off `main` | Short |

**V1 recommendation (solo/small team):** trunk-based on `main` + short-lived `feature/*` branches. Introduce `develop` only if parallel unstable integration becomes painful.

### 3.2 Naming Rules

```
feature/presentation-engine-compiler
fix/timeline-audio-bind
docs/update-dsl-camera-fields
chore/bump-fastapi
```

Use kebab-case. Include issue/ticket id if one exists: `feature/EX-42-voice-agent`.

### 3.3 Branch Rules

| Rule | Detail |
|------|--------|
| Branch from | Latest `main` (or `develop` if adopted) |
| Keep updated | Rebase or merge regularly; prefer rebase for private feature branches |
| No direct force-push to `main` | Protected |
| One primary concern per branch | Do not mix DSL redesign with unrelated UI polish |
| Delete after merge | Clean remote feature branches |

### 3.4 Protection Expectations (When Hosted)

- `main` requires PR  
- CI green required  
- No force-push  
- Optional: 1 approving review for non-docs changes  

---

## 4. Commit Strategy

### 4.1 Conventional Commits

```
<type>(<optional-scope>): <short summary>

[optional body]

[optional footer]
```

**Types:**

| Type | Use |
|------|-----|
| `feat` | New user/capability-facing feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Internal restructure without behavior change |
| `test` | Tests only |
| `chore` | Tooling, deps, housekeeping |
| `perf` | Performance improvement |
| `build` | Build system |
| `ci` | CI config |

**Scopes (examples):** `api`, `agents`, `dsl`, `presentation`, `animation`, `render`, `web`, `db`, `docs`

### 4.2 Examples

```
feat(agents): add script agent contract validation

fix(timeline): bind scene duration from narration audio

docs(api): document pause/resume job endpoints

refactor(engines): extract easing helpers from animation compiler
```

### 4.3 Commit Rules

| Rule | Detail |
|------|--------|
| Atomic | One logical change per commit when practical |
| Why over noise | Body explains motivation when non-obvious |
| No secrets | Never commit `.env`, keys, user projects, model weights |
| No generated junk | Don't commit `data/`, caches, MP4s |
| Pass hooks | Fix failures; do not `--no-verify` unless explicitly required emergency |

### 4.4 Commit vs PR Granularity

- Prefer multiple clean commits on a feature branch  
- Squash-merge is acceptable for tiny fixes  
- Preserve commit history for large architectural features when it aids bisect  

---

## 5. Module Development Order

Build bottom-up **contracts**, then vertical slices. Do not start with a polished UI over empty agents.

### 5.1 Phase Map (Implementation Order)

| Order | Module | Outcome |
|------:|--------|---------|
| 0 | Docs freeze (already in progress) | Specs accepted as baseline |
| 1 | Repo skeleton + `FOLDER_STRUCTURE` | Empty modules, configs, gitignore `data/` |
| 2 | Core config, logging, errors, DI | App boots |
| 3 | DB + repositories + migrations | Projects/jobs persist |
| 4 | Filesystem project store | Artifact paths work |
| 5 | API health/doctor + projects CRUD | Control plane starts |
| 6 | Ports + fake adapters | Testability without models |
| 7 | Presentation DSL schemas + validators | Language locked in code |
| 8 | Presentation Engine (procedural diagrams) | DSL → scene graph |
| 9 | Animation + Camera + Timeline engines | DSL → timeline |
| 10 | Render engine with fixture DSL | Timeline → MP4 (no AI) |
| 11 | Orchestration skeleton (LangGraph) | Job stages + checkpoints |
| 12 | Knowledge-plane agents (parser→strategy) | Document → knowledge |
| 13 | Script + Scene Planner | Knowledge → narration/scenes |
| 14 | Visual/Layout/Theme/Asset agents | Scenes → DSL compile path |
| 15 | Voice + Subtitle (+ Translation) | Media sidecars |
| 16 | Wire Rendering Agent + Output Manager | Full offline path |
| 17 | Frontend project/job/export UX | Usable product loop |
| 18 | Themes polish + caching + resume | V1 hardening |
| 19 | Plugins registry (minimal) | V2 readiness |

### 5.2 Vertical Slice Rule

After engines exist with fixtures, each agent PR should leave behind:

- schema  
- agent node  
- tests with mocks  
- artifact written to store  
- stage visible in job progress  

Avoid merging agents that cannot run in the graph.

### 5.3 What Not to Build Early

- Cloud rendering  
- Generative image plugins  
- Collaborative editing  
- Perfect UI animation  
- Every theme variant  

Stay aligned with roadmap V1 in the constitution.

---

## 6. Coding Workflow

### 6.1 Standard Developer Loop

```
1. Pull latest main
2. Create branch
3. Read relevant docs (DSL / agents / API / folders)
4. Write failing test or contract stub (when behavior exists)
5. Implement smallest change
6. Run targeted tests + linters
7. Update docs if contracts changed
8. Self-review against "Never Happen" list
9. Open PR with checklist
10. Address review; merge; delete branch
```

### 6.2 Layer Checklist While Coding

Ask:

1. Which layer owns this? (`FOLDER_STRUCTURE.md`)  
2. Does an agent need a new artifact schema?  
3. Am I about to call an agent from an engine? (stop)  
4. Am I about to call Ollama from the frontend? (stop)  
5. Will the renderer still be AI-free?  

### 6.3 Code Quality Expectations

| Expectation | Detail |
|-------------|--------|
| Typed interfaces | Pydantic / TypeScript types at boundaries |
| Validation | Validate at API ingress and agent egress |
| Logging | Structured stage logs with project/job ids |
| Errors | Stable error codes from specs |
| DI | Adapters injected; no hidden globals |
| Comments | Only for non-obvious intent; prefer clear names |

### 6.4 Performance Awareness (Target Hardware)

Develop with i7-1255U / 16GB constraints in mind:

- default one heavy job  
- prefer 720p draft during iteration  
- don't load LLM + translation + whisper simultaneously without need  

---

## 7. How to Add New Features

### 7.1 Feature Intake Template

Before coding, write (in PR description or issue):

1. **User outcome** — what becomes possible  
2. **Specs touched** — list docs  
3. **Layer** — api / service / agent / engine / web  
4. **Artifacts** — new/changed JSON  
5. **Risks** — offline, memory, contract breaks  
6. **Test plan** — unit/contract/integration  

### 7.2 Feature Types & Paths

| Feature type | Primary path | Must update |
|--------------|--------------|-------------|
| New API endpoint | `api/routes` + service | `API_SPECIFICATION.md` |
| New agent | `agents/` + graph edge | `AGENT_SPECIFICATIONS.md` |
| New DSL kind/field | `models/dsl` + engines | `PRESENTATION_DSL.md` (+ versioning rules) |
| New theme | `themes/{id}` + seed | constitution themes list if public |
| New DB table | migrations + repository | `DATABASE_DESIGN.md` |
| UI flow | `apps/web/features` | API client types |
| Plugin | `plugins/` + registry | plugin contract docs |

### 7.3 Feature Implementation Sequence

```
Spec → Schema → Engine/Agent → Service/API → UI → Tests → Docs sync → PR
```

Skip UI until API returns real job progress for that feature (unless pure UI).

### 7.4 Backward Compatibility

- Prefer additive JSON fields  
- Bump `dsl_version` per DSL rules when needed  
- Provide migration notes for DB  
- Avoid breaking `/api/v1` without version plan  

---

## 8. Using Cursor AI

Cursor is a force multiplier **inside** the architecture, not a substitute for it.

### 8.1 Golden Rules for Cursor

| Rule | Detail |
|------|--------|
| Specs first | Point Cursor at `docs/*.md` before generating modules |
| One layer per prompt | Don't ask for “whole app” in one shot |
| No architecture by accident | If Cursor invents a new top-level folder, stop and align with `FOLDER_STRUCTURE.md` |
| Preserve isolation | Explicitly forbid agent↔agent calls and renderer→LLM |
| Prefer diffs | Ask for minimal patches over rewrites |
| Verify | Run tests; don't trust compiled-looking code |

### 8.2 Recommended Cursor Workflow

1. **Context priming** — open or `@` the relevant docs (`PRESENTATION_DSL`, `AGENT_SPECIFICATIONS`, `FOLDER_STRUCTURE`, `API_SPECIFICATION`).  
2. **Task framing** — state layer, files allowed to change, files forbidden.  
3. **Contract first** — ask for schemas/tests before implementation when practical.  
4. **Implement** — small vertical step.  
5. **Review pass** — ask Cursor to review against “What Should Never Happen.”  
6. **Human gate** — you own merge decisions.  

### 8.3 Good Cursor Tasks

- Generate Pydantic models from DSL sections  
- Scaffold an agent with envelope I/O and validation stubs  
- Write contract tests with mocked LLM port  
- Add API route stubs matching `API_SPECIFICATION.md`  
- Draft ADR text for a proposed change  
- Refactor a pure engine function with golden fixtures  

### 8.4 Bad Cursor Tasks (Avoid)

- “Build ExplainX”  
- “Connect the frontend directly to Ollama”  
- “Make the renderer call GPT if timeline missing”  
- Silent dependency adds without documenting  
- Massive unrelated file reformatting  

### 8.5 Prompt Constraints to Paste Often

```
Follow docs/PROJECT_CONSTITUTION.md, SYSTEM_ARCHITECTURE.md,
PRESENTATION_DSL.md, AGENT_SPECIFICATIONS.md, FOLDER_STRUCTURE.md,
and API_SPECIFICATION.md.

Constraints:
- Do not invent new top-level folders
- Agents must not call other agents
- Renderer must not call AI
- Frontend must only talk to /api/v1
- Offline-first; no paid APIs
- Keep changes minimal and typed
```

### 8.6 Multi-Agent / Multi-File Edits

When using Cursor across many files:

- Prefer agent/feature branches  
- Ask for a file change list before edits  
- Reject drive-by refactors outside scope  

---

## 9. Testing Strategy

### 9.1 Pyramid

```
        /\
       /  \        E2E / manual offline run (few)
      /----\
     / integ \     API + mini pipeline (mocked LLM or tiny fixtures)
    /--------\
   /  contract \   Agent I/O schemas (LLM mocked)
  /------------\
 /    unit       \ Engines, validators, repos
/----------------\
```

### 9.2 What Each Layer Tests

| Layer | Tests |
|-------|-------|
| Engines | Deterministic DSL/timeline/frame helpers; golden JSON |
| Agents | Schema validation; prompt plumbing with fake LLM |
| Services/API | Status codes, envelopes, job state transitions |
| Repositories | CRUD + FK expectations on SQLite |
| Web | Component/hooks; optional Playwright smoke |
| System | Manual/doctor-assisted offline run on sample MD |

### 9.3 Fixture Policy

Keep small fixtures:

- `binary_search.md`  
- `photosynthesis.md`  
- `networking.md`  

Golden DSL/timeline snapshots change only intentionally (review diffs carefully).

### 9.4 When Tests Are Mandatory

| Change | Required tests |
|--------|----------------|
| Engine math/preset | Unit + golden if output stable |
| Agent contract | Contract test with mock port |
| API endpoint | Integration/API test |
| DSL field | Validator tests + doc bump |
| Bug fix | Regression test reproducing bug |

### 9.5 CI Expectations

CI SHOULD run:

1. Lint/format checks  
2. Unit + contract tests  
3. API integration tests with fake adapters  
4. Boundary import check (when available)  

Full MP4 encode MAY be nightly/manual due to time/hardware.

---

## 10. Review Strategy

### 10.1 Review Goals

Catch:

- layer violations  
- contract drift from docs  
- missing validation/logging  
- offline regressions  
- accidental large scope  

### 10.2 Reviewer Checklist

1. Does this match `FOLDER_STRUCTURE` dependency rules?  
2. Any agent calling another agent?  
3. Any renderer/LLM coupling?  
4. Docs updated if public contract changed?  
5. Tests adequate for risk?  
6. Error codes stable and documented?  
7. Secrets/data files absent?  
8. Performance concerns on 16GB laptop?  

### 10.3 PR Size Guidance

| Preferred | Caution |
|-----------|---------|
| <400 lines logical change | Multi-layer mega PRs |
| One feature concern | “While I was here” refactors |
| Docs+code together for contract changes | Code merged, docs “later” |

Split large work:

- `feat: DSL schema + validators`  
- `feat: presentation compiler for arrays`  
- `feat: API generate/presentation job`  

### 10.4 Review SLA (Team Norm)

- First response within 1 business day when multiple contributors exist  
- Blocking issues labeled clearly (`blocking` vs `nit`)  

### 10.5 Self-Review Required

Authors must self-review the GitHub diff before requesting review.

---

## 11. Dependency Management

### 11.1 Principles

| Principle | Practice |
|-----------|----------|
| Minimal | Add a dependency only for clear leverage |
| Offline-capable | Prefer libs that don't need network at runtime |
| Pinned | Lockfiles committed |
| Free/compatible licenses | Respect constitution (no paid API SDKs in core) |
| Layer-appropriate | UI deps in `apps/web`; Python deps in `backend` |

### 11.2 Python (Backend)

- Manage with `pyproject.toml` + lockfile (e.g. uv/poetry/pip-tools — choose one and document in README)  
- Separate optional extras if needed: `backend[dev]`, `backend[render]`  
- Native tools (FFmpeg, Ollama, Piper) are **system dependencies**, not only pip packages  
- Record versions in doctor output  

### 11.3 Node (Frontend)

- `pnpm` or `npm` with lockfile  
- Avoid heavy UI kits that fight the design system without need  
- Keep Framer Motion for UI only — not video pipeline  

### 11.4 Adding a Dependency Process

1. Justify in PR (why not existing code/lib)  
2. Check license & offline behavior  
3. Pin version  
4. Update README/doctor if operators must install something  
5. Do not add cloud AI SDKs to core path  

### 11.5 Upgrades

- Dependabot/renovate optional  
- Batch routine bumps in `chore/` PRs  
- Major upgrades get an ADR if they affect ports/adapters  

### 11.6 Models Are Not Package.json Deps

Model weights are installed into `data/models` via scripts; version pins live in settings/docs.

---

## 12. Release Process

### 12.1 Versioning

ExplainX product versions follow semver: `MAJOR.MINOR.PATCH`

| Bump | When |
|------|------|
| MAJOR | Breaking DSL/API or product paradigm changes |
| MINOR | New features backward compatible |
| PATCH | Fixes, docs, safe hardening |

Also track:

- `dsl_version`  
- `graph_version`  
- API URI `v1`  

### 12.2 Release Checklist

1. `main` green on CI  
2. Update `CHANGELOG.md` (create when releasing)  
3. Ensure migrations apply cleanly from previous version  
4. Run doctor on target Windows profile  
5. Smoke: topic → MP4 offline sample  
6. Tag `vX.Y.Z`  
7. Attach release notes (models to download, breaking changes)  
8. Optional: package installer artifacts later  

### 12.3 Release Branch (Optional)

For multi-day hardening:

```
release/0.1.0 → only fixes/docs → merge to main → tag
```

### 12.4 Hotfix

```
hotfix/<slug> from main → fix → PR → tag patch → backport if develop exists
```

### 12.5 What a V1 Release Must Include

- Offline pipeline for MD/TXT/(PDF best-effort)  
- At least core themes  
- Export package (video, audio, subs, thumb, metadata)  
- Documented model install + doctor  

---

## 13. Project Milestones

Aligned with constitution roadmap; refined for engineering delivery.

### Milestone M0 — Spec Complete (Phase 0)

**Status target:** documentation baseline  

- Constitution, architecture, DSL, agents, DB, API, folders, this guide  
- No application feature work required beyond scaffolding decisions  

**Exit criteria:** specs reviewed; ADR process agreed.

### Milestone M1 — Skeleton & Control Plane

- Repo structure  
- SQLite + projects/jobs API  
- Frontend project list/create shell  
- Doctor endpoint  

**Exit:** create project via UI/API; persist in DB.

### Milestone M2 — Deterministic Media Core

- DSL schemas/validators  
- Presentation/Animation/Timeline/Render engines  
- Fixture DSL → MP4 without LLM  

**Exit:** golden fixture renders offline.

### Milestone M3 — Knowledge → Script → Scenes

- Parser through Scene Planner agents  
- Artifacts on disk + job progress  

**Exit:** document/topic produces script + scene plan.

### Milestone M4 — Presentation Compile Path

- Visual/Layout/Theme/Asset agents  
- DSL compile integration  

**Exit:** scene plan becomes valid Presentation DSL.

### Milestone M5 — Voice, Subtitles, Full Render

- Voice/Subtitle/(Translation optional)  
- Timeline bind + Rendering Agent + export  

**Exit:** offline explainer MP4 from sample markdown.

### Milestone M6 — V1 Product Hardening

- Resume/cancel/pause  
- Caching  
- Theme pack polish  
- Error UX  
- Windows target validation (i7-1255U/16GB class)  

**Exit:** tag `v0.1.0` or `v1.0.0-beta` per team choice.

### Milestone M7 — V2 Themes & Plugins

- Plugin registry  
- Additional themes  
- Better motion packs  

### Milestone M8+ — Roadmap V3–V5

- Optional image gen plugins  
- Cloud render adapter  
- Collaborative editing  

---

## 14. Definition of Done

### 14.1 Universal DoD (Every Feature)

A feature is **Done** only when all applicable items pass:

| # | Criterion |
|---|-----------|
| 1 | Solves the stated user/engineering outcome |
| 2 | Lives in the correct layer/folder |
| 3 | Public contracts updated in `docs/` if changed |
| 4 | ADR filed if architecture-impacting |
| 5 | Typed models/interfaces added or updated |
| 6 | Validation at boundaries |
| 7 | Structured logging for new stages/endpoints |
| 8 | Tests required by §9.4 added and passing |
| 9 | No layer violations (agents/renderer/frontend rules) |
| 10 | Offline core path not broken; no new paid API in core |
| 11 | Error codes documented when new |
| 12 | Lint/typecheck clean for touched areas |
| 13 | PR checklist completed; review approved (if team) |
| 14 | Merged to `main` (or release branch as applicable) |

### 14.2 DoD by Feature Class

#### API Feature

- Route listed in `API_SPECIFICATION.md`  
- Envelope + error shape correct  
- Integration test for happy path + validation failure  
- Idempotency behavior defined if job-creating  

#### Agent Feature

- Section exists/updated in `AGENT_SPECIFICATIONS.md`  
- Artifact envelope + schema version  
- Contract tests with mocked ports  
- Graph node + checkpoint behavior  
- Progress coarse/fine stage mapped  

#### Engine Feature

- Deterministic unit tests  
- No imports from `agents`  
- Golden fixtures updated deliberately  

#### DSL Feature

- `PRESENTATION_DSL.md` updated  
- Versioning rules followed  
- Validators + at least one example updated  
- Renderer still AI-free  

#### UI Feature

- Uses API client only  
- Loading/error/empty states handled  
- Does not assume sync render completion  

#### Database Feature

- Migration added  
- `DATABASE_DESIGN.md` updated  
- Repository tests  
- No breaking change without upgrade path  

### 14.3 Not Done If

- “Works on my machine” without tests for risky logic  
- Docs pending “follow-up PR” for contract changes  
- Temporary bypass of isolation “just for now”  
- Feature merged behind silent broken doctor dependencies without documenting  

---

## 15. Local Environment Expectations

Developers SHOULD be able to:

1. Clone repo  
2. Install Node + Python tooling  
3. Create `data/` root  
4. Run API + web against localhost  
5. Run unit tests without GPU  
6. Optionally install Ollama/Piper/FFmpeg for full pipeline  

Document exact commands in root `README.md` when implementation begins (not in this phase).

Target validation hardware remains:

- Intel i7-1255U class  
- 16GB RAM  
- Intel Iris Xe optional  
- Windows first-class  

---

## 16. Communication & Documentation Hygiene

| Practice | Detail |
|----------|--------|
| Specs are source of truth | Chat decisions must land in docs |
| PR links ADR/docs | For discoverability |
| Prefer updating canonical docs over new competing markdown | Avoid doc sprawl |
| User projects stay in `data/` | Never commit |
| Security | No secrets in git or Cursor prompts pasted from prod keys |

---

## 17. Appendix: PR Checklist

Copy into PR body:

```markdown
## Summary
- 

## Specs
- [ ] No contract change
- [ ] Updated docs: (list)
- [ ] ADR: (link/id or N/A)

## Layer
- [ ] Correct folder placement
- [ ] No agent↔agent calls
- [ ] Renderer AI-free
- [ ] Frontend API-only

## Tests
- [ ] Unit/contract/integration as required
- [ ] Fixtures/goldens updated if needed

## Offline / Deps
- [ ] No paid API in core
- [ ] New deps justified + pinned
- [ ] Doctor/README note if operator install needed

## DoD
- [ ] Universal DoD satisfied
```

---

## 18. Appendix: Cursor Prompt Templates

### 18.1 Implement an Agent Stub

```
Implement only backend/app/agents/<name>_agent.py and its Pydantic artifact schema.
Follow docs/AGENT_SPECIFICATIONS.md and FOLDER_STRUCTURE.md.
Wire nothing else yet.
Use LLMPort from ports; do not call other agents.
Include a contract test with a fake LLM.
```

### 18.2 Extend Presentation DSL

```
Propose DSL field changes against docs/PRESENTATION_DSL.md first (doc diff).
Then update validators and one golden fixture.
Bump version per versioning rules.
Do not change renderer to call AI.
```

### 18.3 Add API Endpoint

```
Add the endpoint exactly as specified in docs/API_SPECIFICATION.md section X.
Use success/error envelopes.
Enqueue jobs with 202 where required.
Add API tests with fake JobService.
Do not implement agent logic in the route.
```

### 18.4 Architecture Review Pass

```
Review the current diff against docs/FOLDER_STRUCTURE.md §17 What Should Never Happen
and SYSTEM_ARCHITECTURE.md isolation rules.
List blocking violations only.
```

---

## Closing Statement

ExplainX development is a disciplined loop:

```
Spec → Branch → Small layered change → Tests → Review → Main → Release
```

Cursor accelerates each step when constrained by the constitution, DSL, and folder rules.  
Features are done only when contracts, tests, isolation, and docs agree.

Build the presentation engine first in spirit — even when writing process docs — and protect the boundary that makes ExplainX maintainable:

**Agents plan. DSL records. Engines compile. Renderer paints. API controls. UI observes.**

---

*End of DEVELOPMENT_GUIDE.md*  
*ExplainX Engineering — Process Is Part of the Product.*
