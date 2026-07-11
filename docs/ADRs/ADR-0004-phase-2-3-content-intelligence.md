# ADR-0004: Phase 2.3 Content Intelligence (PresentationPlan)

- Status: Accepted
- Date: 2026-07-12

## Context

Phase 2.1/2.2 produces a unified `RawContent` artifact. Before scripts, scenes, or
DSL compilation, ExplainX needs an educational **PresentationPlan** contract that
organizes content into teachable structure.

LLM-backed analysis is planned later. Phase 2.3 must still ship the **schema**,
**service architecture**, and **interfaces** so downstream modules can integrate.

## Decision

### Output: `PresentationPlan`

Fields (normative for v1.0 schema):

| Field | Purpose |
|-------|---------|
| `title` | Presentation title |
| `language` | Detected / hinted language code |
| `estimated_duration_sec` | Narration duration estimate |
| `key_concepts[]` | Core concepts |
| `learning_objectives[]` | Learner objectives |
| `visual_candidates[]` | Suggested visual opportunities |
| `teaching_sections[]` | Ordered teaching units |
| `status` | `placeholder` \| `draft` \| `ready` |

Persisted at: `data/projects/{id}/artifacts/v1/presentation_plan.json`

### Architecture

```
RawContent
   → ContentIntelligenceService
        → PresentationPlanner (Protocol)
             ├─ TitleDetector
             ├─ LanguageDetector
             ├─ DurationEstimator
             ├─ ConceptExtractor
             ├─ ObjectiveBuilder
             ├─ VisualCandidateDetector
             └─ SectionOrganizer
        → PresentationPlanValidator
        → PresentationPlanStore
```

Phase 2.3 ships `PlaceholderPresentationPlanner` — deterministic heuristics,
`status=placeholder`, `metadata.llm=false`.

### HTTP

| Method | Route |
|--------|-------|
| `POST` | `/api/v1/projects/{id}/presentation-plan` |
| `GET` | `/api/v1/projects/{id}/presentation-plan` |

### Non-goals

- No Ollama / LLM calls  
- No Cleaning / Knowledge / Script agents  
- No scene or DSL generation  

## Consequences

- Swapping in an LLM planner later only requires a new `PresentationPlanner`
  implementation; `ContentIntelligenceService` stays stable.
- Consumers must tolerate `status=placeholder` until a later phase marks plans ready.

## Docs

- This ADR  
- Code: `backend/app/services/content_intelligence/`
