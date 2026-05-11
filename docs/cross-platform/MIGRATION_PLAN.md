# Cross-Platform Migration Plan

## Phase 1: Backend Contract Stabilization

- Keep FastAPI as the source of truth.
- Add refresh-token rotation and device session tracking.
- Keep existing localhost buyer demo and static deployment intact.
- Introduce the shared TypeScript SDK.

## Phase 2: Shared Product Layer

- Move API calls into `packages/sdk`.
- Move tokens, status colors, and shared UI constants into `packages/design-system`.
- Keep RBAC helpers shared, but enforce all final authorization in the backend.
- Add client audit event helpers for non-sensitive UI telemetry.

## Phase 3: Web Operator Console

- Use `apps/web` as the Next.js CISO console.
- Keep `frontend` as the current static buyer-facing surface until the Next.js console reaches parity.
- Connect dashboard, risk heatmap, alerts, audit log, reports, and quarantine views through the SDK.

## Phase 4: Desktop Operator Console

- Use `apps/desktop` for Tauri builds on macOS, Windows, and Linux.
- Add native notifications for high-risk CISO alerts.
- Add quarantine review, ledger verification, evidence export, and mTLS management views.
- Enable signed builds and auto-update after buyer signing infrastructure is available.

## Phase 5: Mobile Executive Console

- Use `apps/mobile` for React Native Android/iOS builds.
- Ship executive dashboard, push alerts, quarantine approvals, incident summaries, compliance preview, and read-only audit access.
- Add certificate pinning in production native build profiles.
- Keep emergency kill switch server-owned and ledger-audited.

## Phase 6: Release Automation

- Keep current CI fast for backend and static frontend.
- Use manual cross-platform release workflow for signed artifacts.
- Add buyer-specific signing secrets only in the buyer's GitHub organization.
- Bundle data-room artifacts with architecture, API docs, compliance mapping, screenshots, and known limitations.
