"""Local Hugging Face background removal (offline after first download)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


class BackgroundRemover:
    """Remove image backgrounds to produce a transparent PNG.

    Uses a Hugging Face Hub ONNX/weights cache under ``model_dir``.
    After the first successful download the pipeline runs fully offline.

    For unit tests / environments without the model, pass ``stub=True`` to use
    a deterministic corner-flood heuristic (not production quality).
    """

    HF_REPO_ID = "briaai/RMBG-1.4"
    HF_REVISION = "main"

    def __init__(
        self,
        model_dir: Path,
        *,
        stub: bool = False,
        force_stub: bool | None = None,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        # force_stub aliases stub for clarity in tests.
        self.stub = bool(stub if force_stub is None else force_stub)
        self._pipeline = None
        self._load_error: str | None = None

    def remove(self, image: Image.Image) -> Image.Image:
        """Return an RGBA image with background removed."""
        rgba = image.convert("RGBA")
        if self.stub:
            return self._stub_remove(rgba)
        try:
            return self._hf_remove(rgba)
        except Exception as exc:  # noqa: BLE001
            # Fall back so the pipeline stays usable without GPU/torch.
            self._load_error = str(exc)
            print("[Asset Processor]", flush=True)
            print(
                f"Background model unavailable ({exc}); using stub remover.",
                flush=True,
            )
            return self._stub_remove(rgba)

    def _ensure_pipeline(self):  # noqa: ANN202
        if self._pipeline is not None:
            return self._pipeline
        # Prefer transformers RMBG when installed; otherwise rembg.
        try:
            self._pipeline = self._load_transformers_pipeline()
            return self._pipeline
        except Exception:
            self._pipeline = self._load_rembg_session()
            return self._pipeline

    def _load_transformers_pipeline(self):  # noqa: ANN202
        """Load RMBG-1.4 from a local HF cache directory."""
        from huggingface_hub import snapshot_download

        local_dir = snapshot_download(
            repo_id=self.HF_REPO_ID,
            revision=self.HF_REVISION,
            cache_dir=str(self.model_dir / "hub"),
            local_files_only=False,
        )
        # Attempt transformers AutoModel path when available.
        try:
            import torch
            from transformers import AutoModelForImageSegmentation
            from torchvision import transforms

            model = AutoModelForImageSegmentation.from_pretrained(
                local_dir,
                trust_remote_code=True,
            )
            model.eval()
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device)

            transform = transforms.Compose(
                [
                    transforms.Resize((1024, 1024)),
                    transforms.ToTensor(),
                    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
                ]
            )

            def run(img: Image.Image) -> Image.Image:
                original = img.convert("RGB")
                w, h = original.size
                tensor = transform(original).unsqueeze(0).to(device)
                with torch.no_grad():
                    preds = model(tensor)[-1].sigmoid().cpu()
                mask = preds[0].squeeze()
                mask_img = transforms.ToPILImage()(mask).resize((w, h), Image.Resampling.BILINEAR)
                out = original.convert("RGBA")
                out.putalpha(mask_img)
                return out

            return ("transformers", run)
        except Exception:
            # Fall through to rembg using the same cache root.
            raise

    def _load_rembg_session(self):  # noqa: ANN202
        from rembg import new_session, remove

        # rembg downloads u2net into model_dir when U2NET_HOME is set.
        import os

        os.environ.setdefault("U2NET_HOME", str(self.model_dir / "u2net"))
        session = new_session("u2net")

        def run(img: Image.Image) -> Image.Image:
            return remove(img, session=session)

        return ("rembg", run)

    def _hf_remove(self, image: Image.Image) -> Image.Image:
        kind, run = self._ensure_pipeline()
        _ = kind
        result = run(image)
        if not isinstance(result, Image.Image):
            result = Image.open(result).convert("RGBA")  # type: ignore[arg-type]
        return result.convert("RGBA")

    @staticmethod
    def _stub_remove(image: Image.Image) -> Image.Image:
        """Simple production-fallback / test remover.

        Treats near-white and near-black edge-connected pixels as background.
        """
        rgba = image.convert("RGBA")
        pixels = rgba.load()
        w, h = rgba.size
        assert pixels is not None

        def is_bg(px: tuple[int, int, int, int]) -> bool:
            r, g, b, a = px
            if a < 16:
                return True
            # Near white
            if r >= 245 and g >= 245 and b >= 245:
                return True
            # Near black
            if r <= 12 and g <= 12 and b <= 12:
                return True
            return False

        visited = [[False] * h for _ in range(w)]
        stack: list[tuple[int, int]] = []
        for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            if 0 <= x < w and 0 <= y < h and is_bg(pixels[x, y]):
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
