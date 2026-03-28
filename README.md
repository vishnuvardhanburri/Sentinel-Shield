# Sentinel Shield v2 — Enterprise AI Data Governance Platform

<div align="center">
  <img src="docs/media/dashboard_v1.png" alt="Sentinel Shield Dashboard" width="800" />

  <h3>🛡️ <strong>SENTINEL SHIELD v2.0</strong></h3>
  <p><em>HIPAA · DPDP 2026 · GDPR-Ready AI Governance — from $100k/year</em></p>

  ![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)
  ![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?style=flat-square)
  ![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square)
  ![License](https://img.shields.io/badge/License-Enterprise-gold?style=flat-square)
</div>

---

## What Is Sentinel Shield?

Sentinel Shield is an **enterprise AI governance platform** that ensures every AI interaction inside your organisation is scanned, redacted, policy-governed, and audit-logged before any data leaves your perimeter.

> A nurse types a patient's name into ChatGPT. Sentinel intercepts it, blocks the request, logs the attempt in an immutable ledger, and fires a compliance alert — in under 200ms.

---

## The 6 Enterprise Capabilities

| # | Capability | Status |
|---|-----------|--------|
| 1 | **Real-time PII Interception** — Presidio + 22 India-specific patterns (Aadhaar, PAN, UHID…) | ✅ Live |
| 2 | **RBAC + JWT Authentication** — 4 roles, 18 permissions, SSO-ready | ✅ Live |
| 3 | **Immutable Audit Ledger** — SHA-256 hash-chained JSONL, tamper-proof | ✅ Live |
| 4 | **DPDP 2026 Compliance** — Data Principal rights, consent management, DPB incident reporting | ✅ Live |
| 5 | **Automated License Server** — `SNTL-XXXX` keys, seat tracking, hardware lock, expiry | ✅ Live |
| 6 | **Multi-Model Gateway** — Ollama (air-gap) · GPT-4o · Claude · Gemini · hybrid fallback | ✅ Live |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   SENTINEL SHIELD v2                      │
│                                                          │
│  ┌──────────┐   ┌──────────────────────────────────────┐ │
│  │ Next.js  │──▶│          FastAPI Backend              │ │
│  │ Dashboard│   │                                      │ │
│  │ (v2.0)   │   │  RBAC │ Audit │ Policy │ Compliance  │ │
│  └──────────┘   │  Gateway │ License │ Integrations    │ │
│                 └──────────────┬─────────────────────┘ │
│                                │                        │
│         ┌──────────────────────┼────────────────────┐  │
│         │                      │                    │  │
│    ┌────▼───┐             ┌────▼───┐           ┌───▼──┐ │
│    │Presidio│             │Chroma  │           │ YAML  │ │
│    │+ India │             │Vector  │           │Policy │ │
│    │Scanner │             │  DB    │           │Engine │ │
│    └────────┘             └────────┘           └──────┘ │
│                                                          │
│  ══════════════════════════════════════════════════════  │
│  Air-Gap (SQLite + Ollama) ↔ Cloud (PostgreSQL + GPT-4)  │
└──────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Air-Gap (Local) Mode

```bash
# 1. Clone and enter
git clone https://github.com/vishnuvardhanburri/Sentinel-Shield
cd Sentinel-Shield

# 2. Configure
cp .env.example .env
# Set JWT_SECRET_KEY and optionally OPENAI_API_KEY

# 3. Install Python deps
pip install -r requirements.txt
python -m spacy download en_core_web_lg

# 4. Start Ollama (local LLM)
ollama pull llama3.1

# 5. Start backend
cd backend && uvicorn app:app --host 0.0.0.0 --port 8000

# 6. Start frontend (new terminal)
cd frontend && npm install && npm run dev
# Visit http://localhost:3000
```

### Cloud / Docker Mode

```bash
# Full stack (backend + frontend + PostgreSQL + Ollama)
docker compose --profile airgap up

# Cloud mode (PostgreSQL + Redis instead of SQLite + Ollama)
DEPLOYMENT_MODE=cloud \
DATABASE_URL=postgresql+psycopg2://user:pass@host/sentinel \
OPENAI_API_KEY=sk-... \
docker compose --profile cloud up
```

---

## Compliance Scorecard

| Framework | Coverage |
|-----------|---------|
| **HIPAA** | Audit chain integrity · PHI redaction · breach detection · MFA enforcement |
| **DPDP 2026** | Data Principal rights (Sec 6-13) · DPB incident reporting (Sec 8) · consent management |
| **GDPR Lite** | Policy accountability · 72-hour breach reporting scaffolding · data minimisation |
| **ISO 27001 Lite** | Access control · audit logs · incident management · cryptographic controls |

---

## Industry Presets

Drop into `presets/` and reload:

| Preset | Department | Key Enforcement |
|--------|-----------|----------------|
| `hospital.yaml` | ICU, Emergency, OPD | BLOCK PHI + ICD codes, redact clinical data |
| `ivf_clinic.yaml` | IVF/Fertility | BLOCK donor anonymity, REDACT genetic data |
| `law_firm.yaml` | Legal | BLOCK client identity, REDACT privileged docs |
| `real_estate.yaml` | Realty | BLOCK buyer/seller PII, REDACT deed values |
| `logistics.yaml` | Supply Chain | BLOCK recipient PII, REDACT AWB/tracking |

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/login` | — | Get JWT token |
| `GET` | `/status` | JWT | System health + audit stats |
| `POST` | `/ask` | JWT | Governed AI query (scan→redact→policy→route→log) |
| `GET` | `/audit/log` | JWT | Immutable audit entries |
| `POST` | `/export-audit` | JWT | CSV or PDF compliance export |
| `GET` | `/compliance/score` | JWT | HIPAA/DPDP/GDPR/ISO scorecard |
| `GET` | `/policy/list` | JWT | Active YAML policies |
| `POST` | `/policy/reload` | Admin | Reload policies from disk |
| `POST` | `/license/issue` | Admin | Issue new license key |
| `POST` | `/license/activate` | — | Activate key on machine |
| `POST` | `/license/validate` | — | Check license status |
| `GET` | `/shadow-ai/detections` | JWT | Shadow AI usage events |
| `POST` | `/shadow-ai/scan` | JWT | Trigger on-demand scan |
| `POST` | `/integrations/webhooks/register` | Admin | Register outbound webhook |
| `POST` | `/integrations/incoming/emr` | HMAC | Receive EMR data (Epic/Practo) |
| `GET` | `/api/docs` | — | Swagger UI |

---

## Security Architecture

- **Encryption**: AES-256-GCM, hardware-bound key derivation (PBKDF2 + machine UUID)
- **Audit Integrity**: SHA-256 hash chaining — any tampered entry invalidates the entire chain
- **Auth**: JWT (HS256) + bcrypt password hashing + RBAC with 18 granular permissions
- **PII Scanning**: Microsoft Presidio (English NER) + 22 India-specific regex patterns
- **Policy DSL**: YAML rules with WARN / REDACT / BLOCK enforcement + risk thresholds
- **Network**: All LLM traffic stays local in air-gap mode (Ollama on `localhost:11434`)

---

## Pricing (Reference)

| Plan | Price | Seats | Mode |
|------|-------|-------|------|
| Starter | $20k/year | 5 | Air-gap |
| Professional | $50k/year | 25 | Air-gap + Cloud |
| Enterprise | $100k+/year | Unlimited | Multi-tenant Cloud |

---

## License

Proprietary — VishnuLabs © 2026. All rights reserved.  
Contact: [support@vishnulabs.com](mailto:support@vishnulabs.com)
 
