"""Export generated assets into a project (or demo) directory."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.services.asset_generation.models import (
    AssetBundle,
    AssetFormat,
    GeneratedAsset,
    GenerationResult,
)


class AssetExporter:
    """Copy SVG / PNG / JSON metadata into an export folder."""

    def export(
        self,
        result: GenerationResult,
        export_dir: str | Path,
        *,
        scene_subdir: bool = True,
    ) -> AssetBundle:
        root = Path(export_dir)
        target = root / result.scene_id if scene_subdir else root
        target.mkdir(parents=True, exist_ok=True)

        exported: list[GeneratedAsset] = []
        layer_paths: dict[str, str] = {}
        for asset in result.assets:
            src = Path(asset.path)
            if not src.is_file():
                continue
            dest = target / src.name
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
            exported.append(asset.model_copy(update={"path": str(dest)}))
            layer_paths[asset.format.value] = str(dest)

        meta_path = target / "metadata.json"
        payload = {
            "scene_id": result.scene_id,
            "generator": result.generator.value,
            "status": result.status.value,
            "cache_hit": result.cache_hit,
            "content_hash": result.content_hash,
            "generation_time_sec": result.generation_time_sec,
            "detail": result.detail,
            "metadata": result.metadata.model_dump(mode="json") if result.metadata else None,
            "assets": [a.model_dump(mode="json") for a in exported],
        }
        meta_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        layer_paths[AssetFormat.JSON.value] = str(meta_path)

        primary = result.primary_path
        if primary:
            name = Path(primary).name
            candidate = target / name
            if candidate.is_file():
                primary = str(candidate)

        return AssetBundle(
            scene_id=result.scene_id,
            result=result.model_copy(
                update={"assets": exported, "primary_path": primary}
            ),
            composed_path=primary,
            layer_paths=layer_paths,
            export_dir=str(target),
        )
