# ADR-0007: Phase 3.5 Ollama Integration (OllamaContentGenerator)

- Status: Accepted
- Date: 2026-07-12

## Context

Phase 3 introduced `ContentIntelligenceService` with input-specific processors and
a swappable `ContentGenerator` protocol. Generation used
`PlaceholderContentGenerator` (deterministic, no LLM).

ExplainX must use the local Ollama runtime (Qwen2.5 3B by default) for educational
narration while keeping:

- public HTTP APIs unchanged
- `EducationalScript` schema unchanged
- processors / validator / store unchanged

## Decision

### Components

| Component | Role |
|-----------|------|
| `OllamaClient` | HTTP adapter for `POST /api/generate` |
| `PromptBuilder` | Source-specific system/user prompts (topic / script / PDF) |
| `ResponseParser` | Strict JSON parse → `EducationalScript`; retry once on failure |
| `OllamaContentGenerator` | Implements `ContentGenerator` |
| `create_content_generator(settings)` | Selects Ollama vs Placeholder |

Code lives under `backend/app/features/script/ollama/`.

### Architecture

```
ContentIntelligenceService
   └─ ContentProcessor (topic | script | pdf)
         └─ ContentGenerator
               ├─ OllamaContentGenerator   ← default (dev/prod)
               │     ├─ PromptBuilder + templates
               │     ├─ OllamaClient
               │     └─ ResponseParser (1 retry)
               └─ PlaceholderContentGenerator  ← tests / ollama_enabled=false
```

### Prompt policy

- **Topic** — expand concepts; respect target duration  
- **Custom script** — preserve intent; improve clarity only when needed  
- **PDF** — extracted text only (no file metadata); coherent narration; drop noise  

LLM must return **STRICT JSON** mapping to EducationalScript narration fields.
No markdown, explanations, or code fences.

Server overwrites identity fields (`project_id`, `content_id`, `source_type`,
`created_at`, `target_duration_sec`) after parse.

### Configuration

| Variable | Default | Notes |
|----------|---------|-------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | preferred unprefixed |
| `OLLAMA_MODEL` | `qwen2.5:3b` | preferred unprefixed; must be installed |
| `OLLAMA_TIMEOUT` | `600` | seconds (`EXPLAINX_OLLAMA_TIMEOUT_SEC` also accepted) |
| `OLLAMA_TEMPERATURE` | `0.2` | passed to Ollama `options.temperature` |
| `EXPLAINX_OLLAMA_ENABLED` | `true` | false → Placeholder |

Also accepted: `EXPLAINX_OLLAMA_BASE_URL`, `EXPLAINX_OLLAMA_MODEL`, `EXPLAINX_OLLAMA_TEMPERATURE`.

In `EXPLAINX_ENV=testing`, the factory forces Placeholder so CI never hits Ollama.

### Error codes

| Code | When |
|------|------|
| `OLLAMA_UNAVAILABLE` | connect / HTTP failure |
| `OLLAMA_TIMEOUT` | request timeout |
| `OLLAMA_EMPTY_RESPONSE` | blank model output |
| `OLLAMA_INVALID_JSON` | malformed JSON or schema mismatch (after one retry) |
| `MODEL_NOT_INSTALLED` | configured `OLLAMA_MODEL` not in `ollama list` / `/api/tags` |

### Non-goals

- No public API / route changes  
- No `EducationalScript` schema changes  
- No real Ollama calls in unit/CI tests (mocked client)  
- No OCR / knowledge-agent work  

## Consequences

- Dev/prod script generation requires a running Ollama with the configured model.
- Processors remain the single place for source-specific preparation; Ollama only
  turns prepared sections into `EducationalScript`.
- Swapping models is configuration-only; swapping generators stays DI-only.

## Docs

- This ADR  
- Code: `backend/app/features/script/ollama/`  
- Factory: `backend/app/features/script/factory.py`  
- Tests: `backend/tests/test_ollama_integration.py`
