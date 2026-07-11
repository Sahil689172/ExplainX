"""Common API models for foundation endpoints and stubs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlaceholderResponse(BaseModel):
    """Standard stub payload for not-yet-implemented modules."""

    model_config = ConfigDict(extra="forbid")

    status: str = "not_implemented"
    module: str
    message: str
    phase: str = "1.3"
    next_phase_hint: str | None = None


class SystemInfoData(BaseModel):
    app_name: str
    version: str
    api_version: str
    env: str
    debug: bool
    host: str
    port: int
    data_root: str
    docs_enabled: bool
    features: dict[str, Any] = Field(default_factory=dict)


class ModuleStatusItem(BaseModel):
    name: str
    status: str
    available: bool
    detail: str | None = None
