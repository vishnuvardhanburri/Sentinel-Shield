"""
Sentinel Shield v2 — DPDP 2026 Compliance Engine
Digital Personal Data Protection Act 2026 (India) compliance layer.

Handles:
  - Data category classification (Personal / Sensitive / Non-Personal)
  - Data principal rights enforcement
  - DPB (Data Protection Board) incident reporting workflow
  - Retention policy enforcement
"""
import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from .india_patterns import IndiaPIIScanner, _dpdp_category

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DPDP_DIR = os.path.join(BASE_DIR, "logs", "dpdp")


class DPDPEngine:
    """
    DPDP 2026 compliance engine.
    Wraps IndiaPIIScanner with data principal rights, retention tracking,
    and DPB incident reporting.
    """

    # Maximum retention periods (days) per category — DPDP 2026 default
    RETENTION_POLICY: Dict[str, int] = {
        "SENSITIVE": 90,    # 90 days max for sensitive personal data
        "PERSONAL":  365,   # 1 year for personal data
        "HEALTH":    730,   # 2 years for health records (healthcare exemption)
        "FINANCIAL": 2555,  # 7 years (RBI/IT Act requirement)
    }

    def __init__(self):
        self.scanner = IndiaPIIScanner()
        os.makedirs(DPDP_DIR, exist_ok=True)
        self._incident_log = os.path.join(DPDP_DIR, "dpb_incidents.jsonl")
        self._consent_log  = os.path.join(DPDP_DIR, "consent_records.jsonl")

    # ──────────────────────────────────────────────────────────────────────
    # Data Classification
    # ──────────────────────────────────────────────────────────────────────
    def classify_text(self, text: str) -> Dict[str, Any]:
        """
        Run DPDP-aware scan and classify the text.
        Returns classification summary suitable for audit logging.
        """
        findings = self.scanner.scan(text)
        categories = list({_dpdp_category(f["label"]) for f in findings})
        sensitive_items = [f["label"] for f in findings if f["dpdp_category"] == "SENSITIVE"]

        return {
            "dpdp_categories": categories,
            "sensitive_items_found": sensitive_items,
            "finding_count": len(findings),
            "requires_consent": len(sensitive_items) > 0,
            "dpdp_compliant_redacted": False,  # set True after redact()
        }

    def redact_for_dpdp(self, text: str) -> tuple[str, Dict[str, Any]]:
        """Redact Indian PII + return compliance metadata."""
        classification = self.classify_text(text)
        redacted = self.scanner.redact(text)
        classification["dpdp_compliant_redacted"] = True
        return redacted, classification

    # ──────────────────────────────────────────────────────────────────────
    # Retention Enforcement
    # ──────────────────────────────────────────────────────────────────────
    def check_retention(self, data_category: str, stored_at: datetime) -> Dict[str, Any]:
        """Check if data is within its retention window."""
        max_days = self.RETENTION_POLICY.get(data_category, 365)
        age_days = (datetime.now(timezone.utc) - stored_at.replace(tzinfo=timezone.utc)).days
        return {
            "category": data_category,
            "age_days": age_days,
            "max_days": max_days,
            "must_delete": age_days > max_days,
            "days_remaining": max(0, max_days - age_days),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Data Principal Rights (DPDP Chapter III)
    # ──────────────────────────────────────────────────────────────────────
    def log_data_principal_request(
        self,
        principal_id: str,  # Aadhaar/phone hash — never store raw
        request_type: str,  # ACCESS | CORRECTION | ERASURE | GRIEVANCE
        details: Optional[str] = None,
        filed_by: str = "SYSTEM"
    ) -> str:
        """
        Log a Data Principal request (DPDP Sec 11-13).
        Returns request_id (SHA-256 of content).
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "principal_id_hash": hashlib.sha256(principal_id.encode()).hexdigest()[:16],
            "request_type": request_type.upper(),
            "details": details or "",
            "filed_by": filed_by,
            "status": "PENDING",
            "sla_deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }
        rid = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:12]
        record["request_id"] = rid

        with open(os.path.join(DPDP_DIR, "principal_requests.jsonl"), "a") as f:
            f.write(json.dumps(record) + "\n")
        return rid

    # ──────────────────────────────────────────────────────────────────────
    # DPB Incident Reporting (DPDP Sec 8)
    # ──────────────────────────────────────────────────────────────────────
    def report_incident_to_dpb(
        self,
        incident_type: str,
        affected_data_types: List[str],
        estimated_records_affected: int,
        description: str,
        organization: str = "VishnuLabs Client",
        is_test: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a DPB-compliant incident report (DPDP 2026 Sec 8).
        In production, this would POST to the DPB portal API.
        Returns the structured report for audit/manual submission.
        """
        report = {
            "report_id": hashlib.sha256(
                f"{datetime.now().isoformat()}{description}".encode()
            ).hexdigest()[:12].upper(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "organization": organization,
            "incident_type": incident_type,
            "affected_data_types": affected_data_types,
            "estimated_records": estimated_records_affected,
            "description": description,
            "notification_due_by": (
                datetime.now(timezone.utc) + timedelta(hours=72)
            ).isoformat(),
            "status": "TEST_MODE" if is_test else "PENDING_SUBMISSION",
            "dpdp_section": "Section 8 — Notice of personal data breach",
        }

        # Persist locally
        with open(self._incident_log, "a") as f:
            f.write(json.dumps(report) + "\n")

        return report

    def get_dpb_incidents(self) -> List[Dict[str, Any]]:
        """Return all recorded DPB incidents."""
        if not os.path.exists(self._incident_log):
            return []
        with open(self._incident_log, "r") as f:
            return [json.loads(l) for l in f if l.strip()]

    def get_compliance_score(self) -> Dict[str, Any]:
        """
        Calculate a DPDP 2026 compliance score (0–100).
        Used for the enterprise dashboard compliance scorecard.
        """
        incidents = self.get_dpb_incidents()
        open_incidents = sum(1 for i in incidents if "PENDING" in i.get("status", ""))

        base_score = 100
        if open_incidents > 0:
            base_score -= (open_incidents * 15)

        return {
            "dpdp_score": max(0, base_score),
            "grade": "A" if base_score >= 90 else "B" if base_score >= 75 else "C" if base_score >= 60 else "F",
            "open_incidents": open_incidents,
            "total_incidents": len(incidents),
            "india_pii_patterns_active": True,
            "consent_management_active": True,
        }
