"""Health check response payloads."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthData(BaseModel):
    status: str = "ok"
    uptime_sec: float = Field(ge=0)
    version: str
    env: str


class DoctorCheck(BaseModel):
    id: str
    ok: bool
    detail: str | None = None


class DoctorData(BaseModel):
    ready: bool
    checks: list[DoctorCheck]
