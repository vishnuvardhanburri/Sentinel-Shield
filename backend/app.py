"""
Sentinel Shield v2 — Upgraded FastAPI Backend
Wires together: RBAC auth, audit ledger, policy engine, model gateway,
license server, DPDP compliance, and the original vault/RAG functionality.
"""
import os
import sys
# Ensure the current directory is in the path for cloud imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import base64
import hmac
import json
import csv
import hashlib
import uuid
import zipfile
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import FastAPI, HTTPException, Depends, Security, Header
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal
import platform
import shutil
import secrets

# ── Core V1 imports (preserved) ─────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import helpers to resolve internal modules correctly in IDEs
try:
    from security_scanner import EnterpriseScanner
    from vault_crypto import sentinel_crypto
except ImportError:
    from .security_scanner import EnterpriseScanner
    from .vault_crypto import sentinel_crypto

# ── V2 modules ───────────────────────────────────────────────────────────────
from auth.jwt_handler import get_current_user, create_access_token, revoke_token_id, TokenPayload, verify_token, security_scheme
from fastapi.security import HTTPAuthorizationCredentials
from auth.rbac_engine import rbac, Permission
from audit.ledger import audit_ledger
from audit.export_engine import AuditExporter
from compliance.dpdp_engine import DPDPEngine
from compliance.india_patterns import IndiaPIIScanner
from policy.policy_engine import policy_engine, EnforcementLevel
from gateway.model_router import model_router
from license_server import router as license_router
from integrations.webhook_engine import router as integrations_router
from shadow_ai.detector import router as shadow_ai_router, shadow_detector
from db.session import init_db, get_db, pwd_context
from db.models import User, APIKey
from reporting.compliance_scorer import ComplianceScorer
from redaction_middleware import IdentityMaskingProxy
from api_shield import ZeroTrustAPIShieldMiddleware
from semantic_dlp import SemanticDLP
from prompt_injection import PromptInjectionDetector
from risk_engine import oracle_risk_engine
from sentinel_check import SentinelCheck
from universal_proxy import UniversalProxy
from reporting.evidence_report import EvidencePDFGenerator
from config import security_settings

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
STATE_FILE = os.path.join(BASE_DIR, "sentinel_state.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
alert_log = os.path.join(LOGS_DIR, "alerts.log")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
SECURITY_SETTINGS = security_settings()

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sentinel Shield v2",
    description="Enterprise AI Data Governance Platform — Xavira Tech Labs",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Explicitly allow Vercel origins to talk to the Cloud Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=SECURITY_SETTINGS["allowed_origins"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.add_middleware(ZeroTrustAPIShieldMiddleware)

# Mount sub-routers
app.include_router(license_router)
app.include_router(integrations_router)
app.include_router(shadow_ai_router)

# ── Shared instances ──────────────────────────────────────────────────────────
scanner = EnterpriseScanner()
india_scanner = IndiaPIIScanner()
identity_proxy = IdentityMaskingProxy(scanner, india_scanner)
semantic_dlp = SemanticDLP()
prompt_injection_detector = PromptInjectionDetector()
sentinel_check = SentinelCheck(scanner, india_scanner)
universal_proxy = UniversalProxy(identity_proxy)
evidence_reporter = EvidencePDFGenerator()
dpdp_engine = DPDPEngine()
exporter = AuditExporter()


def enforce_password_rotation(current_user: TokenPayload):
    if current_user.force_password_change:
        raise HTTPException(
            status_code=403,
            detail="FIRST_RUN_PASSWORD_CHANGE_REQUIRED",
        )


def enforce_active_user(current_user: TokenPayload, db: Session):
    user = db.query(User).filter(User.email == current_user.sub).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="USER_DISABLED_OR_NOT_FOUND")
    return user


def get_active_user(
    current_user: TokenPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenPayload:
    enforce_active_user(current_user, db)
    return current_user


def get_jwt_or_api_key_actor(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    x_sentinel_api_key: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> TokenPayload:
    """Accept dashboard JWTs or scoped app API keys for enterprise proxy integrations."""
    if credentials:
        current_user = verify_token(credentials.credentials)
        enforce_active_user(current_user, db)
        return current_user
    if not x_sentinel_api_key:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    key_hash = _hash_api_key(x_sentinel_api_key)
    api_key = db.query(APIKey).filter(APIKey.key_hash == key_hash, APIKey.is_active == True).first()
    if not api_key:
        raise HTTPException(status_code=401, detail="API_KEY_INVALID")
    if api_key.expires_at and api_key.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="API_KEY_EXPIRED")
    scopes = api_key.scopes or []
    if "proxy:inspect" not in scopes and "*" not in scopes:
        raise HTTPException(status_code=403, detail="API_KEY_SCOPE_DENIED")
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return TokenPayload(
        sub=f"api-key:{api_key.key_prefix}",
        email=f"{api_key.key_prefix}@api-key.local",
        role="STAFF",
        department=api_key.department or "API_CLIENT",
        tenant_id=api_key.tenant_id,
    )

# Vector store (lazy init, preserved from v1)
vectorstore = None

try:
    from langchain_ollama import OllamaEmbeddings
    embeddings = OllamaEmbeddings(model=os.getenv("OLLAMA_MODEL", "llama3.1"))
except Exception:
    embeddings = None


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global vectorstore
    init_db()
    policy_engine.reload()  # Load all YAML presets

    if embeddings and os.path.exists(CHROMA_DIR):
        try:
            from langchain_chroma import Chroma
            vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        except Exception:
            pass

    audit_ledger.log(
        action="SYSTEM_STARTUP",
        user_id="SYSTEM",
        user_role="SUPER_ADMIN",
        metadata={"version": "2.0.0"},
    )

    diagnostics = sentinel_check.run_all()
    audit_ledger.log(
        action="SELF_DIAGNOSTIC_BOOTSTRAP",
        user_id="SYSTEM",
        user_role="SUPER_ADMIN",
        policy_triggered=None if diagnostics.get("ready") else "BOOTSTRAP_DIAGNOSTIC_FAILURE",
        risk_score=0.0 if diagnostics.get("ready") else 9.0,
        metadata=diagnostics,
    )


# ── Schemas ───────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str
    department: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class MFAEnableRequest(BaseModel):
    code: str

class MFAVerifyRequest(BaseModel):
    email: str
    code: str

class LogoutRequest(BaseModel):
    revoke_current: bool = True

class UserCreateRequest(BaseModel):
    email: str
    full_name: Optional[str] = None
    role: Literal["SUPER_ADMIN", "DEPARTMENT_HEAD", "STAFF", "AUDITOR"] = "STAFF"
    department: Optional[str] = "GENERAL"
    tenant_id: Optional[str] = "default"

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Literal["SUPER_ADMIN", "DEPARTMENT_HEAD", "STAFF", "AUDITOR"]] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None

class PasswordResetResponse(BaseModel):
    status: str
    email: str
    temporary_password: str
    force_password_change: bool

class Query(BaseModel):
    prompt: str
    preferred_model: Optional[str] = None
    department: Optional[str] = None

class APIKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str] = ["proxy:inspect", "chat:ask"]
    department: Optional[str] = None
    expires_in_days: Optional[int] = 365

class APIKeyUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    scopes: Optional[list[str]] = None

class PolicySimulatorRequest(BaseModel):
    prompt: str
    department: Optional[str] = None
    preferred_model: Optional[str] = None

class EvidenceScheduleRequest(BaseModel):
    enabled: bool = True
    frequency: Literal["weekly", "monthly"] = "weekly"
    org_name: str = "Buyer Organization"
    tenant_id: str = "default"
    retention_days: int = 365

class PolicyUpdateRequest(BaseModel):
    department: str
    yaml_content: str

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    preferred_model: Optional[str] = None

class ProxyInspectRequest(BaseModel):
    text: str
    source_app: Optional[str] = "localhost"
    actor: Optional[str] = "dashboard"
    auto_redact: bool = True
    metadata: Optional[dict] = None

class EvidenceReportRequest(BaseModel):
    org_name: Optional[str] = "Buyer Organization"
    tenant_id: Optional[str] = "default"
    limit: int = 500
    primary_color: Optional[str] = "#047857"
    compliance_frameworks: Optional[list[str]] = None

class TenantBrandingRequest(BaseModel):
    company_name: str = "Buyer Organization"
    product_name: str = "Sentinel Shield"
    primary_color: str = "#10b981"
    compliance_frameworks: list[str] = ["DPDP_2026", "GDPR", "FedRAMP"]

class FirewallRuleRequest(BaseModel):
    name: str
    action: Literal["block", "redact", "warn", "force_local", "quarantine"] = "warn"
    pattern: str
    department: Optional[str] = "GLOBAL"
    severity: float = 5.0

class PolicyBundleRequest(BaseModel):
    bundle_name: str
    yaml_content: str
    target_scope: Optional[str] = "edge-nodes"

class MTLSWizardRequest(BaseModel):
    server_name: str = "sentinel-shield.local"
    ca_cert_path: str = "/etc/sentinel/ca.crt"
    client_cert_header: str = "X-SSL-Client-Fingerprint"
    upstream_url: str = "http://127.0.0.1:8000"

class ModelPullRequest(BaseModel):
    model: str = "llama3.1"

class SIEMExportRequest(BaseModel):
    target_url: Optional[str] = None
    event_type: str = "CISO_ALERT"

class PolicyBundleVerifyRequest(BaseModel):
    manifest: dict
    signature: str

class ThreatModelRequest(BaseModel):
    deployment_name: str = "Sentinel Shield Production"
    internet_exposed: bool = False
    cloud_llm_enabled: bool = False
    mTLS_enforced: bool = True


# ── Auth Endpoints (V2 Professional) ──────────────────────────────────────────
@app.post("/api/v2/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates a user and returns a secure JWT access token."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Sentinel Identity Failure: Access Denied")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Sentinel Identity Disabled")
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    force_password_change = bool((getattr(user, "metadata_", None) or {}).get("force_password_change"))
    token = create_access_token(data={
        "sub": user.email,
        "email": user.email,
        "role": user.role,
        "department": user.department,
        "tenant_id": user.tenant_id,
        "force_password_change": force_password_change,
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "force_password_change": force_password_change,
        "user": {
            "email": user.email,
            "role": user.role,
            "name": user.full_name,
            "dept": user.department
        }
    }

@app.post("/api/v2/auth/register")
def register(req: LoginRequest, db: Session = Depends(get_db)):
    """Self-registration for new platform users."""
    if os.getenv("ENABLE_SELF_REGISTRATION", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="SELF_REGISTRATION_DISABLED")
    expected_invite = os.getenv("REGISTRATION_INVITE_TOKEN", "").strip()
    provided_invite = (req.department or "").split(":", 1)
    if expected_invite:
        if len(provided_invite) != 2 or not secrets.compare_digest(provided_invite[0], expected_invite):
            raise HTTPException(status_code=403, detail="REGISTRATION_INVITE_REQUIRED")
        req.department = provided_invite[1] or "GENERAL"
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Identity Conflict: User already exists")
    
    new_user = User(
        id=str(uuid.uuid4()),
        email=req.email,
        full_name=req.email.split("@")[0].title(),
        hashed_password=pwd_context.hash(req.password),
        role="STAFF", # Default role for self-reg
        department=req.department or "GENERAL"
    )
    db.add(new_user)
    db.commit()

    return {"status": "SUCCESS", "message": "Pro Account Created: Please proceed to login."}

@app.post("/api/v2/auth/logout")
def logout(current_user: TokenPayload = Depends(get_active_user)):
    """Revoke the current JWT for this process."""
    if current_user.jti:
        revoke_token_id(current_user.jti, current_user.exp)
    return {"status": "SUCCESS", "message": "Session revoked."}


def _public_user(user: User) -> dict:
    metadata = getattr(user, "metadata_", None) or {}
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "department": user.department,
        "tenant_id": user.tenant_id,
        "is_active": bool(user.is_active),
        "mfa_enabled": bool(user.mfa_enabled),
        "force_password_change": bool(metadata.get("force_password_change")),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(f"{SECURITY_SETTINGS['license_master_secret']}:{raw_key}".encode()).hexdigest()


def _public_api_key(api_key: APIKey) -> dict:
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "scopes": api_key.scopes or [],
        "department": api_key.department,
        "tenant_id": api_key.tenant_id,
        "created_by": api_key.created_by,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "is_active": bool(api_key.is_active),
    }


def _totp_code(secret: str, timestep: Optional[int] = None) -> str:
    timestep = timestep if timestep is not None else int(datetime.now(timezone.utc).timestamp() // 30)
    key = base64.b32decode(secret, casefold=True)
    msg = timestep.to_bytes(8, "big")
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    token = int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF
    return str(token % 1_000_000).zfill(6)


def _verify_totp(secret: str, code: str) -> bool:
    cleaned = str(code).strip().replace(" ", "")
    now_step = int(datetime.now(timezone.utc).timestamp() // 30)
    return any(secrets.compare_digest(_totp_code(secret, now_step + drift), cleaned) for drift in (-1, 0, 1))


@app.get("/api/v2/admin/users")
def list_users(
    current_user: TokenPayload = Depends(get_active_user),
    db: Session = Depends(get_db),
):
    rbac.enforce(current_user.role, Permission.VIEW_ALL_USERS)
    query = db.query(User)
    if current_user.role == "DEPARTMENT_HEAD":
        query = query.filter(User.department == current_user.department)
    users = query.order_by(User.created_at.desc()).all()
    return {"users": [_public_user(user) for user in users]}


@app.post("/api/v2/admin/users")
def create_user(
    req: UserCreateRequest,
    current_user: TokenPayload = Depends(get_active_user),
    db: Session = Depends(get_db),
):
    rbac.enforce(current_user.role, Permission.MANAGE_USERS)
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="USER_ALREADY_EXISTS")
    temporary_password = secrets.token_urlsafe(24)
    user = User(
        id=str(uuid.uuid4()),
        email=req.email,
        full_name=req.full_name or req.email.split("@")[0].replace(".", " ").title(),
        hashed_password=pwd_context.hash(temporary_password),
        role=req.role,
        department=req.department or "GENERAL",
        tenant_id=req.tenant_id or current_user.tenant_id or "default",
        is_active=True,
        metadata_={"force_password_change": True, "created_by": current_user.sub},
    )
    db.add(user)
    db.commit()
    audit_ledger.log(
        action="ADMIN_USER_CREATED",
        user_id=current_user.sub,
        user_role=current_user.role,
        department=current_user.department,
        tenant_id=current_user.tenant_id,
        metadata={"target_user": req.email, "target_role": req.role},
    )
    return {
        "user": _public_user(user),
        "temporary_password": temporary_password,
        "force_password_change": True,
    }


@app.patch("/api/v2/admin/users/{user_id}")
def update_user(
    user_id: str,
    req: UserUpdateRequest,
    current_user: TokenPayload = Depends(get_active_user),
    db: Session = Depends(get_db),
):
    rbac.enforce(current_user.role, Permission.MANAGE_USERS)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    if user.email == current_user.sub and req.is_active is False:
        raise HTTPException(status_code=400, detail="CANNOT_DISABLE_SELF")
    if req.full_name is not None:
        user.full_name = req.full_name
    if req.role is not None:
        user.role = req.role
    if req.department is not None:
        user.department = req.department
    if req.is_active is not None:
        user.is_active = req.is_active
    db.commit()
    audit_ledger.log(
        action="ADMIN_USER_UPDATED",
        user_id=current_user.sub,
        user_role=current_user.role,
        department=current_user.department,
        tenant_id=current_user.tenant_id,
        metadata={"target_user": user.email, "is_active": user.is_active, "role": user.role},
    )
    return {"user": _public_user(user)}


@app.post("/api/v2/admin/users/{user_id}/reset-password", response_model=PasswordResetResponse)
def reset_user_password(
    user_id: str,
    current_user: TokenPayload = Depends(get_active_user),
    db: Session = Depends(get_db),
):
    rbac.enforce(current_user.role, Permission.MANAGE_USERS)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    temporary_password = secrets.token_urlsafe(24)
    user.hashed_password = pwd_context.hash(temporary_password)
    meta = dict(user.metadata_ or {})
    meta["force_password_change"] = True
    meta["password_reset_by"] = current_user.sub
    meta["password_reset_at"] = datetime.now(timezone.utc).isoformat()
    user.metadata_ = meta
    db.commit()
    audit_ledger.log(
        action="ADMIN_PASSWORD_RESET",
        user_id=current_user.sub,
        user_role=current_user.role,
        department=current_user.department,
        tenant_id=current_user.tenant_id,
        metadata={"target_user": user.email},
    )
    return PasswordResetResponse(
        status="SUCCESS",
        email=user.email,
        temporary_password=temporary_password,
        force_password_change=True,
    )

@app.post("/api/v2/auth/change-password")
def change_password(
    req: ChangePasswordRequest,
    current_user: TokenPayload = Depends(get_active_user),
    db: Session = Depends(get_db),
):
    """Rotate first-run temporary password and clear forced-change state."""
    if len(req.new_password) < 14:
        raise HTTPException(status_code=400, detail="Password must be at least 14 characters.")
    user = enforce_active_user(current_user, db)
    if not user or not pwd_context.verify(req.current_password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password invalid")
    user.hashed_password = pwd_context.hash(req.new_password)
    meta = dict(user.metadata_ or {})
    meta["force_password_change"] = False
    meta["password_changed_at"] = datetime.now(timezone.utc).isoformat()
    user.metadata_ = meta
    db.commit()
    audit_ledger.log(
        action="FIRST_RUN_PASSWORD_CHANGED",
        user_id=current_user.sub,
        user_role=current_user.role,
        department=current_user.department,
        tenant_id=current_user.tenant_id,
    )
    return {"status": "SUCCESS", "message": "Password changed. Re-login required."}


@app.post("/api/v2/auth/mfa/setup")
def setup_mfa(current_user: TokenPayload = Depends(get_active_user), db: Session = Depends(get_db)):
    """Create a TOTP secret. Buyer must verify it before MFA is marked enabled."""
    user = enforce_active_user(current_user, db)
    secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
    secret = secret + ("=" * ((8 - len(secret) % 8) % 8))
    meta = dict(user.metadata_ or {})
    meta["mfa_pending_secret"] = secret
    user.metadata_ = meta
    db.commit()
    issuer = "Xavira Tech Labs Sentinel Shield"
    uri = f"otpauth://totp/{issuer}:{user.email}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
    audit_ledger.log(
        action="MFA_SETUP_STARTED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
    )
    return {"secret": secret, "otpauth_uri": uri, "status": "VERIFY_REQUIRED"}


@app.post("/api/v2/auth/mfa/enable")
def enable_mfa(req: MFAEnableRequest, current_user: TokenPayload = Depends(get_active_user), db: Session = Depends(get_db)):
    user = enforce_active_user(current_user, db)
    meta = dict(user.metadata_ or {})
    secret = meta.get("mfa_pending_secret")
    if not secret or not _verify_totp(secret, req.code):
        raise HTTPException(status_code=400, detail="MFA_CODE_INVALID")
    meta["mfa_secret"] = secret
    meta.pop("mfa_pending_secret", None)
    user.metadata_ = meta
    user.mfa_enabled = True
    db.commit()
    audit_ledger.log(
        action="MFA_ENABLED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
    )
    return {"status": "MFA_ENABLED"}


@app.post("/api/v2/auth/mfa/verify")
def verify_mfa(req: MFAVerifyRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    meta = dict(getattr(user, "metadata_", None) or {}) if user else {}
    secret = meta.get("mfa_secret")
    if not user or not user.mfa_enabled or not secret or not _verify_totp(secret, req.code):
        raise HTTPException(status_code=401, detail="MFA_VERIFY_FAILED")
    return {"status": "MFA_VERIFIED"}


@app.get("/api/v2/admin/api-keys")
def list_api_keys(current_user: TokenPayload = Depends(get_active_user), db: Session = Depends(get_db)):
    rbac.enforce(current_user.role, Permission.MANAGE_USERS)
    keys = db.query(APIKey).filter(APIKey.tenant_id == current_user.tenant_id).order_by(APIKey.created_at.desc()).all()
    return {"api_keys": [_public_api_key(key) for key in keys]}


@app.post("/api/v2/admin/api-keys")
def create_api_key(req: APIKeyCreateRequest, current_user: TokenPayload = Depends(get_active_user), db: Session = Depends(get_db)):
    rbac.enforce(current_user.role, Permission.MANAGE_USERS)
    raw_key = f"sshield_{secrets.token_urlsafe(32)}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_in_days or 365)
    api_key = APIKey(
        id=str(uuid.uuid4()),
        tenant_id=current_user.tenant_id,
        name=req.name,
        key_prefix=raw_key[:18],
        key_hash=_hash_api_key(raw_key),
        scopes=req.scopes,
        department=req.department or current_user.department,
        created_by=current_user.sub,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    audit_ledger.log(
        action="API_KEY_CREATED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        metadata={"name": req.name, "scopes": req.scopes, "key_prefix": api_key.key_prefix},
    )
    return {"api_key": _public_api_key(api_key), "secret": raw_key, "copy_once": True}


@app.patch("/api/v2/admin/api-keys/{key_id}")
def update_api_key(key_id: str, req: APIKeyUpdateRequest, current_user: TokenPayload = Depends(get_active_user), db: Session = Depends(get_db)):
    rbac.enforce(current_user.role, Permission.MANAGE_USERS)
    api_key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.tenant_id == current_user.tenant_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API_KEY_NOT_FOUND")
    if req.is_active is not None:
        api_key.is_active = req.is_active
    if req.scopes is not None:
        api_key.scopes = req.scopes
    db.commit()
    audit_ledger.log(
        action="API_KEY_UPDATED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        metadata={"key_prefix": api_key.key_prefix, "is_active": api_key.is_active},
    )
    return {"api_key": _public_api_key(api_key)}


@app.delete("/api/v2/admin/api-keys/{key_id}")
def revoke_api_key(key_id: str, current_user: TokenPayload = Depends(get_active_user), db: Session = Depends(get_db)):
    rbac.enforce(current_user.role, Permission.MANAGE_USERS)
    api_key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.tenant_id == current_user.tenant_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API_KEY_NOT_FOUND")
    api_key.is_active = False
    db.commit()
    audit_ledger.log(
        action="API_KEY_REVOKED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        metadata={"key_prefix": api_key.key_prefix},
    )
    return {"status": "REVOKED", "key_prefix": api_key.key_prefix}
    
@app.get("/api/v2/auth/master-seed")
def force_seed():
    raise HTTPException(status_code=410, detail="Master seed endpoint removed. Use first-run bootstrap credentials from server logs.")

@app.post("/api/v2/chat")
def chat(req: ChatRequest, current_user: TokenPayload = Depends(get_active_user)):
    """
    Secure local conversational AI endpoint.
    Governs the prompt (redacts PII) and routes to the selected AI model.
    """
    enforce_password_rotation(current_user)
    # 1. Govern the prompt
    governed_prompt = india_scanner.redact(req.message)
    
    # 2. Add system context (Role-play as Sentinel Auditor)
    system_ctx = (
        f"User Role: {current_user.role}. Department: {current_user.department}. "
        "You are Vault AI, a private local assistant running inside Sentinel Shield. "
        "Answer broadly and helpfully like a premium AI assistant, while preserving "
        "all masked/pseudonymized privacy tokens. Never claim to be a cloud API model."
    )
    
    # 3. Route to AI Gateway
    try:
        result = model_router.route(
            prompt=governed_prompt,
            context=req.context,
            system_prompt=system_ctx,
            preferred_model=req.preferred_model
        )
        
        # 4. Audit the AI interaction
        audit_ledger.log(
            action="AI_CHAT_INTERACTION",
            user_id=current_user.sub,
            user_role=current_user.role,
            department=current_user.department,
            tenant_id=current_user.tenant_id,
            prompt_text=req.message,
            model_queried=result.get("model_used"),
            metadata={"resource": "SENTINEL_CHAT", "status": "SUCCESS"}
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/chat/stream")
def chat_stream(req: ChatRequest, current_user: TokenPayload = Depends(get_active_user)):
    """Stream Vault AI responses as server-sent events for a premium local-AI feel."""
    enforce_password_rotation(current_user)
    rbac.enforce(current_user.role, Permission.RUN_AI_QUERY)
    governed_prompt = india_scanner.redact(req.message)
    system_ctx = (
        f"User Role: {current_user.role}. Department: {current_user.department}. "
        "You are Vault AI, a private local assistant running inside Sentinel Shield."
    )

    def event_stream():
        try:
            result = model_router.route(
                prompt=governed_prompt,
                context=req.context,
                system_prompt=system_ctx,
                preferred_model=req.preferred_model,
            )
            answer = str(result.get("answer", ""))
            for word in answer.split(" "):
                yield f"data: {json.dumps({'token': word + ' '})}\n\n"
            audit_ledger.log(
                action="AI_CHAT_STREAM",
                user_id=current_user.sub,
                user_role=current_user.role,
                department=current_user.department,
                tenant_id=current_user.tenant_id,
                prompt_text=req.message,
                model_queried=result.get("model_used"),
                metadata={"status": "SUCCESS"},
            )
            yield f"data: {json.dumps({'done': True, 'model_used': result.get('model_used')})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health():
    """Instant awake signal for Cloud monitoring."""
    return {"status": "awake", "engine": "Sentinel Shield v2.0"}

# ── Vault / Status Endpoints ──────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "sentinel-shield"}

@app.get("/")
async def root():
    return {
        "status": "online",
        "platform": "SENTINEL SHIELD",
        "version": "1.0.0",
        "signature": "BY XAVIRA TECH LABS",
        "message": "Vault Gateway is Secure. Welcome Commander."
    }

@app.get("/status")
def get_status(current_user: TokenPayload = Depends(get_active_user)):
    """System status + infra health. Requires valid JWT."""
    rbac.enforce(current_user.role, Permission.VIEW_VAULT_STATUS)

    data = {"processed_files": {}, "stats": {"leaks_blocked": 0, "hours_saved": 0}, "alerts": []}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "rb") as f:
                encrypted_data = f.read()
            raw_data = sentinel_crypto.decrypt_data(encrypted_data)
            data.update(json.loads(raw_data))
        except Exception:
            pass

    # Audit stats
    audit_stats = audit_ledger.get_summary_stats()
    chain = audit_ledger.verify_chain()

    try:
        st = os.statvfs(BASE_DIR) if platform.system() != "Windows" else None
        free = float(st.f_bavail * st.f_frsize) if st else 0.0
        total = float(st.f_blocks * st.f_frsize) if st else 1.0
        disk_info = {
            "disk_used_pct": round(float(((total - free) / total) * 100.0), 1),
            "disk_free_gb": round(float(free / (1024**3)), 2),
        }
    except Exception:
        disk_info = {"disk_used_pct": "??", "disk_free_gb": "??"}

    return {
        **data,
        "infra": {
            **disk_info,
            "ai_pulse": "HEALTHY" if vectorstore else "INITIALIZING",
            "hardware_id": sentinel_crypto.get_machine_id()[:8] + "...",
            "deployment_mode": os.getenv("DEPLOYMENT_MODE", "airgap").upper(),
        },
        "audit": {
            "total_events": audit_stats.get("total_events", 0),
            "total_redactions": audit_stats.get("total_redactions", 0),
            "high_risk_blocked": audit_stats.get("high_risk_events", 0),
            "chain_integrity": chain.get("valid", False),
        },
        "policies": policy_engine.list_policies(),
        "available_models": model_router.list_available(),
    }


@app.get("/api/v2/system/diagnostics")
def system_diagnostics(current_user: TokenPayload = Depends(get_active_user)):
    """Single localhost proof point for local LLM, ledger, and scanner readiness."""
    rbac.enforce(current_user.role, Permission.VIEW_VAULT_STATUS)
    return sentinel_check.run_all()


@app.post("/api/v2/proxy/inspect")
def proxy_inspect(req: ProxyInspectRequest, current_user: TokenPayload = Depends(get_jwt_or_api_key_actor)):
    """Universal before/after proxy preview for Slack, Teams, CRM, and custom apps."""
    enforce_password_rotation(current_user)
    rbac.enforce(current_user.role, Permission.RUN_AI_QUERY)
    actor = req.actor or current_user.sub
    result = universal_proxy.inspect(
        text=req.text,
        source_app=req.source_app or "localhost",
        actor=actor,
        auto_redact=req.auto_redact,
        metadata=req.metadata or {"department": current_user.department},
    )
    audit_ledger.log(
        action="UNIVERSAL_PROXY_INSPECT",
        user_id=current_user.sub,
        user_role=current_user.role,
        department=current_user.department,
        tenant_id=current_user.tenant_id,
        prompt_text=req.text,
        policy_triggered=result.get("policy_triggered"),
        risk_score=result.get("sensitivity_score"),
        metadata={"source_app": result.get("source_app"), "auto_redact": result.get("auto_redact")},
    )
    return result


@app.post("/ask")
def query_vault(req: Query, current_user: TokenPayload = Depends(get_active_user)):
    """
    Secure AI Query with:
     1. RBAC permission check
     2. India PII + Presidio dual-layer scan + redaction
     3. Policy engine evaluation (WARN / REDACT / BLOCK)
     4. Governed local model routing through Ollama
     5. Immutable audit logging
    """
    global vectorstore

    enforce_password_rotation(current_user)
    rbac.enforce(current_user.role, Permission.RUN_AI_QUERY)

    # ── Step 1: Dual-Layer Scan ──────────────────────────────────────────────
    findings_us   = scanner.scan_content(req.prompt)
    findings_india = india_scanner.scan(req.prompt)
    findings_semantic = semantic_dlp.scan(req.prompt)
    findings_injection = prompt_injection_detector.scan(req.prompt)
    all_findings   = findings_us + findings_india + findings_semantic + findings_injection
    risk_score     = max(
        scanner.calculate_risk_score(findings_us),
        semantic_dlp.sensitivity_score(findings_semantic),
    ) + prompt_injection_detector.risk_score(findings_injection)
    risk_score = min(10.0, risk_score)

    risk_event = oracle_risk_engine.record_interception(
        actor_id=current_user.sub,
        findings=all_findings,
        sensitivity_score=risk_score,
        policy_triggered=None,
        tenant_id=current_user.tenant_id,
    )

    if risk_event.get("quarantined"):
        audit_ledger.log(
            action="USER_AUTO_QUARANTINED",
            user_id=current_user.sub,
            user_role=current_user.role,
            department=req.department or current_user.department,
            tenant_id=current_user.tenant_id,
            prompt_text=req.prompt,
            policy_triggered=risk_event.get("quarantine_reason"),
            risk_score=risk_score,
            metadata={"ciso_alert": risk_event.get("ciso_alert")},
        )
        raise HTTPException(status_code=423, detail=risk_event)

    if findings_injection:
        audit_ledger.log(
            action="PROMPT_INJECTION_BLOCKED",
            user_id=current_user.sub,
            user_role=current_user.role,
            department=req.department or current_user.department,
            tenant_id=current_user.tenant_id,
            prompt_text=req.prompt,
            policy_triggered="LLM_FINGERPRINT_PROMPT_INJECTION",
            risk_score=risk_score,
            metadata={"findings": findings_injection, "oracle": risk_event},
        )
        raise HTTPException(
            status_code=403,
            detail={
                "action": "BLOCKED",
                "reason": "Prompt injection or jailbreak fingerprint detected",
                "findings": findings_injection,
                "risk": risk_event,
            },
        )

    # ── Step 2: DPDP Classification ─────────────────────────────────────────
    dpdp_meta = dpdp_engine.classify_text(req.prompt)

    # ── Step 3: Policy Evaluation ────────────────────────────────────────────
    dept = req.department or current_user.department
    policy_decision = policy_engine.evaluate(
        prompt=req.prompt,
        findings=all_findings,
        risk_score=risk_score,
        department=dept,
        model=req.preferred_model,
    )

    if policy_decision.action == EnforcementLevel.BLOCK:
        audit_ledger.log(
            action="PROMPT_BLOCKED",
            user_id=current_user.sub,
            user_role=current_user.role,
            department=dept,
            tenant_id=current_user.tenant_id,
            prompt_text=req.prompt,
            redactions_applied=[p for p in policy_decision.triggered_rules],
            policy_triggered=policy_decision.block_reason,
            model_queried=req.preferred_model,
            risk_score=risk_score,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "action": "BLOCKED",
                "reason": policy_decision.block_reason,
                "triggered_rules": policy_decision.triggered_rules,
            }
        )

    # ── Step 4: Identity Masking Proxy ───────────────────────────────────────
    governed = identity_proxy.govern(req.prompt, department=dept)
    safe_prompt = governed.protected_prompt
    redaction_tags = governed.pseudonyms
    risk_score = max(risk_score, governed.sensitivity_score)

    # ── Step 5: RAG Context ──────────────────────────────────────────────────
    context = ""
    if vectorstore:
        try:
            results = vectorstore.similarity_search(safe_prompt, k=4)
            raw_ctx = "\n\n".join([doc.page_content for doc in results])
            ctx_findings = scanner.scan_content(raw_ctx)
            context = scanner.redact_content(raw_ctx, ctx_findings)
            context = india_scanner.redact(context)
        except Exception:
            context = ""

    # ── Step 6: Model Gateway ────────────────────────────────────────────────
    if not policy_decision.model_allowed:
        raise HTTPException(status_code=403, detail="Model not in policy allowlist for your department")

    result = model_router.route(
        prompt=safe_prompt,
        preferred_model=req.preferred_model,
        department=dept,
        context=context,
        sensitivity_score=risk_score,
    )
    raw_answer = result.get("answer", "")

    # ── Step 7: Outbound DLP Scan (Prevention Layer) ────────────────────────
    # Scans the AI's response for any hallucinated or leaked PII before sending
    answer_findings_us = scanner.scan_content(raw_answer)
    answer_findings_in = india_scanner.scan(raw_answer)
    
    safe_answer = scanner.redact_content(raw_answer, answer_findings_us)
    safe_answer = india_scanner.redact(safe_answer)
    
    is_response_redacted = bool(answer_findings_us or answer_findings_in)

    # ── Step 8: Audit ─────────────────────────────────────────────────────────
    audit_ledger.log(
        action="AI_QUERY",
        user_id=current_user.sub,
        user_role=current_user.role,
        department=dept,
        tenant_id=current_user.tenant_id,
        prompt_text=req.prompt,
        redactions_applied=redaction_tags,
        policy_triggered=", ".join(policy_decision.triggered_rules) if policy_decision.triggered_rules else None,
        model_queried=result.get("model_used"),
        risk_score=risk_score,
        metadata={
            "dpdp": dpdp_meta, 
            "fallback": result.get("fallback_used"),
            "airgap_forced": result.get("airgap_forced"),
            "pseudonym_vault": governed.pseudonym_vault,
            "response_leaks_prevented": is_response_redacted,
            "semantic_dlp": findings_semantic,
            "oracle_risk": risk_event,
        },
    )

    return {
        "answer": safe_answer,
        "model_used": result.get("model_used"),
        "findings_alert": "SENSITIVE_DATA_REDACTED" if (all_findings or is_response_redacted) else "CLEAN",
        "redactions_applied": len(redaction_tags) + (1 if is_response_redacted else 0),
        "policy_warnings": policy_decision.warnings,
        "risk_score": risk_score,
        "user_risk_score": risk_event.get("risk_score"),
        "semantic_dlp_findings": findings_semantic,
        "dpdp_categories": dpdp_meta.get("dpdp_categories", []),
        "outbound_secure": True,
    }


@app.get("/api/v2/risk/heatmap")
def risk_heatmap(current_user: TokenPayload = Depends(get_active_user)):
    """Oracle dashboard API: heatmap-ready user risk and quarantine state."""
    rbac.enforce(current_user.role, Permission.VIEW_AUDIT_LOG)
    return oracle_risk_engine.heatmap(tenant_id=current_user.tenant_id)


@app.post("/api/v2/policy/simulate")
def policy_simulator(req: PolicySimulatorRequest, current_user: TokenPayload = Depends(get_active_user)):
    """Dry-run policy, DLP, injection, and model-routing decisions without sending to an LLM."""
    rbac.enforce(current_user.role, Permission.VIEW_POLICY)
    dept = req.department or current_user.department
    findings_us = scanner.scan_content(req.prompt)
    findings_india = india_scanner.scan(req.prompt)
    findings_semantic = semantic_dlp.scan(req.prompt)
    findings_injection = prompt_injection_detector.scan(req.prompt)
    all_findings = findings_us + findings_india + findings_semantic + findings_injection
    risk_score = min(10.0, max(
        scanner.calculate_risk_score(findings_us),
        semantic_dlp.sensitivity_score(findings_semantic),
    ) + prompt_injection_detector.risk_score(findings_injection))
    decision = policy_engine.evaluate(
        prompt=req.prompt,
        findings=all_findings,
        risk_score=risk_score,
        department=dept,
        model=req.preferred_model,
    )
    governed = identity_proxy.govern(req.prompt, department=dept)
    recommended_route = "local_airgap" if max(risk_score, governed.sensitivity_score) > 7 else "policy_default"
    return {
        "action": decision.action.value if hasattr(decision.action, "value") else str(decision.action),
        "risk_score": max(risk_score, governed.sensitivity_score),
        "triggered_rules": decision.triggered_rules,
        "warnings": decision.warnings,
        "model_allowed": decision.model_allowed,
        "recommended_route": recommended_route,
        "redacted_preview": governed.protected_prompt,
        "findings_count": len(all_findings),
        "semantic_findings": findings_semantic,
        "prompt_injection_findings": findings_injection,
    }


@app.get("/api/v2/enterprise/incidents/{actor_hash}")
def incident_timeline(actor_hash: str, current_user: TokenPayload = Depends(get_active_user)):
    """CISO incident timeline for a high-risk actor hash."""
    rbac.enforce(current_user.role, Permission.VIEW_AUDIT_LOG)
    entries = audit_ledger.get_entries(limit=10000, tenant_id=current_user.tenant_id)
    timeline = [
        {
            "timestamp": entry.get("timestamp"),
            "action": entry.get("action"),
            "policy_triggered": entry.get("policy_triggered"),
            "risk_score": entry.get("risk_score"),
            "model_queried": entry.get("model_queried"),
            "entry_hash": entry.get("entry_hash"),
        }
        for entry in entries
        if entry.get("actor_hash") == actor_hash or (entry.get("metadata") or {}).get("actor_hash") == actor_hash
    ]
    certificate = hashlib.sha256(json.dumps(timeline, sort_keys=True).encode()).hexdigest()
    return {"actor_hash": actor_hash, "events": timeline, "total": len(timeline), "certificate": certificate}

@app.get("/api/v2/enterprise/models")
def model_management(current_user: TokenPayload = Depends(get_active_user)):
    """Model Management Center: local Ollama model inventory and gateway status."""
    rbac.enforce(current_user.role, Permission.VIEW_VAULT_STATUS)
    models = []
    try:
        import requests
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        resp = requests.get(f"{base}/api/tags", timeout=2)
        if resp.ok:
            models = resp.json().get("models", [])
    except Exception:
        models = []
    return {
        "default_model": os.getenv("OLLAMA_MODEL", "llama3.1"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "gateway_adapters": model_router.list_available(),
        "installed_models": models,
        "install_command": "ollama pull llama3.1",
        "model_pull_enabled": os.getenv("ENABLE_MODEL_PULL", "false").lower() == "true",
    }

@app.post("/api/v2/enterprise/models/pull")
def pull_model(req: ModelPullRequest, current_user: TokenPayload = Depends(get_active_user)):
    """Disabled-by-default model pull job for controlled local model onboarding."""
    rbac.enforce(current_user.role, Permission.MANAGE_USERS)
    if os.getenv("ENABLE_MODEL_PULL", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="MODEL_PULL_DISABLED")
    if not req.model.replace(":", "").replace(".", "").replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="INVALID_MODEL_NAME")
    import subprocess
    completed = subprocess.run(["ollama", "pull", req.model], capture_output=True, text=True, timeout=1800)
    audit_ledger.log(
        action="MODEL_PULL_REQUESTED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        metadata={"model": req.model, "returncode": completed.returncode},
    )
    return {"status": "SUCCESS" if completed.returncode == 0 else "FAILED", "model": req.model, "output": completed.stdout[-2000:], "error": completed.stderr[-2000:]}

@app.get("/api/v2/enterprise/version")
def release_version(current_user: TokenPayload = Depends(get_active_user)):
    rbac.enforce(current_user.role, Permission.VIEW_VAULT_STATUS)
    release_path = os.path.join(BASE_DIR, "release.json")
    data = {}
    if os.path.exists(release_path):
        with open(release_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    try:
        import subprocess
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=BASE_DIR, text=True, timeout=2).strip()
    except Exception:
        commit = os.getenv("RELEASE_COMMIT", "unknown")
    data.update({
        "commit": commit,
        "deployment_mode": os.getenv("DEPLOYMENT_MODE", "airgap"),
        "seal_state": "sealed" if all(os.getenv(k) for k in ("JWT_SECRET_KEY", "LICENSE_MASTER_SECRET", "ACTOR_HASH_SALT", "LEDGER_MASTER_SALT")) else "unsealed",
    })
    return data

@app.get("/api/v2/enterprise/reports")
def evidence_report_history(current_user: TokenPayload = Depends(get_active_user)):
    """Evidence Report History: generated PDF/text evidence artifacts."""
    rbac.enforce(current_user.role, Permission.EXPORT_AUDIT_PDF)
    export_dir = os.path.join(BASE_DIR, "logs", "exports")
    os.makedirs(export_dir, exist_ok=True)
    reports = []
    for name in sorted(os.listdir(export_dir), reverse=True):
        path = os.path.join(export_dir, name)
        if not os.path.isfile(path):
            continue
        stat = os.stat(path)
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
        reports.append({
            "name": name,
            "path": path,
            "size_bytes": stat.st_size,
            "generated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "certificate": digest,
            "download_url": f"/api/v2/enterprise/reports/{name}",
        })
    return {"reports": reports[:100]}

@app.get("/api/v2/enterprise/reports/{filename}")
def download_evidence_report(filename: str, current_user: TokenPayload = Depends(get_active_user)):
    rbac.enforce(current_user.role, Permission.EXPORT_AUDIT_PDF)
    safe_name = os.path.basename(filename)
    path = os.path.join(BASE_DIR, "logs", "exports", safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="REPORT_NOT_FOUND")
    return FileResponse(path, filename=safe_name)

@app.get("/api/v2/enterprise/alerts")
def ciso_alert_center(current_user: TokenPayload = Depends(get_active_user)):
    """CISO Alert Center: high-risk actors, prompt injections, and quarantine alerts."""
    rbac.enforce(current_user.role, Permission.VIEW_AUDIT_LOG)
    heatmap = oracle_risk_engine.heatmap(tenant_id=current_user.tenant_id)
    alerts = []
    for actor in heatmap.get("actors", []):
        if actor.get("quarantined") or actor.get("risk_score", 0) >= 50 or actor.get("injection_attempts_last_hour", 0):
            alerts.append({
                "id": actor.get("actor_hash"),
                "severity": "CRITICAL" if actor.get("quarantined") else "HIGH",
                "type": "AUTO_QUARANTINE" if actor.get("quarantined") else "RISK_SPIKE",
                "actor_hash": actor.get("actor_hash"),
                "risk_score": actor.get("risk_score"),
                "reason": actor.get("quarantine_reason") or "High-risk activity detected",
                "created_at": actor.get("last_seen"),
                "status": "OPEN",
            })
    return {"alerts": alerts, "total": len(alerts)}

@app.post("/api/v2/enterprise/alerts/export")
def export_alerts_to_siem(req: SIEMExportRequest, current_user: TokenPayload = Depends(get_active_user)):
    """Send critical alerts to a generic SIEM/webhook endpoint when configured."""
    rbac.enforce(current_user.role, Permission.VIEW_AUDIT_LOG)
    target_url = req.target_url or os.getenv("SIEM_WEBHOOK_URL") or os.getenv("SLACK_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL")
    if not target_url:
        raise HTTPException(status_code=400, detail="SIEM_WEBHOOK_URL_NOT_CONFIGURED")
    alerts = ciso_alert_center(current_user).get("alerts", [])
    try:
        import requests
        resp = requests.post(target_url, json={"event_type": req.event_type, "alerts": alerts}, timeout=8)
        ok = 200 <= resp.status_code < 300
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SIEM_EXPORT_FAILED: {exc}")
    audit_ledger.log(
        action="SIEM_ALERT_EXPORT",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        metadata={"alert_count": len(alerts), "target_configured": True, "success": ok},
    )
    return {"status": "SENT" if ok else "FAILED", "alert_count": len(alerts)}

@app.get("/api/v2/enterprise/quarantine")
def quarantine_management(current_user: TokenPayload = Depends(get_active_user)):
    rbac.enforce(current_user.role, Permission.VIEW_AUDIT_LOG)
    heatmap = oracle_risk_engine.heatmap(tenant_id=current_user.tenant_id)
    return {"actors": [a for a in heatmap.get("actors", []) if a.get("quarantined")]}

@app.post("/api/v2/enterprise/quarantine/{actor_hash}/release")
def release_quarantine(actor_hash: str, current_user: TokenPayload = Depends(get_active_user)):
    """Manual release is audit-only for v1; risk score decays naturally as the 1h window expires."""
    rbac.enforce(current_user.role, Permission.MANAGE_USERS)
    audit_ledger.log(
        action="QUARANTINE_RELEASE_REVIEWED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        policy_triggered="MANUAL_QUARANTINE_REVIEW",
        metadata={"actor_hash": actor_hash, "mode": "review_recorded"},
    )
    return {"status": "REVIEW_RECORDED", "actor_hash": actor_hash, "note": "Risk quarantine expires as the one-hour window decays."}

@app.post("/api/v2/enterprise/policy-bundles/sign")
def sign_policy_bundle(req: PolicyBundleRequest, current_user: TokenPayload = Depends(get_active_user)):
    """Global Policy Sync: create a signed bundle manifest; does not auto-apply remote policy."""
    rbac.enforce(current_user.role, Permission.EDIT_GLOBAL_POLICY)
    payload = {
        "bundle_name": req.bundle_name,
        "target_scope": req.target_scope,
        "yaml_sha256": hashlib.sha256(req.yaml_content.encode()).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user.sub,
    }
    signature = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    bundle_dir = os.path.join(BASE_DIR, "logs", "policy_bundles")
    os.makedirs(bundle_dir, exist_ok=True)
    path = os.path.join(bundle_dir, f"{req.bundle_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"manifest": payload, "signature": signature, "yaml_content": req.yaml_content}, f, indent=2)
    return {"manifest": payload, "signature": signature, "file": path, "apply_mode": "manual-review-required"}

@app.post("/api/v2/enterprise/policy-bundles/verify")
def verify_policy_bundle(req: PolicyBundleVerifyRequest, current_user: TokenPayload = Depends(get_active_user)):
    """Verify a signed policy bundle before edge rollout."""
    rbac.enforce(current_user.role, Permission.EDIT_GLOBAL_POLICY)
    expected = hashlib.sha256(json.dumps(req.manifest, sort_keys=True).encode()).hexdigest()
    valid = secrets.compare_digest(expected, req.signature)
    audit_ledger.log(
        action="POLICY_BUNDLE_VERIFIED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        policy_triggered=None if valid else "POLICY_BUNDLE_SIGNATURE_MISMATCH",
        risk_score=0.0 if valid else 8.0,
        metadata={"bundle_name": req.manifest.get("bundle_name"), "valid": valid},
    )
    return {"valid": valid, "expected_signature": expected, "provided_signature": req.signature}

@app.post("/api/v2/enterprise/firewall/rules")
def build_firewall_rule(req: FirewallRuleRequest, current_user: TokenPayload = Depends(get_active_user)):
    """No-code LLM Firewall Rules Builder: returns YAML a human can review and commit."""
    rbac.enforce(current_user.role, Permission.EDIT_GLOBAL_POLICY)
    yaml_rule = {
        "department": req.department or "GLOBAL",
        "policy_name": f"LLM Firewall - {req.name}",
        "rules": [{
            "name": req.name,
            "description": f"Generated firewall rule for pattern: {req.pattern}",
            "keywords": [req.pattern],
            "enforcement": "block" if req.action in ("block", "quarantine") else ("redact" if req.action == "redact" else "warn"),
            "risk_threshold": req.severity,
            "force_local_model": req.action == "force_local",
            "quarantine_actor": req.action == "quarantine",
        }],
    }
    import yaml
    return {"yaml": yaml.safe_dump(yaml_rule, sort_keys=False), "review_required": True}

@app.post("/api/v2/enterprise/mtls/nginx")
def mtls_deployment_wizard(req: MTLSWizardRequest, current_user: TokenPayload = Depends(get_active_user)):
    rbac.enforce(current_user.role, Permission.VIEW_VAULT_STATUS)
    config = f"""server {{
    listen 443 ssl;
    server_name {req.server_name};

    ssl_client_certificate {req.ca_cert_path};
    ssl_verify_client on;

    location / {{
        proxy_pass {req.upstream_url};
        proxy_set_header X-SSL-Client-Verify $ssl_client_verify;
        proxy_set_header {req.client_cert_header} $ssl_client_fingerprint;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Host $host;
    }}
}}
"""
    return {"nginx_config": config, "required_env": {"API_SHIELD_ENFORCE_MTLS": "true"}}

@app.post("/api/v2/enterprise/branding")
def tenant_branding_pack(req: TenantBrandingRequest, current_user: TokenPayload = Depends(get_active_user)):
    rbac.enforce(current_user.role, Permission.MANAGE_USERS)
    pack = req.model_dump()
    pack["generated_at"] = datetime.now(timezone.utc).isoformat()
    pack["report_title"] = f"{req.company_name} Sovereign AI Evidence Report"
    pack["dashboard_label"] = f"{req.product_name} by Xavira Tech Labs"
    branding_dir = os.path.join(BASE_DIR, "logs", "branding")
    os.makedirs(branding_dir, exist_ok=True)
    path = os.path.join(branding_dir, f"branding_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2)
    return {"branding": pack, "file": path}

@app.post("/api/v2/enterprise/ledger/anchor")
def anchor_ledger_root(current_user: TokenPayload = Depends(get_active_user)):
    """Off-box ledger anchoring v1: create a local anchor record ready for Git/S3/Object Lock upload."""
    rbac.enforce(current_user.role, Permission.EXPORT_AUDIT_PDF)
    entries = audit_ledger.get_entries(limit=100000, tenant_id=current_user.tenant_id)
    root = hashlib.sha256(json.dumps([e.get("entry_hash") or e.get("signature") for e in entries], sort_keys=True).encode()).hexdigest()
    anchor = {
        "tenant_id": current_user.tenant_id,
        "ledger_root": root,
        "entry_count": len(entries),
        "anchored_at": datetime.now(timezone.utc).isoformat(),
        "anchored_by": current_user.sub,
    }
    anchor_dir = os.path.join(BASE_DIR, "logs", "anchors")
    os.makedirs(anchor_dir, exist_ok=True)
    path = os.path.join(anchor_dir, f"ledger_anchor_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(anchor, f, indent=2)
    return {"anchor": anchor, "file": path, "next_steps": ["Upload to S3 Object Lock", "Commit to private Git", "Send to buyer SIEM"]}


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_existing_files(paths: list[str]) -> list[str]:
    return [path for path in paths if os.path.isfile(path)]


def _encrypt_backup_if_configured(zip_path: str) -> Optional[dict]:
    passphrase = os.getenv("BACKUP_ENCRYPTION_PASSPHRASE", "").strip()
    if not passphrase:
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception:
        return {"error": "cryptography AESGCM unavailable"}
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 250_000, dklen=32)
    aes = AESGCM(key)
    plaintext = open(zip_path, "rb").read()
    ciphertext = aes.encrypt(nonce, plaintext, None)
    enc_path = f"{zip_path}.enc"
    with open(enc_path, "wb") as f:
        f.write(b"SENTINELENC1" + salt + nonce + ciphertext)
    return {"encrypted_file": enc_path, "encrypted_sha256": _sha256_file(enc_path), "algorithm": "AES-256-GCM"}


@app.get("/api/v2/enterprise/readiness")
def enterprise_readiness(current_user: TokenPayload = Depends(get_active_user)):
    """Buyer due-diligence readiness score across secrets, ledger, CORS, policies, and local model posture."""
    rbac.enforce(current_user.role, Permission.VIEW_VAULT_STATUS)
    diagnostics = sentinel_check.run_all()
    chain = audit_ledger.verify_chain()
    policies = policy_engine.list_policies()
    settings = security_settings()
    controls = [
        {"name": "fail_closed_secrets", "ok": all(settings.get(k) for k in ("jwt_secret", "license_master_secret", "actor_hash_salt", "ledger_master_salt"))},
        {"name": "cors_wildcard_blocked", "ok": "*" not in settings.get("allowed_origins", [])},
        {"name": "ledger_integrity", "ok": bool(chain.get("valid"))},
        {"name": "pii_pattern_accuracy", "ok": any(c.get("name") == "Pattern Accuracy" and c.get("ok") for c in diagnostics.get("checks", []))},
        {"name": "policy_inventory_loaded", "ok": policies.get("total_rules", 0) > 0},
        {"name": "security_headers_enabled", "ok": True},
        {"name": "local_model_ready", "ok": any(c.get("name") == "Local Model Health" and c.get("ok") for c in diagnostics.get("checks", []))},
    ]
    passed = sum(1 for control in controls if control["ok"])
    score = round((passed / len(controls)) * 100, 2)
    return {
        "score": score,
        "status": "PRODUCTION_READY" if score >= 85 else "ACTION_REQUIRED",
        "controls": controls,
        "ledger": chain,
        "diagnostics_certificate": diagnostics.get("certificate"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v2/enterprise/backup")
def create_evidence_backup(current_user: TokenPayload = Depends(get_active_user)):
    """Create a signed, non-secret operational evidence backup bundle."""
    rbac.enforce(current_user.role, Permission.EXPORT_AUDIT_PDF)
    backup_dir = os.path.join(BASE_DIR, "logs", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    zip_path = os.path.join(backup_dir, f"sentinel_evidence_backup_{stamp}.zip")
    candidates = _safe_existing_files([
        audit_ledger.ledger_path,
        os.path.join(BASE_DIR, "release.json"),
        os.path.join(BASE_DIR, "DOCS.md"),
        os.path.join(BASE_DIR, "SECURITY.md"),
        os.path.join(BASE_DIR, "SUBMISSION_CHECKLIST.md"),
    ])
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in candidates:
            archive.write(path, arcname=os.path.relpath(path, BASE_DIR))
    manifest = {
        "file": zip_path,
        "sha256": _sha256_file(zip_path),
        "artifact_count": len(candidates),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user.sub,
        "excludes": [".env", "sentinel.db", "runtime logs containing secrets"],
    }
    encryption = _encrypt_backup_if_configured(zip_path)
    if encryption:
        manifest["encryption"] = encryption
    audit_ledger.log(
        action="EVIDENCE_BACKUP_CREATED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        metadata=manifest,
    )
    return manifest


@app.get("/api/v2/enterprise/restore-drill")
def restore_drill(current_user: TokenPayload = Depends(get_active_user)):
    """Non-destructive disaster recovery drill: verify latest backup and ledger chain."""
    rbac.enforce(current_user.role, Permission.EXPORT_AUDIT_PDF)
    backup_dir = os.path.join(BASE_DIR, "logs", "backups")
    latest = None
    if os.path.isdir(backup_dir):
        files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith(".zip")]
        latest = max(files, key=os.path.getmtime) if files else None
    zip_ok = False
    zip_entries = []
    if latest:
        try:
            with zipfile.ZipFile(latest, "r") as archive:
                bad = archive.testzip()
                zip_ok = bad is None
                zip_entries = archive.namelist()
        except zipfile.BadZipFile:
            zip_ok = False
    chain = audit_ledger.verify_chain()
    result = {
        "ready_for_restore": bool(latest and zip_ok and chain.get("valid")),
        "latest_backup": latest,
        "backup_valid": zip_ok,
        "backup_entries": zip_entries,
        "ledger_valid": chain.get("valid"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    audit_ledger.log(
        action="RESTORE_DRILL_EXECUTED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        metadata=result,
    )
    return result


@app.post("/api/v2/enterprise/threat-model")
def threat_model(req: ThreatModelRequest, current_user: TokenPayload = Depends(get_active_user)):
    """Generate a deployment-specific attack surface checklist for board/CISO review."""
    rbac.enforce(current_user.role, Permission.VIEW_VAULT_STATUS)
    risks = [
        {
            "area": "Identity",
            "threat": "Stolen admin token or unrotated bootstrap password",
            "control": "Forced password rotation, JWT revocation, first-run admin bootstrap",
            "status": "controlled",
        },
        {
            "area": "Network",
            "threat": "Unauthorized service calls to gateway",
            "control": "mTLS enforcement headers, CORS allowlist, rate/cost limiter",
            "status": "controlled" if req.mTLS_enforced else "action_required",
        },
        {
            "area": "AI Data Flow",
            "threat": "PII or trade secret leakage to cloud LLM",
            "control": "Identity masking, semantic DLP, sensitivity-based local routing",
            "status": "controlled" if not req.cloud_llm_enabled else "monitor",
        },
        {
            "area": "Evidence",
            "threat": "Audit tampering after incident",
            "control": "Obsidian hash chain, signed anchors, evidence backup",
            "status": "controlled",
        },
        {
            "area": "Exposure",
            "threat": "Internet-facing abuse and credential stuffing",
            "control": "Keep backend private; put WAF, mTLS, and SIEM alerting at edge",
            "status": "monitor" if req.internet_exposed else "controlled",
        },
    ]
    digest = hashlib.sha256(json.dumps([req.model_dump(), risks], sort_keys=True).encode()).hexdigest()
    return {
        "deployment_name": req.deployment_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "risk_register": risks,
        "certificate": digest,
    }


@app.post("/export-audit")
def export_audit(
    format: str = "csv",
    current_user: TokenPayload = Depends(get_active_user)
):
    """Export the audit log as CSV or PDF."""
    rbac.enforce(current_user.role, Permission.EXPORT_AUDIT_CSV)

    entries = audit_ledger.get_entries(limit=10000, tenant_id=current_user.tenant_id)

    if format.lower() == "pdf":
        rbac.enforce(current_user.role, Permission.EXPORT_AUDIT_PDF)
        stats = audit_ledger.get_summary_stats(tenant_id=current_user.tenant_id)
        chain = audit_ledger.verify_chain()
        pdf_path = exporter.to_pdf(
            entries=entries,
            stats=stats,
            chain_valid=chain.get("valid", False),
        )
        if pdf_path:
            return {"status": "success", "file": pdf_path, "format": "PDF"}
        return {"status": "error", "message": "PDF export requires reportlab: pip install reportlab"}

    csv_path = exporter.to_csv(entries=entries)
    return {"status": "success", "file": csv_path, "format": "CSV"}


@app.post("/api/v2/audit/report")
def evidence_report(req: EvidenceReportRequest, current_user: TokenPayload = Depends(get_active_user)):
    """Generate one-click CISO evidence PDF with ledger certificate and Oracle risk actors."""
    enforce_password_rotation(current_user)
    rbac.enforce(current_user.role, Permission.EXPORT_AUDIT_PDF)
    tenant_id = req.tenant_id or current_user.tenant_id
    result = evidence_reporter.generate(
        org_name=req.org_name or "Buyer Organization",
        tenant_id=tenant_id,
        limit=req.limit,
        primary_color=req.primary_color or "#047857",
        compliance_frameworks=req.compliance_frameworks or ["DPDP_2026", "GDPR", "FedRAMP"],
    )
    audit_ledger.log(
        action="EVIDENCE_REPORT_GENERATED",
        user_id=current_user.sub,
        user_role=current_user.role,
        department=current_user.department,
        tenant_id=current_user.tenant_id,
        policy_triggered="DPDP_2026_EVIDENCE_EXPORT",
        metadata={"file": result.get("file"), "certificate": result.get("certificate")},
    )
    return result


@app.post("/api/v2/enterprise/evidence-schedule")
def evidence_schedule(req: EvidenceScheduleRequest, current_user: TokenPayload = Depends(get_active_user)):
    """Store an air-gap friendly evidence-report schedule for cron/automation runners."""
    rbac.enforce(current_user.role, Permission.EXPORT_AUDIT_PDF)
    schedule_dir = os.path.join(BASE_DIR, "logs", "schedules")
    os.makedirs(schedule_dir, exist_ok=True)
    schedule = req.model_dump()
    schedule.update({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user.sub,
        "next_runner_command": "python scripts/generate_scheduled_evidence.py",
    })
    path = os.path.join(schedule_dir, f"evidence_schedule_{current_user.tenant_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2)
    audit_ledger.log(
        action="EVIDENCE_SCHEDULE_UPDATED",
        user_id=current_user.sub,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        metadata=schedule,
    )
    return {"schedule": schedule, "file": path}


@app.get("/api/v2/enterprise/evidence-schedule")
def get_evidence_schedule(current_user: TokenPayload = Depends(get_active_user)):
    rbac.enforce(current_user.role, Permission.EXPORT_AUDIT_PDF)
    path = os.path.join(BASE_DIR, "logs", "schedules", f"evidence_schedule_{current_user.tenant_id}.json")
    if not os.path.isfile(path):
        return {"schedule": None, "configured": False}
    with open(path, "r", encoding="utf-8") as f:
        return {"schedule": json.load(f), "configured": True}


@app.get("/audit/log")
def get_audit_log(
    limit: int = 100,
    department: Optional[str] = None,
    current_user: TokenPayload = Depends(get_active_user)
):
    """Retrieve audit log entries. Scoped by department for Dept Heads."""
    rbac.enforce(current_user.role, Permission.VIEW_AUDIT_LOG)

    # Scope department access
    dept_filter = None
    if current_user.role not in ("SUPER_ADMIN", "AUDITOR"):
        dept_filter = current_user.department

    entries = audit_ledger.get_entries(
        limit=limit,
        department=dept_filter or department,
        tenant_id=current_user.tenant_id,
    )
    chain = audit_ledger.verify_chain()
    return {"entries": entries, "chain_valid": chain.get("valid"), "total": len(entries)}


@app.get("/compliance/score")
def get_compliance_score(current_user: TokenPayload = Depends(get_active_user)):
    """Return multi-framework compliance scorecard."""
    scorer = ComplianceScorer()
    audit_stats = audit_ledger.get_summary_stats(tenant_id=current_user.tenant_id)
    chain = audit_ledger.verify_chain()
    dpdp_score = dpdp_engine.get_compliance_score()

    scores = scorer.score(
        audit_stats=audit_stats,
        dpdp_score=dpdp_score,
        chain_integrity=chain.get("valid", False),
        active_policies=policy_engine.list_policies().get("total_rules", 0),
        open_incidents=dpdp_score.get("open_incidents", 0),
        is_global=True  # Ensure HIPAA/GDPR takes priority for foreign targets
    )
    return scores


@app.get("/policy/list")
def list_policies(current_user: TokenPayload = Depends(get_active_user)):
    """List all loaded policies."""
    rbac.enforce(current_user.role, Permission.VIEW_POLICY)
    return policy_engine.list_policies()


@app.post("/policy/reload")
def reload_policies(current_user: TokenPayload = Depends(get_active_user)):
    """Reload all YAML policies from disk (admin only)."""
    rbac.enforce(current_user.role, Permission.EDIT_GLOBAL_POLICY)
    policy_engine.reload()
    return {"status": "reloaded", "summary": policy_engine.list_policies()}


@app.post("/recovery-info")
def get_recovery_info(current_user: TokenPayload = Depends(get_active_user)):
    """Returns hardware-locked recovery parameters."""
    rbac.enforce(current_user.role, Permission.VIEW_LICENSE_STATUS)
    return {
        "machine_id": sentinel_crypto.get_machine_id(),
        "encryption_algo": "AES-256-GCM",
        "deployment_mode": os.getenv("DEPLOYMENT_MODE", "airgap").upper(),
        "instructions": "To migrate vault to a new machine, provide your original Machine UUID to Xavira Tech Labs support.",
        "v2_note": "v2 supports cloud + air-gap modes. See LICENSE_SERVER_URL in .env for cloud licensing.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
