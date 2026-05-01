"""
Sentinel Shield v2 — Upgraded FastAPI Backend
Wires together: RBAC auth, audit ledger, policy engine, model gateway,
license server, DPDP compliance, and the original vault/RAG functionality.
"""
import os
import sys
# Ensure the current directory is in the path for cloud imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import json
import csv
import hashlib
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
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
from auth.jwt_handler import get_current_user, create_access_token, revoke_token_id, TokenPayload
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
from db.models import User
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

class LogoutRequest(BaseModel):
    revoke_current: bool = True

class Query(BaseModel):
    prompt: str
    preferred_model: Optional[str] = None
    department: Optional[str] = None

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
        revoke_token_id(current_user.jti)
    return {"status": "SUCCESS", "message": "Session revoked."}

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
def proxy_inspect(req: ProxyInspectRequest, current_user: TokenPayload = Depends(get_active_user)):
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
