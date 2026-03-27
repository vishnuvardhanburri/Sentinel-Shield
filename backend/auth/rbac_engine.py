"""
Sentinel Shield v2 — RBAC Engine
Defines roles, permissions, and enforcement decorators for the enterprise platform.

Role Hierarchy (highest → lowest):
  SUPER_ADMIN → DEPARTMENT_HEAD → STAFF → AUDITOR (read-only)
"""
from enum import Enum
from functools import wraps
from typing import Set, Callable, Optional
from fastapi import HTTPException


class Role(str, Enum):
    SUPER_ADMIN      = "SUPER_ADMIN"       # Full system access, license management
    DEPARTMENT_HEAD  = "DEPARTMENT_HEAD"   # Manage own dept policies + view dept audit
    STAFF            = "STAFF"             # Run queries, view own session data
    AUDITOR          = "AUDITOR"           # Read-only: audit log, compliance reports


class Permission(str, Enum):
    # User management
    MANAGE_USERS         = "manage_users"
    VIEW_ALL_USERS       = "view_all_users"

    # Policy management
    EDIT_GLOBAL_POLICY   = "edit_global_policy"
    EDIT_DEPT_POLICY     = "edit_dept_policy"
    VIEW_POLICY          = "view_policy"

    # Vault / AI operations
    RUN_AI_QUERY         = "run_ai_query"
    INGEST_DOCUMENTS     = "ingest_documents"
    VIEW_VAULT_STATUS    = "view_vault_status"

    # Audit & Compliance
    EXPORT_AUDIT_CSV     = "export_audit_csv"
    EXPORT_AUDIT_PDF     = "export_audit_pdf"
    VIEW_AUDIT_LOG       = "view_audit_log"
    VIEW_ALL_SESSIONS    = "view_all_sessions"
    VIEW_OWN_SESSIONS    = "view_own_sessions"

    # License & Billing
    MANAGE_LICENSES      = "manage_licenses"
    VIEW_LICENSE_STATUS  = "view_license_status"

    # Reporting
    GENERATE_BOARD_REPORT = "generate_board_report"


# Role → Permission mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),  # All permissions

    Role.DEPARTMENT_HEAD: {
        Permission.EDIT_DEPT_POLICY,
        Permission.VIEW_POLICY,
        Permission.RUN_AI_QUERY,
        Permission.INGEST_DOCUMENTS,
        Permission.VIEW_VAULT_STATUS,
        Permission.EXPORT_AUDIT_CSV,
        Permission.EXPORT_AUDIT_PDF,
        Permission.VIEW_AUDIT_LOG,
        Permission.VIEW_ALL_SESSIONS,
        Permission.VIEW_OWN_SESSIONS,
        Permission.VIEW_LICENSE_STATUS,
        Permission.GENERATE_BOARD_REPORT,
    },

    Role.STAFF: {
        Permission.RUN_AI_QUERY,
        Permission.INGEST_DOCUMENTS,
        Permission.VIEW_VAULT_STATUS,
        Permission.VIEW_OWN_SESSIONS,
        Permission.VIEW_POLICY,
    },

    Role.AUDITOR: {
        Permission.VIEW_AUDIT_LOG,
        Permission.VIEW_ALL_SESSIONS,
        Permission.EXPORT_AUDIT_CSV,
        Permission.EXPORT_AUDIT_PDF,
        Permission.VIEW_VAULT_STATUS,
        Permission.GENERATE_BOARD_REPORT,
        Permission.VIEW_POLICY,
        Permission.VIEW_LICENSE_STATUS,
    },
}


class RBACEngine:
    """Core RBAC enforcement engine."""

    def has_permission(self, role: str, permission: Permission) -> bool:
        """Check if a role has a specific permission."""
        try:
            r = Role(role)
        except ValueError:
            return False
        return permission in ROLE_PERMISSIONS.get(r, set())

    def get_permissions(self, role: str) -> Set[Permission]:
        """Return all permissions for a role."""
        try:
            r = Role(role)
            return ROLE_PERMISSIONS.get(r, set())
        except ValueError:
            return set()

    def enforce(self, role: str, permission: Permission):
        """Raise HTTP 403 if the role lacks the required permission."""
        if not self.has_permission(role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: role '{role}' requires permission '{permission.value}'"
            )

    def can_access_department(self, user_dept: Optional[str], target_dept: Optional[str], role: str) -> bool:
        """Determine if a user can see data from a specific department."""
        if role in (Role.SUPER_ADMIN.value, Role.AUDITOR.value):
            return True  # Cross-department access
        if role == Role.DEPARTMENT_HEAD.value:
            return user_dept == target_dept
        if role == Role.STAFF.value:
            return user_dept == target_dept
        return False


# Module singleton
rbac = RBACEngine()


def require_permission(permission: Permission):
    """FastAPI dependency factory: enforce RBAC permission on a route."""
    def dependency(current_user=None):
        # current_user is injected by FastAPI from JWT
        # Usage: Depends(require_permission(Permission.EDIT_DEPT_POLICY))
        role = getattr(current_user, "role", "STAFF")
        rbac.enforce(role, permission)
        return current_user
    return dependency
