# Phase 6.1 — Timeline Playback Engine

Generates an ordered sequence of rendered PNG frames by repeatedly calling the
Phase 6.0 Frame Rendering Engine. **No video encoding.**

```text
Timeline JSON → Timeline Player → Frame Renderer → Frame Sequence (PNG folder)
```

## Package (extends `video_renderer/`)

```text
timeline_player.py       # TimelinePlayer.play_timeline()
playback_controller.py   # Entire / time range / frame range / preview modes
frame_scheduler.py       # Timestamps and frame indices
frame_exporter.py        # frame_000000.png naming
fps_manager.py           # 24 / 30 / 60 FPS (120 future)
render_session.py        # Per-run session state
playback_metadata.py     # PlaybackMetadata
```

## Usage

```python
from video_renderer import TimelinePlayer, PlaybackMode

player = TimelinePlayer()
meta = player.play_timeline(scene_json, animation_json, output_dir="output", fps=30)

# Preview (25% / 50% — skips frames)
meta = player.play_preview(scene_json, animation_json, preview_mode=0.5)

# Frame range
meta = player.play_timeline(
    scene_json, animation_json,
    frame_start=0, frame_end=119,
    mode=PlaybackMode.FRAME_RANGE,
)
```

## Output layout

```text
output/frames/<scene_name>/frame_000000.png
output/frames/<scene_name>/frame_000001.png
...
```

## Playback metadata

`session_id`, `scene_id`, `fps`, `duration`, `frame_count`, `exported_count`,
`output_directory`, `start_time`, `end_time`, `render_time_seconds`, `timestamps`.

## Logging

`PLAYBACK_STARTED` → `FRAME_RENDERED` → `FRAME_EXPORTED` → `PLAYBACK_COMPLETED`

## Tests

```bash
cd backend
python test_timeline_player.py
python -m unittest video_renderer.tests.test_timeline_player_unit -v
```

## Non-goals

Does **not** modify upstream engines. Does **not** generate MP4.

Output is designed for future FFmpeg / MoviePy / Remotion / OpenGL pipelines.
