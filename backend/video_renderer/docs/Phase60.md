# Phase 6.0 — Frame Rendering Engine

Renders a single animation frame from **Scene JSON** + **Timeline JSON** and returns a
PIL `Image`. No video encoding (Phase 6.3 / FFmpeg).

```text
Scene JSON + Timeline JSON → FrameEngine.render_frame() → PIL.Image
```

## Package

```text
backend/video_renderer/
  frame_engine.py         # FrameEngine.render_frame()
  frame_renderer.py       # Per-layer Pillow rendering
  layer_manager.py        # Collect visible layers at time t
  compositor.py           # Alpha blend, z-order
  camera_renderer.py      # Pan, zoom, Ken Burns
  transform_engine.py     # Keyframe interpolation + easing
  opacity_engine.py       # Opacity at time t
  canvas.py               # Frame canvas
  renderer_config.py      # Width, height, fps, colors
  renderer_types.py       # LayerType, RenderLayer, TransformState
  renderer_metadata.py    # FrameRenderMetadata
```

## Usage

```python
import json
from video_renderer import FrameEngine

scene = json.loads(open("scene.json").read())
timeline = json.loads(open("animation.json").read())
frame = FrameEngine().render_frame(scene, timeline, current_time=1.5)
frame.save("frame_001.png")
```

## Pipeline

Scene → Timeline → Collect Visible Layers → Apply Transforms → Apply Camera
      → Composite Layers → Return Frame

## Logging

`FRAME_STARTED` → `TRANSFORM_APPLIED` → `LAYER_RENDERED` → `CAMERA_APPLIED` → `FRAME_COMPLETED`

## Tests

```bash
cd backend
python test_frame_renderer.py
python -m unittest video_renderer.tests.test_frame_renderer_unit -v
```

## Non-goals

Does **not** modify Prompt Intelligence, Asset Repository, Diagram Composer,
Scene Composer, or Animation Timeline Engine. Consumes their JSON output only.

Does **not** render MP4 yet — individual frames only. Prepared for FFmpeg in Phase 6.3.
