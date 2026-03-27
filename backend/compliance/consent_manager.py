"""
Sentinel Shield v2 — Consent Management (DPDP 2026 Sec 6-7)
Records, validates, and manages Data Principal consent for all data processing activities.
"""
import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CONSENT_FILE = os.path.join(BASE_DIR, "logs", "dpdp", "consent_records.jsonl")


class ConsentManager:
    """
    DPDP 2026-compliant consent management.
    Sec 6: Consent must be free, specific, informed, unconditional, and unambiguous.
    Sec 7: Processing lawful only if consent given or legitimate use.
    """

    CONSENT_PURPOSES = {
        "HR_PROCESSING":        "Processing employee personal data for HR operations",
        "PATIENT_CARE":         "Processing patient health data for medical care",
        "LEGAL_REPRESENTATION": "Processing client data for legal services",
        "MARKETING":            "Sending promotional communications",
        "ANALYTICS":            "Aggregated analytics and reporting",
        "THIRD_PARTY_SHARE":    "Sharing data with authorized third parties",
        "BACKGROUND_CHECK":     "Employee background verification",
    }

    def __init__(self):
        os.makedirs(os.path.dirname(CONSENT_FILE), exist_ok=True)

    def _load_all(self) -> List[Dict[str, Any]]:
        if not os.path.exists(CONSENT_FILE):
            return []
        with open(CONSENT_FILE, "r") as f:
            return [json.loads(l) for l in f if l.strip()]

    def record_consent(
        self,
        principal_id: str,       # hashed before storage
        purpose: str,
        granted: bool,
        channel: str = "API",    # WEB | API | PAPER | VERBAL
        expires_days: int = 365,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Record a consent decision. Returns consent_id.
        principal_id is SHA-256 hashed before storage (never raw Aadhaar/phone).
        """
        consent_id = hashlib.sha256(
            f"{principal_id}{purpose}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        record = {
            "consent_id": consent_id,
            "principal_hash": hashlib.sha256(principal_id.encode()).hexdigest()[:20],
            "purpose": purpose,
            "purpose_description": self.CONSENT_PURPOSES.get(purpose, purpose),
            "granted": granted,
            "channel": channel,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat(),
            "revoked": False,
            "metadata": metadata or {},
        }

        with open(CONSENT_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")

        return consent_id

    def check_consent(self, principal_id: str, purpose: str) -> Dict[str, Any]:
        """
        Check if valid (non-expired, non-revoked) consent exists.
        Returns {has_consent, consent_id, expires_at, reason}.
        """
        p_hash = hashlib.sha256(principal_id.encode()).hexdigest()[:20]
        now = datetime.now(timezone.utc)
        records = self._load_all()

        for r in reversed(records):
            if r.get("principal_hash") == p_hash and r.get("purpose") == purpose:
                if r.get("revoked"):
                    return {"has_consent": False, "reason": "REVOKED", "consent_id": r["consent_id"]}
                exp = datetime.fromisoformat(r["expires_at"])
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now > exp:
                    return {"has_consent": False, "reason": "EXPIRED", "consent_id": r["consent_id"]}
                if r.get("granted"):
                    return {
                        "has_consent": True,
                        "reason": "VALID",
                        "consent_id": r["consent_id"],
                        "expires_at": r["expires_at"],
                    }

        return {"has_consent": False, "reason": "NOT_FOUND", "consent_id": None}

    def revoke_consent(self, consent_id: str, reason: str = "DATA_PRINCIPAL_REQUEST") -> bool:
        """Revoke a previously granted consent record."""
        records = self._load_all()
        found = False
        with open(CONSENT_FILE, "w") as f:
            for r in records:
                if r.get("consent_id") == consent_id:
                    r["revoked"] = True
                    r["revoked_at"] = datetime.now(timezone.utc).isoformat()
                    r["revoke_reason"] = reason
                    found = True
                f.write(json.dumps(r) + "\n")
        return found

    def get_all_for_principal(self, principal_id: str) -> List[Dict[str, Any]]:
        """Return all consent records for a principal (DPDP Sec 11 — right to access)."""
        p_hash = hashlib.sha256(principal_id.encode()).hexdigest()[:20]
        return [r for r in self._load_all() if r.get("principal_hash") == p_hash]
