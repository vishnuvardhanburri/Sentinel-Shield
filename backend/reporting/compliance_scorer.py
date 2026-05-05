"""
Sovereign Shield v2 — Compliance Scorer
Calculates a unified compliance score (0–100) across HIPAA, DPDP, and GDPR dimensions.
Used by the enterprise dashboard and board-ready PDF report.
"""
from typing import Dict, Any, List


class ComplianceScorer:
    """
    Multi-framework compliance scoring.
    Outputs a dashboard-ready scorecard with per-framework grades.
    """

    FRAMEWORKS = ["HIPAA", "DPDP_2026", "GDPR_LITE", "ISO_27001_LITE"]

    def score(
        self,
        audit_stats: Dict[str, Any],
        dpdp_score: Dict[str, Any],
        chain_integrity: bool,
        active_policies: int,
        open_incidents: int = 0,
        mfa_enabled_pct: float = 0.0,
        is_global: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculate compliance scores per framework.

        Args:
            audit_stats: From AuditLedger.get_summary_stats()
            dpdp_score: From DPDPEngine.get_compliance_score()
            chain_integrity: Whether audit chain is intact
            active_policies: Number of active YAML policies loaded
            open_incidents: Unresolved security incidents
            mfa_enabled_pct: % of users with MFA enabled (0–100)
        """
        scores = {}

        # ── HIPAA ──────────────────────────────────────────────────────────
        hipaa = 100
        if not chain_integrity:
            hipaa -= 40  # Tampered audit log is a critical HIPAA failure
        if audit_stats.get("total_redactions", 0) == 0 and audit_stats.get("total_events", 0) > 5:
            hipaa -= 15  # No redactions despite activity — suspicious
        if open_incidents > 0:
            hipaa -= (open_incidents * 10)
        if mfa_enabled_pct < 80:
            hipaa -= 10
        scores["HIPAA"] = max(0, hipaa)

        # ── DPDP 2026 ─────────────────────────────────────────────────────
        scores["DPDP_2026"] = dpdp_score.get("dpdp_score", 100)

        # ── GDPR Lite ─────────────────────────────────────────────────────
        gdpr = 100
        if not chain_integrity:
            gdpr -= 35
        if active_policies < 1:
            gdpr -= 20  # No policies = no accountability
        if open_incidents > 0:
            gdpr -= (open_incidents * 8)
        scores["GDPR_LITE"] = max(0, gdpr)

        # ── ISO 27001 Lite ────────────────────────────────────────────────
        iso = 100
        if not chain_integrity:
            iso -= 30
        if active_policies < 3:
            iso -= 15
        if mfa_enabled_pct < 50:
            iso -= 20
        if open_incidents > 2:
            iso -= 25
        scores["ISO_27001_LITE"] = max(0, iso)

        # ── Composite ─────────────────────────────────────────────────────
        if is_global:
            # Global focus: Weigh HIPAA/GDPR/ISO higher than DPDP
            composite = round(
                (scores["HIPAA"] * 0.35) + 
                (scores["GDPR_LITE"] * 0.35) + 
                (scores["ISO_27001_LITE"] * 0.20) + 
                (scores["DPDP_2026"] * 0.10)
            )
        else:
            composite = round(sum(scores.values()) / len(scores))
            
        grade = "A" if composite >= 90 else "B" if composite >= 75 else "C" if composite >= 60 else "D" if composite >= 40 else "F"

        return {
            "is_global_audit": is_global,
            "composite_score": composite,
            "grade": grade,
            "framework_scores": scores,
            "framework_grades": {
                k: "A" if v >= 90 else "B" if v >= 75 else "C" if v >= 60 else "F"
                for k, v in scores.items()
            },
            "chain_integrity": chain_integrity,
            "open_incidents": open_incidents,
            "active_policies": active_policies,
            "zero_incident_badge": open_incidents == 0 and chain_integrity,
            "total_redactions": audit_stats.get("total_redactions", 0),
            "high_risk_blocked": audit_stats.get("high_risk_events", 0),
        }
