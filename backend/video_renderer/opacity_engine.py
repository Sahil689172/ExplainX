"""Opacity interpolation for animated layers."""

from __future__ import annotations

from animation.easing import Easing


class OpacityEngine:
    """Compute layer opacity at a given time from keyframes and visibility rules."""

    def __init__(self, *, easing: Easing | None = None) -> None:
        self._easing = easing or Easing()

    def opacity_at(
        self,
        keyframes: list[dict],
        target: str,
        time_s: float,
        *,
        default: float = 1.0,
        visible: bool = True,
    ) -> float:
        if not visible:
            return 0.0
        kfs = [k for k in keyframes if k.get("target") == target and k.get("camera") is None]
        if not kfs:
            return default
        kfs.sort(key=lambda k: k["time"])
        if time_s <= kfs[0]["time"]:
            return float(kfs[0].get("opacity", default))
        if time_s >= kfs[-1]["time"]:
            return float(kfs[-1].get("opacity", default))
        for i in range(len(kfs) - 1):
            a, b = kfs[i], kfs[i + 1]
            if a["time"] <= time_s <= b["time"]:
                span = b["time"] - a["time"]
                t = (time_s - a["time"]) / span if span > 0 else 0.0
                o0 = float(a.get("opacity", default))
                o1 = float(b.get("opacity", default))
                return self._easing.lerp(o0, o1, t)
        return default
