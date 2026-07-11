# ExplainX

Offline-first **AI Presentation-to-Video Engine**. Upload educational content, receive an MP4 — internally ExplainX builds a Presentation DSL and renders it. Not a Sora/Veo-style generative video model.

> **Phase:** 1.1 — Project foundation only (no agents, AI, or rendering yet).

## Documentation (source of truth)

Read these before changing architecture or contracts:

| Document | Role |
|----------|------|
| [`docs/PROJECT_CONSTITUTION.md`](docs/PROJECT_CONSTITUTION.md) | Product & philosophy |
| [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) | Layers & isolation |
| [`docs/PRESENTATION_DSL.md`](docs/PRESENTATION_DSL.md) | Official IR language |
| [`docs/AGENT_SPECIFICATIONS.md`](docs/AGENT_SPECIFICATIONS.md) | Agents (future) |
| [`docs/FOLDER_STRUCTURE.md`](docs/FOLDER_STRUCTURE.md) | Repository layout |
| [`docs/API_SPECIFICATION.md`](docs/API_SPECIFICATION.md) | HTTP contracts |
| [`docs/DEVELOPMENT_GUIDE.md`](docs/DEVELOPMENT_GUIDE.md) | Workflow |
| [`docs/CODING_STANDARDS.md`](docs/CODING_STANDARDS.md) | Style & rules |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Build order |

## Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- **[uv](https://github.com/astral-sh/uv)** (preferred) for backend deps
- Windows 10/11 target: Intel i7-1255U class, 16GB RAM (see constitution)

## Quick start

### Windows (CMD) — without `uv`

`cp` and `uv` are not available in plain CMD by default. Use:

```bat
REM 1. Env file (from repo root)
copy .env.example .env

REM 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a **second** CMD window (repo root):

```bat
npm install
copy apps\web\.env.example apps\web\.env.local
npm run dev:web
```

Run tests (backend venv activated):

```bat
cd backend
.venv\Scripts\activate
pytest
```

### Optional: install `uv` (PowerShell)

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

Then from `backend/`:

```bat
uv sync --extra dev
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API health: http://127.0.0.1:8000/health  
- API v1 health: http://127.0.0.1:8000/api/v1/health  
- Web: http://127.0.0.1:3000  

## Repository layout (Phase 1.1)

```
ExplainX/
├── apps/web/          # Next.js frontend
├── backend/           # FastAPI backend
├── packages/          # Shared types/config
├── assets/            # Icon/illustration packs (placeholders)
├── data/              # Runtime (gitignored): projects, models, logs, DB
├── docs/              # Architecture specs
├── scripts/           # Operator helpers
├── tools/             # Dev tooling
└── tests/             # Cross-cutting tests (future)
```

## What is intentionally NOT in Phase 1.1

- Agents, parsers, LLM/TTS adapters  
- Presentation / animation / render engines  
- SQLAlchemy domain models & migrations content  
- Business services for projects/jobs  

## License

See `LICENSE` (to be finalized with the product release).
