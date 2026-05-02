# Sentinel Shield: Start Here

Use these two commands only.

## Launch The Product

```bash
pnpm launch
```

This starts:

- API gateway at `http://localhost:8000`
- Xavira dashboard at `http://localhost:3000`
- A smoke check that confirms the product is reachable and branded correctly

Keep the terminal open while showing the product.

## Prove It Is Ready To Submit

```bash
pnpm submit:ready
```

This runs the buyer-grade end-to-end verification:

- Backend compile
- Dashboard lint and build
- Dashboard build is reported when the local Next.js toolchain completes; CI remains the production build gate
- Deployment doctor
- API smoke proof
- Optional browser smoke proof
- Release certificate
- Handoff PDF
- Buyer handoff ZIP

Expected final result:

```text
BUYER_VERIFIED
```

## Build The Buyer Data Room

```bash
pnpm generate:data-room
```

This creates a ZIP under `logs/data_room/` with architecture, threat model, compliance mapping, deployment guide, API docs, screenshots when available, and buyer-facing listing copy.

## Investor / Acquisition Demo

```bash
pnpm demo:investor
```

This seeds synthetic security events, opens the dashboard, and launches the live local system.

## Enterprise Deploy

```bash
pnpm deploy:enterprise
```

This starts services, prints URLs, and validates system health.

## Local URLs

```text
Dashboard: http://localhost:3000
API:       http://localhost:8000
Docs:      http://localhost:8000/api/docs
```
