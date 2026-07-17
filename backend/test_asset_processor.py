"""Minimal smoke example for the Asset Processor.

Run from the ``backend/`` directory with the project venv active::

    python test_asset_processor.py

Place a source image at ``raw_assets/earth.jpg`` or ``raw_assets/sun.jpg``.
"""

from __future__ import annotations

from pathlib import Path

from asset_processor import AssetProcessor
from asset_processor.config import AssetProcessorConfig

ROOT = Path(__file__).resolve().parent
CANDIDATES = (
    ROOT / "raw_assets" / "earth.jpg",
    ROOT / "raw_assets" / "sun.jpg",
    ROOT / "raw_assets" / "earth.png",
    ROOT / "raw_assets" / "sun.png",
)


def main() -> None:
    config = AssetProcessorConfig(
        raw_directory=ROOT / "raw_assets",
        output_directory=ROOT / "processed_assets",
        cache_directory=ROOT / "cache",
        # RMBG-2.0 is gated; remover auto-falls back to rembg/u2net if needed.
        use_stub_remover=False,
        device="cpu",
    )
    processor = AssetProcessor(config)

    raw = next((p for p in CANDIDATES if p.is_file()), None)
    if raw is None:
        print(f"Place a test image under: {ROOT / 'raw_assets'}")
        return

    print(f"Input: {raw}")
    result = processor.process(raw)
    print("processed_path :", result.processed_path)
    print("cached         :", result.cached)
    print("size           :", result.metadata.width, "x", result.metadata.height)
    print("transparent    :", result.metadata.transparent)
    print("time_ms        :", result.metadata.processing_time_ms)
    print("backend model  :", processor.remover.active_model_name)


if __name__ == "__main__":
    main()
