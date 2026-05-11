# Sovereign Shield Desktop Console

Tauri operator console for macOS, Windows, and Linux.

Core production requirements:

- use only backend APIs through `@sovereign-shield/sdk`
- no embedded secrets
- no direct Ollama, database, Redis, or ledger-file access
- signed builds for buyer release
- updater artifacts signed by buyer-controlled Tauri update keys

```bash
pnpm --filter @sovereign-shield/desktop dev
pnpm --filter @sovereign-shield/desktop build
```
