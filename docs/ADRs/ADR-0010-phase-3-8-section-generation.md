# ADR-0010: Phase 3.8 Section Generation Engine

- Status: Accepted
- Date: 2026-07-12

## Context

Phase 3.7 introduced `TeachingOutline` (lesson plan, no narration). Generating the
entire EducationalScript in one LLM call still produced uneven length and weak
section continuity.

## Decision

Generate narration **one outline section at a time**, then merge:

```
RawContent
  → TeachingOutline
  → SectionGenerationService
       ├─ SectionGenerator (per TeachingSection)
       ├─ SectionValidator
       ├─ persist artifacts/section_outputs/section_XX.json
       └─ SectionMerger
  → EducationalScript
```

### SectionGenerator inputs

For each outline section the generator receives:

- section title
- learning objective
- target_words
- key concepts
- previous section summary
- next section title

It returns **narration only for that section** (plus a short summary for the next call).

### Components

| Piece | Role |
|-------|------|
| `SectionGenerator` | Protocol |
| `PlaceholderSectionGenerator` | Deterministic per-section narration |
| `OllamaSectionGenerator` | One Ollama `/api/generate` call per section |
| `SectionValidator` | Speakable text + word-count band vs `target_words` |
| `SectionMerger` | Assemble EducationalScript (schema unchanged) |
| `SectionGenerationService` | Orchestrate loop + persistence |
| `SectionOutputStore` | `artifacts/section_outputs/section_01.json` … |

### EducationalScript

Schema remains **1.1**. Metrics still come from `ScriptMetricsCalculator` after merge.

### ContentIntelligenceService

`generate_script` now:

1. Builds / persists TeachingOutline (3.7)
2. Runs SectionGenerationService (3.8)
3. Validates + persists `educational_script.json` (+ metrics/markdown)

HTTP APIs are unchanged.

### Non-goals

- No Scene Planning  
- No full-script single LLM call  
- No EducationalScript schema changes  

## Consequences

- Script generation performs N section LLM calls (N = 8–12) when Ollama is enabled  
- Artifacts include both `teaching_outline.json` and `section_outputs/`  
- Tests: `backend/tests/test_section_generation.py`

## Docs

- This ADR  
- `docs/ROADMAP.md` Phase 3.8  
- Code: `backend/app/features/section_generation/`
