import os
import json
import csv
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from security_scanner import EnterpriseScanner
from vault_crypto import sentinel_crypto
import platform
import shutil

# --- CONFIG ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
STATE_FILE = os.path.join(BASE_DIR, "sentinel_state.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
alert_log = os.path.join(LOGS_DIR, "alerts.log")

app = FastAPI(title="Sentinel Shield Version 1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SEARCH ENGINE ---
scanner = EnterpriseScanner()
embeddings = OllamaEmbeddings(model="llama3.1")
llm = OllamaLLM(model="llama3.1")
vectorstore = None

class Query(BaseModel):
    prompt: str

@app.on_event("startup")
async def startup():
    global vectorstore
    if os.path.exists(CHROMA_DIR):
        vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)

@app.get("/status")
def get_status():
    """Retrieves autonomous monitoring stats and alerts for law firm/clinic reporting."""
    data = {"processed_files": {}, "stats": {"leaks_blocked": 0, "hours_saved": 0}, "alerts": []}
    
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "rb") as f:
                encrypted_data = f.read()
            raw_data = sentinel_crypto.decrypt_data(encrypted_data)
            data.update(json.loads(raw_data))
        except: pass
    
    # Read last 10 alerts
    if os.path.exists(alert_log):
        try:
            with open(alert_log, "r") as f:
                lines = f.readlines()
                data["alerts"] = [l.strip() for l in lines[-10:] if "CRITICAL" in l]
        except: pass
        
    # Infra Health Check
    try:
        total, used, free = 0, 0, 0
        if platform.system() == "Windows":
            total, used, free = shutil.disk_usage(BASE_DIR)
        else:
            st = os.statvfs(BASE_DIR)
            free = st.f_bavail * st.f_frsize
            total = st.f_blocks * st.f_frsize
        
        data["infra"] = {
            "disk_used_pct": round(((total - free) / total) * 100, 1) if total > 0 else 0,
            "disk_free_gb": round(free / (1024**3), 2),
            "ai_pulse": "HEALTHY" if vectorstore else "INITIALIZING",
            "hardware_id": sentinel_crypto.get_machine_id()[:8] + "..."
        }
    except:
        data["infra"] = {"disk_used_pct": "??", "ai_pulse": "OFFLINE"}

    return data

@app.post("/ask")
def query_vault(req: Query):
    """Secure RAG Query with redaction verification."""
    global vectorstore
    if not vectorstore:
        # Try once more to initialize if it was missing at startup
        if os.path.exists(CHROMA_DIR):
            try:
                vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Index Load Fail: {e}")
        
    if not vectorstore:
        raise HTTPException(status_code=400, detail="Vault empty or index not found.")

    # Retrieval
    results = vectorstore.similarity_search(req.prompt, k=4)
    # Context is already redacted in Chroma, but we sanitize the final prompt just in case
    context = "\n\n".join([doc.page_content for doc in results])
    
    # FINAL SAFETY: Scan the context AGAIN before presenting it for query
    # (Paranoid defense for medical HIPAA/Legal compliance)
    scan_results = scanner.scan_content(context)
    safe_context = scanner.redact_content(context, scan_results)

    prompt = f"""You are the 'Sentinel Shield Auditor', a secure internal intelligence system.
    You are analyzing a 100% air-gapped vault for a professional firm (Law/Medical).
    The context provided below has ALREADY been surgically redacted for PII and Secrets.
    
    Context from vault:
    {safe_context}
    
    Task: Answer the user's question accurately using ONLY the context above. 
    If you see [REDACTED_...], acknowledge it as blocked sensitive info but continue the analysis.
    
    Question: {req.prompt}
    
    Helpful Professional Answer:"""
    
    response = llm.invoke(prompt)
    
    return {
        "answer": response,
        "sources": list(set([doc.metadata.get("source") for doc in results])),
        "findings_alert": "SENSITIVE_DATA_REDACTED" if scan_results else "CLEAN"
    }

@app.post("/export-audit")
def export_audit():
    """Generates a detailed CSV audit report for compliance officers."""
    report_name = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    report_path = os.path.join(LOGS_DIR, report_name)
    
    data = {"processed_files": {}}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "rb") as f:
                encrypted_data = f.read()
            raw_data = sentinel_crypto.decrypt_data(encrypted_data)
            data = json.loads(raw_data)
        except: pass

    try:
        with open(report_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "File", "Risk Score", "Words Processed", "Status"])
            for filename, meta in data.get("processed_files", {}).items():
                writer.writerow([
                    meta.get("timestamp"),
                    filename,
                    meta.get("score"),
                    meta.get("words"),
                    meta.get("status")
                ])
        return {"status": "success", "file": report_path}
    except Exception as e:
        return {"status": "error", "message": f"Export Failed: {e}"}

@app.post("/recovery-info")
def get_recovery_info():
    """Returns the hardware-locked recovery parameters (Not the key itself)."""
    return {
        "machine_id": sentinel_crypto.get_machine_id(),
        "encryption_algo": "AES-256-GCM",
        "instructions": "To move your vault to a new machine, you must provide your original Machine UUID."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
