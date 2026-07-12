"""Ollama-backed section repair (Phase 3.9)."""

__all__ = ["OllamaRepairGenerator"]


def __getattr__(name: str):
    if name == "OllamaRepairGenerator":
        from app.features.quality.ollama.generator import OllamaRepairGenerator

        return OllamaRepairGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
