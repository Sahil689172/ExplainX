# ExplainX Architecture Cleanup Report

**Date:** 2026-07-24 (pass 1 + pass 2)  
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

---

## Pass 1 — Files Removed / Archived

### Removed from live tree (junk)

- `backend/_single_script_test_out.txt`
- `backend/_audit_out.txt` (first occurrence)
- `backend/_audit_launch_flag.txt`
- `backend/_fix_ps_lockdown.reg`

### Archived

| Live path (removed) | Archive path |
|---------------------|--------------|
| `app/features/asset_processor/` (9 modules) | `archive/app_features_asset_processor/` |
| `tests/test_asset_processor.py` | `archive/tests/test_asset_processor.py` |
| `test_openvino_backend.py` | `archive/smoke_shims/test_openvino_backend.py` |
| `test_image_generation_engine.py` | `archive/smoke_shims/test_image_generation_engine.py` |

Docs updated: `image_generation/docs/Phase52.md`, `ModelChoice.md`.

---

## Pass 2 — Additional safe cleanup

### Removed from live tree

- `backend/_audit_out.txt` (reappeared; copied to `archive/artifacts/` then deleted)
- `app/features/translation/argos.py` (unused shim; zero importers)
- `asset_processor/test_environment.py` (standalone diagnostic)
- `_run_single_script_tests.bat` (ad-hoc launcher that wrote junk output)

### Refactored (tooling only — not product APIs)

| File | Change |
|------|--------|
| `_run_audit.py` | Write smoke results to `output/audit/import_smoke.txt` instead of littering backend root |
| `_run_audit.bat` | Display the new output path |
| `.gitignore` | Ignore `_audit_out.txt`, `_single_script_test_out.txt`, `_audit_launch_flag.txt` |

### Archived (pass 2)

| Live path | Archive path |
|-----------|--------------|
| `app/features/translation/argos.py` | `archive/translation_argos_shim.py` |
| `asset_processor/test_environment.py` | `archive/asset_processor_test_environment.py` |
| `_run_single_script_tests.bat` | `archive/runners/_run_single_script_tests.bat` |
| `_audit_out.txt` | `archive/artifacts/_audit_out.txt` |

---

## Duplicate Code Eliminated

| Duplicate | Action |
|-----------|--------|
| `app/features/asset_processor` vs `asset_processor/` | Archived unused app-feature fork |
| Top-level OpenVINO / image-engine smoke shims | Archived; package tests remain canonical |
| `translation/argos.py` vs `providers/argos.py` | Archived unused shim |

## Imports Cleaned

- Removed unused `translation.argos` module from live tree (no external importers).
- Wildcard imports were already absent under `app/`.

## Schemas Merged

None. Multiple `AssetCache` types remain intentional across planes.

## Utilities Merged

None. Dual easing helpers left in place (each stack owns its API).

## Configuration Cleaned

- Gitignore entries for local audit dump filenames.
- No environment variables removed (still referenced / uncertain).

## Folder Improvements

- `backend/archive/` quarantine for recoverable obsolete code.
- Audit smoke output redirected under `output/audit/`.

## Intentionally left alone

| Item | Why |
|------|-----|
| `refine_pipeline.py` | `build_video.py` still imports helpers |
| `section_generation/`, `single_script/` | Still required by many tests |
| `_run_audit.py` / Cursor hooks | Live tooling; only output path cleaned |
| `_run_mvp_qa_tests.bat` | Useful local launcher; does not litter junk files |
| Phase 1.3 stubs (`agents`, `rendering`, `settings`) | Mounted APIs |
| Dual render / scene stacks | Both live; unification is future work |
| Print-based CLI progress | Operator-facing behaviour |

## Potential Future Refactors

1. Extract shared helpers from `refine_pipeline.py` → shared module; archive CLI entry.
2. Migrate/drop `section_generation` / `single_script` tests after narration is sole path, then archive packages.
3. Unify smoke demos under package `tests/` once CI coverage is confirmed.
4. Long-term shared asset-cache adapter (additive) across VI and offline processors.
5. Replace Phase 1.3 stub routers when real HTTP surfaces exist.

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Accidental deletion of live asset processor | Low | Only app-feature fork archived |
| Broken Argos imports | Low | Zero repo importers; providers path unchanged |
| Broken Cursor audit hook | Low | `_run_audit.py` kept; only output path moved |
| Behaviour / API change | None intended | Protected modules untouched |

## Validation

```bat
cd backend
python -m pytest tests -q
python -c "from asset_processor import AssetProcessor; from app.features.translation.providers.argos import ArgosProvider; from app.main import create_app; create_app(); print('ok')"
```

Expected: suite green; no imports of archived modules; APIs unchanged.
