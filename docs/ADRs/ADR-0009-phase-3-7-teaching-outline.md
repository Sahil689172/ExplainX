# ADR-0009: Phase 3.7 Teaching Outline Service

- Status: Accepted
- Date: 2026-07-12

## Context

EducationalScript generation jumped from `RawContent` straight to spoken narration.
Without an intermediate lesson plan, models often produced short or uneven scripts
and mixed planning with narration in one step.

## Decision

Introduce **TeachingOutline** between RawContent and EducationalScript:

```
RawContent → TeachingOutline → EducationalScript
```

### TeachingOutline

A lesson plan only — **no narration**.

Each outline has **8–12** `TeachingSection` entries with:

| Field | Purpose |
|-------|---------|
| `id` | Stable section id |
| `title` | Teaching beat title |
| `learning_objective` | What the learner should achieve |
| `target_words` | Allocated narration budget for later scripting |
| `key_concepts` | Concepts this beat must cover |

This outline `TeachingSection` is distinct from `script.schemas.TeachingSection`
(which carries spoken `narration`).

### Word budget

- Total budget = `round(140 WPM × duration_seconds / 60)`
- V1 canonical duration remains 150s → **350 words**
- Budget is distributed across sections; sum must match total within ±2 words
- Generators must not invent narration or trust LLM `target_words`; code applies allocation

### Components

| Piece | Role |
|-------|------|
| `OutlineGenerator` | Protocol |
| `PlaceholderOutlineGenerator` | Deterministic (tests / offline) |
| `OllamaOutlineGenerator` | LLM lesson-plan titles/objectives/concepts |
| `OutlineValidator` | Structure + budget checks |
| `TeachingOutlineService` | Orchestrate → validate → persist |
| `OutlineArtifactStore` | `artifacts/teaching_outline.json` |

### Pipeline

`ContentIntelligenceService.generate_script` now:

1. Generates and persists `TeachingOutline`
2. Generates `EducationalScript` (existing path)
3. Records `teaching_outline_id` in script metadata

### Non-goals

- No new HTTP APIs in Phase 3.7  
- No Scene Planning  
- EducationalScript still generates narration (outline consumption for section-level scripting is future work)

## Consequences

- Script generation always writes `teaching_outline.json` first  
- Outline package lives under `backend/app/features/outline/`  
- Tests: `backend/tests/test_teaching_outline.py`

## Docs

- This ADR  
- `docs/ROADMAP.md` Phase 3.7 note  
- Code: `backend/app/features/outline/`
