# Cross-Platform API Contract

The shared TypeScript SDK in `packages/sdk` is the only supported client-side API layer for web, desktop, and mobile operator consoles.

## Auth

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v2/auth/login` | Login with email, password, and device context |
| `POST` | `/api/v2/auth/refresh` | Rotate refresh token and receive a fresh access token |
| `POST` | `/api/v2/auth/logout` | Revoke current access token |
| `GET` | `/api/v2/devices/sessions` | List tracked device sessions |
| `POST` | `/api/v2/devices/sessions/revoke` | Revoke a device session |

Device context is sent on login and refresh:

```json
{
  "device": {
    "device_id": "macbook-ciso-01",
    "platform": "macos",
    "app_version": "0.1.0",
    "device_name": "CISO MacBook"
  }
}
```

## Security Operations

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v2/risk/heatmap` | Risk actors, quarantine state, and heatmap input |
| `GET` | `/audit/log` | Tamper-evident audit entries |
| `POST` | `/api/v2/audit/report` | Evidence PDF generation |
| `GET` | `/api/v2/enterprise/alerts` | CISO alert center |
| `GET` | `/api/v2/enterprise/quarantine` | Quarantined actors |
| `POST` | `/api/v2/enterprise/quarantine/action` | Review, extend, deny, or release quarantine action |
| `POST` | `/api/v2/enterprise/kill-switch` | Audit-backed emergency action |

## SDK Guarantees

- Adds device metadata to every request.
- Persists tokens only through injected platform storage adapters.
- Never stores API keys, database credentials, LLM provider keys, or ledger salts.
- Keeps RBAC helpers shared while leaving final authorization to FastAPI.
- Raises explicit API errors so clients fail closed.
