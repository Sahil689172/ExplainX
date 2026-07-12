"""Ollama-backed per-section narration (Phase 3.8)."""

__all__ = ["OllamaSectionGenerator"]


def __getattr__(name: str):
    if name == "OllamaSectionGenerator":
        from app.features.section_generation.ollama.generator import OllamaSectionGenerator

        return OllamaSectionGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
