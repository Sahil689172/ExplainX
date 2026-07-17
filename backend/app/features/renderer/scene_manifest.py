"""Load and validate ``scene_manifest.json``."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import ValidationAppError
from app.features.renderer.scene_schemas import SceneDefinition, SceneManifest

_MANIFEST_NAME = "scene_manifest.json"
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def candidate_manifest_paths(project_root: Path) -> tuple[Path, ...]:
    """Locations checked for a scene manifest (first existing wins).

    Canonical: ``artifacts/scene_manifest.json``.
    Also accepted: project-root ``scene_manifest.json`` (manual / CLI placement).
    """
    return (
        project_root / "artifacts" / _MANIFEST_NAME,
        project_root / _MANIFEST_NAME,
    )


def manifest_path(project_root: Path) -> Path:
    """Return the resolvable manifest path, preferring ``artifacts/`` when present."""
    for path in candidate_manifest_paths(project_root):
        if path.is_file():
            return path
    return candidate_manifest_paths(project_root)[0]


def manifest_exists(project_root: Path) -> bool:
    return any(path.is_file() for path in candidate_manifest_paths(project_root))


def load_scene_manifest(project_root: Path) -> SceneManifest:
    """Parse and validate ``scene_manifest.json`` (artifacts/ or project root)."""
    path = manifest_path(project_root)
    if not path.is_file():
        raise ValidationAppError(
            "Scene manifest not found.",
            code="SCENE_MANIFEST_NOT_FOUND",
            details={
                "searched": [str(p) for p in candidate_manifest_paths(project_root)],
            },
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        manifest = SceneManifest.model_validate(data)
    except (OSError, ValueError) as exc:
        raise ValidationAppError(
            "Invalid scene_manifest.json.",
            code="SCENE_MANIFEST_INVALID",
            details={"path": str(path), "error": str(exc)},
        ) from exc

    validate_manifest(manifest, project_root=project_root)
    print("[SceneManifest] Loaded", flush=True)
    print(f"Path : {path}", flush=True)
    print(f"Scenes : {len(manifest.scenes)}", flush=True)
    return manifest


def validate_manifest(manifest: SceneManifest, *, project_root: Path) -> None:
    """Verify scenes, images, durations, cameras, and ordering."""
    if not manifest.scenes:
        raise ValidationAppError(
            "Scene manifest must contain at least one scene.",
            code="SCENE_MANIFEST_INVALID",
            details={"field": "scenes"},
        )

    seen_ids: set[str] = set()
    total_duration = 0
    for index, scene in enumerate(manifest.scenes):
        if scene.scene_id in seen_ids:
            raise ValidationAppError(
                f"Duplicate scene_id: {scene.scene_id!r}.",
                code="SCENE_ORDER_INVALID",
                details={"scene_id": scene.scene_id, "index": index},
            )
        seen_ids.add(scene.scene_id)

        if scene.duration <= 0:
            raise ValidationAppError(
                f"Scene {scene.scene_id!r} duration must be > 0.",
                code="SCENE_DURATION_INVALID",
                details={"scene_id": scene.scene_id, "duration": scene.duration},
            )

        image_path = resolve_scene_image(project_root, scene.image)
        if not image_path.is_file():
            raise ValidationAppError(
                f"Scene image not found: {scene.image!r}.",
                code="SCENE_IMAGE_NOT_FOUND",
                details={"scene_id": scene.scene_id, "image": scene.image},
            )
        if image_path.suffix.lower() not in _IMAGE_SUFFIXES:
            raise ValidationAppError(
                f"Scene image must be PNG or JPG: {scene.image!r}.",
                code="SCENE_IMAGE_INVALID",
                details={"scene_id": scene.scene_id, "image": scene.image},
            )

        # Camera type validated by pydantic on SceneDefinition.
        total_duration += scene.duration

    if manifest.video_duration is not None and manifest.video_duration != total_duration:
        raise ValidationAppError(
            "video_duration does not match sum of scene durations.",
            code="SCENE_MANIFEST_INVALID",
            details={
                "video_duration": manifest.video_duration,
                "sum_scene_duration": total_duration,
            },
        )


def resolve_scene_image(project_root: Path, image_ref: str) -> Path:
    """Resolve a scene image path relative to the project root."""
    raw = (image_ref or "").strip().replace("\\", "/")
    if not raw:
        raise ValidationAppError(
            "Scene image path is empty.",
            code="SCENE_IMAGE_INVALID",
            details={"image": image_ref},
        )
    path = Path(raw)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (project_root / path).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValidationAppError(
            "Scene image path escapes project root.",
            code="SCENE_IMAGE_INVALID",
            details={"image": image_ref, "resolved": str(resolved)},
        ) from exc
    return resolved


def ordered_scenes(manifest: SceneManifest) -> list[SceneDefinition]:
    """Return scenes in manifest order (explicit ordering contract)."""
    return list(manifest.scenes)
