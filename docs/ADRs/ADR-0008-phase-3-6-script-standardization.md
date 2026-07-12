# ADR-0008: Phase 3.6 Educational Script Standardization (V1 2–3 min)

- Status: Accepted
- Date: 2026-07-12

## Context

ExplainX V1 needs one consistent narration product: a high-quality educational
script for a **2–3 minute animated explainer**. Supporting many duration presets
(30s/60s/90s/3min/5min) fragmented generation quality and complicated validation.

## Decision

### Single V1 format

| Metric | Target | Hard accept band |
|--------|--------|------------------|
| Duration | ~150s | 120–180s |
| Words | 320–420 | 300–450 |
| Speaking rate | 135–145 WPM | ~140 WPM used for estimates |
| Estimated scenes | 18–25 | derived (~7.5s/scene) |

Multiple duration presets are **retired**. API body fields
`target_duration` / `target_duration_sec` remain for compatibility but are ignored.

### EducationalScript schema (`1.1`)

Required educational fields:

- `title`, `language`
- `target_duration_sec`, `estimated_duration_sec`
- `estimated_word_count`, `estimated_scene_count`
- `summary`
- `key_concepts[]`
- `learning_objectives[]`
- `teaching_sections[]` with `id`, `title`, `narration`,
  `estimated_duration_sec`, `estimated_words`, `concept_tags`

Identity/system fields (`script_id`, `project_id`, `content_id`, `source_type`,
`status`, `warnings`, `metadata`, `created_at`) remain.

Beats / legacy `sections` were removed from the public schema in favor of
`teaching_sections`.

### ScriptMetrics

Computed and persisted separately:

- `total_words`
- `estimated_duration_sec`
- `estimated_scene_count`
- `average_words_per_section`
- `reading_level`
- `language`

### Persistence

Under each project:

```
artifacts/educational_script.json
artifacts/educational_script.md
artifacts/script_metrics.json
```

### Generators

- **Topic** — complete 2–3 minute explanation  
- **Custom script** — preserve meaning; expand only if needed for duration  
- **PDF** — coherent narration from extracted text; ignore references,
  bibliography, acknowledgements, indexes, appendices, repeated headers/footers  

`PlaceholderContentGenerator` and `OllamaContentGenerator` both emit schema 1.1.

### Validation

Reject with `SCRIPT_VALIDATION_ERROR` when:

- estimated duration < 120s or > 180s  
- total words < 300 or > 450  

### Non-goals

- No API route changes  
- No Scene Planning implementation  
- No changes to unrelated downstream services (presentation plan, input, etc.)

## Consequences

- Clients must consume `teaching_sections` (not beats).  
- Old `artifacts/v1/script.json` is not auto-migrated; regenerate scripts.  
- Ollama prompts updated to template version `1.1`.

## Docs

- This ADR  
- Code: `backend/app/features/script/`  
- Tests: `backend/tests/test_phase36_script_standardization.py`
