# ExplainX Architecture Cleanup Report

**Date:** 2026-07-24  
**Scope:** Safe maintainability cleanup only — no feature work, no behaviour changes to completed engines.

## Protected (untouched)

| Module | Reason |
|--------|--------|
| `animation/` | Timeline Engine |
| `video_renderer/` | Offline Rendering Engine |
| `app/features/script`, `narration`, `quality`, `outline`, `scene_builder` | Content Intelligence / Script Generation |
| `app/services/visual_intelligence/` + `app/features/visual_intelligence/` | Visual Intelligence |
| `app/features/renderer/` | Live control-plane renderer (distinct from `video_renderer/`) |
| Top-level `asset_processor/`, `image_generation/`, `scene_generation/`, `asset_intelligence/` | Live offline pipeline |

## Files Removed (from live tree)

Junk artifacts (moved to archive, then removed from live paths):

- `backend/_single_script_test_out.txt`
- `backend/_audit_out.txt`
- `backend/_audit_launch_flag.txt`
- `backend/_fix_ps_lockdown.reg`

## Files Archived

See `backend/archive/README.md`.

| Live path (removed) | Archive path |
|---------------------|--------------|
| `app/features/asset_processor/` (9 modules) | `archive/app_features_asset_processor/` |
| `tests/test_asset_processor.py` | `archive/tests/test_asset_processor.py` |
| `test_openvino_backend.py` | `archive/smoke_shims/test_openvino_backend.py` |
| `test_image_generation_engine.py` | `archive/smoke_shims/test_image_generation_engine.py` |
| Junk artifacts listed above | `archive/artifacts/` |

**Canonical replacement for the archived fork:** top-level `backend/asset_processor/` (covered by `tests/test_asset_processor_pipeline.py` and smoke `test_asset_processor.py`).

## Files Refactored

None (no business-logic edits). Documentation-only updates:

- `image_generation/docs/Phase52.md` — smoke command → package test module
- `image_generation/docs/ModelChoice.md` — same
- `archive/README.md` — new
- this report

## Duplicate Code Eliminated

| Duplicate | Action |
|-----------|--------|
| `app/features/asset_processor` vs `asset_processor/` | Archived the unused app-feature fork |
| Top-level OpenVINO / image-engine smoke shims vs `image_generation/tests/` | Archived shims; package tests remain canonical |

## Imports Cleaned

No live import graph changes beyond removing the unused feature package (it had no external production importers). Wildcard imports were already absent under `app/`.

## Schemas Merged

None in this pass. Multiple `AssetCache` / asset-library types remain intentionally (different planes: control-plane VI cache vs offline processors). Merging would risk behaviour change.

## Utilities Merged

None. Dual easing helpers (`animation/easing.py` vs `app/features/renderer/easing.py`) left in place — each stack owns its API.

## Configuration Cleaned

No environment variables removed (uncertain / still referenced). No settings API changes.

## Folder Improvements

- Introduced `backend/archive/` as the quarantine for obsolete but recoverable code.
- Removed empty / unused `app/features/asset_processor` package from the live feature tree.

## Intentionally left alone (MEDIUM / future)

| Item | Why left |
|------|----------|
| `refine_pipeline.py` | Deprecated CLI, but `build_video.py` still imports helpers from it |
| `section_generation/`, `single_script/` | Alternate script paths; still covered by many tests |
| Phase 1.3 stubs (`agents`, `rendering`, `settings`) | Mounted APIs — removing would break routes |
| Dual render stacks (`app/features/renderer` vs `video_renderer`) | Both live; unification is a future project |
| Dual scene builders (`scene_builder` vs `scene_generation`) | Different domains (script vs offline scenes) |
| Top-level `test_*.py` smoke scripts | Manual demos; pytest `testpaths` is `tests/` only |
| Print-based CLI progress in CI / renderer | Behavioural output for operators — not debug leftovers |
| `doctor_stub.py` | Referenced by npm `doctor` script |

## Potential Future Refactors

1. Extract shared helpers from `refine_pipeline.py` → shared module; make `build_video.py` the sole CLI; archive `refine_pipeline.py`.
2. Unify offline smoke scripts under `*/tests/` and drop remaining top-level `test_*.py` wrappers after CI coverage is confirmed.
3. Long-term: single asset-cache abstraction shared by Visual Intelligence and offline processors (additive adapter, not a rewrite).
4. Replace Phase 1.3 stub routers once real agents/settings/rendering HTTP surfaces exist.
5. Optionally archive `section_generation` / `single_script` after narration pipeline is the only supported path and tests are migrated.

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Accidental deletion of live asset processor | Low | Only the **app/features** fork was archived; top-level package kept |
| Broken docs for smoke commands | Low | Docs updated to `python -m image_generation.tests…` |
| Broken pytest collection | Low | Only the fork-specific test was archived; pipeline tests remain |
| Behaviour / API change | None intended | No protected modules edited; no route changes |

## Validation

Run from `backend/` (agent shell was unavailable in this session — validate locally):

```bat
cd backend
python -m pytest tests -q
python -m pytest app/services/visual_intelligence/tests -q
python -c "from asset_processor import AssetProcessor; print('ok')"
python -c "from app.main import create_app; create_app(); print('ok')"
```

Expected: no import errors for archived packages; existing suite green; APIs unchanged.
