"""Background removal with Bria RMBG 2.0 + public offline fallbacks.

Preferred model: ``briaai/RMBG-2.0`` (gated — requires Hugging Face login).

If the gated repo is unavailable, automatically falls back to:

1. ``briaai/RMBG-1.4`` (when accessible)
2. ``rembg`` / u2net (public, offline after first download)

The chosen backend is loaded once and reused for every image.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from PIL import Image

from asset_processor.config import AssetProcessorConfig
from asset_processor.exceptions import BackgroundRemovalError

logger = logging.getLogger(__name__)

# Public / semi-public fallbacks when RMBG-2.0 is gated.
_FALLBACK_HF_MODELS = (
    "briaai/RMBG-1.4",
    "ZhengPeng7/BiRefNet",
)


class BackgroundRemover:
    """Remove image backgrounds. Model is loaded once via ``load_model()``."""

    def __init__(self, config: AssetProcessorConfig | None = None) -> None:
        self.config = config or AssetProcessorConfig()
        self._backend: str | None = None  # "transformers" | "rembg" | "stub"
        self._model: Any = None
        self._transform: Any = None
        self._rembg_session: Any = None
        self._device: str = self.config.device
        self._loaded = False
        self._active_model_name: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def active_model_name(self) -> str | None:
        return self._active_model_name

    def load_model(self) -> None:
        """Load RMBG-2.0 when authorized; otherwise use a public fallback."""
        if self._loaded:
            return

        if self.config.use_stub_remover:
            print("Loading Model", flush=True)
            print("(stub remover — tests / offline CI)", flush=True)
            self._backend = "stub"
            self._active_model_name = "stub"
            self._loaded = True
            return

        print("Loading Model", flush=True)

        try:
            import torch  # noqa: F401
            from torchvision import transforms  # noqa: F401
            from transformers import AutoModelForImageSegmentation  # noqa: F401
        except ImportError as exc:
            raise BackgroundRemovalError(
                "torch, torchvision, and transformers are required. "
                "Install: pip install torch torchvision transformers accelerate safetensors"
            ) from exc

        candidates = [self.config.model_name, *_FALLBACK_HF_MODELS]
        # De-duplicate while preserving order.
        seen: set[str] = set()
        ordered: list[str] = []
        for name in candidates:
            if name not in seen:
                seen.add(name)
                ordered.append(name)

        last_error: Exception | None = None
        for model_name in ordered:
            try:
                self._load_transformers_model(model_name)
                self._backend = "transformers"
                self._active_model_name = model_name
                self._loaded = True
                print(f"Model ready: {model_name} ({self._device})", flush=True)
                if model_name != self.config.model_name:
                    print(
                        f"Note: preferred {self.config.model_name} unavailable; "
                        f"using public fallback {model_name}.",
                        flush=True,
                    )
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Could not load %s: %s", model_name, exc)
                print(f"Could not load {model_name}: {type(exc).__name__}", flush=True)

        # Final public fallback: rembg (no gated HF access required).
        try:
            self._load_rembg()
            self._backend = "rembg"
            self._active_model_name = "rembg/u2net"
            self._loaded = True
            print("Model ready: rembg/u2net (CPU)", flush=True)
            print(
                "Note: Bria RMBG-2.0 is gated. Using rembg fallback.\n"
                "To use RMBG-2.0 later:\n"
                "  1) Visit https://huggingface.co/briaai/RMBG-2.0 and accept terms\n"
                "  2) Run: huggingface-cli login\n"
                "  3) Re-run the processor",
                flush=True,
            )
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc

        raise BackgroundRemovalError(
            "Failed to load any background-removal backend.\n"
            f"Last error: {last_error}\n"
            "Options:\n"
            "  • pip install rembg onnxruntime\n"
            "  • Or accept RMBG-2.0 terms + huggingface-cli login\n"
            "  • Or set use_stub_remover=True for a heuristic test path"
        )

    def remove_background(self, image: Image.Image) -> Image.Image:
        """Return an RGBA image with the background removed."""
        if not self._loaded:
            self.load_model()

        if self._backend == "stub":
            return self._stub_remove(image.convert("RGBA"))
        if self._backend == "rembg":
            return self._rembg_remove(image)
        if self._backend == "transformers":
            return self._transformers_remove(image)

        raise BackgroundRemovalError("No background-removal backend is loaded.")

    def _load_transformers_model(self, model_name: str) -> None:
        import torch
        from torchvision import transforms
        from transformers import AutoModelForImageSegmentation

        if self.config.device == "cuda" and torch.cuda.is_available():
            self._device = "cuda"
        else:
            self._device = "cpu"

        token = (
            os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGINGFACE_HUB_TOKEN")
            or True  # use cached login if present
        )

        model = AutoModelForImageSegmentation.from_pretrained(
            model_name,
            trust_remote_code=True,
            revision=self.config.model_revision
            if model_name == self.config.model_name
            else "main",
            token=token,
        )
        model.eval()
        model.to(self._device)

        self._transform = transforms.Compose(
            [
                transforms.Resize((1024, 1024)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
        self._model = model

    def _load_rembg(self) -> None:
        from rembg import new_session

        # Keep rembg weights under backend/cache/u2net when possible.
        u2net_home = self.config.cache_directory / "u2net"
        u2net_home.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("U2NET_HOME", str(u2net_home))
        self._rembg_session = new_session("u2net")

    def _transformers_remove(self, image: Image.Image) -> Image.Image:
        assert self._model is not None
        assert self._transform is not None
        try:
            import torch
            from torchvision import transforms as tv_transforms

            original = image.convert("RGB")
            width, height = original.size
            tensor = self._transform(original).unsqueeze(0).to(self._device)

            with torch.no_grad():
                outputs = self._model(tensor)
                if isinstance(outputs, (list, tuple)):
                    pred = outputs[-1]
                else:
                    pred = outputs
                mask = pred.sigmoid().cpu()

            while mask.ndim > 3:
                mask = mask.squeeze(0)
            if mask.ndim == 3:
                mask = mask[0]

            mask_img = tv_transforms.ToPILImage()(mask).resize(
                (width, height),
                Image.Resampling.BILINEAR,
            )
            result = original.convert("RGBA")
            result.putalpha(mask_img)
            return result
        except Exception as exc:  # noqa: BLE001
            raise BackgroundRemovalError(f"Background removal failed: {exc}") from exc

    def _rembg_remove(self, image: Image.Image) -> Image.Image:
        try:
            from rembg import remove

            result = remove(image.convert("RGBA"), session=self._rembg_session)
            if not isinstance(result, Image.Image):
                result = Image.open(result).convert("RGBA")  # type: ignore[arg-type]
            return result.convert("RGBA")
        except Exception as exc:  # noqa: BLE001
            raise BackgroundRemovalError(f"rembg removal failed: {exc}") from exc

    @staticmethod
    def _stub_remove(image: Image.Image) -> Image.Image:
        """Deterministic corner-flood remover for tests (not production quality)."""
        rgba = image.convert("RGBA")
        pixels = rgba.load()
        w, h = rgba.size
        assert pixels is not None

        def is_bg(px: tuple[int, int, int, int]) -> bool:
            r, g, b, a = px
            if a < 16:
                return True
            if r >= 245 and g >= 245 and b >= 245:
                return True
            if r <= 12 and g <= 12 and b <= 12:
                return True
            return False

        visited = [[False] * h for _ in range(w)]
        stack: list[tuple[int, int]] = []
        for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            if is_bg(pixels[x, y]):
                stack.append((x, y))

        while stack:
            x, y = stack.pop()
            if visited[x][y]:
                continue
            visited[x][y] = True
            if not is_bg(pixels[x, y]):
                continue
            r, g, b, _a = pixels[x, y]
            pixels[x, y] = (r, g, b, 0)
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny]:
                    stack.append((nx, ny))
        return rgba
