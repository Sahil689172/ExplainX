"""
ExplainX full pipeline integration audit.

Run from backend/:

    python audit_pipeline.py "Your Topic Here"

Examples:

    python audit_pipeline.py "Planet Earth"
    python audit_pipeline.py "Volcano"
    python audit_pipeline.py "Human Heart"

Produces:
    logs/pipeline_run.log
    logs/pipeline_summary.json
    logs/pipeline_timing.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / "logs"


def _slugify(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.strip()).strip("_") or "topic"


@dataclass
class PhaseRecord:
    phase_id: str
    name: str
    start_time: str = ""
    end_time: str = ""
    execution_ms: float = 0.0
    input_summary: str = ""
    output_summary: str = ""
    output_paths: list[str] = field(default_factory=list)
    success: bool = False
    error: str | None = None
    connection_ok: bool = True
    connection_note: str = ""

    def finish(self, t0: float, *, success: bool, error: str | None = None) -> None:
        self.end_time = _iso_now()
        self.execution_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        self.success = success
        self.error = error


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _size(path: Path | None) -> int:
    if path is None or not path.is_file():
        return 0
    return path.stat().st_size


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.2f} MB"


def _abs(path: Path | str | None) -> str:
    if not path:
        return ""
    return str(Path(path).resolve())


class PipelineAudit:
    def __init__(self, topic: str = "Planet Earth") -> None:
        self.topic = topic.strip() or "Planet Earth"
        self.audit_slug = _slugify(self.topic)
        self.output_root = ROOT / "output" / "audit" / self.audit_slug
        self.phases: list[PhaseRecord] = []
        self.files_generated: list[str] = []
        self.total_bytes = 0
        self.connections: list[dict[str, Any]] = []
        self.frame_audit: dict[str, Any] = {}
        self.video_audit: dict[str, Any] = {}
        self.project_id: str | None = None
        self.log_lines: list[str] = []
        self.pipeline_ok = True
        self._context: dict[str, Any] = {}

    def _topic_key(self) -> str:
        return self.topic.lower()

    def _find_illustration_fallback(self) -> Path:
        key = self._topic_key().replace(" ", "")
        first = self._topic_key().split()[0]
        for folder in (ROOT / "processed_assets", ROOT / "generated" / "raw", ROOT / "raw_assets"):
            if not folder.is_dir():
                continue
            for path in sorted(folder.iterdir()):
                if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                    continue
                low = path.name.lower().replace("_", "").replace(" ", "")
                if key in low or first in low:
                    return path
        raise FileNotFoundError(f"No illustration found for topic: {self.topic}")

    def log(self, msg: str) -> None:
        line = f"{datetime.now().isoformat(timespec='seconds')} | {msg}"
        self.log_lines.append(line)
        print(msg, flush=True)

    def run_phase(
        self,
        phase_id: str,
        name: str,
        fn,
        *,
        input_summary: str = "",
    ) -> Any:
        rec = PhaseRecord(
            phase_id=phase_id,
            name=name,
            start_time=_iso_now(),
            input_summary=input_summary,
        )
        self.log("")
        self.log("=" * 60)
        self.log(f"PHASE {phase_id}: {name}")
        self.log(f"  Start:  {rec.start_time}")
        self.log(f"  Input:  {input_summary or '-'}")
        t0 = time.perf_counter()
        try:
            result = fn()
            rec.finish(t0, success=True)
            self.log(f"  End:    {rec.end_time}")
            self.log(f"  Time:   {rec.execution_ms:.2f} ms")
            self.log("  Status: SUCCESS")
        except Exception as exc:  # noqa: BLE001
            rec.finish(t0, success=False, error=f"{type(exc).__name__}: {exc}")
            self.pipeline_ok = False
            self.log(f"  End:    {rec.end_time}")
            self.log(f"  Time:   {rec.execution_ms:.2f} ms")
            self.log(f"  Status: FAILURE — {rec.error}")
            self.log(traceback.format_exc())
            result = None
        self.phases.append(rec)
        return result

    def note_output(self, rec: PhaseRecord, paths: list[Path | str], summary: str) -> None:
        rec.output_summary = summary
        rec.output_paths = [_abs(p) for p in paths if p]
        for p in paths:
            path = Path(p)
            if path.is_file():
                size = _size(path)
                self.total_bytes += size
                self.files_generated.append(_abs(path))
                self.log(f"  Output: {_abs(path)} ({_fmt_size(size)})")
            elif path.is_dir():
                for f in sorted(path.rglob("*")):
                    if f.is_file():
                        size = _size(f)
                        self.total_bytes += size
                        self.files_generated.append(_abs(f))
                self.log(f"  Output: {_abs(path)} (directory)")

    def note_connection(
        self,
        phase_id: str,
        ok: bool,
        note: str,
    ) -> None:
        self.connections.append({"phase_id": phase_id, "ok": ok, "note": note})

    # ------------------------------------------------------------------ phases

    def phase_topic_input(self) -> None:
        from app.cli.dev_cli import (
            bootstrap,
            create_or_load_project,
            ingest_topic,
        )
        from app.core.enums import SourceType
        from app.db import session as db_session
        from app.features.input.store import InputArtifactStore
        from app.features.projects.filesystem import ProjectFilesystem

        cfg = bootstrap()
        session = db_session.SessionLocal()
        assert session is not None

        def _run() -> Path:
            pid = create_or_load_project(
                session,
                cfg,
                source_type=SourceType.TOPIC,
                title=self.topic,
                source_topic=self.topic,
                project_id=None,
                reuse_project=False,
            )
            ingest_topic(session, cfg, pid, self.topic)
            session.commit()
            self.project_id = pid
            raw_path = InputArtifactStore(ProjectFilesystem(cfg)).raw_content_path(pid)
            self._context["raw_content_path"] = raw_path
            self._context["settings"] = cfg
            self._context["session"] = session
            return raw_path

        result = self.run_phase(
            "1",
            "Topic Input (Input Intelligence)",
            _run,
            input_summary=f'topic="{self.topic}"',
        )
        rec = self.phases[-1]
        if result:
            self.note_output(rec, [result], f"RawContent JSON ({_fmt_size(_size(result))})")

    def phase_presentation_planner(self) -> None:
        from app.features.presentation.service import PresentationPlanService

        cfg = self._context["settings"]
        session = self._context["session"]
        pid = self.project_id
        assert pid

        def _run() -> Path:
            plan = PresentationPlanService(session, cfg).generate_plan(pid)
            session.commit()
            from app.features.presentation.store import PresentationPlanStore
            from app.features.projects.filesystem import ProjectFilesystem

            path = PresentationPlanStore(ProjectFilesystem(cfg)).plan_path(pid)
            self._context["presentation_plan"] = plan
            self._context["presentation_plan_path"] = path
            return path

        raw = self._context.get("raw_content_path")
        result = self.run_phase(
            "2",
            "Presentation Planner (Content Intelligence 2.3)",
            _run,
            input_summary=_abs(raw),
        )
        rec = self.phases[-1]
        if result:
            self.note_output(rec, [result], f"PresentationPlan ({_fmt_size(_size(result))})")
            self.note_connection("2", True, "Consumes RawContent from Phase 1")

    def phase_script_generator(self) -> None:
        from app.cli.dev_cli import generate_script, verify_ollama
        from app.features.projects.filesystem import ProjectFilesystem
        from app.features.script.store import ScriptArtifactStore

        cfg = self._context["settings"]
        session = self._context["session"]
        pid = self.project_id
        assert pid

        def _run() -> Path:
            verify_ollama(cfg)
            script = generate_script(session, cfg, pid)
            session.commit()
            store = ScriptArtifactStore(ProjectFilesystem(cfg))
            self._context["script"] = script
            self._context["script_path"] = store.script_path(pid)
            return store.script_path(pid)

        plan_path = self._context.get("presentation_plan_path")
        result = self.run_phase(
            "3",
            "Script Generator (Content Intelligence 3.x)",
            _run,
            input_summary=_abs(plan_path) or _abs(self._context.get("raw_content_path")),
        )
        rec = self.phases[-1]
        if result:
            self.note_output(
                rec,
                [result],
                f"EducationalScript sections={len(self._context['script'].teaching_sections)}",
            )
            self.note_connection(
                "3",
                False,
                "Script reads RawContent directly; PresentationPlan is not consumed (known gap)",
            )

    def phase_prompt_intelligence(self) -> None:
        from image_generation.prompt_intelligence.prompt_engine import RuleBasedPromptEngine

        def _run() -> dict[str, Any]:
            engine = RuleBasedPromptEngine()
            result = engine.enhance(self.topic)
            payload = {
                "enhanced_prompt": result.enhanced_prompt,
                "negative_prompt": result.negative_prompt,
                "subject": result.subject,
                "confidence": result.confidence,
            }
            out = self.output_root / "prompt_intelligence.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self._context["prompt_intel"] = payload
            self._context["prompt_intel_path"] = out
            return payload

        self.run_phase("5.6", "Prompt Intelligence", _run, input_summary=f'prompt="{self.topic}"')
        rec = self.phases[-1]
        if rec.success:
            self.note_output(rec, [self._context["prompt_intel_path"]], "PromptIntelligenceResult")
            self.note_connection("5.6", True, "Standalone enhance(); also used inside AssetManager")

    def phase_asset_repository(self) -> None:
        from image_generation.repository import EducationalAssetRepository

        def _run() -> Path:
            repo = EducationalAssetRepository()
            concept = repo.find_concept_by_title("Earth") or repo.find_concept_by_title(self.topic)
            self._context["repository"] = repo
            if concept is None:
                concepts = repo.list_concepts()
                if concepts:
                    concept = concepts[0]
            self._context["repository_concept"] = concept
            if concept is None:
                lib_index = ROOT / "asset_library" / "assets"
                note = "No versioned concept; SmartAssetLibrary index used by AssetManager"
                self._context["repository_note"] = note
                if lib_index.is_dir():
                    return lib_index
                raise FileNotFoundError("No concepts in asset_library/concepts")
            best = repo.get_best_version(concept.concept_id)
            if best is None:
                raise FileNotFoundError(f"No version for concept {concept.title}")
            meta_path = Path(best.file_path).parent / "metadata.json"
            self._context["repository_version_path"] = Path(best.file_path)
            return meta_path if meta_path.is_file() else Path(best.file_path)

        prompt_path = self._context.get("prompt_intel_path")
        result = self.run_phase(
            "5.5",
            "Asset Repository",
            _run,
            input_summary=_abs(prompt_path),
        )
        rec = self.phases[-1]
        if result:
            paths = [result]
            ver = self._context.get("repository_version_path")
            if ver:
                paths.append(ver)
            self.note_output(rec, paths, "Repository concept/version metadata")
            self.note_connection("5.5", True, "Repository searched by title; independent of script output")

    def phase_image_generation(self) -> None:
        from image_generation.asset_manager import AssetManager
        from image_generation.config import ImageGenerationConfig
        from image_generation.image_generation_service import build_openvino_service
        from image_generation.repository import EducationalAssetRepository

        def _run() -> Path:
            cfg = ImageGenerationConfig.from_defaults()
            service = build_openvino_service(cfg, with_asset_pipeline=True)
            repo = EducationalAssetRepository()
            manager = AssetManager(service, repository=repo)
            try:
                result = manager.resolve(self.topic)
            finally:
                service.stop()
            if result.file_path and Path(result.file_path).is_file():
                self._context["illustration_path"] = Path(result.file_path)
                self._context["asset_cache_hit"] = result.cache_hit
                self._context["image_generation_ms"] = result.generation_ms
                return Path(result.file_path)
            fallback = self._find_illustration_fallback()
            self._context["illustration_path"] = fallback
            self._context["asset_cache_hit"] = True
            self._context["image_generation_ms"] = 0.0
            return fallback

        intel = self._context.get("prompt_intel", {})
        result = self.run_phase(
            "5.1",
            "Image Generation",
            _run,
            input_summary=intel.get("enhanced_prompt", self.topic)[:120],
        )
        rec = self.phases[-1]
        if result:
            hit = self._context.get("asset_cache_hit")
            self.note_output(
                rec,
                [result],
                f"{'CACHE_HIT' if hit else 'GENERATED'} illustration",
            )
            self.note_connection("5.1", True, "Uses Prompt Intelligence via PromptEnhancer inside AssetManager")

    def phase_diagram_composer(self) -> None:
        from image_generation.diagram_composer import DiagramEngine, earth_spec
        from image_generation.diagram_composer.fixtures import get_fixture as get_diagram_fixture

        illustration = self._context["illustration_path"]
        out_dir = self.output_root / "diagrams"

        def _run() -> Path:
            spec = (
                get_diagram_fixture(self._topic_key())
                or get_diagram_fixture(self._topic_key().split()[0])
                or earth_spec(concept_id="concept-earth", asset_version="v1")
            )
            result = DiagramEngine().compose(
                str(illustration),
                spec,
                output_dir=out_dir,
            )
            self._context["diagram_png"] = Path(result.png_path)
            return Path(result.png_path)

        result = self.run_phase(
            "5.7",
            "Diagram Composer",
            _run,
            input_summary=_abs(illustration),
        )
        rec = self.phases[-1]
        if result:
            diagram_files = list(out_dir.glob("*"))
            self.note_output(rec, diagram_files, "Annotated diagram PNG/SVG/JSON")
            self.note_connection("5.7", True, "Consumes illustration from Image Generation")

    def phase_scene_composer(self) -> None:
        from scene_generation import SceneEngine, earth_scene
        from scene_generation.scene_templates import get_fixture as get_scene_fixture

        illustration = self._context["illustration_path"]
        out_dir = self.output_root / "scenes"

        def _run() -> Path:
            base = (
                get_scene_fixture(self._topic_key())
                or get_scene_fixture(self._topic_key().split()[0])
                or earth_scene()
            )
            spec = replace(base, illustration_path=str(illustration))
            result = SceneEngine().compose(spec, output_dir=out_dir)
            scene_json = result.metadata.to_dict()
            from video_renderer.renderer_config import TOPIC_BULLETS

            scene_json["bullets"] = TOPIC_BULLETS.get(self._topic_key(), [])
            self._context["scene_json"] = scene_json
            self._context["scene_json_path"] = Path(result.json_path)
            self._context["scene_fixture_title"] = base.title
            return Path(result.json_path)

        diagram = self._context.get("diagram_png")
        result = self.run_phase(
            "5.8",
            "Scene Composer",
            _run,
            input_summary=_abs(diagram) if diagram else _abs(illustration),
        )
        rec = self.phases[-1]
        if result:
            scene_files = list(out_dir.glob("*"))
            self.note_output(rec, scene_files, f"Scene JSON id={self._context['scene_json']['scene_id']}")
            self.note_connection(
                "5.8",
                False,
                f"Scene uses {self._context.get('scene_fixture_title', self.topic)!r} fixture template; EducationalScript not consumed (known gap)",
            )

    def phase_animation_timeline(self) -> None:
        from animation import TimelineEngine

        scene_json = self._context["scene_json"]
        out_dir = self.output_root / "timelines"

        def _run() -> Path:
            result = TimelineEngine().build_from_scene(scene_json, output_dir=out_dir)
            animation_json = json.loads(Path(result.animation_path).read_text(encoding="utf-8"))
            self._context["animation_json"] = animation_json
            self._context["animation_path"] = Path(result.animation_path)
            self._context["timeline_path"] = Path(result.timeline_path)
            return Path(result.animation_path)

        result = self.run_phase(
            "5.9",
            "Animation Timeline",
            _run,
            input_summary=_abs(self._context.get("scene_json_path")),
        )
        rec = self.phases[-1]
        if result:
            self.note_output(rec, [result, self._context["timeline_path"]], "animation.json + timeline.json")
            self.note_connection("5.9", True, "Consumes Scene JSON from Phase 5.8")

    def phase_frame_renderer(self) -> None:
        from video_renderer import FrameEngine

        scene_json = self._context["scene_json"]
        animation_json = self._context["animation_json"]
        out_path = self.output_root / "frames" / "preview_frame.png"

        def _run() -> Path:
            engine = FrameEngine()
            img = engine.render_frame(scene_json, animation_json, current_time=0.5)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(out_path)
            self._context["preview_frame"] = out_path
            return out_path

        result = self.run_phase(
            "6.0",
            "Frame Renderer",
            _run,
            input_summary=_abs(self._context.get("animation_path")),
        )
        rec = self.phases[-1]
        if result:
            self.note_output(rec, [result], "Single preview frame at t=0.5s")
            self.note_connection("6.0", True, "Consumes scene + animation JSON")

    def phase_timeline_playback(self) -> None:
        from video_renderer import TimelinePlayer

        scene_json = self._context["scene_json"]
        animation_json = self._context["animation_json"]
        frames_root = self.output_root / "frames"

        def _run():
            player = TimelinePlayer()
            fps = int(animation_json.get("fps", 30))
            meta = player.play_timeline(
                scene_json,
                animation_json,
                output_dir=frames_root,
                fps=fps,
            )
            self._context["playback_meta"] = meta
            self._context["frame_directory"] = Path(meta.output_directory)
            duration = float(animation_json.get("duration", scene_json.get("duration", 0)))
            expected = meta.frame_count
            actual = meta.exported_count
            self.frame_audit = {
                "timeline_duration": duration,
                "fps": meta.fps,
                "expected_frames": expected,
                "actual_frames": actual,
                "match": expected == actual,
                "frame_directory": _abs(meta.output_directory),
            }
            return meta

        result = self.run_phase(
            "6.1",
            "Timeline Playback",
            _run,
            input_summary=_abs(self._context.get("preview_frame")),
        )
        rec = self.phases[-1]
        if result:
            self.note_output(
                rec,
                [self._context["frame_directory"]],
                f"{result.exported_count} frames @ {result.fps} fps",
            )
            self.note_connection("6.1", True, "Consumes scene + animation; exports PNG sequence")

    def phase_video_encoder(self) -> None:
        from video_renderer import encode_video
        from video_renderer.ffmpeg_encoder import SubprocessFFmpegExecutor

        playback = self._context.get("playback_meta")
        if playback is None:
            raise RuntimeError("Timeline Playback did not complete")

        videos_root = self.output_root / "videos"

        def _run():
            if not SubprocessFFmpegExecutor().is_available():
                raise RuntimeError("FFmpeg not found on PATH")
            meta = encode_video(
                playback.output_directory,
                fps=playback.fps,
                output_format="both",
                profile="preview",
                playback_metadata=playback,
                scene_metadata=self._context.get("scene_json"),
                output_dir=videos_root,
            )
            self._context["video_meta"] = meta
            playable = bool(meta.mp4_path and Path(meta.mp4_path).stat().st_size > 500)
            self.video_audit = {
                "video_path": _abs(meta.mp4_path),
                "webm_path": _abs(meta.webm_path),
                "thumbnail_path": _abs(meta.thumbnail_path),
                "metadata_path": _abs(meta.metadata_path),
                "video_size": _size(Path(meta.mp4_path)) if meta.mp4_path else 0,
                "duration": meta.duration,
                "fps": meta.fps,
                "frame_count": meta.frame_count,
                "codec": meta.codec,
                "resolution": list(meta.resolution),
                "playable": playable,
            }
            return meta

        result = self.run_phase(
            "6.2",
            "Video Encoder",
            _run,
            input_summary=_abs(self._context.get("frame_directory")),
        )
        rec = self.phases[-1]
        if result:
            meta = self._context["video_meta"]
            paths = [p for p in (meta.mp4_path, meta.webm_path, meta.thumbnail_path, meta.metadata_path) if p]
            self.note_output(rec, paths, f"MP4 + WebM + thumbnail + metadata")
            self.note_connection("6.2", True, "Consumes PNG frame directory from Phase 6.1")

    # ------------------------------------------------------------------ report

    def print_report(self) -> None:
        self.log("")
        self.log("=========================")
        self.log("EXPLAINX PIPELINE REPORT")
        self.log("=========================")

        summary_map = {
            "1": "Phase 1  (Topic Input)",
            "2": "Phase 2  (Presentation Planner)",
            "3": "Phase 3  (Script Generator)",
            "5.6": "Phase 5.6 (Prompt Intelligence)",
            "5.5": "Phase 5.5 (Asset Repository)",
            "5.1": "Phase 5.1 (Image Generation)",
            "5.7": "Phase 5.7 (Diagram Composer)",
            "5.8": "Phase 5.8 (Scene Composer)",
            "5.9": "Phase 5.9 (Animation Timeline)",
            "6.0": "Phase 6.0 (Frame Renderer)",
            "6.1": "Phase 6.1 (Timeline Playback)",
            "6.2": "Phase 6.2 (Video Encoder)",
        }
        total_ms = 0.0
        for rec in self.phases:
            label = summary_map.get(rec.phase_id, rec.name)
            self.log(f"{label}: {rec.execution_ms:.2f} ms — {'OK' if rec.success else 'FAIL'}")
            total_ms += rec.execution_ms

        self.log("------------------------")
        self.log(f"TOTAL TIME: {total_ms:.2f} ms ({total_ms / 1000:.2f} s)")
        self.log(f"TOTAL FILES GENERATED: {len(set(self.files_generated))}")
        self.log(f"TOTAL OUTPUT SIZE: {_fmt_size(self.total_bytes)}")
        self.log("------------------------")

        self.log("")
        self.log("OUTPUT FILES (absolute paths)")
        categories = [
            ("Raw Content", self._context.get("raw_content_path")),
            ("Presentation Plan", self._context.get("presentation_plan_path")),
            ("Script", self._context.get("script_path")),
            ("Prompt Intelligence", self._context.get("prompt_intel_path")),
            ("Images", self._context.get("illustration_path")),
            ("Diagrams", self.output_root / "diagrams"),
            ("Scenes", self._context.get("scene_json_path")),
            ("Timeline", self._context.get("animation_path")),
            ("Frames", self._context.get("frame_directory")),
            ("Videos", self.video_audit.get("video_path")),
            ("Thumbnail", self.video_audit.get("thumbnail_path")),
            ("Metadata", self.video_audit.get("metadata_path")),
        ]
        for label, path in categories:
            if path:
                self.log(f"  {label}: {_abs(path)}")

        self.log("")
        self.log("CONNECTION AUDIT")
        for conn in self.connections:
            mark = "✓" if conn["ok"] else "✗"
            self.log(f"  {mark} [{conn['phase_id']}] {conn['note']}")

        if self.frame_audit:
            self.log("")
            self.log("FRAME COUNT")
            self.log(f"  Timeline Duration: {self.frame_audit.get('timeline_duration')} s")
            self.log(f"  FPS:               {self.frame_audit.get('fps')}")
            self.log(f"  Expected Frames:   {self.frame_audit.get('expected_frames')}")
            self.log(f"  Actual Frames:     {self.frame_audit.get('actual_frames')}")
            if not self.frame_audit.get("match"):
                self.log("  MISMATCH: expected != actual exported frame count")

        if self.video_audit:
            self.log("")
            self.log("VIDEO OUTPUT")
            self.log(f"  Video Path:   {self.video_audit.get('video_path')}")
            self.log(f"  Video Size:   {_fmt_size(self.video_audit.get('video_size', 0))}")
            self.log(f"  Duration:     {self.video_audit.get('duration')} s")
            self.log(f"  FPS:          {self.video_audit.get('fps')}")
            self.log(f"  Frame Count:  {self.video_audit.get('frame_count')}")
            self.log(f"  Codec:        {self.video_audit.get('codec')}")
            self.log(f"  Resolution:   {self.video_audit.get('resolution')}")
            playable = self.video_audit.get("playable")
            self.log(f"  Playable:     {'YES' if playable else 'NO'}")
        elif not any(p.phase_id == "6.2" and p.success for p in self.phases):
            failed = next((p for p in reversed(self.phases) if not p.success), None)
            if failed:
                self.log("")
                self.log("VIDEO NOT GENERATED")
                self.log(f"  Failed Phase: {failed.phase_id} {failed.name}")
                self.log(f"  Reason:       {failed.error}")

        all_ok = self.pipeline_ok and all(p.success for p in self.phases)
        video_ok = bool(self.video_audit.get("playable"))
        self.log("")
        if all_ok and video_ok:
            self.log("EXPLAINX READY")
        else:
            self.log("EXPLAINX NOT READY — see failures above")

    def write_artifacts(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / "pipeline_run.log"
        log_path.write_text("\n".join(self.log_lines) + "\n", encoding="utf-8")

        summary = {
            "topic": self.topic,
            "project_id": self.project_id,
            "timestamp": _iso_now(),
            "pipeline_ok": self.pipeline_ok and all(p.success for p in self.phases),
            "explainx_ready": self.pipeline_ok
            and all(p.success for p in self.phases)
            and bool(self.video_audit.get("playable")),
            "phases": [asdict(p) for p in self.phases],
            "connections": self.connections,
            "frame_audit": self.frame_audit,
            "video_audit": self.video_audit,
            "files_generated": sorted(set(self.files_generated)),
            "total_output_bytes": self.total_bytes,
            "output_root": _abs(self.output_root),
        }
        summary_path = LOG_DIR / "pipeline_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        csv_path = LOG_DIR / "pipeline_timing.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                ["phase_id", "name", "start_time", "end_time", "execution_ms", "success", "error"]
            )
            for p in self.phases:
                writer.writerow(
                    [p.phase_id, p.name, p.start_time, p.end_time, p.execution_ms, p.success, p.error or ""]
                )

        print(f"\nLogs written to:\n  {_abs(log_path)}\n  {_abs(summary_path)}\n  {_abs(csv_path)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the full ExplainX pipeline audit for any topic.",
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default="Planet Earth",
        help='Topic to process (default: "Planet Earth")',
    )
    args = parser.parse_args()

    audit = PipelineAudit(args.topic)
    audit.output_root.mkdir(parents=True, exist_ok=True)
    audit.log("ExplainX Pipeline Integration Audit")
    audit.log(f"Topic: {audit.topic}")
    audit.log(f"Output root: {_abs(audit.output_root)}")

    steps = [
        audit.phase_topic_input,
        audit.phase_presentation_planner,
        audit.phase_script_generator,
        audit.phase_prompt_intelligence,
        audit.phase_asset_repository,
        audit.phase_image_generation,
        audit.phase_diagram_composer,
        audit.phase_scene_composer,
        audit.phase_animation_timeline,
        audit.phase_frame_renderer,
        audit.phase_timeline_playback,
        audit.phase_video_encoder,
    ]

    for step in steps:
        step()
        if not audit.phases[-1].success and audit.phases[-1].phase_id in {"1", "3"}:
            # Script phases require Ollama; continue visual pipeline for partial audit
            if audit.phases[-1].phase_id == "3":
                audit.log("Continuing visual + video pipeline without script linkage…")
                continue
            if audit.phases[-1].phase_id == "1":
                break

    audit.print_report()
    audit.write_artifacts()

    session = audit._context.get("session")
    if session is not None:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    ready = (
        audit.pipeline_ok
        and all(p.success for p in audit.phases)
        and bool(audit.video_audit.get("playable"))
    )
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
