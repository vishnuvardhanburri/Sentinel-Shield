"""
Sovereign Shield Enterprise — LLM Fingerprint Detector

Local prompt-injection and jailbreak classifier. It uses deterministic pattern
features so it can run in air-gapped environments before any model call.
"""
import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class InjectionFinding:
    label: str
    score: float
    evidence: str
    type: str = "PROMPT_INJECTION"
    confidence: str = "HIGH"

    def to_dict(self) -> Dict[str, object]:
        return {
            "type": self.type,
            "label": self.label,
            "confidence": self.confidence,
            "score": self.score,
            "entity": self.evidence,
            "snippet": self.evidence[:160],
            "start": 0,
            "end": 0,
        }


class PromptInjectionDetector:
    PATTERNS = {
        "DAN / Role Override": [
            r"(?i)\b(do anything now|dan mode|developer mode|jailbreak)\b",
            r"(?i)\byou are now (dan|free|unrestricted|uncensored)\b",
        ],
        "Instruction Hierarchy Attack": [
            r"(?i)\b(ignore|disregard|forget|override)\b.{0,80}\b(previous|system|developer|security|policy|instructions?)\b",
            r"(?i)\bnew instructions?:\b.{0,120}\b(do not|never|bypass|disable)\b",
        ],
        "Prompt Leakage Attempt": [
            r"(?i)\b(reveal|print|show|repeat|dump)\b.{0,80}\b(system prompt|hidden prompt|policy|instructions|rules)\b",
            r"(?i)\bwhat (are|were) your (system|developer) instructions\b",
        ],
        "Redaction Bypass": [
            r"(?i)\b(reconstruct|decode|deanonymize|de-anonymize|unmask)\b.{0,80}\b(redacted|masked|pii|token)\b",
            r"(?i)\breturn the original\b.{0,80}\b(aadhaar|pan|ssn|patient|secret)\b",
        ],
        "Adversarial Suffix": [
            r"(?i)(?:[!#@$%^&*_=+\-]{8,}|(?:\b[a-z]{1,3}\b\s*){18,})$",
            r"(?i)\b(base64|rot13|hex encoded|unicode smuggling|token smuggling)\b",
        ],
    }

    def scan(self, prompt: str) -> List[Dict[str, object]]:
        findings: List[InjectionFinding] = []
        for label, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, prompt)
                if match:
                    findings.append(InjectionFinding(label=label, score=self._score(label), evidence=match.group(0)))
                    break
        return [finding.to_dict() for finding in findings]

    def risk_score(self, findings: List[Dict[str, object]]) -> float:
        return min(10.0, round(sum(float(f.get("score", 0)) for f in findings), 2))

    @staticmethod
    def _score(label: str) -> float:
        if label in {"Instruction Hierarchy Attack", "Redaction Bypass"}:
            return 4.0
        if label == "Prompt Leakage Attempt":
            return 3.0
        return 2.5
