"""Phase 3.5 Ollama integration for EducationalScript generation."""

__all__ = [
    "MODEL_NOT_INSTALLED",
    "OllamaClient",
    "OllamaClientProtocol",
    "OllamaContentGenerator",
    "PromptBuilder",
    "ResponseParser",
]


def __getattr__(name: str):
    if name == "MODEL_NOT_INSTALLED":
        from app.features.script.ollama.client import MODEL_NOT_INSTALLED

        return MODEL_NOT_INSTALLED
    if name == "OllamaClient":
        from app.features.script.ollama.client import OllamaClient

        return OllamaClient
    if name == "OllamaClientProtocol":
        from app.features.script.ollama.client import OllamaClientProtocol

        return OllamaClientProtocol
    if name == "OllamaContentGenerator":
        from app.features.script.ollama.generator import OllamaContentGenerator

        return OllamaContentGenerator
    if name == "PromptBuilder":
        from app.features.script.ollama.prompt_builder import PromptBuilder

        return PromptBuilder
    if name == "ResponseParser":
        from app.features.script.ollama.response_parser import ResponseParser

        return ResponseParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
