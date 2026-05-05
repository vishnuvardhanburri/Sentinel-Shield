# Code

This folder is the buyer-facing pointer to the hardened private repo source.

The production code remains in the root-level application folders so existing commands, imports, Docker files, CI, and deployment scripts keep working without brittle path rewrites.

## Hardened Source Map

| Area | Path |
| --- | --- |
| FastAPI security gateway | `../backend/app.py` |
| Authentication and RBAC | `../backend/auth/` |
| Zero-Trust API shield | `../backend/api_shield.py` |
| Fail-closed config loader | `../backend/config.py` |
| PII and India-stack detection | `../backend/security_scanner.py`, `../backend/compliance/india_patterns.py` |
| Identity masking proxy | `../backend/redaction_middleware.py` |
| Prompt injection defense | `../backend/prompt_injection.py` |
| Semantic DLP | `../backend/semantic_dlp.py` |
| Risk scoring and quarantine | `../backend/risk_engine.py` |
| Local/cloud model routing | `../backend/gateway/` |
| Tamper-evident audit ledger | `../backend/audit/` |
| Evidence PDF reporting | `../backend/reporting/` |
| Buyer dashboard | `../frontend/site/` |
| Enterprise scripts | `../scripts/` |
| Tests | `../tests/` |

## Buyer Verification

Run from the repository root:

```bash
pnpm deploy:enterprise
pnpm submit:ready
pnpm generate:data-room
```

Expected proof:

```text
BUYER_VERIFIED
score: 100.0
```
