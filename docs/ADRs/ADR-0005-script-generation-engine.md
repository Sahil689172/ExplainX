# ADR-0005: Script Generation Engine (EducationalScript)

- Status: Accepted
- Date: 2026-07-12

## Context

Topic, PDF, and custom script inputs are normalized to `RawContent` (Phase 2.1/2.2).
Downstream voice, scenes, and DSL need a single **EducationalScript** narration
contract. LLM/Ollama script writing comes later; the engine must still ship a
stable schema and swappable generator interface now.

## Decision

### Output: `EducationalScript`

Aligned with constitution `NarrationScript` beats, extended with sections,
title, duration, and preserved concepts.

Persisted at: `data/projects/{id}/artifacts/v1/script.json`

### Architecture

```
Topic / PDF / Custom Script
        ↓ (already unified)
     RawContent
        ↓
ScriptGenerationService
   ├─ optional PresentationPlan (title / concepts)
   ├─ ScriptGenerator (Protocol)
   │     └─ PlaceholderScriptGenerator  ← now
   │     └─ OllamaScriptGenerator       ← later
   ├─ ScriptValidator
   └─ ScriptArtifactStore
        ↓
  EducationalScript
```

### Source-specific placeholder behaviour

| Source | Behaviour |
|--------|-----------|
| `topic` | Teaching template framing around the topic text |
| `script` | Preserve author wording; whitespace normalize only |
| `pdf` | Spoken framing around extracted section text |

### HTTP

| Method | Route |
|--------|-------|
| `POST` | `/api/v1/projects/{id}/script` |
| `GET` | `/api/v1/projects/{id}/script` |

### Swapping in Ollama

Implement `ScriptGenerator.generate(raw, plan=...)` with an Ollama-backed class
and inject it into `ScriptGenerationService(generator=...)`. No changes required
to routes, validator, or store.

### Non-goals

- No Ollama / LLM calls in this change  
- No scene planning, voice, or DSL  
- No Cleaning/Knowledge agents  

## Consequences

- Scene Planner / Voice Agent should consume `EducationalScript` / beats.
- Consumers must tolerate `status=placeholder` until an LLM generator marks ready.

## Docs

- This ADR  
- Code: `backend/app/services/script_generation/`
