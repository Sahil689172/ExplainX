"""Phase 3.7 Teaching Outline — lesson plan between RawContent and EducationalScript.

Import the service from ``app.features.outline.service`` directly when needed.
"""

from app.features.outline.schemas import TeachingOutline, TeachingSection

__all__ = [
    "TeachingOutline",
    "TeachingSection",
]


def __getattr__(name: str):
    if name == "TeachingOutlineService":
        from app.features.outline.service import TeachingOutlineService

        return TeachingOutlineService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
