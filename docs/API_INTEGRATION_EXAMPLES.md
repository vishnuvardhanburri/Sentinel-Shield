# Sovereign Shield API Integration Examples

Use scoped app keys from the Enterprise Center. The raw key is shown once.

## Python CRM Client

```python
import requests

resp = requests.post(
    "http://localhost:8000/api/v2/proxy/inspect",
    headers={"X-Sentinel-API-Key": "sshield_copy_once_key"},
    json={
        "text": "Aadhaar 2345 6789 0123 needs review.",
        "source_app": "custom-crm",
        "actor": "crm-user-42",
        "auto_redact": True,
    },
    timeout=20,
)
print(resp.json()["protected_text"])
```

## Node.js Client

```js
const res = await fetch("http://localhost:8000/api/v2/proxy/inspect", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Sentinel-API-Key": "sshield_copy_once_key",
  },
  body: JSON.stringify({
    text: "PAN ABCDE1234F should be masked before AI.",
    source_app: "node-service",
    actor: "service-account",
    auto_redact: true,
  }),
});

console.log(await res.json());
```

## Slack Or Teams Webhook Registration

```bash
curl -X POST http://localhost:8000/integrations/webhooks/register \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://hooks.example.com/services/...",
    "event_types": ["CISO_ALERT", "HIGH_RISK_BLOCKED"],
    "tenant_id": "default",
    "secret": "buyer-owned-hmac-secret"
  }'
```

Failed webhook deliveries are queued in `logs/webhook_delivery_queue.jsonl` and can be retried:

```bash
curl -X POST http://localhost:8000/integrations/webhooks/queue/retry
```
