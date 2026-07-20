"""Asset Diversity Manager — prevent the same visual being reused (Task 3).

Educational videos look like slideshows when every scene shows the same image.
This manager tracks the perceptual fingerprint of each accepted asset and
rejects new assets that are too visually similar (default: > 80% similarity).

The similarity metric is a 64-bit average hash (aHash) compared with Hamming
distance — no third-party dependencies beyond Pillow (already required).

    similarity = 1 - (hamming_distance / 64)

Typical use::

    dm = AssetDiversityManager(similarity_threshold=0.80)
    chosen = dm.select(candidate_paths)      # first sufficiently-different asset
    dm.register(chosen)                       # remember it for later scenes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

_HASH_SIDE = 8  # 8x8 => 64-bit hash
_HASH_BITS = _HASH_SIDE * _HASH_SIDE


def average_hash(path: str | Path) -> int:
    """Compute a 64-bit perceptual average-hash for an image."""
    with Image.open(path) as img:
        small = img.convert("L").resize((_HASH_SIDE, _HASH_SIDE), Image.BILINEAR)
        pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for i, px in enumerate(pixels):
        if px >= avg:
            bits |= 1 << i
    return bits


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def similarity(a: int, b: int) -> float:
    """Fraction of matching bits in [0.0, 1.0]. 1.0 == identical."""
    return 1.0 - hamming_distance(a, b) / _HASH_BITS


@dataclass(slots=True)
class DiversityDecision:
    """Outcome of evaluating a candidate against previously used assets."""

    path: str
    accepted: bool
    max_similarity: float
    most_similar_to: str | None = None
    reason: str = ""


@dataclass(slots=True)
class RejectedAsset:
    path: str
    similarity: float
    reason: str


@dataclass(slots=True)
class SelectionAudit:
    """Full audit trail for one selection pass."""

    chosen: str | None
    rejected: list[RejectedAsset]
    reason: str


@dataclass(slots=True)
class AssetDiversityManager:
    """Tracks used assets and enforces a minimum visual difference.

    Parameters
    ----------
    similarity_threshold:
        Assets whose similarity to any already-used asset is strictly greater
        than this value are considered duplicates and rejected. Default 0.80
        (i.e. reject if > 80% similar).
    """

    similarity_threshold: float = 0.80
    _hashes: dict[str, int] = field(default_factory=dict)
    _order: list[str] = field(default_factory=list)
    _last_selected: str | None = field(default=None, repr=False)

    # ---- queries --------------------------------------------------------- #

    def evaluate(self, path: str | Path) -> DiversityDecision:
        """Score a candidate against everything registered so far."""
        key = str(path)
        try:
            h = average_hash(key)
        except (OSError, ValueError):
            return DiversityDecision(
                path=key,
                accepted=False,
                max_similarity=1.0,
                reason="unreadable file",
            )

        max_sim = 0.0
        nearest: str | None = None
        for used_path, used_hash in self._hashes.items():
            sim = similarity(h, used_hash)
            if sim > max_sim:
                max_sim = sim
                nearest = used_path

        accepted = max_sim <= self.similarity_threshold
        reason = "accepted"
        if not accepted:
            reason = f"similarity {max_sim:.2%} > threshold {self.similarity_threshold:.0%}"
            if nearest:
                reason += f" (nearest: {Path(nearest).name})"
        elif key == self._last_selected:
            reason = "same as previous scene (only candidate)"

        return DiversityDecision(
            path=key,
            accepted=accepted,
            max_similarity=round(max_sim, 4),
            most_similar_to=nearest,
            reason=reason,
        )

    def is_diverse(self, path: str | Path) -> bool:
        return self.evaluate(path).accepted

    # ---- selection ------------------------------------------------------- #

    def _prepare_candidates(self, candidates: list[str | Path]) -> list[str]:
        """Deduplicate and drop the previous selection when alternatives exist."""
        seen: set[str] = set()
        unique: list[str] = []
        for cand in candidates:
            key = str(cand)
            if key not in seen:
                seen.add(key)
                unique.append(key)
        if self._last_selected and len(unique) > 1:
            unique = [c for c in unique if c != self._last_selected]
        return unique

    def select_with_audit(self, candidates: list[str | Path]) -> SelectionAudit:
        """Pick an asset and return a full audit (chosen, rejected, scores, reasons)."""
        pool = self._prepare_candidates(candidates)
        if not pool:
            return SelectionAudit(chosen=None, rejected=[], reason="no candidates")

        rejected: list[RejectedAsset] = []
        accepted_pool: list[tuple[str, DiversityDecision]] = []

        for cand in pool:
            decision = self.evaluate(cand)
            if decision.accepted:
                accepted_pool.append((str(cand), decision))
            else:
                rejected.append(
                    RejectedAsset(
                        path=str(cand),
                        similarity=decision.max_similarity,
                        reason=decision.reason,
                    )
                )

        if accepted_pool:
            chosen, decision = accepted_pool[0]
            return SelectionAudit(
                chosen=chosen,
                rejected=rejected,
                reason=decision.reason,
            )

        # Every candidate too similar — pick least similar, avoiding consecutive
        # duplicate when more than one option exists.
        scored = [(self.evaluate(c), str(c)) for c in pool]
        scored.sort(key=lambda x: x[0].max_similarity)
        for decision, path in scored:
            if self._last_selected and path == self._last_selected and len(scored) > 1:
                rejected.append(
                    RejectedAsset(
                        path=path,
                        similarity=decision.max_similarity,
                        reason="consecutive duplicate avoided",
                    )
                )
                continue
            return SelectionAudit(
                chosen=path,
                rejected=rejected,
                reason=f"fallback — least similar ({decision.max_similarity:.2%})",
            )

        chosen = scored[0][1] if scored else None
        return SelectionAudit(
            chosen=chosen,
            rejected=rejected,
            reason="only one candidate available",
        )

    def select(self, candidates: list[str | Path]) -> str | None:
        """Return the first candidate that is different enough from used assets."""
        return self.select_with_audit(candidates).chosen

    # ---- mutation -------------------------------------------------------- #

    def register(self, path: str | Path) -> bool:
        """Record an asset as used. Returns False if it was unreadable."""
        key = str(path)
        if key in self._hashes:
            return True
        try:
            self._hashes[key] = average_hash(key)
        except (OSError, ValueError):
            return False
        self._order.append(key)
        return True

    def select_and_register(self, candidates: list[str | Path]) -> SelectionAudit:
        audit = self.select_with_audit(candidates)
        if audit.chosen is not None:
            self.register(audit.chosen)
            self._last_selected = audit.chosen
        return audit

    @property
    def last_selected(self) -> str | None:
        return self._last_selected

    # ---- introspection --------------------------------------------------- #

    @property
    def used(self) -> list[str]:
        return list(self._order)

    def __len__(self) -> int:
        return len(self._hashes)
