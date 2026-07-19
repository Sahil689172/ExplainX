"""Lightweight keyword / synonym expansion (no LLM)."""

from __future__ import annotations

from typing import Iterable

# Educational synonym packs — expand titles into searchable keywords.
_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"earth", "planet earth", "the earth", "globe", "world", "blue planet", "planet"}),
    frozenset({"sun", "solar", "star", "sol"}),
    frozenset({"moon", "luna", "satellite"}),
    frozenset({"solar system", "planets", "heliocentric system"}),
    frozenset({"heart", "human heart", "cardiac", "cardiac organ", "heart anatomy"}),
    frozenset({"volcano", "volcanoes", "volcano cross section", "eruption", "magma"}),
    frozenset({"water cycle", "hydrologic cycle", "hydrological cycle"}),
    frozenset({"photosynthesis", "plant energy", "chlorophyll process"}),
    frozenset({"dna", "deoxyribonucleic acid", "genetic code", "double helix"}),
    frozenset({"motherboard", "mainboard", "computer motherboard", "pcb motherboard"}),
    frozenset({"neuron", "nerve cell", "brain cell"}),
    frozenset({"cell", "plant cell", "animal cell"}),
)


def normalize_token(text: str) -> str:
    return " ".join(text.strip().lower().split())


def expand_keywords(seed: str | Iterable[str]) -> list[str]:
    """Expand a title/keyword into related terms via synonym groups."""
    seeds = [seed] if isinstance(seed, str) else list(seed)
    out: set[str] = set()
    for raw in seeds:
        key = normalize_token(raw)
        if not key:
            continue
        out.add(key)
        for group in _SYNONYM_GROUPS:
            if key in group or any(key == g or key in g or g in key for g in group):
                out.update(group)
    return sorted(out)


def expand_from_prompt(prompt: str, *, title: str | None = None) -> list[str]:
    """Derive keywords from an optional title plus prompt tokens."""
    seeds: list[str] = []
    if title:
        seeds.append(title)
    seeds.append(prompt)
    # Also seed known multi-word concepts found in the prompt
    lowered = normalize_token(prompt)
    for group in _SYNONYM_GROUPS:
        for term in group:
            if term in lowered:
                seeds.append(term)
    return expand_keywords(seeds)
