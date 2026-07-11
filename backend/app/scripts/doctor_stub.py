"""Minimal doctor stub for npm script wiring (Phase 1.1)."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.paths import ensure_runtime_directories


def main() -> None:
    settings = get_settings()
    ensure_runtime_directories(settings)
    print(f"ExplainX doctor stub OK — env={settings.env.value} data={settings.data_root_path}")


if __name__ == "__main__":
    main()
