#!/usr/bin/env python3
"""Generate Sentinel Shield deployment hardening pack."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "logs" / "deployment_pack"
OUT.mkdir(parents=True, exist_ok=True)

(OUT / "nginx-sentinel.conf").write_text("""server {
    listen 443 ssl http2;
    server_name sentinel-shield.local;

    ssl_certificate /etc/sentinel/tls/server.crt;
    ssl_certificate_key /etc/sentinel/tls/server.key;
    ssl_client_certificate /etc/sentinel/tls/ca.crt;
    ssl_verify_client on;

    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy no-referrer always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-SSL-Client-Verify $ssl_client_verify;
        proxy_set_header X-SSL-Client-Fingerprint $ssl_client_fingerprint;
    }
}
""")

(OUT / "sentinel-backend.service").write_text(f"""[Unit]
Description=Sentinel Shield FastAPI Gateway
After=network-online.target

[Service]
WorkingDirectory={ROOT}/backend
EnvironmentFile={ROOT}/.env
ExecStart={ROOT}/.runtime_venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths={ROOT}/logs {ROOT}/sentinel.db {ROOT}/chroma_db

[Install]
WantedBy=multi-user.target
""")

(OUT / "ufw-rules.sh").write_text("""#!/usr/bin/env bash
set -euo pipefail
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 443/tcp
ufw enable
""")

(OUT / "production-env-checklist.md").write_text("""# Sentinel Shield Production Checklist

- Set strong `JWT_SECRET_KEY`, `LICENSE_MASTER_SECRET`, `ACTOR_HASH_SALT`, `LEDGER_MASTER_SALT`.
- Set `ALLOWED_ORIGINS` to buyer dashboard domains only.
- Set `API_SHIELD_ENFORCE_MTLS=true` behind Nginx/Envoy.
- Set `REDIS_URL` for distributed risk/quarantine state.
- Run `pnpm production:seal`.
- Run `bash scripts/security_due_diligence.sh`.
- Generate and archive `/api/v2/enterprise/readiness` output.
- Generate `/api/v2/enterprise/backup` and store it in buyer-controlled storage.
""")

print(f"Deployment pack generated: {OUT}")
