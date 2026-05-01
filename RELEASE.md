# Sentinel Shield Release Checklist

Use this checklist before buyer handoff, investor demo, or production deployment.

## 1. Local Verification

```bash
pnpm check
.runtime_venv/bin/python -m pytest tests/ --cov=backend --cov-report=xml --cov-report=term-missing -v --tb=short
pnpm smoke:e2e
```

For authenticated smoke:

```bash
SENTINEL_SMOKE_EMAIL=admin@sentinel.local \
SENTINEL_SMOKE_PASSWORD='<changed-password>' \
pnpm smoke:e2e
```

## 2. Docker Verification

Start Docker Desktop, then run:

```bash
docker build -f Dockerfile.backend -t sentinel-backend:test .
docker build -f Dockerfile.frontend -t sentinel-frontend:test .
```

## 3. Production Seal

```bash
pnpm production:seal
```

Confirm:

- Runtime logs scrubbed
- Fresh salts generated
- Full tests pass
- Seal commit created

## 4. GitHub Verification

Confirm the GitHub Actions checks are green:

- Backend Tests + Security Scan
- Frontend Build
- Policy YAML Validation
- Docker Build Validation

Protect `main` and require the checks above before merge.

## 5. Buyer Evidence

Before demo:

- Login works
- Temporary password rotation works
- Admin can create, disable, and reset a user
- Enterprise Center model inventory loads
- CISO Alert Center and quarantine widgets load
- Evidence report history lists generated artifacts
- mTLS config wizard returns Nginx config
- LLM firewall builder returns reviewable YAML
- Policy bundle signer returns a manifest signature
- Tenant branding pack returns buyer labels
- Ledger anchor creates a root hash record
- Proxy masks Aadhaar and PAN
- Vault AI answers through local Ollama
- Oracle Risk heatmap loads
- Audit ledger chain verifies
- Evidence PDF generates

## 6. Handoff Package

Include:

- `README.md`
- `DOCS.md`
- `SECURITY.md`
- `SUBMISSION_CHECKLIST.md`
- `.env.example.production`
- Latest sealed Git commit hash
- Evidence PDF sample generated in the buyer environment
