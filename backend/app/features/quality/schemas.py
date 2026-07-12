"""Quality assurance models (Phase 3.9)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

QUALITY_REPORT_SCHEMA_VERSION = "1.0"
MAX_REPAIR_ATTEMPTS = 2

ValidationStatus = Literal["pass", "fail", "repair"]
FinalStatus = Literal["approved", "rejected", "pending"]


class RepairAction(str, Enum):
    """Targeted repair operations — never full-script regeneration."""

    EXPAND = "expand_section"
    SHORTEN = "shorten_section"
    IMPROVE_TRANSITIONS = "improve_transitions"
    REMOVE_REPETITION = "remove_repetition"
    SIMPLIFY = "simplify_difficult_wording"
    STRENGTHEN_INTRODUCTION = "strengthen_introduction"
    IMPROVE_CONCLUSION = "improve_conclusion"


class QualityFinding(BaseModel):
    """One validation / quality issue, optionally tied to a section."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    section_id: str | None = None
    repair_action: RepairAction | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class SectionRepairRequest(BaseModel):
    """Inputs for repairing a single teaching section."""

    model_config = ConfigDict(extra="forbid")

    section_id: str
    action: RepairAction
    validation_failures: list[str] = Field(default_factory=list)
    target_words: int = Field(ge=1)
    actual_words: int = Field(ge=0)
    learning_objective: str = ""
    previous_section_summary: str = ""
    next_section_title: str | None = None
    original_narration: str
    original_title: str


class RepairLogEntry(BaseModel):
    """One repair attempt record."""

    model_config = ConfigDict(extra="forbid")

    attempt: int = Field(ge=1, le=MAX_REPAIR_ATTEMPTS)
    section_id: str
    action: RepairAction
    before_words: int = Field(ge=0)
    after_words: int = Field(ge=0)
    notes: str = ""


class RepairLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    script_id: str
    entries: list[RepairLogEntry] = Field(default_factory=list)
    created_at: str
    schema_version: str = QUALITY_REPORT_SCHEMA_VERSION


class QualityReport(BaseModel):
    """QA outcome for an EducationalScript."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    script_id: str
    validation_status: ValidationStatus
    repair_attempts: int = Field(ge=0, le=MAX_REPAIR_ATTEMPTS)
    total_words: int = Field(ge=0)
    estimated_duration_sec: float = Field(ge=0.0)
    readability_score: float = Field(ge=0.0, le=1.0)
    repeated_concepts: list[str] = Field(default_factory=list)
    empty_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    findings: list[QualityFinding] = Field(default_factory=list)
    final_status: FinalStatus = "pending"
    created_at: str
    schema_version: str = QUALITY_REPORT_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)
