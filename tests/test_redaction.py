"""
Sentinel Shield v2 — Redaction Engine Tests
Tests the core PII redaction pipeline: Presidio + India patterns.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

import pytest
from security_scanner import EnterpriseScanner
from compliance.india_patterns import IndiaPIIScanner


class TestEnterpriseScanner:
    @pytest.fixture
    def scanner(self):
        return EnterpriseScanner()

    def test_ssn_detected(self, scanner):
        text = "Patient SSN is 123-45-6789, please process."
        findings = scanner.scan_content(text)
        labels = [f["label"] for f in findings]
        assert "PII (SSN)" in labels

    def test_aws_token_detected(self, scanner):
        text = "Access key: AKIAIOSFODNN7EXAMPLE should be rotated."
        findings = scanner.scan_content(text)
        labels = [f["label"] for f in findings]
        assert "AWS Token" in labels

    def test_credit_card_detected(self, scanner):
        text = "Card number 4532015112830366 was used."
        findings = scanner.scan_content(text)
        labels = [f["label"] for f in findings]
        assert "Credit Card" in labels

    def test_redaction_replaces_ssn(self, scanner):
        text = "SSN: 123-45-6789 belongs to John."
        findings = scanner.scan_content(text)
        redacted = scanner.redact_content(text, findings)
        assert "123-45-6789" not in redacted
        assert "REDACTED" in redacted

    def test_ssn_redaction_preserves_last4(self, scanner):
        text = "SSN: 123-45-6789"
        findings = scanner.scan_content(text)
        redacted = scanner.redact_content(text, findings)
        assert "6789" in redacted  # SSN last-4 preserved per spec

    def test_clean_text_returns_zero_risk(self, scanner):
        text = "The quarterly report shows growth in revenue for Q3."
        findings = scanner.scan_content(text)
        score = scanner.calculate_risk_score(findings)
        assert score < 3.0

    def test_high_risk_text_scores_above_7(self, scanner):
        text = "SSN 123-45-6789, AKIA1234567890ABCDEF, card 4532015112830366"
        findings = scanner.scan_content(text)
        score = scanner.calculate_risk_score(findings)
        assert score > 7.0

    def test_redaction_order_independence(self, scanner):
        """Multiple overlapping findings should not corrupt redaction."""
        text = "Contact John Smith at 123-45-6789 or 555-1234."
        findings = scanner.scan_content(text)
        redacted = scanner.redact_content(text, findings)
        # Should not raise; result should be shorter or equal and contain no raw SSN
        assert "123-45-6789" not in redacted


class TestIndiaPIIScanner:
    @pytest.fixture
    def scanner(self):
        return IndiaPIIScanner()

    def test_aadhaar_detected(self, scanner):
        text = "Patient Aadhaar: 2345 6789 0123"
        findings = scanner.scan(text)
        labels = [f["label"] for f in findings]
        assert "Aadhaar Number" in labels

    def test_pan_detected(self, scanner):
        text = "PAN card ABCDE1234F on file."
        findings = scanner.scan(text)
        labels = [f["label"] for f in findings]
        assert "PAN Card" in labels

    def test_upi_detected(self, scanner):
        text = "Please pay to user@oksbi for the invoice."
        findings = scanner.scan(text)
        labels = [f["label"] for f in findings]
        assert "UPI ID" in labels

    def test_indian_mobile_detected(self, scanner):
        text = "Call the patient on +919876543210 for appointment."
        findings = scanner.scan(text)
        labels = [f["label"] for f in findings]
        assert "Indian Mobile" in labels

    def test_aadhaar_redacted(self, scanner):
        text = "Aadhaar: 2345 6789 0123"
        redacted = scanner.redact(text)
        assert "2345 6789 0123" not in redacted
        assert "AADHAAR" in redacted

    def test_gst_detected(self, scanner):
        text = "GST Number: 27ABCDE1234F1Z5"
        findings = scanner.scan(text)
        labels = [f["label"] for f in findings]
        assert "GST Number" in labels

    def test_clean_text_no_findings(self, scanner):
        text = "The board meeting is scheduled for next Monday at 10AM."
        findings = scanner.scan(text)
        assert len(findings) == 0

    def test_dpdp_sensitive_category_aadhaar(self, scanner):
        text = "Aadhaar: 2345 6789 0123"
        findings = scanner.scan(text)
        categories = [f["dpdp_category"] for f in findings]
        assert "SENSITIVE" in categories
