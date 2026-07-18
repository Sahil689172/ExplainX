"""Style System — loads JSON style profiles (HOW, never WHAT)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from asset_intelligence.schemas.style import StyleProfile

_DEFAULT_STYLES_DIR = Path(__file__).resolve().parent / "styles"


class StyleSystem:
    """Resolves style profiles from disk. Prompts are never hardcoded in Python."""

    def __init__(self, styles_dir: Path | None = None) -> None:
        self.styles_dir = Path(styles_dir) if styles_dir else _DEFAULT_STYLES_DIR
        self._cache: dict[str, StyleProfile] = {}
        self.reload()

    def reload(self) -> None:
        self._cache.clear()
        if not self.styles_dir.is_dir():
            return
        for path in sorted(self.styles_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            profile = StyleProfile(
                style_id=str(data["style_id"]),
                display_name=str(data.get("display_name", data["style_id"])),
                positive_prompt=str(data.get("positive_prompt", "")),
                negative_prompt=str(data.get("negative_prompt", "")),
                color_palette=list(data.get("color_palette", [])),
                line_weight=str(data.get("line_weight", "medium")),
                lighting=str(data.get("lighting", "flat")),
                background_rules=str(
                    data.get("background_rules", "plain solid or transparent")
                ),
                renderer_preferences=dict(data.get("renderer_preferences", {})),
                lora_mapping=dict(data.get("lora_mapping", {})),
                controlnet_mapping=dict(data.get("controlnet_mapping", {})),
                metadata=dict(data.get("metadata", {})),
            )
            self._cache[profile.style_id] = profile

    def get(self, style_id: str) -> StyleProfile:
        if style_id not in self._cache:
            raise KeyError(f"Unknown style_id: {style_id!r}")
        return self._cache[style_id]

    def list_styles(self) -> Sequence[StyleProfile]:
        return list(self._cache.values())
