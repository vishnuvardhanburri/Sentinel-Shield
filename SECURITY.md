# Security Policy

## Supported Versions

Sentinel Shield is maintained on the `main` branch. Production buyers should run the latest sealed commit and keep a private copy of their `.env`, ledger, and database.

## Reporting a Vulnerability

Report security issues privately to Xavira Tech Labs support. Do not open public GitHub issues for secrets, bypasses, tenant isolation failures, authentication bugs, prompt-injection bypasses, or data exposure.

Include:

- Affected commit hash
- Deployment mode: `airgap`, `cloud`, or `hybrid`
- Reproduction steps
- Relevant logs with secrets redacted
- Expected impact

## Secret Handling

The backend is fail-closed. These values must be present and non-placeholder before boot:

- `JWT_SECRET_KEY`
- `LICENSE_MASTER_SECRET`
- `ACTOR_HASH_SALT`
- `LEDGER_MASTER_SALT`
- `ALLOWED_ORIGINS`

Never commit `.env`, local databases, ledger files, vault documents, certificates, or private keys.

## Data Residency

Air-gap mode routes Vault AI requests through Ollama by default. Sensitive prompts are scanned, pseudonymized, policy-checked, and audit-logged before model inference.

Cloud adapters are optional and should only be enabled by explicit buyer policy.

## Production Defaults

- Self-registration is disabled unless `ENABLE_SELF_REGISTRATION=true`.
- First-run admin credentials are generated once and must be rotated.
- Protected APIs reject disabled users even if they hold an old JWT.
- JWT revocation uses Redis when `REDIS_URL` is configured, with memory fallback for localhost.
- The API shield blocks suspicious paths, oversized requests, and excessive protected calls.

## Disclosure Expectations

Responsible disclosure reports are acknowledged as soon as possible by the project owner. High-severity reports should include a minimal proof of concept and avoid destructive testing against buyer data.
