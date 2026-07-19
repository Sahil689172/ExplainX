"""Per-subject educational prompt templates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    subject: str
    template_id: str
    lead_in: str
    subject_hints: str


TEMPLATES: dict[str, PromptTemplate] = {
    "Biology": PromptTemplate(
        subject="Biology",
        template_id="biology_v1",
        lead_in="A flat vector anatomical educational illustration of {subject}",
        subject_hints="front view, biological accuracy, clear silhouette",
    ),
    "Physics": PromptTemplate(
        subject="Physics",
        template_id="physics_v1",
        lead_in="A clean educational physics illustration explaining {subject}",
        subject_hints="simple schematic clarity, conceptual focus",
    ),
    "Chemistry": PromptTemplate(
        subject="Chemistry",
        template_id="chemistry_v1",
        lead_in="A clean educational chemistry illustration of {subject}",
        subject_hints="clear molecular or lab concept shapes",
    ),
    "Mathematics": PromptTemplate(
        subject="Mathematics",
        template_id="mathematics_v1",
        lead_in="A clean educational mathematics illustration of {subject}",
        subject_hints="simple geometric clarity",
    ),
    "Computer Science": PromptTemplate(
        subject="Computer Science",
        template_id="cs_v1",
        lead_in="A clean educational computer science illustration of {subject}",
        subject_hints="tech diagram clarity, recognizable hardware or concept shapes",
    ),
    "Geography": PromptTemplate(
        subject="Geography",
        template_id="geography_v1",
        lead_in="A clean flat vector educational illustration of {subject}",
        subject_hints="clear geographic forms, earth science clarity",
    ),
    "Astronomy": PromptTemplate(
        subject="Astronomy",
        template_id="astronomy_v1",
        lead_in="A clean educational astronomy illustration of {subject}",
        subject_hints="space science textbook clarity",
    ),
    "Engineering": PromptTemplate(
        subject="Engineering",
        template_id="engineering_v1",
        lead_in="A clean educational engineering illustration of {subject}",
        subject_hints="technical diagram clarity",
    ),
    "History": PromptTemplate(
        subject="History",
        template_id="history_v1",
        lead_in="A clean educational history illustration of {subject}",
        subject_hints="simple historical silhouette clarity",
    ),
    "General": PromptTemplate(
        subject="General",
        template_id="general_v1",
        lead_in="A clean flat vector educational illustration of {subject}",
        subject_hints="clear educational silhouette",
    ),
}

# Subject-specific extras injected into the enhanced prompt
SUBJECT_EXTRAS: dict[str, dict[str, str]] = {
    "photosynthesis": (
        "illustrating photosynthesis using simple plant structures, sunlight, water, "
        "carbon dioxide, oxygen, chloroplasts"
    ),
    "human heart": "anatomical illustration of the human heart, front view",
    "heart": "anatomical illustration of the human heart, front view",
    "dna": "double helix DNA molecule educational illustration",
    "sorting algorithm": "abstract educational visualization of a sorting algorithm concept",
    "computer motherboard": "educational illustration of a computer motherboard with clear component shapes",
    "newton's laws": "conceptual physics illustration of Newton's laws of motion",
    "volcano": "volcano cross section educational earth science illustration",
    "earth": "planet Earth globe educational geography illustration",
}


UNIVERSAL_POSITIVE_RULES: tuple[str, ...] = (
    "educational illustration",
    "flat vector",
    "centered composition",
    "isolated object",
    "transparent background",
    "minimal colors",
    "clean outlines",
    "high quality",
    "simple shapes",
    "science textbook style",
    "high contrast",
)


def get_template(subject: str) -> PromptTemplate:
    return TEMPLATES.get(subject, TEMPLATES["General"])
