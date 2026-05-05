# System Snapshot

## Acquisition Status

**Enterprise Acquisition Ready — Verified Build**

Includes: Security Hardening, Compliance Mapping, Data Room, Deployment Pack

Positioning: production-ready AI security infrastructure with full compliance, audit, and deployment stack—replacing 9–12 months of engineering.

## Build Summary

| Metric | Snapshot |
| --- | --- |
| Product | Sovereign Shield |
| Company | Xavira Tech Labs |
| Category | Enterprise AI Security Gateway for Private LLM Deployments |
| API endpoints | 96 total routes / 58 API routes |
| Backend Python modules | 50 |
| Buyer UI pages/assets | 6 static frontend files |
| Simulated validation events | 1,200 |
| Demo event disclaimer | Simulated system validation data; not customer usage, revenue, or traction |
| Deployment command | `pnpm deploy:enterprise` |
| Verification command | `pnpm submit:ready` |
| Tier 3 proof endpoint | `GET /demo/tier3-self-healing` |
| Target deployment time | Under 15 minutes on a prepared machine |
| Data-room command | `pnpm generate:data-room` |
| Buyer demo video | `docs/demo/sovereign-shield-enterprise-demo.mp4` |

## Required Runtime Variables

Sovereign Shield is designed to depend on a buyer-owned database and local AI runtime by default.

Required production variables:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `LICENSE_MASTER_SECRET`
- `ACTOR_HASH_SALT`
- `LEDGER_MASTER_SALT`
- `ALLOWED_ORIGINS`
- `DEPLOYMENT_MODE=airgap`
- `CLOUD_ADAPTERS_ENABLED=false`

No OpenRouter, OpenAI, Anthropic, Gemini, or other third-party LLM API key is required for the default buyer deployment.

## Security Controls Count

22 core security controls are implemented or packaged for buyer deployment:

1. JWT authentication
2. RBAC permissions
3. Session/token revocation
4. Disabled-user enforcement
5. Fail-closed secret validation
6. Strict CORS allowlist
7. Request size limits
8. Rate limiting
9. Cost-budget limiting
10. Suspicious path blocking
11. Secure headers including CSP and HSTS
12. mTLS support via reverse-proxy verified headers
13. India and global PII detection
14. Context-preserving pseudonymization
15. Prompt injection blocking
16. Semantic DLP detection
17. Oracle risk scoring and quarantine
18. Tamper-evident JSONL audit ledger with evidence PDF certificate
19. Hallucination and jailbreak guardian
20. Base64/adversarial suffix bypass detection
21. Active-passive HA state-sync package
22. Golden-image Terraform/CloudFormation deployment pack

## Components

| Component | Path |
| --- | --- |
| FastAPI security gateway | `backend/app.py` |
| Zero-Trust API shield | `backend/api_shield.py` |
| Fail-closed config loader | `backend/config.py` |
| JWT/RBAC auth | `backend/auth/` |
| Identity masking proxy | `backend/redaction_middleware.py` |
| India PII patterns | `backend/compliance/india_patterns.py` |
| Prompt injection shield | `backend/prompt_injection.py` |
| Hallucination/jailbreak guardian | `backend/llm_guardian.py` |
| Semantic DLP | `backend/semantic_dlp.py` |
| Risk/quarantine engine | `backend/risk_engine.py` |
| Local/cloud model router | `backend/gateway/model_router.py` |
| Audit ledger | `backend/audit/ledger.py` |
| Evidence report generator | `backend/reporting/evidence_report.py` |
| Buyer dashboard | `frontend/site/` |
| Data room generator | `scripts/generate_data_room.py` |
| Enterprise deploy launcher | `scripts/deploy_enterprise.py` |
| Buyer verifier | `scripts/verify_buyer.py` |
| Active-passive HA runbook | `docs/HA_RUNBOOK.md` |
| Golden-image IaC | `iac/terraform/aws/`, `iac/cloudformation/sovereign-shield-ha.yaml` |

## Buyer Proof Commands

```bash
pnpm deploy:enterprise
pnpm demo:investor
pnpm submit:ready
pnpm generate:data-room
```

## Demo Video Requirement

Recommended file name:

```text
sentinel_shield_enterprise_demo.mp4
```

Recommended 5–6 minute flow:

1. Start with `pnpm deploy:enterprise`.
2. Show `http://localhost:3000` dashboard.
3. Open `/ops/` to show metrics, logs, risk scoring, and implementation map.
4. Run gateway proof to show Aadhaar/PAN masking and local route.
5. Generate evidence PDF and show SHA-256 certificate.
6. Run `pnpm submit:ready` and show `BUYER_VERIFIED 100.0`.
7. Show generated data-room ZIP.

Expected buyer verification output:

```text
status: BUYER_VERIFIED
score: 100.0
```

## Diligence Package

The generated data room includes architecture, threat model, security controls, API docs, deployment guide, screenshots, compliance mapping, known limitations, listing copy, buyer replies, and verification artifacts.

The GitHub demo video is available at `docs/demo/sovereign-shield-enterprise-demo.mp4`.
