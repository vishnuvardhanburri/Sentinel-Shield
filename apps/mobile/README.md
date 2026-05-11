# Sovereign Shield Mobile Console

React Native executive and incident-response console for Android and iOS.

Core production requirements:

- encrypted token storage
- certificate pinning in native production builds
- push notifications without PII payloads
- read-only audit by default
- emergency actions routed through FastAPI and written to the ledger

```bash
pnpm --filter @sovereign-shield/mobile dev
pnpm --filter @sovereign-shield/mobile android
pnpm --filter @sovereign-shield/mobile ios
```
