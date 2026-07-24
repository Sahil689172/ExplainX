"""Shared drawing helpers for deterministic asset generators."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence


def wrap_label(text: str, *, max_chars: int = 28) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def extract_nodes(plan_title: str, narration: str, keywords: Sequence[str], *, limit: int = 5) -> list[str]:
    """Derive a small set of node labels from scene text."""
    nodes: list[str] = []
    for kw in keywords:
        label = wrap_label(kw.title(), max_chars=22)
        if label and label not in nodes:
            nodes.append(label)
        if len(nodes) >= limit:
            return nodes
    if plan_title and plan_title not in nodes:
        nodes.insert(0, wrap_label(plan_title, max_chars=22))
    # Fall back to first sentences of narration.
    if len(nodes) < 2 and narration:
        parts = [p.strip() for p in narration.replace("!", ".").split(".") if p.strip()]
        for part in parts:
            label = wrap_label(part, max_chars=22)
            if label and label not in nodes:
                nodes.append(label)
            if len(nodes) >= limit:
                break
    while len(nodes) < 2:
        nodes.append(f"Step {len(nodes) + 1}")
    return nodes[:limit]


def save_rgba_png(path: Path, size: tuple[int, int], draw_fn) -> tuple[int, int]:
    """Create an RGBA PNG via Pillow; ``draw_fn(draw, width, height)`` paints it."""
    from PIL import Image, ImageDraw

    width, height = size
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw_fn(draw, width, height)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return width, height


def rasterize_boxes_png(
    path: Path,
    *,
    title: str,
    boxes: Sequence[str],
    size: tuple[int, int] = (960, 540),
    fill: tuple[int, int, int, int] = (37, 99, 235, 255),
) -> tuple[int, int]:
    """Simple educational box diagram as PNG (no SVG→PNG converter needed)."""
    from PIL import ImageFont

    def _draw(draw, width: int, height: int) -> None:
        margin = 40
        draw.rectangle([0, 0, width, height], fill=(248, 250, 252, 255))
        try:
            font = ImageFont.load_default()
        except OSError:
            font = None
        draw.text((margin, 16), wrap_label(title, max_chars=50), fill=(15, 23, 42, 255), font=font)
        n = max(1, len(boxes))
        box_h = min(70, (height - 100) // n - 10)
        y = 70
        for i, label in enumerate(boxes):
            x0, y0 = margin, y
            x1, y1 = width - margin, y + box_h
            draw.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=fill)
            draw.text((x0 + 16, y0 + box_h // 3), wrap_label(label, max_chars=40), fill=(255, 255, 255, 255), font=font)
            if i < n - 1:
                cx = width // 2
                draw.line([(cx, y1), (cx, y1 + 18)], fill=(100, 116, 139, 255), width=3)
                draw.polygon([(cx - 6, y1 + 12), (cx + 6, y1 + 12), (cx, y1 + 20)], fill=(100, 116, 139, 255))
            y = y1 + 24

    return save_rgba_png(path, size, _draw)
