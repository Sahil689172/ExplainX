# Phase 5.7 — Educational Diagram Composer

Transforms generated illustrations into complete educational diagrams with
**programmatic** labels, arrows, callouts, and legends.

Diffusion models produce illustrations only; ExplainX composes diagrams.

```text
User Prompt → Prompt Intelligence → Asset Repository → Image Generation
      → Diagram Composer → Labels / Callouts / Arrows / Legends → Final Diagram
```

## Package

```text
backend/image_generation/diagram_composer/
  diagram_engine.py       # Orchestrator
  layout_engine.py        # Auto label placement
  label_engine.py         # Fonts, wrap, measurement
  arrow_engine.py         # Straight / curved / dashed / leader
  legend_engine.py        # Auto legend blocks
  theme_manager.py        # Light, Dark, Textbook, Minimal, Presentation
  export_manager.py       # PNG + SVG (+ metadata JSON)
  geometry.py             # Point, Rect, BoundingBox
  canvas.py               # Canvas sizing, illustration fit
  object_locator.py       # ObjectLocator interface (manual now; SAM/YOLO later)
  fixtures.py             # Built-in anchor fixtures for demos/tests
  elements.py             # DiagramSpec, metadata, diagram types
```

## Diagram types

Object, Biology, Flow, Process, Anatomy, Computer Architecture, Physics Concept,
Chemistry, Simple Infographic.

## Usage

```python
from image_generation.diagram_composer import DiagramEngine, earth_spec

engine = DiagramEngine()
result = engine.compose(
    "processed_assets/Earth_abc.png",
    earth_spec(concept_id="earth-1", asset_version="v2"),
    output_dir="processed_assets/diagrams",
)
# result.png_path, result.svg_path, result.metadata
```

### Manual anchors

```python
from image_generation.diagram_composer import DiagramSpec, make_anchor, ManualObjectLocator

spec = DiagramSpec(
    concept="Volcano",
    anchors=[make_anchor("vent", "Vent", x=0.5, y=0.3)],
)
engine = DiagramEngine(object_locator=ManualObjectLocator(spec.anchors))
```

### Fixtures

Built-in fixtures: Earth, Human Heart, Photosynthesis, Computer Motherboard, DNA.

```python
engine.compose_from_fixture("earth.png", "Earth", output_dir="out/")
```

## Repository metadata

`DiagramMetadata` stores `diagram_id`, `concept`, `subject`, `diagram_type`,
`canvas_size`, `labels`, `arrows`, `theme`, `created_at`, `export_format`,
plus optional `concept_id` and `asset_version` for repository linking.

## Logging

`DIAGRAM_CREATED` → `LAYOUT_SELECTED` → `LABEL_PLACED` → `ARROW_DRAWN`
→ `LEGEND_CREATED` → `EXPORT_COMPLETED`

## Tests

```bash
cd backend
python test_diagram_composer.py
python -m unittest image_generation.tests.test_diagram_composer_unit -v
```

## Non-goals (Phase 5.7)

Does **not** modify OpenVINO, Prompt Intelligence, Asset Repository,
Asset Manager, or Smart Cache.

Object detection (`SAM`, `YOLO`, `GroundingDINO`, `Florence`) is interface-only.

Future: PDF/PPTX export, interactive SVG, animation, editable diagrams.
