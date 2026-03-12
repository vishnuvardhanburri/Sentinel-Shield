import re
import os
from typing import List, Dict
try:
    from presidio_analyzer import AnalyzerEngine
except ImportError:
    AnalyzerEngine = None

class EnterpriseScanner:
    """Enterprise-grade security scanner for local data leakage detection."""
    
    def __init__(self):
        # NLP Analyzer for PII
        self.analyzer = AnalyzerEngine() if AnalyzerEngine else None
        
        # High-Value Secrets Patterns
        self.secret_patterns = {
            "AWS Token": r"AKIA[0-9A-Z]{16}",
            "Secret Key": r"(?i)(key|secret|token|pass|auth|api)[:=]\s*[a-zA-Z0-9/+=]{30,}",
            "PII (SSN)": r"\b\d{3}-\d{2}-\d{4}\b",
            "Credit Card": r"\b(?:\d[ -]*?){13,16}\b",
            "SSH Key": r"-----BEGIN (RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----",
            "DB String": r"([a-zA-Z0-9]+):\/\/([a-zA-Z0-9]+):([a-zA-Z0-9]+)@([a-zA-Z0-9\.-]+)",
            "Environment File": r"(?i)(\.env|\.history|\.bash_history|\.ssh\/id_rsa)"
        }

        # Data Classification Patterns (Legal/Medical/System)
        self.classification_patterns = {
            "System Intrusion": r"(?i)(bash -i|rm -rf /|nc -e /bin/sh|exploit|payload|reverse shell|sudo -l)",
            "Legal/Compliance": r"(?i)(NDA|Confidentiality|Plaintiff|Defendant|Lawsuit|Agreement)",
            "Medical/HIPAA": r"(?i)(Patient|Diagnosis|Medical Record|HIPAA|PHI|NPI)"
        }

    def scan_content(self, text: str) -> List[Dict]:
        """Scans text for PII, Secrets, and Sensitive Classification."""
        findings = []

        # 1. Secret Scanning (Regex)
        for label, pattern in self.secret_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                findings.append({
                    "type": "SECRET",
                    "label": label,
                    "confidence": "HIGH",
                    "snippet": text[max(0, match.start()-30) : min(len(text), match.end()+30)],
                    "start": match.start(),
                    "end": match.end(),
                    "entity": match.group()
                })

        # 2. Sensitivity Classification
        for label, pattern in self.classification_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                findings.append({
                    "type": "CLASSIFICATION",
                    "label": label,
                    "confidence": "MEDIUM",
                    "snippet": text[max(0, match.start()-30) : min(len(text), match.end()+30)],
                    "start": match.start(),
                    "end": match.end(),
                    "entity": match.group()
                })

        # 3. PII NLP Scanning (Presidio)
        if self.analyzer:
            results = self.analyzer.analyze(text=text, entities=[], language='en')
            for res in results:
                # Filter out low confidence PII to avoid noise
                if res.score > 0.4:
                    findings.append({
                        "type": "PII",
                        "label": res.entity_type,
                        "confidence": f"{res.score*100:.1f}%",
                        "snippet": text[max(0, res.start-30) : min(len(text), res.end+30)],
                        "start": res.start,
                        "end": res.end,
                        "entity": text[res.start:res.end]
                    })
        
        return findings

    def calculate_risk_score(self, findings: List[Dict]) -> float:
        """Calculate a risk score from 0.0 to 10.0 based on severity."""
        if not findings:
            return 0.0
        
        score = 0.0
        for f in findings:
            if f["type"] == "SECRET":
                score += 2.5  # Secrets are high risk
            elif f["type"] == "PII":
                score += 1.0  # PII is moderate risk
            elif f["type"] == "CLASSIFICATION":
                score += 0.8  # Classification is informational risk
        
        return min(10.0, score)

    def _build_redaction_token(self, finding: Dict) -> str:
        """Builds human-readable redaction tags with SSN-preserving last4 format."""
        label = str(finding.get("label", "DATA"))
        entity = str(finding.get("entity", "")).strip()

        ssn_match = re.search(r"(\d{3}-\d{2}-(\d{4}))", entity)
        if "SSN" in label.upper() or ssn_match:
            last4 = ssn_match.group(2) if ssn_match else "0000"
            return f"[REDACTED_SSN_XXX-XX-{last4}]"

        normalized = re.sub(r"[^A-Z0-9]+", "_", label.upper()).strip("_") or "DATA"
        return f"[REDACTED_{normalized}]"

    def redact_content(self, text: str, findings: List[Dict]) -> str:
        """Returns redacted content for UI/Safe viewing."""
        if not findings:
            return text

        redacted_text = text
        # Apply from right-to-left so original offsets remain valid.
        safe_findings = sorted(findings, key=lambda x: x.get("start", -1), reverse=True)
        rightmost_boundary = len(text)

        for finding in safe_findings:
            start = finding.get("start")
            end = finding.get("end")
            if not isinstance(start, int) or not isinstance(end, int):
                continue
            if start < 0 or end > len(text) or start >= end:
                continue
            if end > rightmost_boundary:
                # Skip overlapping spans already replaced.
                continue

            token = self._build_redaction_token(finding)
            redacted_text = redacted_text[:start] + token + redacted_text[end:]
            rightmost_boundary = start

        return redacted_text

    def audit_system(self) -> List[Dict]:
        """Scans the local host for exposed security risks outside vault."""
        leaks = []
        # 1. Environment Variables Scan
        for k, v in os.environ.items():
            for pattern_name, pattern in self.secret_patterns.items():
                if re.search(pattern, str(v)):
                    leaks.append({"type": "SYSTEM_LEAK", "label": f"Env Var: {k}", "risk": 8.5})

        # 2. History Check (common Mac/Linux paths)
        hist_files = [os.path.expanduser("~/.bash_history"), os.path.expanduser("~/.zsh_history")]
        for hf in hist_files:
            if os.path.exists(hf):
                try:
                    with open(hf, "r", errors='ignore') as f:
                        content = f.read()[-5000:] # Last 5k chars for speed
                        findings = self.scan_content(content)
                        if findings:
                            leaks.append({"type": "HISTORY_LEAK", "label": hf, "risk": 7.0})
                except: pass
        return leaks
