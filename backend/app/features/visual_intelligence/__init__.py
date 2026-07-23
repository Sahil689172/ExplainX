"""Visual Intelligence HTTP feature — thin REST surface over the service.

This feature only *exposes* the additive
:mod:`app.services.visual_intelligence` package over HTTP. It does not perform
image generation, does not call any LLM, and does not modify any completed
phase (Script, Timeline, Rendering).
"""

from __future__ import annotations
