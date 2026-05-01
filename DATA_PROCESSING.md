# Data Processing Summary

## Data Categories

- User account metadata.
- API key metadata, never copy-once raw secrets after creation.
- Prompt hashes and redaction metadata.
- Pseudonymized inspection results.
- Audit events, risk scores, policy triggers, model routing metadata.

## Processing Purposes

- Prevent sensitive data leakage to AI systems.
- Enforce department and tenant policy.
- Produce compliance evidence.
- Detect risky actors and prompt-injection attempts.

## Retention

Retention is buyer-controlled. Evidence schedules and backup retention can be configured through the Enterprise Center and local automation.

## Subprocessors

None are required in air-gapped mode. Optional cloud LLM, SIEM, Slack, Teams, or storage integrations are buyer-configured.
