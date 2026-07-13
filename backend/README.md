# ExplainX Backend

FastAPI control plane for the offline presentation-to-video engine.

## Run API

From the repository root (``.venv`` lives at the repo root, not under ``backend/``):

```bat
cd /d c:\Users\hp\ExplainX
.venv\Scripts\activate
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Developer CLI (no frontend)

Thin wrapper around existing services. Generates a V1 EducationalScript
(2–3 minute explainer) and writes artifacts under ``data/projects/<id>/artifacts/``.

Word counts and durations are calculated deterministically at **140 WPM**
after narration is generated (the LLM never supplies numerical metadata).

Phase 3.7+ writes a lesson-plan ``artifacts/teaching_outline.json``.
On the live path the outline is **derived deterministically** from SceneBuilder
scenes (no LLM outline call).

Continuous narration is generated in **one** Ollama call (topic/PDF), then
``SceneBuilder`` splits it into teaching sections. Custom scripts are
normalized only (no rewrite).

Phase 3.9 runs Quality Assurance. Repair regenerates narration (not scenes)
when duration is too short.

### Prerequisites

1. Install Ollama
2. Pull the model named in ``OLLAMA_MODEL`` (default ``qwen2.5:3b``), e.g. ``ollama pull qwen2.5:3b``
3. Start Ollama with ``ollama serve``
4. Configure Ollama in the repo-root ``.env`` (see ``.env.example``)

### Switching Models

Set ``OLLAMA_MODEL`` in ``.env`` — no code changes:

```env
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_MODEL=llama3:latest
OLLAMA_MODEL=gemma3:4b
```

Also available: ``OLLAMA_BASE_URL``, ``OLLAMA_TIMEOUT`` (seconds), ``OLLAMA_TEMPERATURE``.

The CLI checks that Ollama is reachable and the configured model exists
before script generation.

```bat
cd /d c:\Users\hp\ExplainX\backend

python run.py topic "Binary search for beginners"
python run.py script path\to\script.txt
python run.py pdf path\to\document.pdf
```

Optional flags (after the command):

```bat
python run.py topic "Graphs" --title "Intro to Graphs"
python run.py topic "Trees" --project-id <existing-uuid>
```

Exit codes: ``0`` success · ``1`` validation/usage · ``2`` app/service error · ``3`` unexpected.

Artifacts written:

- ``educational_script.json``
- ``educational_script.md``
- ``script_metrics.json``
- ``v1/raw_content.json``

## Tests

```bat
cd /d c:\Users\hp\ExplainX\backend
..\.venv\Scripts\python.exe -m pytest -q
```
