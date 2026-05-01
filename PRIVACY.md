# Privacy Statement

Sentinel Shield is designed for local-first AI governance.

- Prompts are scanned before model routing.
- PII and India DPDP identifiers are pseudonymized before inference.
- Audit entries store hashes and metadata, not raw prompt bodies as primary evidence.
- Local mode does not require external LLM API keys.
- Buyer-owned secrets, salts, and backup passphrases stay in the buyer environment.

For production, buyers should configure mTLS, Redis, encrypted backups, and off-box ledger anchoring to buyer-controlled immutable storage.
