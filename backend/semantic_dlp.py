"""
Sovereign Shield Enterprise — Semantic DLP Hook

Detects sensitive business context that does not have stable regex structure:
M&A activity, trade secrets, unreleased financials, source code secrets, and
proprietary formulas. Uses a local embedding strategy with no network calls.
"""
import hashlib
import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class SemanticFinding:
    label: str
    score: float
    matched_concept: str
    type: str = "SEMANTIC_DLP"
    confidence: str = "MEDIUM"

    def to_dict(self) -> Dict[str, object]:
        return {
            "type": self.type,
            "label": self.label,
            "confidence": self.confidence,
            "score": self.score,
            "matched_concept": self.matched_concept,
            "start": 0,
            "end": 0,
            "entity": self.matched_concept,
            "snippet": self.matched_concept,
        }


class LocalHashEmbeddingModel:
    """
    Tiny deterministic embedding model.

    It is intentionally local and dependency-free. If you later add
    sentence-transformers, this class can be swapped without changing the DLP API.
    """

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def encode(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        for token in self._tokens(text):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    @staticmethod
    def _tokens(text: str) -> Iterable[str]:
        words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_\-]{1,}", text.lower())
        for word in words:
            yield word
        for left, right in zip(words, words[1:]):
            yield f"{left}_{right}"


class SemanticDLP:
    SENSITIVE_CONCEPTS: Dict[str, List[str]] = {
        "Trade Secret": [
            "proprietary chemical formula catalyst synthesis compound ratio",
            "confidential manufacturing process yield optimization recipe",
            "source code signing key private implementation exploit mitigation",
        ],
        "M&A / Insider Information": [
            "secret merger acquisition target due diligence valuation term sheet",
            "unannounced earnings guidance revenue forecast board confidential",
            "material non public information investor disclosure blackout",
        ],
        "Strategic Customer Data": [
            "confidential customer list renewal pricing discount contract negotiation",
            "enterprise account churn risk private pipeline competitor displacement",
        ],
        "Security Architecture": [
            "zero day vulnerability internal network diagram firewall bypass",
            "production credentials admin token incident response containment plan",
        ],
        "Regulated Health Context": [
            "patient diagnosis treatment plan clinical trial adverse event",
            "genetic marker fertility treatment embryo donor medical history",
        ],
    }

    def __init__(self, threshold: float = 0.34, embedding_model: LocalHashEmbeddingModel | None = None):
        self.threshold = threshold
        self.embedding_model = embedding_model or LocalHashEmbeddingModel()
        self._concept_vectors = {
            label: [(concept, self.embedding_model.encode(concept)) for concept in concepts]
            for label, concepts in self.SENSITIVE_CONCEPTS.items()
        }

    def scan(self, text: str) -> List[Dict[str, object]]:
        prompt_vector = self.embedding_model.encode(text)
        findings: List[SemanticFinding] = []

        for label, concepts in self._concept_vectors.items():
            best_score = 0.0
            best_concept = ""
            for concept, vector in concepts:
                score = self._cosine(prompt_vector, vector)
                if score > best_score:
                    best_score = score
                    best_concept = concept

            keyword_boost = self._keyword_boost(text, best_concept)
            final_score = min(1.0, round(best_score + keyword_boost, 3))
            if final_score >= self.threshold:
                confidence = "HIGH" if final_score >= 0.55 else "MEDIUM"
                findings.append(SemanticFinding(label, final_score, best_concept, confidence=confidence))

        return [finding.to_dict() for finding in sorted(findings, key=lambda f: f.score, reverse=True)]

    def sensitivity_score(self, findings: List[Dict[str, object]]) -> float:
        if not findings:
            return 0.0
        score = sum(float(f.get("score", 0.0)) * 4.0 for f in findings)
        return min(10.0, round(score, 2))

    @staticmethod
    def _cosine(left: List[float], right: List[float]) -> float:
        return sum(a * b for a, b in zip(left, right))

    @staticmethod
    def _keyword_boost(text: str, concept: str) -> float:
        text_tokens = set(LocalHashEmbeddingModel._tokens(text))
        concept_tokens = set(LocalHashEmbeddingModel._tokens(concept))
        if not concept_tokens:
            return 0.0
        overlap = len(text_tokens & concept_tokens) / len(concept_tokens)
        return min(0.3, overlap * 0.45)
