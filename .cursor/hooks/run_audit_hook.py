"""Hook: heartbeat on edits; run backend audit when TRIGGER_AUDIT is touched."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(r"c:\Users\hp\ExplainX\backend")
HEARTBEAT = BACKEND / "_hook_heartbeat.txt"
MARKER = BACKEND / "_hook_fired.txt"
AUDIT_PY = BACKEND / "_run_audit.py"
PYTHON = Path(r"c:\Users\hp\ExplainX\.venv\Scripts\python.exe")


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}

    path = str(data.get("file_path") or data.get("path") or "")
    event = str(data.get("hook_event_name") or "")
    HEARTBEAT.write_text(
        f"{datetime.now(timezone.utc).isoformat()} event={event} path={path}\n",
        encoding="utf-8",
    )

    normalized = path.replace("\\", "/").lower()
    if "trigger_audit" not in normalized:
        return 0

    MARKER.write_text(f"hook_fired path={path}\n", encoding="utf-8")
    proc = subprocess.run(
        [str(PYTHON), str(AUDIT_PY)],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )
    MARKER.write_text(
        f"hook_done exit={proc.returncode}\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
