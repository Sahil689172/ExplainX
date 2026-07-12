"""RepairGenerator protocol — targeted section narration repair (Phase 3.9)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.features.quality.schemas import SectionRepairRequest


@runtime_checkable
class RepairGenerator(Protocol):
    """Return repaired narration for one teaching section only."""

    def repair_section(self, request: SectionRepairRequest) -> str: ...
