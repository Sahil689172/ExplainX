#!/usr/bin/env python3
"""ExplainX Developer CLI — test the backend without a frontend.

Usage (from the ``backend/`` directory, with the repo-root ``.venv`` active)::

    python run.py topic "Binary search for beginners"
    python run.py script path/to/script.txt
    python run.py pdf path/to/document.pdf

Optional flags::

    --project-id <uuid>   Reuse an existing project
    --title "My Title"    Override the project title

Exit codes::

    0  success
    1  usage / validation error
    2  application / service error
    3  unexpected error

This file is a thin entrypoint. Business logic lives in backend services;
orchestration is in ``app.cli.dev_cli``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure ``backend/`` is on sys.path when invoked as ``python run.py``.
_BACKEND_ROOT = Path(__file__).resolve().parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.cli.dev_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
