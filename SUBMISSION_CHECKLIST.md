# Sentinel Shield Submission Checklist

Use this before every buyer demo, GitHub push, investor review, or deployment.

## 1. Services

Start backend:

```bash
set -a; source .env; set +a
.runtime_venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Start frontend:

```bash
cd frontend
pnpm dev
```

Confirm:

```text
http://localhost:8000/health
http://localhost:3000
```

## 2. Required Verification

Run:

```bash
python3 -m compileall backend tests
.runtime_venv/bin/python -m pytest
cd frontend && pnpm lint
cd frontend && pnpm build
pnpm smoke:e2e
```

Pass criteria:

- No backend syntax failures
- No frontend lint errors
- Production frontend build succeeds

## 3. Brand Check

Confirm visible UI says:

```text
Sentinel Shield
BY XAVIRA TECH LABS
```

Confirm no visible starter framework logos, legacy company names, or external model branding.

Framework/package references inside package files and lockfiles are allowed.

## 4. Security Check

Confirm `.env` contains non-placeholder values:

```text
JWT_SECRET_KEY
LICENSE_MASTER_SECRET
ACTOR_HASH_SALT
LEDGER_MASTER_SALT
ALLOWED_ORIGINS
```

Confirm backend fails closed if secrets are missing.

Confirm external onboarding is closed unless intentionally enabled:

```text
ENABLE_SELF_REGISTRATION=false
```

Confirm API shield behavior:

- Protected API responses include `X-Frame-Options: DENY`
- Oversized protected requests return `413 REQUEST_TOO_LARGE`
- Suspicious probe paths such as `/.env` return `404`

## 5. Demo Flow

Open dashboard:

```text
http://localhost:3000
```

Verify:

- Login works
- Forced password-change screen appears for first-run/reset users
- Users tab lists real backend users
- Admin can create, disable, and reset users
- Proxy tab masks Aadhaar/PAN
- Vault AI answers through local model
- Oracle Risk tab loads
- Audit Log tab loads
- Evidence report generation works

## 6. Seal Before Final Delivery

Run:

```bash
pnpm production:seal
```

Expected:

```text
tests passed
chore: enterprise production seal applied
```

## 7. Push

After seal:

```bash
git push origin main
```
