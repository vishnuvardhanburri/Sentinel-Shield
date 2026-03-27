"""
Sentinel Shield v2 — India-Specific PII Patterns
DPDP 2026 compliant regex patterns for Indian PII/sensitive data categories.

Covers: Aadhaar, PAN, UHID, Indian phone, Indian driving license,
        Voter ID, Passport, GST, UPI, Indian bank accounts.
"""
import re
from typing import List, Dict, Any

INDIA_PATTERNS: Dict[str, str] = {
    # ── Identity Documents ─────────────────────────────────────────────────
    "Aadhaar Number":         r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b",
    "PAN Card":               r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "Voter ID":               r"\b[A-Z]{3}[0-9]{7}\b",
    "Passport (India)":       r"\b[A-PR-WY][1-9]\d\s?\d{4}[1-9]\b",
    "Driving License (India)": r"\b[A-Z]{2}[0-9]{2}\s?[0-9]{4}[0-9]{7}\b",

    # ── Financial / Tax ────────────────────────────────────────────────────
    "GST Number":             r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b",
    "UPI ID":                 r"\b[a-zA-Z0-9.\-_]{2,49}@[a-zA-Z]{2,}\b",
    "IFSC Code":              r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    "Indian Bank Account":    r"\b[0-9]{9,18}\b",  # Generic; refine per bank
    "MICR Code":              r"\b[0-9]{9}\b",

    # ── Healthcare ─────────────────────────────────────────────────────────
    "UHID (Hospital ID)":     r"\bUHID[-\s]?[A-Z0-9]{6,12}\b",
    "NPI (Indian Doctor)":    r"\bMCI[-\s]?[0-9]{6}\b",
    "Ayushman Bharat ID":     r"\b\d{2}-\d{4}-\d{4}-\d{4}\b",

    # ── Contact ────────────────────────────────────────────────────────────
    "Indian Mobile":          r"\b(?:\+91|0)?[6-9]\d{9}\b",
    "Indian Landline":        r"\b0\d{2,4}[-\s]?\d{6,8}\b",
    "Indian Pincode":         r"\b[1-9][0-9]{5}\b",

    # ── Corporate ──────────────────────────────────────────────────────────
    "CIN (Company ID)":       r"\b[LUu]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b",
    "LLPIN":                  r"\bAAA[-]?\d{4}\b",

    # ── DPDP 2026 Sensitive Categories ────────────────────────────────────
    "Caste / Tribe Reference":     r"(?i)\b(scheduled caste|sc\b|scheduled tribe|st\b|OBC|backward class)\b",
    "Religious Identity":          r"(?i)\b(hindu|muslim|christian|sikh|jain|buddhist|parsi|jewish)\b",
    "Political Opinion":           r"(?i)\b(BJP|INC|congress|AAP|DMK|AIADMK|voter preference)\b",
    "Health Data (India-specific)": r"(?i)\b(HIV|AIDS|cancer|tuberculosis|TB|mental health|psychiatric)\b",
    "Biometric Reference":         r"(?i)\b(fingerprint|iris scan|retina|face recognition|biometric)\b",
}

# Redaction tag map for display
INDIA_REDACTION_TAGS: Dict[str, str] = {
    "Aadhaar Number":         "[REDACTED_AADHAAR]",
    "PAN Card":               "[REDACTED_PAN]",
    "Voter ID":               "[REDACTED_VOTER_ID]",
    "GST Number":             "[REDACTED_GST]",
    "UPI ID":                 "[REDACTED_UPI]",
    "Indian Mobile":          "[REDACTED_PHONE]",
    "UHID (Hospital ID)":     "[REDACTED_UHID]",
    "Ayushman Bharat ID":     "[REDACTED_ABHA]",
    "Caste / Tribe Reference": "[REDACTED_SENSITIVE_CATEGORY]",
    "Religious Identity":     "[REDACTED_SENSITIVE_CATEGORY]",
    "Health Data (India-specific)": "[REDACTED_HEALTH]",
    "Biometric Reference":    "[REDACTED_BIOMETRIC]",
}


class IndiaPIIScanner:
    """
    Scans text for Indian-specific PII using DPDP 2026 categories.
    Supplements the base EnterpriseScanner (Presidio).
    """

    def __init__(self):
        self._compiled = {
            label: re.compile(pattern)
            for label, pattern in INDIA_PATTERNS.items()
        }

    def scan(self, text: str) -> List[Dict[str, Any]]:
        """Returns list of findings matching Indian PII patterns."""
        findings = []
        for label, regex in self._compiled.items():
            for match in regex.finditer(text):
                findings.append({
                    "type": "INDIA_PII",
                    "label": label,
                    "confidence": "HIGH",
                    "entity": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "snippet": text[max(0, match.start()-20): match.end()+20],
                    "redaction_tag": INDIA_REDACTION_TAGS.get(label, "[REDACTED_INDIA_PII]"),
                    "dpdp_category": _dpdp_category(label),
                })
        return findings

    def redact(self, text: str) -> str:
        """Redact all Indian PII from text."""
        for label, regex in self._compiled.items():
            tag = INDIA_REDACTION_TAGS.get(label, "[REDACTED_INDIA_PII]")
            text = regex.sub(tag, text)
        return text


def _dpdp_category(label: str) -> str:
    """Map pattern label to DPDP 2026 data category."""
    sensitive = {
        "Aadhaar Number", "PAN Card", "Voter ID", "Passport (India)",
        "Driving License (India)", "Caste / Tribe Reference",
        "Religious Identity", "Political Opinion",
        "Health Data (India-specific)", "Biometric Reference",
        "UHID (Hospital ID)", "Ayushman Bharat ID"
    }
    return "SENSITIVE" if label in sensitive else "PERSONAL"
