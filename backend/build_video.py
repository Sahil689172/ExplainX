"""ExplainX stabilized pipeline — ONE final video per topic.

Stabilization entry point (no new features, no new image models):

    Topic → Scenes → Frames → SceneCollection → Encode ONCE → final_video.mp4

Run from ``backend/``::

    python build_video.py "Planet Earth"
    python build_video.py "Photosynthesis" --debug
    python build_video.py --all
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from animation import TimelineEngine  # noqa: E402
from image_generation.asset_diversity import AssetDiversityManager, SelectionAudit  # noqa: E402
from refine_pipeline import (  # noqa: E402
    BASE_FIXTURE,
    SHOT_ZOOM,
    TOPIC_SCENES,
    _find_illustration,
    _fmt_size,
    _placeholder,
    _size,
    _slug,
)
from scene_generation import SceneEngine  # noqa: E402
from scene_generation.scene_duration import classify_complexity, estimate_scene_duration  # noqa: E402
from scene_generation.scene_templates import get_fixture  # noqa: E402
from video_renderer import TimelinePlayer  # noqa: E402
from video_renderer.ffmpeg_encoder import SubprocessFFmpegExecutor  # noqa: E402
from video_renderer.scene_collection import SceneClip, SceneCollection  # noqa: E402
from video_renderer.video_encoder import encode_collection  # noqa: E402

# --------------------------------------------------------------------------- #
# Pipeline phases (Task 7)
# --------------------------------------------------------------------------- #

PIPELINE_PHASES = (
    "Content Intelligence",
    "Presentation Plan",
    "Script",
    "Prompt",
    "Asset Lookup",
    "Scene Builder",
    "Timeline",
    "Frame Renderer",
    "Scene Collection",
    "Video Encoder",
    "Final Video",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass(slots=True)
class PhaseLogEntry:
    phase: str
    start_time: str
    end_time: str
    execution_ms: float
    output: str
    output_path: str
    status: str  # PASS | FAIL | SKIP


@dataclass(slots=True)
class SceneRecord:
    index: int
    title: str
    shot: str
    zoom: float
    duration: float
    asset: str
    asset_missing: bool
    diagrams: int
    expected_frames: int = 0
    frames: int = 0
    frame_start: int = 0
    frame_end: int = 0
    frame_match: bool = True


@dataclass(slots=True)
class TopicReport:
    topic: str
    output_root: Path
    scenes: list[SceneRecord] = field(default_factory=list)
    assets_used: list[str] = field(default_factory=list)
    missing_assets: list[str] = field(default_factory=list)
    diversity_logs: list[str] = field(default_factory=list)
    total_diagrams: int = 0
    total_frames: int = 0
    expected_total_frames: int = 0
    fps: int = 30
    duration: float = 0.0
    encode_seconds: float = 0.0
    video_size: int = 0
    final_video: str = ""
    phase_log: list[PhaseLogEntry] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    encode_invocations: int = 0

    @property
    def unique_assets(self) -> set[str]:
        return set(self.assets_used)

    @property
    def ok(self) -> bool:
        return not self.failures and all(e.status == "PASS" for e in self.phase_log)


class PhaseRunner:
    """Run a phase, record timing, and emit PASS/FAIL (Task 7/9)."""

    def __init__(self, report: TopicReport, emit: Callable[[str], None]) -> None:
        self._report = report
        self._emit = emit

    def run(
        self,
        phase: str,
        fn: Callable[[], Any],
        *,
        output: str = "",
        path: str = "",
    ) -> Any:
        start = _ts()
        t0 = time.perf_counter()
        status = "PASS"
        result = None
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001
            status = "FAIL"
            self._report.failures.append(f"{phase}: {exc}")
            self._emit(f"  [{phase}] FAIL — {exc}")
            raise
        finally:
            ms = round((time.perf_counter() - t0) * 1000, 2)
            end = _ts()
            entry = PhaseLogEntry(
                phase=phase,
                start_time=start,
                end_time=end,
                execution_ms=ms,
                output=output or phase,
                output_path=path,
                status=status,
            )
            self._report.phase_log.append(entry)
            self._emit(f"  [{phase}] {status} ({ms:.0f} ms) → {path or output}")
        return result

    def record(
        self,
        phase: str,
        status: str,
        *,
        output: str = "",
        path: str = "",
        execution_ms: float = 0.0,
    ) -> None:
        now = _ts()
        entry = PhaseLogEntry(
            phase=phase,
            start_time=now,
            end_time=now,
            execution_ms=execution_ms,
            output=output or phase,
            output_path=path,
            status=status,
        )
        self._report.phase_log.append(entry)
        self._emit(f"  [{phase}] {status} → {path or output}")


def _dirs(topic_root: Path) -> dict[str, Path]:
    names = ["raw", "scripts", "scenes", "frames", "timelines", "videos", "logs"]
    out: dict[str, Path] = {}
    for n in names:
        d = topic_root / n
        d.mkdir(parents=True, exist_ok=True)
        out[n] = d
    return out


def _all_assets(topic: str) -> list[str]:
    """Every image on disk for this topic (asset lookup pool)."""
    needles = [topic.lower().split()[0]]
    found: list[str] = []
    for folder in (ROOT / "processed_assets", ROOT / "generated" / "raw", ROOT / "raw_assets"):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            low = path.name.lower()
            if any(n in low for n in needles):
                found.append(str(path))
    return found


def _scene_candidates(all_assets: list[str], keyword: str, *, used: set[str]) -> list[str]:
    """Prefer keyword-specific assets, then unused, then any remaining."""
    kw = keyword.lower()
    keyword_hits = [a for a in all_assets if kw in Path(a).name.lower()]
    unused = [a for a in all_assets if a not in used]
    pool: list[str] = []
    for group in (keyword_hits, unused, all_assets):
        for item in group:
            if item not in pool:
                pool.append(item)
    return pool


def _log_diversity(emit: Callable[[str], None], audit: SelectionAudit, scene: str) -> None:
    emit(f"  Asset diversity [{scene}]")
    if audit.chosen:
        emit(f"    Chosen:      {Path(audit.chosen).name} — {audit.reason}")
    else:
        emit("    Chosen:      (none)")
    for rej in audit.rejected:
        emit(
            f"    Rejected:    {Path(rej.path).name} "
            f"sim={rej.similarity:.2%} — {rej.reason}"
        )


def _resolve_asset(
    *,
    topic: str,
    concept: str,
    scene_tag: str,
    keyword: str,
    all_assets: list[str],
    used: set[str],
    diversity: AssetDiversityManager,
    images_dir: Path,
    debug: bool,
    continue_on_missing: bool,
    emit: Callable[[str], None],
    report: TopicReport,
) -> Path | None:
    candidates = _scene_candidates(all_assets, keyword, used=used)
    audit = diversity.select_with_audit(candidates)
    _log_diversity(emit, audit, scene_tag)
    report.diversity_logs.append(
        json.dumps(
            {
                "scene": scene_tag,
                "concept": concept,
                "prompt": keyword,
                "chosen": audit.chosen,
                "reason": audit.reason,
                "rejected": [
                    {"path": r.path, "similarity": r.similarity, "reason": r.reason}
                    for r in audit.rejected
                ],
            },
            indent=2,
        )
    )

    if audit.chosen:
        diversity.register(audit.chosen)
        diversity._last_selected = audit.chosen  # noqa: SLF001 — consecutive guard
        return Path(audit.chosen)

    # ---- Missing asset (Task 3) ------------------------------------------ #
    msg = (
        f"MISSING ASSET | topic={topic} | concept={concept} | "
        f"scene={scene_tag} | prompt={keyword}"
    )
    emit(f"  {msg}")
    report.missing_assets.append(msg)

    if debug:
        ph = _placeholder(images_dir / f"{scene_tag}_debug.png", concept)
        emit(f"  DEBUG placeholder inserted: {ph.name}")
        return ph

    if continue_on_missing:
        emit("  --continue-on-missing: skipping scene asset")
        return None

    report.failures.append(msg)
    return None


def run_topic(
    topic: str,
    *,
    ffmpeg_ok: bool,
    debug: bool,
    continue_on_missing: bool,
    log: list[str],
) -> TopicReport:
    key = topic.strip().lower()
    concepts = TOPIC_SCENES.get(key)
    if concepts is None:
        raise ValueError(f"No concept breakdown for {topic!r}. Known: {sorted(TOPIC_SCENES)}")

    topic_root = ROOT / "output" / _slug(topic)
    if topic_root.exists():
        shutil.rmtree(topic_root, ignore_errors=True)
    d = _dirs(topic_root)

    report = TopicReport(topic=topic, output_root=topic_root)

    def emit(msg: str) -> None:
        line = f"{_ts()} | {msg}"
        log.append(line)
        print(msg, flush=True)

    phases = PhaseRunner(report, emit)
    emit("=" * 64)
    emit(f"TOPIC: {topic}  ({len(concepts)} scenes)")
    emit("=" * 64)

    # ---- Content Intelligence + Presentation Plan + Script ---------------- #
    def content_phase() -> dict[str, Any]:
        raw_doc = {"topic": topic, "concepts": concepts, "created_at": _now()}
        raw_path = d["raw"] / "content.json"
        raw_path.write_text(json.dumps(raw_doc, indent=2, default=str), encoding="utf-8")
        plan = {
            "topic": topic,
            "scene_count": len(concepts),
            "layout_sequence": [c["layout"].value if hasattr(c["layout"], "value") else str(c["layout"]) for c in concepts],
        }
        (d["raw"] / "presentation_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        script_lines = [f"# {topic}", ""]
        for i, c in enumerate(concepts, 1):
            script_lines += [f"## Scene {i}: {c['title']}", f"_{c['subtitle']}_"]
            script_lines += [f"- {b}" for b in c["bullets"]] + [""]
        script_path = d["scripts"] / "script.md"
        script_path.write_text("\n".join(script_lines), encoding="utf-8")
        return {"raw": str(raw_path), "script": str(script_path)}

    content_out = phases.run("Content Intelligence", lambda: content_phase()["raw"],
                             output="content.json", path=str(d["raw"] / "content.json"))
    phases.run("Presentation Plan", lambda: content_out,
               output="presentation_plan.json", path=str(d["raw"] / "presentation_plan.json"))
    phases.run("Script", lambda: content_out,
               output="script.md", path=str(d["scripts"] / "script.md"))
    phases.run("Prompt", lambda: True, output="scene keyword prompts", path=str(d["scripts"]))

    # ---- Asset lookup + scene build + timeline ---------------------------- #
    all_assets = _all_assets(topic)
    diversity = AssetDiversityManager(similarity_threshold=0.80)
    scene_engine = SceneEngine()
    timeline_engine = TimelineEngine()
    collection = SceneCollection(TimelinePlayer())
    used_assets: set[str] = set()

    for idx, concept in enumerate(concepts, 1):
        scene_tag = f"scene_{idx:02d}"
        keyword = concept["title"].split()[0]
        emit(f"[{scene_tag}] {concept['title']}")

        illustration = _resolve_asset(
            topic=topic,
            concept=concept["title"],
            scene_tag=scene_tag,
            keyword=keyword,
            all_assets=all_assets,
            used=used_assets,
            diversity=diversity,
            images_dir=d["logs"],  # debug placeholders go to logs/, not scenes
            debug=debug,
            continue_on_missing=continue_on_missing,
            emit=emit,
            report=report,
        )
        if illustration is None:
            continue

        used_assets.add(str(illustration))
        report.assets_used.append(str(illustration))

        duration = estimate_scene_duration(
            bullet_count=len(concept["bullets"]),
            asset_count=2,
            diagram_count=1,
        )
        expected_frames = max(1, int(round(duration * 30)))

        base_spec = get_fixture(BASE_FIXTURE.get(key, "earth")) or get_fixture("earth")
        spec = replace(
            base_spec,
            title=concept["title"],
            subtitle=concept["subtitle"],
            bullets=list(concept["bullets"]),
            scene_type=concept["scene_type"],
            layout=concept["layout"],
            scene_number=idx,
            duration_seconds=duration,
            illustration_path=str(illustration),
        )
        scene_dir = d["scenes"] / scene_tag
        scene_result = scene_engine.compose(spec, output_dir=scene_dir, compose_diagram=True)
        scene_json = scene_result.metadata.to_dict()
        scene_json["duration"] = duration
        scene_json["bullets"] = list(concept["bullets"])
        scene_json["footer"] = f"ExplainX · {topic}"
        scene_json.setdefault("camera", {})
        zoom = min(SHOT_ZOOM.get(concept["shot"], 1.04), 1.10)
        scene_json["camera"]["zoom"] = zoom
        diagrams = scene_json.get("diagrams") or []
        report.total_diagrams += len(diagrams)

        tl = timeline_engine.build_from_scene(scene_json, output_dir=d["timelines"] / scene_tag)
        animation_json = json.loads(Path(tl.animation_path).read_text(encoding="utf-8"))
        animation_json["duration"] = duration
        fps = int(animation_json.get("fps", 30))
        report.fps = fps
        expected_frames = max(1, int(round(duration * fps)))

        collection.add(
            SceneClip(name=concept["title"], scene=scene_json, animation=animation_json, fps=fps)
        )
        report.scenes.append(
            SceneRecord(
                index=idx,
                title=concept["title"],
                shot=concept["shot"],
                zoom=zoom,
                duration=duration,
                asset=str(illustration),
                asset_missing=False,
                diagrams=len(diagrams),
                expected_frames=expected_frames,
            )
        )
        report.expected_total_frames += expected_frames

    if not collection:
        report.failures.append("no scenes rendered — all assets missing")
        phases.record("Asset Lookup", "FAIL", output="0 assets", path=str(d["logs"]))
        phases.record("Scene Builder", "SKIP", output="no scenes")
        phases.record("Timeline", "SKIP", output="no timelines")
        phases.record("Frame Renderer", "SKIP", output="no frames")
        phases.record("Scene Collection", "SKIP", output="empty")
    else:
        phases.run(
            "Asset Lookup",
            lambda: len(report.assets_used),
            output=f"{len(report.unique_assets)} unique / {len(report.assets_used)} total",
            path=str(d["logs"] / "diversity.json"),
        )
        (d["logs"] / "diversity.json").write_text(
            "[\n" + ",\n".join(report.diversity_logs) + "\n]", encoding="utf-8"
        )
        phases.run("Scene Builder", lambda: len(report.scenes),
                   output=f"{len(report.scenes)} scenes", path=str(d["scenes"]))
        phases.run("Timeline", lambda: report.total_diagrams,
                   output=f"{report.total_diagrams} diagrams", path=str(d["timelines"]))

    merged = None
    if collection:
        emit("")
        emit("SceneCollection → merging frames …")

        def on_scene(i: int, clip: SceneClip, stat) -> None:
            rec = report.scenes[i - 1]
            rec.frames = stat.frame_count
            rec.frame_start = stat.frame_start
            rec.frame_end = stat.frame_end
            rec.frame_match = stat.frame_match
            match = "OK" if stat.frame_match else "MISMATCH"
            emit(
                f"  {clip.name:<22} frames {stat.frame_start}..{stat.frame_end} "
                f"({stat.frame_count}/{stat.expected_frames}) [{match}]"
            )
            if not stat.frame_match:
                report.failures.append(
                    f"{clip.name}: expected {stat.expected_frames} frames, got {stat.frame_count}"
                )

        def render_frames():
            nonlocal merged
            merged = collection.render(
                d["frames"] / "merged",
                scratch_dir=d["frames"] / "_scenes",
                on_scene=on_scene,
            )
            return merged.frame_count

        phases.run("Frame Renderer", render_frames,
                   output=f"{report.expected_total_frames} expected",
                   path=str(d["frames"] / "merged"))
        report.total_frames = merged.frame_count if merged else 0
        report.duration = merged.duration if merged else 0.0
        report.fps = merged.fps if merged else report.fps

        phases.run("Scene Collection", lambda: merged.frame_count if merged else 0,
                   output=f"{merged.frame_count} merged frames" if merged else "empty",
                   path=str(d["frames"] / "merged"))

    # ---- Encode ONCE (Task 1) --------------------------------------------- #
    final_path = d["videos"] / "final_video.mp4"
    if ffmpeg_ok and merged and merged.frame_count > 0:
        t0 = time.perf_counter()

        def do_encode():
            nonlocal report
            report.encode_invocations += 1
            meta = encode_collection(
                merged,
                output_format="mp4",
                profile="standard",
                scene_metadata={"title": topic, "scene_id": _slug(topic)},
                output_dir=d["videos"],
            )
            if meta.mp4_path and Path(meta.mp4_path).is_file():
                if final_path.exists():
                    final_path.unlink()
                shutil.move(meta.mp4_path, final_path)
                # Remove nested encoder dir so only ONE mp4 remains.
                nested = Path(meta.mp4_path).parent
                if nested.is_dir() and nested != d["videos"]:
                    shutil.rmtree(nested, ignore_errors=True)
            report.final_video = str(final_path)
            report.video_size = _size(final_path)
            report.encode_seconds = round(time.perf_counter() - t0, 2)
            if report.video_size <= 1024:
                raise RuntimeError("encoded MP4 too small or missing")
            return report.video_size

        try:
            phases.run("Video Encoder", do_encode,
                       output="final_video.mp4", path=str(final_path))
            sz = _fmt_size(report.video_size)
            report.phase_log[-1].output = sz
            phases.run("Final Video", lambda: final_path.is_file(),
                       output="final_video.mp4", path=str(final_path))
        except Exception:
            pass
    else:
        if not ffmpeg_ok:
            report.failures.append("FFmpeg not available")
        reason = "FFmpeg missing" if not ffmpeg_ok else "no frames to encode"
        status = "FAIL" if not ffmpeg_ok else "SKIP"
        phases.record("Video Encoder", status, output=reason, path=str(d["videos"]))
        phases.record("Final Video", status, output=reason, path=str(final_path))

    _write_pipeline_log(d["logs"] / "pipeline.log", report)
    _write_stabilization_report(topic_root, report)
    (d["logs"] / "run.log").write_text("\n".join(log), encoding="utf-8")
    _print_summary(report, emit)
    return report


def _write_pipeline_log(path: Path, report: TopicReport) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="|")
        w.writerow(["Phase", "Start Time", "End Time", "Execution Time (ms)",
                    "Output", "Output Path", "Status"])
        for e in report.phase_log:
            w.writerow([e.phase, e.start_time, e.end_time, e.execution_ms,
                        e.output, e.output_path, e.status])


def _write_stabilization_report(topic_root: Path, report: TopicReport) -> None:
    mp4_count = len(list(topic_root.rglob("*.mp4")))
    consecutive_dupes = sum(
        1 for i in range(1, len(report.assets_used))
        if report.assets_used[i] == report.assets_used[i - 1]
    )
    lines = [
        f"# Stabilization Report — {report.topic}",
        "",
        f"Generated: {_now()}",
        "",
        "## Architectural Fixes",
        "",
        "- **Single encode**: all scenes render frames; `SceneCollection` merges them; "
        "`encode_collection()` invokes FFmpeg exactly once.",
        "- **No per-scene videos**: scene loop never calls the encoder.",
        "- **Asset diversity**: `AssetDiversityManager.select_with_audit()` logs chosen/rejected "
        "assets with similarity scores; consecutive duplicate selection is blocked when "
        "alternatives exist.",
        "- **No silent placeholders**: missing assets are logged explicitly; placeholders only "
        "when `--debug` is set.",
        "- **Camera**: max zoom clamped to **1.10×**, `ease-in-out-quart` easing, bounded pan.",
        "- **Frame verification**: each scene compares `expected_frames = duration × fps` "
        "against actual exported count.",
        "",
        "## Files Modified",
        "",
        "- `build_video.py` — stabilized entry point",
        "- `video_renderer/scene_collection.py` — frame merge + expected frame stats",
        "- `video_renderer/video_encoder.py` — `encode_collection()`",
        "- `image_generation/asset_diversity.py` — audit trail + consecutive guard",
        "- `animation/camera_animation.py` — zoom/pan/easing limits",
        "- `video_renderer/camera_renderer.py` — 1.10× viewport clamp",
        "- `refine_pipeline.py` — SHOT_ZOOM capped; delegates to `build_video.py`",
        "",
        "## Quality Checks",
        "",
        f"| Check | Result |",
        f"|-------|--------|",
        f"| Exactly one MP4 | {'PASS' if mp4_count == 1 and report.final_video else 'FAIL'} ({mp4_count} mp4 files) |",
        f"| Multiple scenes | {'PASS' if len(report.scenes) >= 2 else 'FAIL'} ({len(report.scenes)}) |",
        f"| No duplicate videos | {'PASS' if report.encode_invocations <= 1 else 'FAIL'} ({report.encode_invocations} encode calls) |",
        f"| No repeated assets (consecutive) | {'PASS' if consecutive_dupes == 0 else 'FAIL'} ({consecutive_dupes} consecutive dupes) |",
        f"| Smooth camera (zoom ≤ 1.10) | {'PASS' if all(s.zoom <= 1.10 for s in report.scenes) else 'FAIL'} |",
        f"| Correct frame count | {'PASS' if all(s.frame_match for s in report.scenes) else 'FAIL'} |",
        f"| Duration matches output | {'PASS' if abs(report.duration - sum(s.duration for s in report.scenes)) < 2.0 else 'FAIL'} "
        f"({round(report.duration, 2)}s vs {round(sum(s.duration for s in report.scenes), 2)}s) |",
        f"| Scene transitions (merged) | {'PASS' if report.total_frames > 0 else 'FAIL'} |",
        "",
        "## Pipeline Audit",
        "",
        "| Phase | Status | Detail |",
        "|-------|--------|--------|",
    ]
    for e in report.phase_log:
        lines.append(f"| {e.phase} | {e.status} | {e.output} |")

    if report.missing_assets:
        lines += ["", "## Missing Assets", ""] + [f"- {m}" for m in report.missing_assets]
    if report.failures:
        lines += ["", "## Failures", ""] + [f"- {f}" for f in report.failures]

    lines += [
        "",
        "## Remaining Issues",
        "",
        "- Image generation is **not integrated** — pipeline uses on-disk assets only.",
        "- High-quality backends (FLUX/SDXL) are intentionally **not wired** (stabilization scope).",
        "- When only one asset exists for a topic, reuse is unavoidable.",
        "",
        "## Readiness for Image Generation Integration",
        "",
        "- `SceneCollection` + `encode_collection()` provide a stable render/encode boundary.",
        "- `AssetDiversityManager` is ready to gate generated assets before scene compose.",
        "- Next step: call existing `ImageGenerationService.generate()` per scene **after** "
        "stabilization passes, without changing the stitch/encode flow.",
        "",
        f"**Overall**: {'PIPELINE STABLE' if _quality_ok(report, mp4_count) else 'NOT STABLE'}",
        "",
    ]
    (topic_root / "stabilization_report.md").write_text("\n".join(lines), encoding="utf-8")


def _quality_ok(report: TopicReport, mp4_count: int) -> bool:
    if report.failures:
        return False
    if mp4_count != 1 or not report.final_video:
        return False
    if len(report.scenes) < 2:
        return False
    if report.encode_invocations != 1:
        return False
    if report.total_frames <= 0:
        return False
    if not all(s.frame_match for s in report.scenes):
        return False
    if not all(s.zoom <= 1.10 for s in report.scenes):
        return False
    consecutive = any(
        report.assets_used[i] == report.assets_used[i - 1]
        for i in range(1, len(report.assets_used))
    )
    if consecutive and len(report.unique_assets) > 1:
        return False
    return all(e.status == "PASS" for e in report.phase_log)


def _print_summary(report: TopicReport, emit: Callable[[str], None]) -> None:
    emit("")
    emit("-" * 64)
    emit(f"SUMMARY — {report.topic}")
    emit("-" * 64)
    emit(f"  Scenes:          {len(report.scenes)}")
    emit(f"  Unique assets:   {len(report.unique_assets)}")
    emit(f"  Missing assets:  {len(report.missing_assets)}")
    emit(f"  Frames:          {report.total_frames} (expected {report.expected_total_frames})")
    emit(f"  Duration:        {round(report.duration, 2)} s")
    emit(f"  Encode calls:    {report.encode_invocations}")
    emit(f"  Final video:     {report.final_video or '(none)'}")
    emit(f"  Report:          {report.output_root / 'stabilization_report.md'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="ExplainX stabilized pipeline")
    parser.add_argument("topic", nargs="?", default="Planet Earth")
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Allow placeholder images when assets are missing",
    )
    parser.add_argument(
        "--continue-on-missing",
        action="store_true",
        help="Skip scenes with missing assets instead of failing",
    )
    args = parser.parse_args()

    debug = args.debug or os.environ.get("EXPLAINX_DEBUG", "").lower() in ("1", "true", "yes")

    ffmpeg_ok = SubprocessFFmpegExecutor().is_available()
    if not ffmpeg_ok:
        print("WARNING: FFmpeg not found — final video will not be encoded.", flush=True)

    print("=" * 64)
    print("EXPLAINX — PIPELINE STABILIZATION")
    print("=" * 64)

    topics = ["Planet Earth", "Photosynthesis", "Human Heart"] if args.all else [args.topic]
    reports: list[TopicReport] = []

    for topic in topics:
        log: list[str] = []
        try:
            reports.append(
                run_topic(
                    topic,
                    ffmpeg_ok=ffmpeg_ok,
                    debug=debug,
                    continue_on_missing=args.continue_on_missing,
                    log=log,
                )
            )
        except Exception as exc:  # noqa: BLE001
            import traceback
            print(f"FAILED {topic}: {exc}")
            traceback.print_exc()
            r = TopicReport(topic=topic, output_root=ROOT / "output" / _slug(topic))
            r.failures.append(str(exc))
            reports.append(r)

    print("\n" + "=" * 64)
    print("QUALITY CHECK")
    print("=" * 64)

    all_stable = True
    for r in reports:
        mp4_count = len(list(r.output_root.rglob("*.mp4"))) if r.output_root.exists() else 0
        ok = _quality_ok(r, mp4_count)
        all_stable = all_stable and ok
        print(f"\n{r.topic}: {'PASS' if ok else 'FAIL'}")
        checks = {
            "exactly_one_mp4": mp4_count == 1 and bool(r.final_video),
            "multiple_scenes": len(r.scenes) >= 2,
            "no_duplicate_videos": r.encode_invocations <= 1,
            "no_consecutive_asset_dupes": not any(
                r.assets_used[i] == r.assets_used[i - 1]
                for i in range(1, len(r.assets_used))
            ) or len(r.unique_assets) <= 1,
            "smooth_camera": all(s.zoom <= 1.10 for s in r.scenes),
            "correct_frame_count": all(s.frame_match for s in r.scenes),
            "duration_matches": abs(r.duration - sum(s.duration for s in r.scenes)) < 2.0,
            "scene_transitions": r.total_frames > 0,
        }
        for name, val in checks.items():
            print(f"  {'[x]' if val else '[ ]'} {name}")
        for f in r.failures:
            print(f"    - {f}")

    # Global stabilization report for multi-topic runs
    if len(reports) > 1:
        global_report = ROOT / "output" / "stabilization_report.md"
        lines = ["# ExplainX Global Stabilization Report", "", f"Generated: {_now()}", ""]
        for r in reports:
            mp4 = len(list(r.output_root.rglob("*.mp4"))) if r.output_root.exists() else 0
            status = "STABLE" if _quality_ok(r, mp4) else "NOT STABLE"
            lines.append(f"- **{r.topic}**: {status} → `{r.final_video or 'none'}`")
        lines += ["", f"**Overall**: {'PIPELINE STABLE' if all_stable and ffmpeg_ok else 'NOT STABLE'}", ""]
        global_report.write_text("\n".join(lines), encoding="utf-8")

    print("")
    if all_stable and ffmpeg_ok:
        print("PIPELINE STABLE")
        return 0
    print("PIPELINE NOT STABLE — see stabilization_report.md")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
