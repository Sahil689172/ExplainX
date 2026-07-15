"""Deterministic topic-relevance checks for generated narration (no LLM)."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

# Lightweight English stopwords — keep domain words like "search", "sort", "day".
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "by",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "at",
        "from",
        "into",
        "about",
        "over",
        "under",
        "than",
        "then",
        "so",
        "if",
        "but",
        "not",
        "no",
        "nor",
        "too",
        "very",
        "can",
        "could",
        "should",
        "would",
        "will",
        "just",
        "also",
        "how",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "why",
        "we",
        "you",
        "they",
        "he",
        "she",
        "our",
        "your",
        "their",
        "my",
        "his",
        "her",
        "vs",
        "versus",
        "using",
        "use",
        "used",
        "via",
        "per",
        "etc",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class TopicVerificationResult:
    """Outcome of deterministic topic relevance scoring."""

    requested_topic: str
    detected_keywords: list[str]
    topic_relevance_score: float
    passed: bool
    keyword_coverage: float
    cosine_similarity: float
    phrase_match: bool
    reason: str = ""
    language: str = "en"
    skipped: bool = False


def _normalize_token(token: str) -> str:
    t = token.lower().strip("'")
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens with light normalization."""
    return [_normalize_token(m.group(0)) for m in _TOKEN_RE.finditer(text) if m.group(0)]


def extract_topic_keywords(topic: str) -> list[str]:
    """Distinctive content tokens from the requested topic (order preserved)."""
    seen: set[str] = set()
    keywords: list[str] = []
    for tok in tokenize(topic):
        if tok in _STOPWORDS or len(tok) < 2:
            continue
        if tok not in seen:
            seen.add(tok)
            keywords.append(tok)
    # Keep short technical tokens (e.g. "ai", "ml") if topic is only that.
    if not keywords:
        for tok in tokenize(topic):
            if tok not in seen and len(tok) >= 2:
                seen.add(tok)
                keywords.append(tok)
    return keywords


def _tf(tokens: list[str]) -> Counter[str]:
    return Counter(tokens)


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _tfidf_vectors(
    topic_tokens: list[str], narration_tokens: list[str]
) -> tuple[dict[str, float], dict[str, float]]:
    """Two-document TF-IDF over topic + narration token bags."""
    docs = [topic_tokens, narration_tokens]
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))
    n_docs = 2.0

    def vector(tokens: list[str]) -> dict[str, float]:
        tf = _tf(tokens)
        total = float(sum(tf.values())) or 1.0
        vec: dict[str, float] = {}
        for term, count in tf.items():
            idf = math.log((n_docs + 1.0) / (df[term] + 1.0)) + 1.0
            vec[term] = (count / total) * idf
        return vec

    return vector(topic_tokens), vector(narration_tokens)


class TopicVerificationService:
    """Verify narration is about the requested topic using deterministic NLP."""

    def __init__(self, *, threshold: float = 0.45) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        self.threshold = threshold

    def verify(
        self,
        requested_topic: str,
        narration: str,
        *,
        language: str = "en",
    ) -> TopicVerificationResult:
        topic = (requested_topic or "").strip()
        text = (narration or "").strip()
        keywords = extract_topic_keywords(topic)
        lang = (language or "en").strip().lower()
        if "-" in lang:
            lang = lang.split("-", 1)[0]
        lang = lang[:2] if len(lang) >= 2 else "en"

        # MVP: English keyword relevance does not apply to native multilingual output.
        if lang != "en":
            return TopicVerificationResult(
                requested_topic=topic,
                detected_keywords=list(keywords),
                topic_relevance_score=1.0,
                passed=True,
                keyword_coverage=1.0,
                cosine_similarity=1.0,
                phrase_match=False,
                reason="skipped_non_english",
                language=lang,
                skipped=True,
            )

        compact = re.sub(r"\s+", " ", text).strip().lower()
        if not topic or not text:
            return self._result(
                topic,
                keywords,
                score=0.0,
                coverage=0.0,
                cosine=0.0,
                phrase=False,
                passed=False,
                reason="empty_topic_or_narration",
                language=lang,
            )

        topic_norm = re.sub(r"\s+", " ", topic.lower()).strip()
        phrase_match = bool(topic_norm) and topic_norm in compact

        narration_tokens = [
            t for t in tokenize(text) if t not in _STOPWORDS and len(t) >= 2
        ]
        narration_set = set(narration_tokens)
        topic_tokens = tokenize(topic)

        matched = [k for k in keywords if k in narration_set]
        # Substring fallback for long scientific terms that may appear with slight affixes.
        if keywords and len(matched) < len(keywords):
            for k in keywords:
                if k in matched:
                    continue
                if len(k) >= 5 and any(k in tok or tok in k for tok in narration_set if len(tok) >= 4):
                    matched.append(k)
        coverage = (len(set(matched)) / len(keywords)) if keywords else (1.0 if phrase_match else 0.0)

        topic_vec, narr_vec = _tfidf_vectors(
            [t for t in topic_tokens if t not in _STOPWORDS or len(keywords) <= 1],
            narration_tokens,
        )
        # Restrict cosine to topic vocabulary so narration length does not wash out signal.
        topic_vocab = set(topic_vec)
        narr_focused = {k: v for k, v in narr_vec.items() if k in topic_vocab}
        cosine = _cosine(topic_vec, narr_focused) if narr_focused else 0.0

        # Weighted blend; phrase hit is a strong positive signal.
        score = (0.55 * coverage) + (0.35 * cosine) + (0.10 * (1.0 if phrase_match else 0.0))
        if phrase_match and coverage >= 0.5:
            score = max(score, 0.85)
        if coverage >= 1.0 and len(keywords) >= 1:
            score = max(score, 0.75)
        score = max(0.0, min(1.0, score))

        passed = score >= self.threshold and (coverage > 0.0 or phrase_match)
        reason = "ok" if passed else "below_threshold"
        return self._result(
            topic,
            keywords,
            score=score,
            coverage=coverage,
            cosine=cosine,
            phrase=phrase_match,
            passed=passed,
            reason=reason,
            language=lang,
        )

    @staticmethod
    def _result(
        topic: str,
        keywords: list[str],
        *,
        score: float,
        coverage: float,
        cosine: float,
        phrase: bool,
        passed: bool,
        reason: str,
        language: str = "en",
        skipped: bool = False,
    ) -> TopicVerificationResult:
        return TopicVerificationResult(
            requested_topic=topic,
            detected_keywords=list(keywords),
            topic_relevance_score=round(score, 4),
            passed=passed,
            keyword_coverage=round(coverage, 4),
            cosine_similarity=round(cosine, 4),
            phrase_match=phrase,
            reason=reason,
            language=language,
            skipped=skipped,
        )

    def log_result(self, result: TopicVerificationResult) -> None:
        """Print verification summary (and suitable for CI capture)."""
        if result.skipped:
            print("[Topic Validation]", flush=True)
            print("Skipped", flush=True)
            print("Reason:", flush=True)
            print("Non-English narration", flush=True)
            print("Language:", flush=True)
            print(result.language, flush=True)
            return

        status = "PASS" if result.passed else "FAIL"
        print("Requested Topic:")
        print(result.requested_topic)
        print("Detected Keywords:")
        print(", ".join(result.detected_keywords) if result.detected_keywords else "(none)")
        print("Similarity Score:")
        print(f"{result.topic_relevance_score:.4f}")
        print("Result:")
        print(status)
