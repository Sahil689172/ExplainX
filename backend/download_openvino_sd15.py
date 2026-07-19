"""Download-only smoke for ModelManager (no inference)."""

from __future__ import annotations

import sys

from image_generation.config import ImageGenerationConfig
from image_generation.exceptions import ModelDownloadError
from image_generation.openvino.model_manager import ModelManager


def main() -> int:
    cfg = ImageGenerationConfig.from_defaults()
    mgr = ModelManager(cfg)
    print(f"Repo: {cfg.openvino_model_repo_id}")
    print(f"Local: {cfg.model_dir()}")
    try:
        path = mgr.ensure_model()
    except ModelDownloadError as exc:
        print(str(exc))
        return 1
    print(f"OK path={path}")
    print(f"Missing after verify: {mgr._missing_required_files(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
