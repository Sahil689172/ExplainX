# Phase 5.2 — OpenVINO Backend

First real local image backend. Model: **`OpenVINO/stable-diffusion-v1-5-fp16-ov`**.

See [ModelChoice.md](ModelChoice.md).

## Flow

```text
GenerationRequest
  → ImageGenerationService
  → BackendRouter
  → OpenVINOBackend
  → ModelManager (detect / download / load / warmup)
  → OpenVINO GenAI or Optimum pipeline
  → Temp PNG 512×512
  → Asset Processor → Asset Library
  → GenerationResponse
```

## Constraints

- One prompt → one PNG → 512×512  
- No batching, img2img, ControlNet, LoRA  
- GPU first, CPU fallback  

## Smoke test

```bat
cd backend
python test_openvino_backend.py
```

Stub-only wiring (no inference): `set EXPLAINX_OPEN_VINO_STUB=1`
