# ExplainX backend archive

Code moved here during the architecture cleanup remains available for reference
and can be restored if needed. Nothing in this tree is imported by the live
application or the offline engines.

## Layout

| Path | Why archived |
|------|----------------|
| `app_features_asset_processor/` | Unused fork of top-level `backend/asset_processor/`. Production uses the top-level package (`image_generation/openvino/output_pipeline.py`). |
| `tests/test_asset_processor.py` | Tests for the archived app-feature fork only. Live coverage: `tests/test_asset_processor_pipeline.py` against top-level `asset_processor/`. |
| `smoke_shims/` | Thin `__main__` wrappers that re-exported package tests. Run the package tests directly instead. |
| `artifacts/` | One-off run outputs / local Windows registry tweak — not source. |

## How to run archived smoke tests (if needed)

```bat
cd backend
python -m image_generation.tests.test_openvino_backend
python -m image_generation.tests.test_image_generation_engine
```

Or restore a shim from `smoke_shims/` temporarily.

## Restoring the app-feature asset processor

Copy `app_features_asset_processor/` back to `app/features/asset_processor/` and
restore `tests/test_asset_processor.py`. Prefer extending the **top-level**
`asset_processor/` package instead of resurrecting the fork.
