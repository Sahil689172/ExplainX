"""Built-in manual anchor fixtures for deterministic diagram demos/tests."""

from __future__ import annotations

from image_generation.diagram_composer.elements import (
    Anchor,
    DiagramSpec,
    DiagramType,
    LegendItem,
)
from image_generation.diagram_composer.geometry import Point
from image_generation.diagram_composer.object_locator import make_anchor


def earth_spec(*, concept_id: str | None = None, asset_version: str | None = None) -> DiagramSpec:
    anchors = [
        make_anchor("core", "Core", x=0.5, y=0.55, color_hint="core", description="Inner Core"),
        make_anchor("mantle", "Mantle", x=0.35, y=0.45, color_hint="mantle", description="Mantle Layer"),
        make_anchor("crust", "Crust", x=0.62, y=0.38, color_hint="crust", description="Earth Crust"),
    ]
    return DiagramSpec(
        concept="Earth",
        subject="Geography",
        diagram_type=DiagramType.OBJECT,
        title="Planet Earth",
        subtitle="Internal structure",
        anchors=anchors,
        legend_items=[
            LegendItem("Core", "Inner hot core", swatch_color=(200, 120, 60, 255)),
            LegendItem("Mantle", "Rocky mantle", swatch_color=(200, 100, 60, 255)),
            LegendItem("Crust", "Thin outer crust", swatch_color=(120, 90, 60, 255)),
        ],
        concept_id=concept_id,
        asset_version=asset_version,
    )


def human_heart_spec(
    *, concept_id: str | None = None, asset_version: str | None = None
) -> DiagramSpec:
    anchors = [
        make_anchor("left_atrium", "Left Atrium", x=0.42, y=0.32, color_hint="heart"),
        make_anchor("right_atrium", "Right Atrium", x=0.58, y=0.32, color_hint="heart"),
        make_anchor("left_ventricle", "Left Ventricle", x=0.42, y=0.62, color_hint="heart"),
        make_anchor("right_ventricle", "Right Ventricle", x=0.58, y=0.62, color_hint="heart"),
    ]
    return DiagramSpec(
        concept="Human Heart",
        subject="Biology",
        diagram_type=DiagramType.ANATOMY,
        title="Human Heart",
        subtitle="Front view — chambers",
        anchors=anchors,
        concept_id=concept_id,
        asset_version=asset_version,
    )


def photosynthesis_spec(
    *, concept_id: str | None = None, asset_version: str | None = None
) -> DiagramSpec:
    anchors = [
        make_anchor("sun", "Sunlight", x=0.15, y=0.2, color_hint="sun", description="Yellow energy source"),
        make_anchor("water", "Water", x=0.25, y=0.75, color_hint="water", description="Blue arrow input"),
        make_anchor("co2", "Carbon Dioxide", x=0.75, y=0.25, color_hint="carbon dioxide", description="Grey molecule"),
        make_anchor("o2", "Oxygen", x=0.8, y=0.7, color_hint="oxygen", description="Blue output"),
        make_anchor("chloroplast", "Chloroplast", x=0.5, y=0.5, color_hint="chloroplast", description="Green organelle"),
    ]
    return DiagramSpec(
        concept="Photosynthesis",
        subject="Biology",
        diagram_type=DiagramType.PROCESS,
        title="Photosynthesis",
        subtitle="Energy conversion in plants",
        anchors=anchors,
        legend_items=[
            LegendItem("Sun", "Yellow Circle", swatch_color=(255, 200, 50, 255), symbol="circle"),
            LegendItem("Water", "Blue Arrow", swatch_color=(60, 140, 220, 255), symbol="arrow"),
            LegendItem("Carbon Dioxide", "Grey Molecule", swatch_color=(140, 140, 140, 255)),
        ],
        concept_id=concept_id,
        asset_version=asset_version,
    )


def motherboard_spec(
    *, concept_id: str | None = None, asset_version: str | None = None
) -> DiagramSpec:
    anchors = [
        make_anchor("cpu", "CPU", x=0.5, y=0.4, color_hint="cpu"),
        make_anchor("ram", "RAM Slots", x=0.72, y=0.35, color_hint="ram"),
        make_anchor("pcie", "PCIe Slot", x=0.3, y=0.55, color_hint="grey"),
        make_anchor("chipset", "Chipset", x=0.55, y=0.62, color_hint="grey"),
    ]
    return DiagramSpec(
        concept="Computer Motherboard",
        subject="Computer Science",
        diagram_type=DiagramType.COMPUTER_ARCHITECTURE,
        title="Computer Motherboard",
        subtitle="Main components",
        anchors=anchors,
        concept_id=concept_id,
        asset_version=asset_version,
    )


def dna_spec(*, concept_id: str | None = None, asset_version: str | None = None) -> DiagramSpec:
    anchors = [
        make_anchor("helix", "Double Helix", x=0.5, y=0.45, color_hint="dna"),
        make_anchor("base_pair", "Base Pairs", x=0.62, y=0.52, color_hint="dna"),
        make_anchor("backbone", "Sugar-Phosphate Backbone", x=0.38, y=0.58, color_hint="blue"),
    ]
    return DiagramSpec(
        concept="DNA",
        subject="Biology",
        diagram_type=DiagramType.BIOLOGY,
        title="DNA",
        subtitle="Molecular structure",
        anchors=anchors,
        concept_id=concept_id,
        asset_version=asset_version,
    )


FIXTURES: dict[str, DiagramSpec] = {
    "earth": earth_spec(),
    "human heart": human_heart_spec(),
    "heart": human_heart_spec(),
    "photosynthesis": photosynthesis_spec(),
    "computer motherboard": motherboard_spec(),
    "motherboard": motherboard_spec(),
    "dna": dna_spec(),
}


def get_fixture(name: str) -> DiagramSpec | None:
    key = name.strip().lower()
    return FIXTURES.get(key)
