# Phase 5.4 — Smart Asset Library

Semantic cache in front of ``ImageGenerationService``.

```text
Prompt → PromptEnhancer → AssetManager
                              ├── CACHE_HIT  → existing PNG (no OpenVINO)
                              └── CACHE_MISS → ImageGenerationService → save library
```

OpenVINOBackend / generation internals are unchanged.

## Modules

| File | Role |
|------|------|
| `asset_manager.py` | Orchestration + stats logging |
| `asset_library.py` | Persist PNG + JSON under `backend/asset_library/` |
| `asset_index.py` | UUID catalog + `_index.json` |
| `asset_search.py` | `AssetSearcher` / `KeywordSearcher` / `EmbeddingSearcher` |
| `keyword_expand.py` | Synonym dictionary |
| `prompt_enhancer.py` | Title / category / enhanced prompt |

## CLI

```bat
cd backend
python test_asset_library.py
```

## Unit tests (no GPU)

```bat
python -m unittest image_generation.tests.test_asset_library_unit -v
```
