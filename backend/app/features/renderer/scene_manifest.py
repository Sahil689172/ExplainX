"""Load and validate ``scene_manifest.json``."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import ValidationAppError
from app.features.renderer.frame_renderer import read_image_resolution
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
    """Verify scenes, images, layers, durations, cameras, and ordering."""
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

        _validate_scene_visuals(scene, project_root=project_root)
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


def _validate_scene_visuals(scene: SceneDefinition, *, project_root: Path) -> None:
    """Validate background / legacy image and object assets for one scene."""
    bg_ref = scene.background_ref()
    bg_path = resolve_layer_image(project_root, bg_ref)
    if not bg_path.is_file():
        code = (
            "SCENE_BACKGROUND_NOT_FOUND"
            if scene.background is not None
            else "SCENE_IMAGE_NOT_FOUND"
        )
        raise ValidationAppError(
            f"Scene background/image not found: {bg_ref!r}.",
            code=code,
            details={"scene_id": scene.scene_id, "image": bg_ref},
        )
    if bg_path.suffix.lower() not in _IMAGE_SUFFIXES:
        raise ValidationAppError(
            f"Scene background must be PNG or JPG: {bg_ref!r}.",
            code="SCENE_IMAGE_INVALID",
            details={"scene_id": scene.scene_id, "image": bg_ref},
        )
    frame_width, frame_height = read_image_resolution(bg_path)

    seen_object_ids: set[str] = set()
    for obj in scene.objects:
        if obj.id in seen_object_ids:
            raise ValidationAppError(
                f"Duplicate object id: {obj.id!r}.",
                code="SCENE_OBJECT_DUPLICATE_ID",
                details={"scene_id": scene.scene_id, "object_id": obj.id},
            )
        seen_object_ids.add(obj.id)

        obj_path = resolve_layer_image(project_root, obj.image)
        if not obj_path.is_file():
            raise ValidationAppError(
                f"Object image not found: {obj.image!r}.",
                code="SCENE_OBJECT_IMAGE_NOT_FOUND",
                details={
                    "scene_id": scene.scene_id,
                    "object_id": obj.id,
                    "image": obj.image,
                },
            )
        if obj_path.suffix.lower() not in _IMAGE_SUFFIXES:
            raise ValidationAppError(
                f"Object image must be PNG or JPG: {obj.image!r}.",
                code="SCENE_OBJECT_IMAGE_INVALID",
                details={
                    "scene_id": scene.scene_id,
                    "object_id": obj.id,
                    "image": obj.image,
                },
            )
        if not (0 <= obj.x <= frame_width and 0 <= obj.y <= frame_height):
            raise ValidationAppError(
                f"Object {obj.id!r} center is outside the render area.",
                code="SCENE_OBJECT_CENTER_OUTSIDE_FRAME",
                details={
                    "scene_id": scene.scene_id,
                    "object_id": obj.id,
                    "center": [obj.x, obj.y],
                    "render_size": [frame_width, frame_height],
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


def resolve_layer_image(project_root: Path, image_ref: str) -> Path:
    """Resolve background/object images; try ``assets/`` fallbacks for bare names."""
    primary = resolve_scene_image(project_root, image_ref)
    if primary.is_file():
        return primary

    name = Path(str(image_ref).replace("\\", "/")).name
    if not name:
        return primary

    for rel in (f"assets/{name}", f"assets/images/{name}"):
        candidate = resolve_scene_image(project_root, rel)
        if candidate.is_file():
            return candidate
    return primary


def ordered_scenes(manifest: SceneManifest) -> list[SceneDefinition]:
    """Return scenes in manifest order (explicit ordering contract)."""
    return list(manifest.scenes)
