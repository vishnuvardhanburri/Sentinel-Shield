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
from auth.jwt_handler import get_current_user, create_access_token, TokenPayload
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

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
STATE_FILE = os.path.join(BASE_DIR, "sentinel_state.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
alert_log = os.path.join(LOGS_DIR, "alerts.log")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sentinel Shield v2",
    description="Enterprise AI Data Governance Platform — VishnuLabs",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Mount sub-routers
app.include_router(license_router)
app.include_router(integrations_router)
app.include_router(shadow_ai_router)

# ── Shared instances ──────────────────────────────────────────────────────────
scanner = EnterpriseScanner()
india_scanner = IndiaPIIScanner()
dpdp_engine = DPDPEngine()
exporter = AuditExporter()

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


# ── Schemas ───────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str
    department: Optional[str] = None

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
    preferred_model: Optional[str] = "openrouter/google/gemini-2.0-flash-lite-preview-02-05:free"


# ── Auth Endpoints (V2 Professional) ──────────────────────────────────────────
@app.post("/api/v2/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates a user and returns a secure JWT access token."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Sentinel Identity Failure: Access Denied")
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(data={"sub": user.email, "role": user.role, "dept": user.department})
    return {
        "access_token": token,
        "token_type": "bearer",
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
    
@app.get("/api/v2/auth/master-seed")
def force_seed(db: Session = Depends(get_db)):
    """FORCE creates the master admin account if it's missing (Fail-safe)."""
    try:
        existing = db.query(User).filter(User.email == "admin@demo.com").first()
        if existing:
            return {"status": "READY", "message": "Master Admin is already registered."}
        
        new_user = User(
            id=str(uuid.uuid4()),
            email="admin@demo.com",
            full_name="Master Admin",
            hashed_password=pwd_context.hash("demo1234"),
            role="SUPER_ADMIN",
            department="SECURITY"
        )
        db.add(new_user)
        db.commit()
        return {"status": "SUCCESS", "message": "Master Admin Forced Successfully! Proceed to login."}
    except Exception as e:
        return {"status": "ERROR", "message": f"Seeding failed: {str(e)}"}

@app.post("/api/v2/chat")
def chat(req: ChatRequest, current_user: TokenPayload = Depends(get_current_user)):
    """
    Secure Conversational AI endpoint.
    Governs the prompt (redacts PII) and routes to the selected AI model.
    """
    # 1. Govern the prompt
    governed_prompt = india_scanner.redact(req.message)
    
    # 2. Add system context (Role-play as Sentinel Auditor)
    system_ctx = (
        f"User Role: {current_user.role}. Department: {current_user.department}. "
        "You are the Sentinel Shield AI Security Auditor. Your goal is to help "
        "the user manage data governance and compliance risks. Be professional, "
        "concise, and never bypass redaction [REDACTED_*] tokens."
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
        audit_ledger.log_event(
            user_id=current_user.sub,
            event_type="AI_CHAT_INTERACTION",
            resource="SENTINEL_CHAT",
            action="QUERY",
            status="SUCCESS",
            details=f"Model: {result.get('model_used')}"
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Instant awake signal for Cloud monitoring."""
    return {"status": "awake", "engine": "Sentinel Shield v2.0"}

# ── Vault / Status Endpoints ──────────────────────────────────────────────────
@app.get("/status")
def get_status(current_user: TokenPayload = Depends(get_current_user)):
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


@app.post("/ask")
def query_vault(req: Query, current_user: TokenPayload = Depends(get_current_user)):
    """
    Secure AI Query with:
     1. RBAC permission check
     2. India PII + Presidio dual-layer scan + redaction
     3. Policy engine evaluation (WARN / REDACT / BLOCK)
     4. Governed model routing (Ollama / GPT-4 / Gemini)
     5. Immutable audit logging
    """
    global vectorstore

    rbac.enforce(current_user.role, Permission.RUN_AI_QUERY)

    # ── Step 1: Dual-Layer Scan ──────────────────────────────────────────────
    findings_us   = scanner.scan_content(req.prompt)
    findings_india = india_scanner.scan(req.prompt)
    all_findings   = findings_us + findings_india
    risk_score     = scanner.calculate_risk_score(findings_us)

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

    # ── Step 4: Redact ───────────────────────────────────────────────────────
    safe_prompt = scanner.redact_content(req.prompt, findings_us)
    safe_prompt = india_scanner.redact(safe_prompt)
    redaction_tags = list({scanner._build_redaction_token(f) for f in findings_us}
                          | {f["redaction_tag"] for f in findings_india})

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
            "response_leaks_prevented": is_response_redacted
        },
    )

    return {
        "answer": safe_answer,
        "model_used": result.get("model_used"),
        "findings_alert": "SENSITIVE_DATA_REDACTED" if (all_findings or is_response_redacted) else "CLEAN",
        "redactions_applied": len(redaction_tags) + (1 if is_response_redacted else 0),
        "policy_warnings": policy_decision.warnings,
        "risk_score": risk_score,
        "dpdp_categories": dpdp_meta.get("dpdp_categories", []),
        "outbound_secure": True,
    }


@app.post("/export-audit")
def export_audit(
    format: str = "csv",
    current_user: TokenPayload = Depends(get_current_user)
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


@app.get("/audit/log")
def get_audit_log(
    limit: int = 100,
    department: Optional[str] = None,
    current_user: TokenPayload = Depends(get_current_user)
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
def get_compliance_score(current_user: TokenPayload = Depends(get_current_user)):
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
def list_policies(current_user: TokenPayload = Depends(get_current_user)):
    """List all loaded policies."""
    rbac.enforce(current_user.role, Permission.VIEW_POLICY)
    return policy_engine.list_policies()


@app.post("/policy/reload")
def reload_policies(current_user: TokenPayload = Depends(get_current_user)):
    """Reload all YAML policies from disk (admin only)."""
    rbac.enforce(current_user.role, Permission.EDIT_GLOBAL_POLICY)
    policy_engine.reload()
    return {"status": "reloaded", "summary": policy_engine.list_policies()}


@app.post("/recovery-info")
def get_recovery_info(current_user: TokenPayload = Depends(get_current_user)):
    """Returns hardware-locked recovery parameters."""
    rbac.enforce(current_user.role, Permission.VIEW_LICENSE_STATUS)
    return {
        "machine_id": sentinel_crypto.get_machine_id(),
        "encryption_algo": "AES-256-GCM",
        "deployment_mode": os.getenv("DEPLOYMENT_MODE", "airgap").upper(),
        "instructions": "To migrate vault to a new machine, provide your original Machine UUID to VishnuLabs support.",
        "v2_note": "v2 supports cloud + air-gap modes. See LICENSE_SERVER_URL in .env for cloud licensing.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
