# Phase 5.2 — Model Choice

**Decision:** Official Intel OpenVINO IR — **`OpenVINO/stable-diffusion-v1-5-fp16-ov`**  
**Rejected for Phase 5.2:** SD-Turbo (too large / stalled downloads), SDXL, FLUX, community-converted IR repos

## Why this model

| Criterion | Result |
|-----------|--------|
| Source | Official OpenVINO org on Hugging Face |
| Architecture | Stable Diffusion **v1.5** FP16 IR (not SDXL) |
| Hardware | Fits Iris Xe + 16 GB better than Turbo multi‑GB stalled packs |
| Compatibility | OpenVINO ≥ 2025.0, Optimum Intel ≥ 1.22, GenAI `Text2ImagePipeline` |
| Maintainability | Config-only swap of `openvino_model_repo_id` / path |

## What we do **not** use

- SDXL / SDXL-Turbo  
- FLUX  
- Community packs (e.g. `rupeshs/sd-turbo-openvino`)  
- Multiple concurrent models  

## Architecture (unchanged engine)

```text
ImageGenerationService → BackendRouter → ImageBackend (OpenVINOBackend)
                                              ↓
                                         ModelManager
                                              ↓
                         OpenVINO/stable-diffusion-v1-5-fp16-ov
```

Engine / router / protocols stay model-agnostic. Only config + ModelManager + OpenVINOBackend know the repo id.

## Defaults (Iris Xe)

| Setting | Value |
|---------|-------|
| Local path | `backend/models/openvino_sd15/` |
| HF cache | `backend/models/cache/` (reusable Hub cache) |
| Resolution | 512×512 PNG |
| Steps | 20 |
| Guidance | 7.5 |
| Device | GPU → CPU fallback |
| Auto-download | enabled |

## Install / first run

```bat
cd backend
pip install openvino openvino-genai "optimum[openvino]" huggingface-hub pillow
python test_openvino_backend.py
```

ModelManager downloads the official repo into `models/openvino_sd15` if missing and reuses the Hub cache under `models/cache`.
