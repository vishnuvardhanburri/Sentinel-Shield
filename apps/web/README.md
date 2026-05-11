# Sovereign Shield Web Console

Next.js operator console for CISO, security operations, audit, and deployment teams.

This app consumes the FastAPI backend through `@sovereign-shield/sdk`. It must not duplicate DLP, policy, routing, risk, audit, or license enforcement logic.

```bash
pnpm --filter @sovereign-shield/web dev
pnpm --filter @sovereign-shield/web build
```
