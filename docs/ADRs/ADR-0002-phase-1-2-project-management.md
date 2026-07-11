# ADR-0002: Phase 1.2 Project Management

- Status: Accepted
- Date: 2026-07-11

## Context

Phase 1.1 provided the app skeleton. ExplainX needs a project lifecycle module before document intelligence.

## Decision

- Persist projects in SQLite (`projects`, `project_settings`, seeded `themes`/`languages`).
- Mirror metadata to `data/projects/{id}/project.json`.
- Create per-project folders: source, assets, scenes, audio, subtitles, generated, export, logs, temp, artifacts.
- Expose CRUD + rename/save/archive/duplicate/export/import via `/api/v1/projects`.
- Enforce unique active titles in the service layer (soft-delete friendly).
- No agents, parsers, renderers, or DSL compilation.

## Consequences

- Future agents receive `project_id` and write artifacts under the project tree.
- Rendering/export later reuses `export/` and project settings.

## Docs updated

- This ADR
- README (implicit via Phase 1.2 implementation)
