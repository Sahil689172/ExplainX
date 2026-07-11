# ExplainX Backend

FastAPI control plane for the offline presentation-to-video engine.

## Phase 1.1 scope

- Application entrypoint & lifespan  
- Settings (development / testing / production)  
- Structured logging (console + file)  
- Health endpoint  
- Global exception handling & API envelopes  
- DI composition root stub  
- SQLAlchemy/Alembic **scaffolding only** (no domain models yet)  

## Run

```bash
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Tests

```bash
uv sync --extra dev
uv run pytest
```
