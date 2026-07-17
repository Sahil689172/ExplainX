"""Temporary environment verification for the ExplainX Asset Processor.

Run from the repo root with the project venv active::

    python backend/asset_processor/test_environment.py

This does NOT implement background removal. It only verifies that every
dependency imports, prints installed versions, and reports the compute device.
"""

from __future__ import annotations

import importlib
import platform
import sys

# (module_to_import, friendly_label, distribution_name_for_version)
_CHECKS: list[tuple[str, str, str]] = [
    ("torch", "Torch", "torch"),
    ("torchvision", "TorchVision", "torchvision"),
    ("transformers", "Transformers", "transformers"),
    ("accelerate", "Accelerate", "accelerate"),
    ("safetensors", "Safetensors", "safetensors"),
    ("PIL", "Pillow", "pillow"),
    ("numpy", "NumPy", "numpy"),
    ("cv2", "OpenCV", "opencv-python"),
    ("huggingface_hub", "HuggingFace Hub", "huggingface_hub"),
]


def _version(module, dist_name: str) -> str:
    for attr in ("__version__", "version"):
        value = getattr(module, attr, None)
        if isinstance(value, str):
            return value
    try:
        from importlib.metadata import version

        return version(dist_name)
    except Exception:  # noqa: BLE001
        return "unknown"


def _ram_estimate_gb() -> str:
    try:
        import psutil

        total = psutil.virtual_memory().total
        avail = psutil.virtual_memory().available
        return f"{avail / 1e9:.1f} GB available / {total / 1e9:.1f} GB total"
    except Exception:  # noqa: BLE001
        try:
            import os

            pages = os.sysconf("SC_PHYS_PAGES")  # type: ignore[attr-defined]
            page_size = os.sysconf("SC_PAGE_SIZE")  # type: ignore[attr-defined]
            return f"{(pages * page_size) / 1e9:.1f} GB total"
        except Exception:  # noqa: BLE001
            return "unknown"


def main() -> int:
    results: dict[str, str] = {}
    missing: list[str] = []
    versions: dict[str, str] = {}

    # 1. Python
    py = platform.python_version()
    print(f"Python version : {py}")
    if sys.version_info >= (3, 11):
        print("\u2713 Python OK")
    else:
        print("\u2717 Python too old (need >= 3.11)")

    # 2. Virtual environment
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    print(f"Virtualenv     : {'active' if in_venv else 'NOT active'} ({sys.prefix})")

    # 3. Dependency imports + versions
    modules: dict[str, object] = {}
    for module_name, label, dist_name in _CHECKS:
        try:
            module = importlib.import_module(module_name)
            modules[module_name] = module
            ver = _version(module, dist_name)
            versions[label] = ver
            results[label] = "OK"
            print(f"\u2713 {label} OK ({ver})")
        except Exception as exc:  # noqa: BLE001
            results[label] = f"MISSING ({exc})"
            missing.append(label)
            print(f"\u2717 {label} MISSING: {exc}")

    # 4. Torch backend / CUDA
    device = "CPU"
    torch = modules.get("torch")
    if torch is not None:
        try:
            cuda = bool(torch.cuda.is_available())  # type: ignore[attr-defined]
            if cuda:
                device = f"GPU ({torch.cuda.get_device_name(0)})"  # type: ignore[attr-defined]
            print(f"Torch CUDA     : {'available' if cuda else 'not available'}")
            mps = getattr(getattr(torch, "backends", None), "mps", None)
            if mps is not None and mps.is_available():  # type: ignore[union-attr]
                device = "GPU (Apple MPS)"
                print("Torch MPS      : available")
        except Exception as exc:  # noqa: BLE001
            print(f"Torch backend check failed: {exc}")

    # 5. Hugging Face cache location
    try:
        from huggingface_hub import constants

        print(f"HF cache dir   : {constants.HF_HUB_CACHE}")
    except Exception as exc:  # noqa: BLE001
        print(f"HF cache dir   : unknown ({exc})")

    # 6. Report
    print("\n===== REPORT =====")
    print(f"Python version : {py}")
    print(f"Torch version  : {versions.get('Torch', 'n/a')}")
    print(f"Device         : {device}")
    print(f"Available RAM  : {_ram_estimate_gb()}")
    print(f"Missing        : {', '.join(missing) if missing else 'none'}")

    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
