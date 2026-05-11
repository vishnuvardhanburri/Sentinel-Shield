# Cross-Platform Release Workflow

Sovereign Shield uses GitHub Actions as the release control plane. The checked-in workflow is intentionally manual so buyer-side signing secrets are never required for normal CI.

## Build Targets

| Target | Output |
| --- | --- |
| Web | Next.js operator console |
| macOS | Tauri `.app` and `.dmg`, notarized by buyer credentials |
| Windows | Tauri `.msi`, signed by buyer code-signing certificate |
| Linux | Tauri AppImage |
| Android | APK/AAB through Expo/EAS or buyer native CI |
| iOS | TestFlight archive through Expo/EAS or buyer Apple account |

## Required Buyer Secrets

```text
APPLE_ID
APPLE_PASSWORD
APPLE_TEAM_ID
TAURI_PRIVATE_KEY
TAURI_KEY_PASSWORD
WINDOWS_CERTIFICATE
WINDOWS_CERTIFICATE_PASSWORD
EXPO_TOKEN
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
IOS_ASC_API_KEY
```

## Auto-Update Strategy

- Tauri updater is configured with a buyer-replaceable endpoint.
- Update artifacts must be signed by the buyer's private update key.
- Mobile updates use app-store/TestFlight channels.
- Web updates remain controlled by the buyer's deployment platform.
- Backend compatibility is preserved through the shared SDK contract.

## Promotion Flow

1. Run `pnpm submit:ready`.
2. Run `pnpm generate:data-room`.
3. Build cross-platform artifacts through the manual release workflow.
4. Validate smoke tests on each platform against a staging FastAPI gateway.
5. Promote the backend and clients together only after device-session and audit checks pass.
