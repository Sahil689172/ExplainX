# ADR-0003: Phase 2.1 / 2.2 Input Intelligence

- Status: Accepted
- Date: 2026-07-12

## Context

Phase 1 delivered projects and the API foundation. Before cleaning, knowledge, or
script generation, ExplainX needs a deterministic **Input Intelligence** layer
that turns heterogeneous user inputs into one artifact contract.

Supported inputs for this phase:

1. **Topic** — short teaching subject string  
2. **PDF** — local text extraction (no OCR, no AI)  
3. **Custom Script** — user-authored narration/script text  

## Decision

### Components

| Component | Role |
|-----------|------|
| `InputService` | Validate project association, replace policy, persist sources + artifact, update project metadata |
| `InputRouter` | Dispatch by `source_type` to a processor |
| `TopicProcessor` | Topic → `RawContent` |
| `PDFProcessor` | PDF bytes → `RawContent` via `pypdf` |
| `ScriptProcessor` | Script text → `RawContent` (paragraph sections) |

### Unified output: `RawContent`

Every processor returns the same Pydantic schema (`app.models.artifacts.raw_content.RawContent`):

- `content_id`, `project_id`, `source_type`
- `text` (concatenated readable body)
- `sections[]` (`id`, `text`, `order`, optional `title`)
- `warnings[]`, `extraction_stats`, `source_path`, `source_hash`, `metadata`

Stored at: `data/projects/{project_id}/artifacts/v1/raw_content.json`

Source files at: `data/projects/{project_id}/source/`

### HTTP surface (under `/api/v1`)

| Method | Route | Input |
|--------|-------|-------|
| `PUT` | `/projects/{id}/source/topic` | Topic |
| `PUT` | `/projects/{id}/source/script` | Custom script |
| `POST` | `/projects/{id}/documents` | PDF upload |
| `GET` | `/projects/{id}/raw-content` | Fetch `RawContent` |

### Explicit non-goals (stop after 2.2)

- No LLM / Ollama  
- No Cleaning / Structure / Knowledge agents  
- No scene generation or rendering  
- No DOCX OCR / scanned-PDF OCR  

## Consequences

- Downstream phases must consume `RawContent` only (never raw upload formats).
- `source_type=script` is added to the domain enum for custom scripts.
- PDF quality depends on embedded text; empty extracts fail with `PARSER_EMPTY_CONTENT`.

## Docs

- This ADR  
- Implementation under `backend/app/services/input/`
