#!/usr/bin/env python3
"""Seed safe synthetic demo events for Sentinel Shield buyer walkthroughs."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from audit.ledger import audit_ledger  # noqa: E402
from risk_engine import oracle_risk_engine  # noqa: E402


def main() -> int:
    events = [
        {
            "action": "DEMO_PII_MASKED",
            "user_id": "demo.ciso@buyer.local",
            "policy_triggered": "INDIA_PII_PSEUDONYMIZED",
            "risk_score": 6.4,
            "redactions_applied": ["[Aadhaar_1]", "[PAN_1]"],
        },
        {
            "action": "DEMO_PROMPT_BLOCKED",
            "user_id": "demo.redteam@buyer.local",
            "policy_triggered": "LLM_FINGERPRINT_PROMPT_INJECTION",
            "risk_score": 9.1,
            "redactions_applied": [],
        },
        {
            "action": "DEMO_EVIDENCE_READY",
            "user_id": "demo.audit@buyer.local",
            "policy_triggered": "DPDP_2026_EVIDENCE_EXPORT",
            "risk_score": 2.0,
            "redactions_applied": [],
        },
    ]
    for event in events:
        audit_ledger.log(
            action=event["action"],
            user_id=event["user_id"],
            user_role="SUPER_ADMIN",
            department="GLOBAL_SECURITY",
            prompt_text="Synthetic buyer demo prompt with fake identifiers only.",
            redactions_applied=event["redactions_applied"],
            policy_triggered=event["policy_triggered"],
            risk_score=event["risk_score"],
            metadata={"synthetic_demo": True},
        )

    for _ in range(4):
        oracle_risk_engine.record_interception(
            actor_id="demo-risk-actor",
            findings=[{"type": "PII", "label": "Aadhaar Number"}],
            sensitivity_score=8.5,
            policy_triggered="DEMO_QUARANTINE",
        )

    print("Seeded safe synthetic buyer demo data.")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("DEPLOYMENT_MODE", "airgap")
    raise SystemExit(main())
