# Compliance Mapping

This document is an implementation-oriented mapping, not legal advice.

| Control Area | DPDP/GDPR Need | Sovereign Shield Capability |
| --- | --- | --- |
| Data minimization | Reduce exposure of personal data | PII pseudonymization before LLM inference |
| Purpose limitation | Govern use of sensitive data | Policy engine and source-app metadata |
| Security safeguards | Prevent unauthorized disclosure | Prompt injection shield, API shield, rate limits |
| Data residency | Keep high-risk data local | Sensitivity-based local model routing |
| Auditability | Produce evidence of controls | Tamper-evident Obsidian ledger and PDF reports |
| Incident readiness | Identify misuse patterns | Oracle risk scoring and quarantine |
| Access governance | Restrict admin/API operations | JWT auth, RBAC, API keys, mTLS config generator |

## Buyer Positioning

Sovereign Shield helps buyers demonstrate that AI prompts are inspected, masked, routed, and logged before reaching model inference. This creates a defensible evidence trail for internal AI governance programs.
