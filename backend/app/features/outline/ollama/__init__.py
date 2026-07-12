"""Ollama-backed TeachingOutline generation (Phase 3.7)."""

__all__ = ["OllamaOutlineGenerator"]


def __getattr__(name: str):
    if name == "OllamaOutlineGenerator":
        from app.features.outline.ollama.generator import OllamaOutlineGenerator

        return OllamaOutlineGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
