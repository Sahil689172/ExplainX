# ExplainX backend archive

Code moved here during architecture cleanup remains available for reference
and can be restored if needed. Nothing in this tree is imported by the live
application or the offline engines.

## Layout

| Path | Why archived |
|------|----------------|
| `app_features_asset_processor/` | Unused fork of top-level `backend/asset_processor/`. Production uses the top-level package. |
| `tests/test_asset_processor.py` | Tests for the archived app-feature fork only. Live coverage: `tests/test_asset_processor_pipeline.py`. |
| `smoke_shims/` | Thin `__main__` wrappers that re-exported package tests. |
| `artifacts/` | One-off run outputs / local Windows registry tweak — not source. |
| `translation_argos_shim.py` | Unused compatibility aliases (`ArgosEngine`). Canonical: `app.features.translation.providers.argos`. |
| `asset_processor_test_environment.py` | Standalone dependency printer; not part of the package API. |
| `runners/_run_single_script_tests.bat` | Ad-hoc pytest launcher that littered `_single_script_test_out.txt`. |

## How to run archived smoke tests (if needed)

```bat
cd backend
python -m image_generation.tests.test_openvino_backend
python -m image_generation.tests.test_image_generation_engine
```

## Restoring the app-feature asset processor

Copy `app_features_asset_processor/` back to `app/features/asset_processor/` and
restore `tests/test_asset_processor.py`. Prefer extending the **top-level**
`asset_processor/` package instead of resurrecting the fork.

## Still live (do not archive without a migration)

- `_run_audit.py` / hooks — Cursor audit hook depends on them (output now under `output/audit/`)
- `refine_pipeline.py` — helpers still imported by `build_video.py`
- `section_generation/` / `single_script/` — still covered by the pytest suite
