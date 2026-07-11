"""Shared enums (expand in later phases)."""

from __future__ import annotations

from enum import Enum


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"
