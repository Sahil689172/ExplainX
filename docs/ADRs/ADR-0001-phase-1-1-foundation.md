"""
# ADR-0001: Phase 1.1 foundation stack choices

- Status: Accepted
- Date: 2026-07-11

## Context

ExplainX needs a production-quality skeleton before agents, DSL engines, or rendering.

## Decision

- Backend: FastAPI + Pydantic Settings + structured logging; SQLAlchemy/Alembic present but **no domain models** yet.
- Frontend: Next.js App Router + TypeScript + Tailwind + Framer Motion + Zustand.
- Runtime data under `data/` (gitignored); source under `apps/`, `backend/`, `packages/`, `assets/`, `docs/`.
- Dependency management: `uv` for Python, npm workspaces for JS.

## Consequences

- Health/doctor endpoints exist for local verification.
- Later phases plug into reserved packages (`agents`, `engines`, `ports`, `repositories`) without restructuring.

## Docs updated

- README.md
- This ADR
"""
