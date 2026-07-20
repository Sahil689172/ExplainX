# Phase 6.2 — Video Encoding Engine

Converts a rendered PNG frame sequence into playable MP4 (H.264) and WebM (VP9)
video files. **Completely independent of rendering** — consumes only frame
directories and metadata from Phase 6.1 playback.

```text
Frame Sequence → VideoEncoder → FFmpeg → MP4 / WebM
```

## Package (extends `video_renderer/`)

```text
video_encoder.py        # VideoEncoder, encode_video()
ffmpeg_encoder.py       # FFmpegCommandBuilder, FFmpegExecutor
encoding_profiles.py    # Preview / Standard / High Quality / 4K presets
encoder_config.py       # OutputFormat, CodecSettings, EncoderConfig
encoder_metadata.py     # VideoMetadata
video_validator.py      # FrameValidator, FrameSequenceInfo
video_exporter.py       # output/videos/<scene>/ layout
thumbnail_generator.py  # Middle-frame thumbnail.png
```

## Usage

```python
from video_renderer import encode_video, FFmpegVideoEncoder, TimelinePlayer

# 1. Render frames (Phase 6.1)
playback = TimelinePlayer().play_timeline(scene_json, animation_json, output_dir="output/frames")

# 2. Encode video (Phase 6.2)
meta = encode_video(
    playback.output_directory,
    fps=playback.fps,
    output_format="both",   # mp4 + webm
    profile="preview",
    playback_metadata=playback,
    output_dir="output",
)
```

## Output layout

```text
output/videos/<scene_name>/
  video.mp4
  video.webm
  thumbnail.png
  metadata.json
```

## Encoding profiles

| Profile       | Resolution | Bitrate |
|---------------|------------|---------|
| preview       | 1280×720   | 2 Mbps  |
| standard      | 1920×1080  | 6 Mbps  |
| high_quality  | 2560×1440  | 12 Mbps |
| 4k (future)   | 3840×2160  | 24 Mbps |

## Metadata

`video_id`, `scene_id`, `fps`, `duration`, `resolution`, `codec`, `bitrate`,
`frame_count`, `render_profile`, `encoding_time`, `video_size`, `thumbnail_path`.

## Logging

`ENCODING_STARTED` → `FRAME_VALIDATED` → `FFMPEG_COMMAND_BUILT` →
`ENCODING_PROGRESS` → `ENCODING_COMPLETED` → `THUMBNAIL_CREATED` → `VIDEO_EXPORTED`

## Dependency injection

Interfaces: `VideoEncoder`, `FrameValidator`, `ThumbnailGenerator`, `FFmpegExecutor`.

Default implementations: `FFmpegVideoEncoder`, `DefaultFrameValidator`,
`MiddleFrameThumbnailGenerator`, `SubprocessFFmpegExecutor`.

## Tests

```bash
cd backend
python -m unittest video_renderer.tests.test_video_encoder_unit
python test_video_encoder.py   # requires FFmpeg on PATH
```

## Future compatibility

Encoder API accepts optional `scene_metadata` / `playback_metadata` and uses
profile-based scaling — designed for later audio tracks, captions, multi-scene
merging, and streaming without breaking the public `encode_video()` signature.
