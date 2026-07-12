"""Phase 3.9 Quality Assurance — approve EducationalScript before downstream use.

Import services from ``app.features.quality.service`` directly to avoid
eager package loading during submodule imports.
"""

from app.features.quality.schemas import QualityReport

__all__ = [
    "QualityReport",
]


def __getattr__(name: str):
    if name == "QualityAssuranceService":
        from app.features.quality.service import QualityAssuranceService

        return QualityAssuranceService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
