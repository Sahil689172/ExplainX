# Asset Generation Engine

Deterministic, local-first conversion of Visual Intelligence `ScenePlan` objects
into educational visual assets (SVG / PNG / Mermaid source / metadata).

**No cloud APIs. No paid tools. No AI image generation in this phase.**

## Architecture

```text
EducationalScript
        │
        ▼
VisualIntelligenceService.plan_script()   (unchanged)
        │
        ▼
     ScenePlan
        │
        ▼
AssetGenerationService
        │
        ├─ GeneratorRegistry (plugin priority)
        ├─ AssetGenerationCache (SHA256)
        ├─ AssetValidator
        ├─ AssetExporter
        └─ SceneComposer
        │
        ▼
  AssetBundle / ScenePackage
```

## Folder structure

```text
asset_generation/
├── __init__.py
├── service.py
├── registry.py
├── cache.py
├── models.py
├── interfaces.py
├── validator.py
├── exporter.py
├── scene_composer.py
├── generators/
│   ├── mermaid_generator.py
│   ├── svg_generator.py
│   ├── matplotlib_generator.py
│   ├── icon_generator.py
│   ├── background_generator.py
│   ├── timeline_generator.py
│   ├── infographic_generator.py
│   └── local_image_generator.py   # interface only
└── docs/README.md
```

## Generator priority

1. Mermaid — flowcharts / sequence / state  
2. SVG — boxes, cycles, pyramids, tables  
3. Matplotlib — bar / pie / line / scatter / hist  
4. Icons — local SVG/PNG icon strips  
5. Background — notebook / grid / chalkboard / gradient / dots  
6. Timeline — horizontal / vertical  
7. Infographic — panels + icons + labels  
8. LocalImage — **interface only** (future OpenVINO / ONNX / GGUF / SD)

Selection is plugin-based via `GeneratorRegistry`. Prefer the ScenePlan’s
`primary_renderer` when that plugin supports the plan; otherwise walk priority.

## Usage

```python
from app.services.visual_intelligence import VisualIntelligenceService
from app.services.asset_generation import AssetGenerationService

plans = VisualIntelligenceService().plan_script(script)
svc = AssetGenerationService.with_cache("path/to/cache")
bundle = svc.generate(plans[0], output_dir="out", export_dir="export")
print(bundle.result.generator, bundle.composed_path, bundle.result.cache_hit)
```

## Demo

```bat
cd backend
python demo_asset_generation.py
```

## Adding a new generator

1. Implement `AssetGenerator` (`supports` / `generate` / `estimate_time` / `estimate_memory`).
2. Register in `default_registry()` (or call `registry.register_generator("name", plugin)`).
3. Optionally extend `GENERATOR_PRIORITY`.
4. Add unit tests in `tests/test_asset_generation.py`.

## Future AI generators

`LocalImageGenerator` is a seam only. Later you can add:

- `OpenVINOProvider`
- `ONNXProvider`
- `GGUFProvider`
- `StableDiffusionProvider` / Flux / Fable / Runware

…by implementing `AssetGenerator` and registering them **without** changing
`AssetGenerationService` call sites. Deterministic generators always win when
they support the ScenePlan.

## Dependencies

Core runtime needs only **Pillow** (+ **matplotlib** for charts).

SVG is written with a stdlib helper (`generators/_svg.py`) so **svgwrite is not required**.
Optional extras still listed under `pip install -e ".[asset_generation]"` for matplotlib/networkx/lxml/opencv.
