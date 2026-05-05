"""
Sovereign Shield — Hallucination & Jailbreak Guardian

Local-first validator for advanced adversarial intent. The default path is
deterministic and air-gapped. If a buyer enables a local Ollama judge model, the
same interface can add model-based adjudication without sending data to a cloud
LLM.
"""
import base64
import binascii
import os
import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class GuardianVerdict:
    blocked: bool
    score: float
    labels: List[str]
    evidence: List[str]
    judge_mode: str = "deterministic-local"

    def to_dict(self) -> Dict[str, object]:
        return {
            "blocked": self.blocked,
            "score": self.score,
            "labels": self.labels,
            "evidence": self.evidence,
            "judge_mode": self.judge_mode,
        }


class HallucinationJailbreakGuardian:
    """
    Detects adversarial intent before the gateway routes a prompt.

    Sellable proof: this scans for Base64/encoding bypass, roleplay jailbreaks,
    policy extraction, data reconstruction, and suffix/token-smuggling patterns.
    """

    ROLEPLAY_PATTERNS = [
        r"(?i)\bpretend you are\b.{0,80}\b(unfiltered|evil|developer|admin|auditor|root)\b",
        r"(?i)\broleplay\b.{0,120}\b(ignore|bypass|disable|override|leak)\b",
        r"(?i)\bfor educational purposes\b.{0,120}\b(reveal|dump|bypass|exfiltrate)\b",
    ]
    EXFIL_PATTERNS = [
        r"(?i)\b(print|dump|reveal|exfiltrate|show)\b.{0,120}\b(secret|policy|system prompt|hidden rules|token|key)\b",
        r"(?i)\bdecode\b.{0,120}\b(masked|redacted|aadhaar|pan|ssn|patient)\b",
        r"(?i)\breturn\b.{0,80}\b(original|unmasked|raw)\b.{0,80}\b(value|identifier|pii|secret)\b",
    ]
    SUFFIX_PATTERNS = [
        r"(?i)(?:\b[a-z]{1,3}\b[\s,.;:/\\|]*){24,}$",
        r"(?i)[^\w\s]{10,}.{0,60}$",
        r"(?i)\b(token smuggling|unicode smuggling|adversarial suffix|gradient suffix)\b",
    ]

    def __init__(self, block_threshold: float = 7.0):
        self.block_threshold = block_threshold

    def validate(self, prompt: str) -> Dict[str, object]:
        score = 0.0
        labels: List[str] = []
        evidence: List[str] = []

        for label, patterns, weight in [
            ("Roleplay Jailbreak", self.ROLEPLAY_PATTERNS, 3.5),
            ("Data Exfiltration Intent", self.EXFIL_PATTERNS, 4.0),
            ("Adversarial Suffix", self.SUFFIX_PATTERNS, 3.0),
        ]:
            hit = self._first_match(prompt, patterns)
            if hit:
                labels.append(label)
                evidence.append(hit[:180])
                score += weight

        encoded = self._encoded_payload(prompt)
        if encoded:
            labels.append("Encoded Payload Bypass")
            evidence.append(encoded[:180])
            score += 4.0

        if os.getenv("LOCAL_JUDGE_ENABLED", "false").lower() == "true":
            judge = self._local_judge(prompt)
            if judge.get("blocked"):
                labels.extend(judge.get("labels", []))
                evidence.extend(judge.get("evidence", []))
                score += float(judge.get("score", 0.0))

        score = min(10.0, round(score, 2))
        verdict = GuardianVerdict(
            blocked=score >= self.block_threshold,
            score=score,
            labels=sorted(set(labels)),
            evidence=evidence,
            judge_mode="deterministic+local-judge" if os.getenv("LOCAL_JUDGE_ENABLED", "false").lower() == "true" else "deterministic-local",
        )
        return verdict.to_dict()

    @staticmethod
    def _first_match(text: str, patterns: List[str]) -> str:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""

    @staticmethod
    def _encoded_payload(text: str) -> str:
        candidates = re.findall(r"\b[A-Za-z0-9+/]{28,}={0,2}\b", text)
        for candidate in candidates[:5]:
            try:
                decoded = base64.b64decode(candidate + "==", validate=False).decode("utf-8", "ignore")
            except (binascii.Error, ValueError):
                continue
            if re.search(r"(?i)(ignore|bypass|reveal|secret|system prompt|policy|aadhaar|pan)", decoded):
                return f"base64:{decoded}"
        return ""

    @staticmethod
    def _local_judge(prompt: str) -> Dict[str, object]:
        """
        Placeholder for buyer-owned local judge model.

        Kept deterministic by default so acquisition demos do not depend on a
        model download. Buyers can wire this to Ollama in production.
        """
        lowered = prompt.lower()
        if "you are now root" in lowered or "disable all safety" in lowered:
            return {"blocked": True, "score": 3.0, "labels": ["Local Judge Jailbreak"], "evidence": ["root/safety override intent"]}
        return {"blocked": False, "score": 0.0, "labels": [], "evidence": []}

