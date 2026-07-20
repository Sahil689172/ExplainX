# Phase 5.9 — Animation Timeline Engine

Converts Phase 5.8 Scene JSON into a complete animation timeline describing how
every scene element appears, moves, zooms, fades, and exits.

**No video rendering** — metadata only for future renderers.

```text
Scene JSON → Animation Timeline Engine → timeline.json + animation.json
                                              ↓
                                    Future Video Renderer
```

## Package

```text
backend/animation/
  timeline_engine.py        # Orchestrator
  animation_builder.py      # Scene elements → animation clips
  animation_library.py      # Presets (diagram, bullet reveal, process, …)
  keyframes.py              # Position / scale / opacity keyframes
  easing.py                 # Easing curves
  camera_animation.py       # Pan, zoom, Ken Burns, focus
  transition_engine.py      # Entry / exit transitions
  timeline_serializer.py    # timeline.json + animation.json export
  animation_metadata.py     # Schemas + sync interfaces
```

## Usage

```python
import json
from animation import TimelineEngine

scene = json.loads(Path("scenes/earth/<id>.json").read_text())
result = TimelineEngine().build_from_scene(scene, output_dir="timelines/earth")
```

## Animation types

Fade in/out, slide (4 directions), zoom in/out, scale, rotate, highlight, pulse,
draw arrow, write label, sequential reveal.

## Camera

Static, pan, zoom, focus region, follow target, Ken Burns.

## Transitions

Crossfade, cut, push, slide, dissolve, fade through white.

## Sync (future)

`SyncProvider`, `NarrationSyncProvider`, `NullSyncProvider` — interfaces only.

## Logging

`TIMELINE_CREATED` → `ANIMATION_CREATED` → `KEYFRAME_GENERATED` → `CAMERA_EVENT`
→ `TRANSITION_CREATED` → `TIMELINE_EXPORTED`

## Tests

```bash
cd backend
python test_animation_timeline.py
python -m unittest animation.tests.test_animation_timeline_unit -v
```

## Non-goals

Does **not** modify Prompt Intelligence, Asset Repository, Diagram Composer,
Scene Composer, or OpenVINO. Consumes Scene JSON via import/file only.

Compatible future renderers: MoviePy, Remotion, Manim, FFmpeg, custom OpenGL.
