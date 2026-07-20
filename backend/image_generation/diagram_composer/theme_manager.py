"""Theme manager for educational diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DiagramTheme(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    TEXTBOOK = "textbook"
    MINIMAL = "minimal"
    PRESENTATION = "presentation"


@dataclass(frozen=True, slots=True)
class ThemeColors:
    """Color tokens for a diagram theme."""

    background: tuple[int, int, int, int]
    text: tuple[int, int, int, int]
    muted_text: tuple[int, int, int, int]
    stroke: tuple[int, int, int, int]
    accent: tuple[int, int, int, int]
    label_fill: tuple[int, int, int, int]
    arrow: tuple[int, int, int, int]
    legend_bg: tuple[int, int, int, int]
    title: tuple[int, int, int, int]


_THEMES: dict[DiagramTheme, ThemeColors] = {
    DiagramTheme.LIGHT: ThemeColors(
        background=(255, 255, 255, 255),
        text=(30, 30, 30, 255),
        muted_text=(90, 90, 90, 255),
        stroke=(50, 50, 50, 255),
        accent=(30, 100, 180, 255),
        label_fill=(255, 255, 255, 230),
        arrow=(40, 40, 40, 255),
        legend_bg=(248, 248, 248, 240),
        title=(20, 20, 20, 255),
    ),
    DiagramTheme.DARK: ThemeColors(
        background=(28, 28, 32, 255),
        text=(240, 240, 240, 255),
        muted_text=(180, 180, 180, 255),
        stroke=(200, 200, 200, 255),
        accent=(100, 180, 255, 255),
        label_fill=(40, 40, 48, 230),
        arrow=(220, 220, 220, 255),
        legend_bg=(36, 36, 42, 240),
        title=(250, 250, 250, 255),
    ),
    DiagramTheme.TEXTBOOK: ThemeColors(
        background=(255, 255, 252, 255),
        text=(25, 35, 45, 255),
        muted_text=(70, 80, 90, 255),
        stroke=(35, 55, 75, 255),
        accent=(0, 90, 140, 255),
        label_fill=(255, 255, 255, 235),
        arrow=(20, 50, 80, 255),
        legend_bg=(245, 248, 250, 240),
        title=(10, 40, 70, 255),
    ),
    DiagramTheme.MINIMAL: ThemeColors(
        background=(0, 0, 0, 0),
        text=(20, 20, 20, 255),
        muted_text=(100, 100, 100, 255),
        stroke=(60, 60, 60, 255),
        accent=(0, 0, 0, 255),
        label_fill=(255, 255, 255, 200),
        arrow=(40, 40, 40, 255),
        legend_bg=(255, 255, 255, 180),
        title=(0, 0, 0, 255),
    ),
    DiagramTheme.PRESENTATION: ThemeColors(
        background=(245, 248, 255, 255),
        text=(15, 25, 50, 255),
        muted_text=(60, 80, 110, 255),
        stroke=(40, 70, 120, 255),
        accent=(0, 110, 200, 255),
        label_fill=(255, 255, 255, 240),
        arrow=(0, 90, 180, 255),
        legend_bg=(230, 238, 250, 240),
        title=(0, 50, 110, 255),
    ),
}


class ThemeManager:
    """Resolve diagram visual themes by name."""

    DEFAULT = DiagramTheme.TEXTBOOK

    def get(self, theme: DiagramTheme | str | None = None) -> ThemeColors:
        if theme is None:
            return _THEMES[self.DEFAULT]
        if isinstance(theme, str):
            key = theme.strip().lower()
            try:
                theme = DiagramTheme(key)
            except ValueError:
                theme = self.DEFAULT
        return _THEMES.get(theme, _THEMES[self.DEFAULT])

    def list_themes(self) -> list[str]:
        return [t.value for t in DiagramTheme]
