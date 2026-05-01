# Sentinel Shield Technical Due Diligence

## Security Disclosure

The final production lockdown healed the five release blockers identified during the production-readiness review:

1. **Hardcoded JWT fallback secret — HEALED**
   `JWT_SECRET_KEY` is now loaded through the fail-closed security loader. Missing, short, or placeholder values stop application boot.

2. **Hardcoded license master secret — HEALED**
   `LICENSE_MASTER_SECRET` is now mandatory in both license server and validator paths. The prior default master secret has been removed.

3. **Wildcard CORS policy — HEALED**
   API CORS now uses `ALLOWED_ORIGINS` and rejects wildcard `*`. Defaults are limited to localhost dashboard ports and the production dashboard origin.

4. **Demo admin credentials — HEALED**
   `admin@demo.com / demo1234` has been removed from database seeding and dashboard login. First boot generates a one-time random temporary Super Admin password in backend logs and marks the account for immediate password rotation.

5. **Unsealed actor/ledger salts — HEALED**
   `ACTOR_HASH_SALT` and `LEDGER_MASTER_SALT` are now mandatory. `scripts/production_seal.sh` rotates both salts, runs tests, scrubs runtime evidence, and creates a production seal commit.

## Production Seal Command

```bash
pnpm production:seal
```

The seal script generates fresh secrets, installs pytest if needed, runs the full test suite, removes runtime logs and temporary bytecode, stages all changes, and commits:

```text
chore: enterprise production seal applied
```

## Required Production Environment

The backend refuses to boot unless these values are present and non-placeholder:

- `JWT_SECRET_KEY`
- `LICENSE_MASTER_SECRET`
- `ACTOR_HASH_SALT`
- `LEDGER_MASTER_SALT`
- `ALLOWED_ORIGINS` without wildcard values
