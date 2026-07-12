"""Phase 3.5 Ollama integration for EducationalScript generation."""

from app.features.script.ollama.client import OllamaClient, OllamaClientProtocol
from app.features.script.ollama.generator import OllamaContentGenerator
from app.features.script.ollama.prompt_builder import PromptBuilder
from app.features.script.ollama.response_parser import ResponseParser

__all__ = [
    "OllamaClient",
    "OllamaClientProtocol",
    "OllamaContentGenerator",
    "PromptBuilder",
    "ResponseParser",
]
