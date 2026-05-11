# Cross-Platform Packaging Matrix

| Platform | App | Command | Release Notes |
| --- | --- | --- | --- |
| Web | `apps/web` | `pnpm --filter @sovereign-shield/web build` | Next.js CISO console; deploy behind strict CORS and CSP |
| macOS | `apps/desktop` | `pnpm --filter @sovereign-shield/desktop build` | Requires Apple Developer signing and notarization |
| Windows | `apps/desktop` | `pnpm --filter @sovereign-shield/desktop build` | Requires Windows code-signing certificate |
| Linux | `apps/desktop` | `pnpm --filter @sovereign-shield/desktop build` | Produces AppImage target |
| Android | `apps/mobile` | `pnpm --filter @sovereign-shield/mobile android` | Production AAB should be signed in buyer CI |
| iOS | `apps/mobile` | `pnpm --filter @sovereign-shield/mobile ios` | TestFlight requires buyer Apple account |

## Packaging Rules

- Backend URLs are environment or release-channel configuration, not compiled secrets.
- Client builds cannot include `.env`, database URLs, LLM keys, license master secrets, salts, or private signing keys.
- Evidence PDFs must be generated server-side and downloaded by authorized users.
- Mobile push notifications must carry incident IDs only, never PII.
- All production clients must point to the buyer-owned FastAPI gateway.
