"""VisualIntentAnalyzer — deterministic, rule-based visual classification.

Given a scene (title, narration, keywords, educational concepts, learning
objective) it decides the best :class:`VisualType`, a suggested renderer, a
confidence score, human-readable reasoning, an estimated duration, and a
complexity band.

It does NOT call an LLM. Prompt templates for a future LLM classifier live in
:mod:`app.services.visual_intelligence.prompt_templates`; this analyzer is the
current, fully-offline implementation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.visual_intelligence.schemas import (
    Complexity,
    RendererType,
    SceneInput,
    VisualIntent,
    VisualType,
)


@dataclass(frozen=True, slots=True)
class VisualRule:
    """One keyword-driven rule mapping evidence to a visual type."""

    visual_type: VisualType
    renderer: RendererType
    keywords: tuple[str, ...]
    weight: float = 1.0

    def score(self, corpus: str) -> tuple[float, list[str]]:
        matched = [kw for kw in self.keywords if _contains_word(corpus, kw)]
        return len(matched) * self.weight, matched


def _contains_word(corpus: str, keyword: str) -> bool:
    """Whole-word / phrase match against the corpus."""
    kw = keyword.lower().strip()
    if not kw:
        return False
    if " " in kw:
        return kw in corpus
    return re.search(rf"\b{re.escape(kw)}\b", corpus) is not None


# Ordered by specificity: earlier rules win ties.
DEFAULT_RULES: tuple[VisualRule, ...] = (
    VisualRule(
        VisualType.FLOWCHART,
        RendererType.MERMAID,
        ("flowchart", "process", "step", "steps", "workflow", "procedure",
         "sequence", "pipeline", "stage", "stages", "decision", "if then"),
        weight=1.2,
    ),
    VisualRule(
        VisualType.TIMELINE,
        RendererType.MERMAID,
        ("timeline", "history", "chronology", "era", "century", "year",
         "before", "after", "evolution", "over time", "milestone"),
        weight=1.1,
    ),
    VisualRule(
        VisualType.CHART,
        RendererType.MATPLOTLIB,
        ("chart", "graph", "percentage", "percent", "statistics", "data",
         "trend", "distribution", "compare values", "bar", "plot", "rate"),
        weight=1.1,
    ),
    VisualRule(
        VisualType.TABLE,
        RendererType.SVG,
        ("table", "comparison", "versus", "vs", "rows", "columns",
         "pros and cons", "matrix"),
        weight=1.0,
    ),
    VisualRule(
        VisualType.MAP,
        RendererType.OPENVINO,
        ("map", "geography", "country", "continent", "region", "location",
         "terrain", "border", "ocean", "territory"),
        weight=1.1,
    ),
    VisualRule(
        VisualType.MATHEMATICAL,
        RendererType.MANIM,
        ("equation", "formula", "theorem", "proof", "integral", "derivative",
         "function", "geometry", "vector", "matrix math", "calculus", "algebra"),
        weight=1.3,
    ),
    VisualRule(
        VisualType.SCIENTIFIC,
        RendererType.OPENVINO,
        ("molecule", "atom", "cell", "dna", "reaction", "photosynthesis",
         "anatomy", "organ", "physics", "chemistry", "biology", "force",
         "energy", "electron"),
        weight=1.1,
    ),
    VisualRule(
        VisualType.DIAGRAM,
        RendererType.SVG,
        ("diagram", "structure", "component", "components", "parts", "layer",
         "layers", "system", "architecture", "cross section", "cross-section",
         "label", "relationship"),
        weight=1.0,
    ),
    VisualRule(
        VisualType.ICON,
        RendererType.ICON,
        ("icon", "symbol", "logo", "badge", "glyph", "marker"),
        weight=0.9,
    ),
    VisualRule(
        VisualType.PHOTO,
        RendererType.OPENVINO,
        ("photo", "photograph", "realistic", "real world", "scene of",
         "landscape", "portrait", "picture of"),
        weight=1.0,
    ),
    VisualRule(
        VisualType.ILLUSTRATION,
        RendererType.OPENVINO,
        ("illustration", "drawing", "depict", "imagine", "artistic",
         "concept art", "visualize", "scene"),
        weight=0.8,
    ),
    VisualRule(
        VisualType.BACKGROUND,
        RendererType.BACKGROUND,
        ("background", "backdrop", "ambient", "gradient", "texture"),
        weight=0.7,
    ),
)


@dataclass
class VisualIntentAnalyzer:
    """Rule-based analyzer. Stateless across calls; safe to reuse."""

    rules: tuple[VisualRule, ...] = field(default=DEFAULT_RULES)
    min_confidence: float = 0.35

    def analyze(self, scene: SceneInput) -> VisualIntent:
        corpus = scene.text_corpus()

        scored: list[tuple[float, list[str], VisualRule]] = []
        for rule in self.rules:
            raw, matched = rule.score(corpus)
            if raw > 0:
                scored.append((raw, matched, rule))

        if not scored:
            return self._fallback(scene, corpus)

        # Highest score wins; rule order breaks ties (earlier = more specific).
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_matched, best_rule = scored[0]

        total = sum(item[0] for item in scored)
        confidence = _confidence(best_score, total)

        alternatives = [
            item[2].visual_type
            for item in scored[1:4]
            if item[2].visual_type != best_rule.visual_type
        ]
        complexity = self._complexity(scene, best_rule.visual_type, len(best_matched))
        duration = self._duration(scene, complexity)

        reasoning = (
            f"Matched {len(best_matched)} '{best_rule.visual_type.value}' "
            f"keyword(s): {', '.join(best_matched[:5])}. "
            f"Selected over {len(scored) - 1} competing type(s)."
        )

        return VisualIntent(
            scene_id=scene.scene_id,
            visual_type=best_rule.visual_type,
            confidence=confidence,
            reasoning=reasoning,
            suggested_renderer=best_rule.renderer,
            estimated_duration=duration,
            complexity=complexity,
            matched_keywords=best_matched,
            alternatives=alternatives,
        )

    def analyze_many(self, scenes: list[SceneInput]) -> list[VisualIntent]:
        return [self.analyze(s) for s in scenes]

    # ---- helpers --------------------------------------------------------- #

    def _fallback(self, scene: SceneInput, corpus: str) -> VisualIntent:
        """No keyword evidence — choose ILLUSTRATION or TEXT_ONLY."""
        has_text = bool(corpus.strip())
        visual_type = VisualType.ILLUSTRATION if has_text else VisualType.TEXT_ONLY
        renderer = (
            RendererType.OPENVINO if has_text else RendererType.SVG
        )
        complexity = Complexity.SIMPLE
        return VisualIntent(
            scene_id=scene.scene_id,
            visual_type=visual_type,
            confidence=self.min_confidence,
            reasoning=(
                "No specific visual keywords detected; defaulting to "
                f"{visual_type.value}."
            ),
            suggested_renderer=renderer,
            estimated_duration=self._duration(scene, complexity),
            complexity=complexity,
            matched_keywords=[],
            alternatives=[VisualType.TEXT_ONLY, VisualType.DIAGRAM],
        )

    @staticmethod
    def _complexity(
        scene: SceneInput, visual_type: VisualType, match_count: int
    ) -> Complexity:
        concept_count = len(scene.educational_concepts)
        word_count = len(scene.narration.split())

        heavy_types = {
            VisualType.MATHEMATICAL,
            VisualType.SCIENTIFIC,
            VisualType.MAP,
            VisualType.MIXED,
        }
        score = 0
        score += 2 if visual_type in heavy_types else 0
        score += 1 if concept_count >= 3 else 0
        score += 1 if word_count >= 60 else 0
        score += 1 if match_count >= 4 else 0

        if score >= 4:
            return Complexity.COMPLEX
        if score >= 2:
            return Complexity.MODERATE
        if score >= 1:
            return Complexity.SIMPLE
        return Complexity.TRIVIAL

    @staticmethod
    def _duration(scene: SceneInput, complexity: Complexity) -> float:
        if scene.duration_hint_sec and scene.duration_hint_sec > 0:
            return round(float(scene.duration_hint_sec), 2)
        base = {
            Complexity.TRIVIAL: 4.0,
            Complexity.SIMPLE: 6.0,
            Complexity.MODERATE: 9.0,
            Complexity.COMPLEX: 13.0,
        }[complexity]
        # Longer narration nudges duration up (reading time ~2.5 words/sec).
        words = len(scene.narration.split())
        reading = words / 2.5 if words else 0.0
        return round(max(base, reading), 2)


def _confidence(best: float, total: float) -> float:
    if total <= 0:
        return 0.35
    share = best / total
    # Map dominance (0.5..1.0 share) onto a 0.5..0.95 confidence band.
    conf = 0.5 + (share - 0.5) * 0.9
    return round(max(0.4, min(0.95, conf)), 3)
