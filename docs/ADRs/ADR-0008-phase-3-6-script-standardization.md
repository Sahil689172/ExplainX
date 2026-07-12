# ADR-0008: Phase 3.6 Educational Script Standardization (V1 2–3 min)

- Status: Accepted
- Date: 2026-07-12
- Updated: 2026-07-12 (deterministic metrics)

## Context

ExplainX V1 needs one consistent narration product: a high-quality educational
script for a **2–3 minute animated explainer**. Supporting many duration presets
(30s/60s/90s/3min/5min) fragmented generation quality and complicated validation.

LLM-generated numerical metadata (`estimated_words`, `estimated_duration_sec`)
was unreliable and could disagree with narration text, causing false validation
failures.

## Decision

### Single V1 format

| Metric | Generation target | MVP hard accept band |
|--------|-------------------|----------------------|
| Duration | ~150s | 60–300s (configurable) |
| Words | 320–420 | reporting only (not hard-gated) |
| Speaking rate | 140 WPM | used for all duration estimates |
| Estimated scenes | 18–25 | derived (~7.5s/scene) |

Per-section `target_words` remains **prompt guidance only** and does not fail
validation. MVP prioritizes pipeline completion over strict 2–3 minute accuracy
(see ADR-0011).

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

### Deterministic metrics (required)

The LLM / generator must **never** invent numerical metadata.

Generate content only:

- `title`, `summary`, `learning_objectives`
- `key_concepts`
- section `title`, `narration`, `concept_tags`

After generation, `ScriptMetricsCalculator` computes at **140 WPM**:

- per-section `estimated_words`, `estimated_duration_sec`
- `total_words` / `estimated_word_count`
- `total_duration_sec` / `estimated_duration_sec`
- `estimated_scene_count`
- `average_words_per_section`
- `reading_level`

`ScriptValidator` validates **calculated** values only (never LLM guesses).

### ScriptMetrics artifact

Persisted separately:

- `total_words`
- `total_duration_sec`
- `estimated_duration_sec` (same as total duration)
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

`PlaceholderContentGenerator` and `OllamaContentGenerator` both emit schema 1.1
and always run metrics enrichment after narration is ready.

If an Ollama draft is under 120s / 300 words, one expansion pass rewrites
narration (examples, analogies, explanations, transitions) toward ~180s
while keeping section structure.

Ollama prompt template version: `1.3` (no numerical fields; expansion pass for short drafts).

### Validation

Reject with `SCRIPT_VALIDATION_ERROR` when calculated metrics show:

- duration < 120s or > 180s  
- total words < 300 or > 450  
- empty section narration  

### Non-goals

- No API route changes  
- No Scene Planning implementation  
- No changes to unrelated downstream services (presentation plan, input, etc.)

## Consequences

- Clients must consume `teaching_sections` (not beats).  
- Old `artifacts/v1/script.json` is not auto-migrated; regenerate scripts.  
- Ollama prompts updated to template version `1.3`.  
- `script_metrics.json` includes `total_duration_sec`.

## Docs

- This ADR  
- Code: `backend/app/features/script/` (`metrics.py`, `validator.py`, `ollama/`)  
- Tests: `backend/tests/test_phase36_script_standardization.py`,
  `backend/tests/test_ollama_integration.py`
