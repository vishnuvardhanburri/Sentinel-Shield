import type { SovereignRole } from "./types";

export type SovereignPermission =
  | "view_dashboard"
  | "view_risk"
  | "review_quarantine"
  | "approve_quarantine_action"
  | "view_audit"
  | "export_evidence"
  | "manage_mtls"
  | "emergency_kill_switch";

const ROLE_PERMISSIONS: Record<SovereignRole, SovereignPermission[]> = {
  SUPER_ADMIN: [
    "view_dashboard",
    "view_risk",
    "review_quarantine",
    "approve_quarantine_action",
    "view_audit",
    "export_evidence",
    "manage_mtls",
    "emergency_kill_switch"
  ],
  DEPARTMENT_HEAD: ["view_dashboard", "view_risk", "review_quarantine", "view_audit", "export_evidence"],
  STAFF: ["view_dashboard"],
  AUDITOR: ["view_dashboard", "view_audit", "export_evidence"],
  CISO: [
    "view_dashboard",
    "view_risk",
    "review_quarantine",
    "approve_quarantine_action",
    "view_audit",
    "export_evidence",
    "emergency_kill_switch"
  ],
  SECURITY_ANALYST: ["view_dashboard", "view_risk", "review_quarantine", "view_audit"],
  EXECUTIVE: ["view_dashboard", "view_risk", "view_audit", "emergency_kill_switch"],
  VIEWER: ["view_dashboard"]
};

export function can(role: SovereignRole, permission: SovereignPermission): boolean {
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

export function permissionsFor(role: SovereignRole): SovereignPermission[] {
  return [...(ROLE_PERMISSIONS[role] ?? [])];
}
