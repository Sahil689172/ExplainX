"""Ollama adapters for single-pass EducationalScript generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.features.single_script.ollama.generator import OllamaSingleScriptGenerator

__all__ = ["OllamaSingleScriptGenerator"]


def __getattr__(name: str):
    if name == "OllamaSingleScriptGenerator":
        from app.features.single_script.ollama.generator import OllamaSingleScriptGenerator

        return OllamaSingleScriptGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
