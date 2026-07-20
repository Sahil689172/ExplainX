# Phase 5.8 — Educational Scene Composer

Composes multiple assets, diagrams, labels, and layout elements into a single
presentation-ready educational scene (one slide / one video frame).

```text
Topic → Prompt Intelligence → Asset Repository → Diagram Composer
      → Scene Composer → Scene Renderer → Timeline Metadata → Video (future)
```

## Package

```text
backend/scene_generation/
  scene_engine.py       # Orchestrator
  scene_builder.py      # Assemble components (+ optional DiagramEngine)
  scene_layout.py       # Auto placement without overlap
  scene_renderer.py     # PNG / SVG / JSON export
  scene_templates.py    # Reusable templates + fixtures
  camera.py             # Camera metadata for future animation
  timeline.py           # Duration, appearance order, transitions
  transition.py         # Transition types (future)
  scene_metadata.py     # SceneSpec, SceneMetadata, components
```

## Usage

```python
from scene_generation import SceneEngine, earth_scene
from dataclasses import replace

spec = replace(earth_scene(), illustration_path="processed_assets/earth.png")
result = SceneEngine().compose(spec, output_dir="processed_assets/scenes")
```

## Scene types & layouts

**Types:** single concept, comparison, timeline, process, step-by-step, flow,
architecture, cycle, split view, question/answer.

**Layouts:** centered, two/three column, grid, hero, left/right illustration, comparison.

## Metadata

`SceneMetadata` stores `scene_id`, `scene_number`, `title`, `subject`, `layout`,
`assets`, `diagrams`, `camera`, `timeline`, `duration`, plus `concept_id`,
`asset_version`, `diagram_version`.

## Logging

`SCENE_CREATED` → `LAYOUT_SELECTED` → `ASSET_PLACED` / `DIAGRAM_PLACED`
→ `TIMELINE_CREATED` → `SCENE_RENDERED`

## Tests

```bash
cd backend
python test_scene_composer.py
python -m unittest scene_generation.tests.test_scene_composer_unit -v
```

## Non-goals

Does **not** modify Prompt Intelligence, Asset Repository, Diagram Composer,
OpenVINO, or Smart Cache. Diagram Composer is consumed via import only.

Future: animated camera, Ken Burns, voice sync, PPTX/PDF video pipeline.
