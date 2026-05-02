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

## Local URLs

```text
Dashboard: http://localhost:3000
API:       http://localhost:8000
Docs:      http://localhost:8000/api/docs
```
