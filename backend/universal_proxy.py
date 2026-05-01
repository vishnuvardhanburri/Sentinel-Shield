"""
Sentinel Shield Enterprise — Universal Proxy Hook

Standard app-agnostic interface for Slack, Teams, CRMs, and custom tools.
It returns raw-vs-protected text for localhost demonstrations and forwards the
same governed payload shape used by the AI gateway.
"""
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

try:
    from .redaction_middleware import IdentityMaskingProxy
except ImportError:
    from redaction_middleware import IdentityMaskingProxy


@dataclass(frozen=True)
class ProxyEnvelope:
    source_app: str
    actor: str
    raw_text: str
    protected_text: str
    auto_redact: bool
    sensitivity_score: float
    route: str
    policy_triggered: Optional[str]
    metadata: Dict[str, Any]


class UniversalProxy:
    def __init__(self, masking_proxy: IdentityMaskingProxy):
        self.masking_proxy = masking_proxy

    def inspect(
        self,
        text: str,
        source_app: str = "localhost",
        actor: str = "anonymous",
        auto_redact: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        governed = self.masking_proxy.govern(text, department=metadata.get("department") if metadata else None)
        envelope = ProxyEnvelope(
            source_app=source_app,
            actor=actor,
            raw_text=text,
            protected_text=governed.protected_prompt if auto_redact else text,
            auto_redact=auto_redact,
            sensitivity_score=governed.sensitivity_score,
            route=governed.route,
            policy_triggered=governed.policy_triggered,
            metadata={
                **(metadata or {}),
                "pseudonyms": governed.pseudonyms,
                "pseudonym_vault": governed.pseudonym_vault,
                "finding_labels": sorted({str(f.get("label", "UNKNOWN")) for f in governed.findings}),
            },
        )
        return asdict(envelope)
