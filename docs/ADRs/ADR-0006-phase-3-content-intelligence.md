# ADR-0006: Phase 3 Content Intelligence (EducationalScript)

- Status: Accepted
- Date: 2026-07-12

## Context

ExplainX accepts three learner inputs — **topic**, **custom script**, and **PDF**.
Downstream voice, scenes, and DSL need **one** narration contract:
`EducationalScript`.

Phase 2.1/2.2 already unifies inputs as `RawContent`. Phase 2.3 builds an
optional `PresentationPlan`. Phase 3 turns any supported input into a single
`EducationalScript`, with input-specific processors and a swappable generator
so Ollama can replace the placeholder later without rewriting the pipeline.

## Decision

### Output

`EducationalScript` (schema `1.0`) persisted at:

`data/projects/{id}/artifacts/v1/script.json`

Includes `target_duration_sec` and TTS-friendly `beats[]` / `sections[]`.

### Supported target durations

| Label | Seconds |
|-------|---------|
| `30s` | 30 |
| `60s` | 60 (default) |
| `90s` | 90 |
| `3min` | 180 |
| `5min` | 300 |

### Architecture

```
Topic / Custom Script / PDF
        ↓ (Input Intelligence)
     RawContent
        ↓
ContentIntelligenceService
   ├─ input validation (topic/script length; PDF ≤25MB, ≤30 pages;
   │     reject encrypted / image-only PDFs in v1)
   ├─ optional PresentationPlan (title / concepts)
   ├─ ContentProcessor by source_type
   │     ├─ TopicContentProcessor   (placeholder research + narration)
   │     ├─ ScriptContentProcessor  (preserve intent, improve readability)
   │     └─ PDFContentProcessor     (PyMuPDF4LLM extract → narration)
   ├─ ContentGenerator
   │     ├─ PlaceholderContentGenerator  ← now
   │     └─ OllamaContentGenerator       ← later
   ├─ ScriptValidator
   └─ ScriptArtifactStore
        ↓
  EducationalScript
```

### HTTP

| Method | Route | Body |
|--------|-------|------|
| `POST` | `/api/v1/projects/{id}/script` | optional `{ "target_duration": "60s" }` or `{ "target_duration_sec": 60 }` |
| `GET` | `/api/v1/projects/{id}/script` | — |

Routes and status codes remain the same as the earlier Script Generation Engine;
Phase 3 adds optional duration targeting and processor-based generation.

### Validation (v1)

| Input | Rule |
|-------|------|
| Topic | length 3–500 characters |
| Script | length 10–200_000 characters |
| PDF | max 25 MB, max 30 pages |
| PDF | reject encrypted PDFs |
| PDF | reject image-only / empty extract (OCR disabled in v1) |

PDF extraction uses **PyMuPDF4LLM** (`pymupdf4llm.to_markdown`, `use_ocr=False`).

### Swapping in Ollama

Implement `ContentGenerator.generate(...)` as `OllamaContentGenerator` and inject:

```python
ContentIntelligenceService(session, settings, generator=OllamaContentGenerator(...))
```

No changes required to processors, routes, validator, or store.

### Naming note

Phase 2.3’s plan builder is now `PresentationPlanService` (HTTP paths for
`/presentation-plan` unchanged). The name `ContentIntelligenceService` refers
to Phase 3 EducationalScript generation under `app.features.script`.

### Non-goals

- No Ollama / LLM calls in this phase  
- No scene planning, voice, or DSL  
- No OCR for scanned PDFs  
- No Knowledge Agent plane artifacts  

## Consequences

- Scene Planner / Voice Agent consume `EducationalScript` / beats.
- Consumers must tolerate `status=placeholder` until an LLM generator marks ready.
- Input Intelligence PDF limits align with Phase 3 (25 MB / 30 pages).

## Docs

- This ADR  
- Code: `backend/app/features/script/`  
- PDF helpers: `backend/app/features/input/pdf_extract.py`
