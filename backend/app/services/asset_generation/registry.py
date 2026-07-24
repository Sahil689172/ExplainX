"""Plugin registry for asset generators — no hardcoded if/else chains."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.asset_generation.interfaces import AssetGenerator
from app.services.asset_generation.models import GENERATOR_PRIORITY, GeneratorType

if TYPE_CHECKING:
    from app.services.visual_intelligence.service import ScenePlan


class GeneratorRegistry:
    """Register / discover / select generators by capability and priority."""

    def __init__(self) -> None:
        self._generators: dict[GeneratorType, AssetGenerator] = {}

    def register(self, generator: AssetGenerator, *, replace: bool = False) -> None:
        key = generator.generator_type()
        if key in self._generators and not replace:
            raise ValueError(f"Generator already registered: {key.value}")
        self._generators[key] = generator

    def register_generator(self, name: str, generator: AssetGenerator, *, replace: bool = False) -> None:
        """Register by string name (must match :class:`GeneratorType`)."""
        key = GeneratorType(name)
        if generator.generator_type() != key:
            raise ValueError(
                f"Name {name!r} does not match generator_type {generator.generator_type().value!r}"
            )
        self.register(generator, replace=replace)

    def unregister(self, name: str | GeneratorType) -> None:
        key = name if isinstance(name, GeneratorType) else GeneratorType(name)
        self._generators.pop(key, None)

    def get(self, name: str | GeneratorType) -> AssetGenerator | None:
        key = name if isinstance(name, GeneratorType) else GeneratorType(name)
        return self._generators.get(key)

    def all(self) -> list[AssetGenerator]:
        ordered: list[AssetGenerator] = []
        for key in GENERATOR_PRIORITY:
            gen = self._generators.get(key)
            if gen is not None:
                ordered.append(gen)
        # Any extras not in the priority list (future plugins).
        for key, gen in self._generators.items():
            if key not in GENERATOR_PRIORITY:
                ordered.append(gen)
        return ordered

    def select(self, plan: ScenePlan) -> AssetGenerator | None:
        """Pick the highest-priority generator that supports ``plan``.

        Prefers the ScenePlan's ``primary_renderer`` when that plugin is registered
        and supports the plan; otherwise walks :data:`GENERATOR_PRIORITY`.
        """
        preferred = self._preferred_from_plan(plan)
        if preferred is not None and preferred.supports(plan):
            return preferred

        for gen in self.all():
            if gen.supports(plan):
                return gen
        return None

    def candidates(self, plan: ScenePlan) -> list[AssetGenerator]:
        return [g for g in self.all() if g.supports(plan)]

    def describe(self) -> list[dict[str, object]]:
        return [g.metadata() for g in self.all()]

    def _preferred_from_plan(self, plan: ScenePlan) -> AssetGenerator | None:
        renderer = plan.strategy.primary_renderer.value
        mapping = {
            "mermaid": GeneratorType.MERMAID,
            "svg": GeneratorType.SVG,
            "matplotlib": GeneratorType.MATPLOTLIB,
            "icon": GeneratorType.ICON,
            "background": GeneratorType.BACKGROUND,
            "openvino": GeneratorType.LOCAL_IMAGE,
            "manim": GeneratorType.SVG,
        }
        key = mapping.get(renderer)
        return self._generators.get(key) if key else None


def default_registry() -> GeneratorRegistry:
    """Registry pre-loaded with all built-in deterministic generators."""
    from app.services.asset_generation.generators.background_generator import (
        BackgroundGenerator,
    )
    from app.services.asset_generation.generators.icon_generator import IconGenerator
    from app.services.asset_generation.generators.infographic_generator import (
        InfographicGenerator,
    )
    from app.services.asset_generation.generators.local_image_generator import (
        LocalImageGenerator,
    )
    from app.services.asset_generation.generators.matplotlib_generator import (
        MatplotlibGenerator,
    )
    from app.services.asset_generation.generators.mermaid_generator import (
        MermaidGenerator,
    )
    from app.services.asset_generation.generators.svg_generator import SVGGenerator
    from app.services.asset_generation.generators.timeline_generator import (
        TimelineGenerator,
    )

    registry = GeneratorRegistry()
    for gen in (
        MermaidGenerator(),
        SVGGenerator(),
        MatplotlibGenerator(),
        IconGenerator(),
        BackgroundGenerator(),
        TimelineGenerator(),
        InfographicGenerator(),
        LocalImageGenerator(),
    ):
        registry.register(gen)
    return registry
