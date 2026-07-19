"""Heuristic QualityEvaluator for educational illustration PNGs (0–10)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class QualityResult:
    """Quality score plus per-heuristic breakdown."""

    score: float
    details: dict[str, Any]


class QualityEvaluator:
    """Score educational PNG assets using lightweight image heuristics.

    Designed so OCR / ML watermark detectors can plug into ``details`` later
    without changing the repository API.
    """

    def evaluate(self, image_path: Path | str) -> QualityResult:
        path = Path(image_path)
        details: dict[str, float | str | bool] = {}
        score = 5.0  # neutral baseline

        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            details["error"] = "pillow_or_numpy_missing"
            return QualityResult(score=5.0, details=details)

        if not path.is_file():
            details["error"] = "missing_file"
            return QualityResult(score=0.0, details=details)

        with Image.open(path) as im:
            image = im.convert("RGBA")
            width, height = image.size
            arr = np.asarray(image)

        # Resolution (prefer 512+)
        min_dim = min(width, height)
        if min_dim >= 512:
            score += 1.5
            details["resolution"] = "good"
        elif min_dim >= 256:
            score += 0.5
            details["resolution"] = "ok"
        else:
            score -= 1.0
            details["resolution"] = "low"
        details["width"] = width
        details["height"] = height

        # Transparent background
        alpha = arr[:, :, 3]
        transparent_ratio = float((alpha < 32).mean())
        if transparent_ratio > 0.15:
            score += 1.5
            details["transparent_background"] = True
        else:
            score -= 0.5
            details["transparent_background"] = False
        details["transparent_ratio"] = round(transparent_ratio, 3)

        # Subject size (non-transparent area)
        subject_mask = alpha >= 32
        subject_ratio = float(subject_mask.mean())
        if 0.15 <= subject_ratio <= 0.85:
            score += 1.5
            details["subject_size"] = "good"
        elif 0.05 <= subject_ratio < 0.15 or 0.85 < subject_ratio <= 0.95:
            score += 0.3
            details["subject_size"] = "ok"
        else:
            score -= 1.0
            details["subject_size"] = "poor"
        details["subject_ratio"] = round(subject_ratio, 3)

        # Centeredness
        ys, xs = np.where(subject_mask)
        if len(xs) > 0:
            cx = float(xs.mean()) / max(width - 1, 1)
            cy = float(ys.mean()) / max(height - 1, 1)
            offset = ((cx - 0.5) ** 2 + (cy - 0.5) ** 2) ** 0.5
            if offset < 0.12:
                score += 1.0
                details["centered"] = True
            elif offset < 0.25:
                score += 0.3
                details["centered"] = "near"
            else:
                score -= 0.8
                details["centered"] = False
            details["center_offset"] = round(offset, 3)

            # Cropping — subject touching edges heavily
            edge_touch = (
                float((xs <= 1).any())
                + float((ys <= 1).any())
                + float((xs >= width - 2).any())
                + float((ys >= height - 2).any())
            )
            if edge_touch >= 3 and subject_ratio > 0.6:
                score -= 0.8
                details["cropping"] = "excessive"
            else:
                score += 0.4
                details["cropping"] = "ok"
        else:
            score -= 2.0
            details["centered"] = False
            details["cropping"] = "empty"

        # Text / watermark heuristics (simple high-frequency / edge density proxy)
        gray = arr[:, :, :3].mean(axis=2)
        edges = np.abs(np.diff(gray, axis=1)).mean() + np.abs(np.diff(gray, axis=0)).mean()
        details["edge_energy"] = round(float(edges), 3)
        # Very high edge energy often indicates dense text / clutter
        if edges > 25:
            score -= 1.0
            details["text_or_clutter"] = "likely"
        else:
            score += 0.5
            details["text_or_clutter"] = "unlikely"

        # Completeness / non-empty opacity variance
        if subject_ratio > 0.02:
            score += 0.5
            details["completeness"] = "ok"
        else:
            score -= 1.5
            details["completeness"] = "empty"

        score = max(0.0, min(10.0, round(score, 2)))
        details["watermark_detection"] = "heuristic_only"
        return QualityResult(score=score, details=dict(details))
