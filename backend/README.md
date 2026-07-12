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
