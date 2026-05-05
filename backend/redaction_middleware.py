"""
Sovereign Shield Enterprise — Identity Masking Proxy

Stateless redaction middleware for LLM requests. It scans inbound prompts,
replaces PII with contextual pseudonyms, and returns routing metadata without
persisting the raw PII mapping in process memory.
"""
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from .security_scanner import EnterpriseScanner
    from .compliance.india_patterns import IndiaPIIScanner
except ImportError:
    from security_scanner import EnterpriseScanner
    from compliance.india_patterns import IndiaPIIScanner


@dataclass(frozen=True)
class GovernedPrompt:
    protected_prompt: str
    sensitivity_score: float
    findings: List[Dict[str, Any]]
    pseudonyms: List[str]
    pseudonym_vault: Dict[str, Dict[str, str]]
    route: str
    policy_triggered: Optional[str]


class IdentityMaskingProxy:
    """
    Stateless LLM request interceptor.

    The proxy returns a request-local pseudonym vault containing only hashes of
    original values. Callers can store that vault in encrypted audit storage if
    needed, but should never send it to a cloud model.
    """

    AIRGAP_THRESHOLD = 7.0

    def __init__(
        self,
        enterprise_scanner: Optional[EnterpriseScanner] = None,
        india_scanner: Optional[IndiaPIIScanner] = None,
    ):
        self.enterprise_scanner = enterprise_scanner or EnterpriseScanner()
        self.india_scanner = india_scanner or IndiaPIIScanner()

    def govern(self, prompt: str, department: Optional[str] = None) -> GovernedPrompt:
        us_findings = self.enterprise_scanner.scan_content(prompt)
        india_findings = self.india_scanner.scan(prompt)
        findings = self._dedupe_findings(us_findings + india_findings)
        sensitivity_score = self.calculate_sensitivity(findings)

        protected = self.enterprise_scanner.pseudonymize_content(prompt, findings)
        route = "airgap" if sensitivity_score > self.AIRGAP_THRESHOLD else "cloud_or_hybrid"
        triggered = self._policy_name(findings, sensitivity_score, department)

        return GovernedPrompt(
            protected_prompt=protected["text"],
            sensitivity_score=sensitivity_score,
            findings=findings,
            pseudonyms=protected["tokens"],
            pseudonym_vault=protected["mapping"],
            route=route,
            policy_triggered=triggered,
        )

    def calculate_sensitivity(self, findings: List[Dict[str, Any]]) -> float:
        score = 0.0
        for finding in findings:
            label = str(finding.get("label", "")).lower()
            ftype = str(finding.get("type", "")).upper()
            if ftype == "SECRET":
                score += 3.0
            elif any(term in label for term in ("aadhaar", "pan", "passport", "bank", "health", "biometric")):
                score += 2.0
            elif ftype in {"INDIA_PII", "PII"}:
                score += 1.25
            elif ftype == "CLASSIFICATION":
                score += 0.75
        return min(10.0, round(score, 2))

    def audit_payload(self, actor: str, governed: GovernedPrompt) -> Dict[str, Any]:
        return {
            "actor_hash": hashlib.sha256(actor.encode()).hexdigest(),
            "policy_triggered": governed.policy_triggered,
            "sensitivity_score": governed.sensitivity_score,
            "route": governed.route,
            "pseudonyms": governed.pseudonyms,
            "finding_labels": sorted({str(f.get("label", "UNKNOWN")) for f in governed.findings}),
        }

    @staticmethod
    def _dedupe_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen = set()
        for finding in sorted(findings, key=lambda f: (f.get("start", 0), -(f.get("end", 0)))):
            key = (finding.get("start"), finding.get("end"), finding.get("label"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(finding)
        return deduped

    @staticmethod
    def _policy_name(findings: List[Dict[str, Any]], sensitivity_score: float, department: Optional[str]) -> Optional[str]:
        if not findings:
            return None
        scope = department or "GLOBAL"
        if sensitivity_score > IdentityMaskingProxy.AIRGAP_THRESHOLD:
            return f"{scope}:FORCE_AIRGAP_HIGH_SENSITIVITY"
        return f"{scope}:PSEUDONYMIZE_BEFORE_LLM"
