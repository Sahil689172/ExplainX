# Phase 5.5 — Educational Asset Repository

Extends Phase 5.4 without replacing Smart Cache / Asset Manager generation flow.

```text
Prompt → PromptEnhancer → AssetManager
                              ↓
                   EducationalAssetRepository
                              ↓
                     Best Version Selector
                              ↓
                    CACHE HIT → return version PNG
                    CACHE MISS → ImageGenerationService → create_version()
```

## Layout

```text
backend/asset_library/
  concepts/<slug>/
    concept.json
    versions/vN/image.png
    versions/vN/metadata.json
  pending_review/
  assets/          # Phase 5.4 flat library (still used)
  metadata/
```

## API

`EducationalAssetRepository`: `create_concept`, `create_version`, `approve_version`,
`reject_version`, `set_preferred_version`, `get_best_version`, `record_usage`,
`repository_statistics`.

## Integration

```python
from image_generation.repository import EducationalAssetRepository
from image_generation.asset_manager import AssetManager

repo = EducationalAssetRepository()
manager = AssetManager(service, repository=repo)  # Phase 5.5 enabled
# manager = AssetManager(service)                 # Phase 5.4-only still works
```

## Tests

```bat
cd backend
python test_asset_repository.py
python -m unittest image_generation.tests.test_asset_repository_unit -v
python test_asset_library.py
```
