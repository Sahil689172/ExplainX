"""Reusable educational scene templates."""

from __future__ import annotations

from dataclasses import dataclass

from scene_generation.scene_metadata import SceneLayout, SceneSpec, SceneType


@dataclass(frozen=True, slots=True)
class SceneTemplate:
    template_id: str
    display_name: str
    subject: str
    scene_type: SceneType
    layout: SceneLayout
    default_bullets: tuple[str, ...] = ()
    default_subtitle: str | None = None
    default_footer: str | None = "ExplainX Educational Scene"


TEMPLATES: dict[str, SceneTemplate] = {
    "biology_process": SceneTemplate(
        template_id="biology_process",
        display_name="Biology Process",
        subject="Biology",
        scene_type=SceneType.PROCESS,
        layout=SceneLayout.LEFT_ILLUSTRATION,
        default_subtitle="Biological process overview",
        default_bullets=(
            "Inputs and outputs labeled",
            "Key structures highlighted",
            "Educational textbook style",
        ),
    ),
    "computer_architecture": SceneTemplate(
        template_id="computer_architecture",
        display_name="Computer Architecture",
        subject="Computer Science",
        scene_type=SceneType.ARCHITECTURE,
        layout=SceneLayout.RIGHT_ILLUSTRATION,
        default_subtitle="System components",
        default_bullets=(
            "CPU and memory",
            "Expansion slots",
            "Data flow paths",
        ),
    ),
    "physics_concept": SceneTemplate(
        template_id="physics_concept",
        display_name="Physics Concept",
        subject="Physics",
        scene_type=SceneType.SINGLE_CONCEPT,
        layout=SceneLayout.CENTERED,
        default_subtitle="Conceptual illustration",
    ),
    "geography_overview": SceneTemplate(
        template_id="geography_overview",
        display_name="Geography Overview",
        subject="Geography",
        scene_type=SceneType.SINGLE_CONCEPT,
        layout=SceneLayout.HERO,
        default_subtitle="Earth science overview",
    ),
    "comparison": SceneTemplate(
        template_id="comparison",
        display_name="Comparison",
        subject="General",
        scene_type=SceneType.COMPARISON,
        layout=SceneLayout.COMPARISON,
        default_subtitle="Side-by-side comparison",
    ),
    "timeline": SceneTemplate(
        template_id="timeline",
        display_name="Timeline",
        subject="History",
        scene_type=SceneType.TIMELINE,
        layout=SceneLayout.THREE_COLUMN,
        default_subtitle="Chronological overview",
    ),
}


def apply_template(spec: SceneSpec, template_id: str) -> SceneSpec:
    """Merge a template into a scene spec (non-destructive for explicit fields)."""
    tpl = TEMPLATES.get(template_id)
    if tpl is None:
        return spec
    bullets = spec.bullets or list(tpl.default_bullets)
    return SceneSpec(
        topic=spec.topic,
        title=spec.title or spec.topic,
        subject=spec.subject or tpl.subject,
        scene_type=spec.scene_type if spec.scene_type != SceneType.SINGLE_CONCEPT else tpl.scene_type,
        layout=spec.layout if spec.layout != SceneLayout.CENTERED else tpl.layout,
        subtitle=spec.subtitle or tpl.default_subtitle,
        caption=spec.caption,
        footer=spec.footer or tpl.default_footer,
        bullets=bullets,
        asset_path=spec.asset_path,
        diagram_path=spec.diagram_path,
        illustration_path=spec.illustration_path,
        concept_id=spec.concept_id,
        asset_version=spec.asset_version,
        diagram_version=spec.diagram_version,
        scene_number=spec.scene_number,
        duration_seconds=spec.duration_seconds,
        width=spec.width,
        height=spec.height,
        theme=spec.theme,
        template_id=template_id,
    )


def earth_scene(*, concept_id: str | None = None, asset_version: str = "v1") -> SceneSpec:
    return SceneSpec(
        topic="Earth",
        title="Planet Earth",
        subject="Geography",
        scene_type=SceneType.SINGLE_CONCEPT,
        layout=SceneLayout.HERO,
        subtitle="Structure of our planet",
        bullets=["Core", "Mantle", "Crust"],
        template_id="geography_overview",
        concept_id=concept_id or "concept-earth",
        asset_version=asset_version,
        diagram_version="v1",
        duration_seconds=6.0,
    )


def human_heart_scene(*, concept_id: str | None = None, asset_version: str = "v1") -> SceneSpec:
    return SceneSpec(
        topic="Human Heart",
        title="Human Heart",
        subject="Biology",
        scene_type=SceneType.SPLIT_VIEW,
        layout=SceneLayout.LEFT_ILLUSTRATION,
        subtitle="Chambers and blood flow",
        bullets=["Left atrium", "Right ventricle", "Valves"],
        template_id="biology_process",
        concept_id=concept_id or "concept-heart",
        asset_version=asset_version,
        diagram_version="v1",
    )


def photosynthesis_scene(*, concept_id: str | None = None, asset_version: str = "v1") -> SceneSpec:
    return SceneSpec(
        topic="Photosynthesis",
        title="Photosynthesis",
        subject="Biology",
        scene_type=SceneType.PROCESS,
        layout=SceneLayout.LEFT_ILLUSTRATION,
        subtitle="Energy conversion in plants",
        bullets=["Sunlight", "Water + CO₂", "Oxygen output"],
        template_id="biology_process",
        concept_id=concept_id or "concept-photo",
        asset_version=asset_version,
        diagram_version="v1",
        duration_seconds=7.0,
    )


def motherboard_scene(*, concept_id: str | None = None, asset_version: str = "v1") -> SceneSpec:
    return SceneSpec(
        topic="Computer Motherboard",
        title="Computer Motherboard",
        subject="Computer Science",
        scene_type=SceneType.ARCHITECTURE,
        layout=SceneLayout.RIGHT_ILLUSTRATION,
        subtitle="Main board components",
        bullets=["CPU socket", "RAM slots", "PCIe"],
        template_id="computer_architecture",
        concept_id=concept_id or "concept-mb",
        asset_version=asset_version,
        diagram_version="v1",
    )


def solar_system_scene(*, concept_id: str | None = None, asset_version: str = "v1") -> SceneSpec:
    return SceneSpec(
        topic="Solar System",
        title="The Solar System",
        subject="Astronomy",
        scene_type=SceneType.SINGLE_CONCEPT,
        layout=SceneLayout.CENTERED,
        subtitle="Planets orbiting the Sun",
        bullets=["Sun", "Inner planets", "Outer planets"],
        concept_id=concept_id or "concept-solar",
        asset_version=asset_version,
        diagram_version="v1",
        duration_seconds=8.0,
    )


FIXTURES: dict[str, SceneSpec] = {
    "earth": earth_scene(),
    "human heart": human_heart_scene(),
    "heart": human_heart_scene(),
    "photosynthesis": photosynthesis_scene(),
    "computer motherboard": motherboard_scene(),
    "motherboard": motherboard_scene(),
    "solar system": solar_system_scene(),
}


def get_fixture(name: str) -> SceneSpec | None:
    return FIXTURES.get(name.strip().lower())
