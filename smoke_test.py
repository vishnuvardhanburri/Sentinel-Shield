"""
Sentinel Shield v2 — End-to-End Smoke Test
Verifies all core modules: Auth, Audit, Policy, Compliance, Gateway, and Shadow AI.
"""
import requests
import json
import time
import sys
import os

API_BASE = "http://localhost:8000"

def log_test(name, success, detail=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"[{status}] {name}")
    if not success and detail:
        print(f"    Error: {detail}")

def run_smoke_test():
    print("🚀 Starting Sentinel Shield v2 End-to-End Smoke Test...\n")
    
    # ── 1. Auth Test (Login) ──────────────────────────────────────────────────
    token = ""
    try:
        resp = requests.post(f"{API_BASE}/auth/login", json={
            "email": "admin@demo.com",
            "password": "demo1234"
        })
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            log_test("Authentication (Login)", True)
        else:
            log_test("Authentication (Login)", False, f"Status {resp.status_code}: {resp.text}")
            return
    except Exception as e:
        log_test("Authentication (Login)", False, str(e))
        return

    headers = {"Authorization": f"Bearer {token}"}

    # ── 2. System Status Test ─────────────────────────────────────────────────
    try:
        resp = requests.get(f"{API_BASE}/status", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            log_test("System Status Check", True)
            print(f"    Mode: {data.get('infra', {}).get('deployment_mode')}")
            print(f"    Audit Chain: {'Intact' if data.get('audit', {}).get('chain_integrity') else 'BROKEN'}")
        else:
            log_test("System Status Check", False, resp.text)
    except Exception as e:
        log_test("System Status Check", False, str(e))

    # ── 3. Governed AI Query (PII Redaction + Policy) ─────────────────────────
    try:
        # Test Aadhaar detection (India PII) + Block Policy
        test_prompt = "Patient Aadhaar: 2345 6789 0123 has been admitted to the ICU."
        print(f"\nTesting Query with Aadhaar: '{test_prompt}'")
        resp = requests.post(f"{API_BASE}/ask", headers=headers, json={
            "prompt": test_prompt,
            "department": "HOSPITAL"
        })
        
        # Hospital policy should block raw PII at high risk
        if resp.status_code == 403:
            data = resp.json().get("detail", {})
            log_test("PII Policy Enforcement (BLOCK)", True)
            print(f"    Action: {data.get('action')}, Reason: {data.get('reason')}")
        elif resp.status_code == 200:
            data = resp.json()
            if "REDACTED" in data.get("answer", "") or data.get("redactions_applied", 0) > 0:
                log_test("PII Policy Enforcement (REDACT)", True)
            else:
                log_test("PII Policy Enforcement", False, "No redaction applied to sensitive data")
        else:
            log_test("Governed AI Query", False, resp.text)
    except Exception as e:
        log_test("Governed AI Query", False, str(e))

    # ── 4. Audit Log Test ─────────────────────────────────────────────────────
    try:
        resp = requests.get(f"{API_BASE}/audit/log?limit=5", headers=headers)
        if resp.status_code == 200:
            entries = resp.json().get("entries", [])
            if len(entries) > 0:
                log_test("Audit Ledger Retrieval", True)
                print(f"    Last Event: {entries[0].get('action')} by {entries[0].get('user_id')}")
            else:
                log_test("Audit Ledger Retrieval", False, "No entries found in log")
        else:
            log_test("Audit Ledger Retrieval", False, resp.text)
    except Exception as e:
        log_test("Audit Ledger Retrieval", False, str(e))

    # ── 5. Compliance Scoring Test ────────────────────────────────────────────
    try:
        resp = requests.get(f"{API_BASE}/compliance/score", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            log_test("Compliance Scoring Engine", True)
            print(f"    Global Grade: {data.get('grade')} (Score: {data.get('composite_score')})")
        else:
            log_test("Compliance Scoring Engine", False, resp.text)
    except Exception as e:
        log_test("Compliance Scoring Engine", False, str(e))

    # ── 6. Shadow AI Detection Test ───────────────────────────────────────────
    try:
        # Trigger a manual scan
        resp = requests.post(f"{API_BASE}/shadow-ai/scan", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            log_test("Shadow AI Scanning Engine", True)
            print(f"    Domains Scanned: {data.get('scanned')}, Detections: {data.get('detected')}")
        else:
            log_test("Shadow AI Scanning Engine", False, resp.text)
    except Exception as e:
        log_test("Shadow AI Scanning Engine", False, str(e))

    # ── 7. License Server Test ────────────────────────────────────────────────
    try:
        test_key = "SNTL-TEST-KEY-1234"
        # Since we just started, let's try to list licenses
        resp = requests.get(f"{API_BASE}/license/list", headers=headers)
        if resp.status_code == 200:
            log_test("License Server API", True)
        else:
            log_test("License Server API", False, resp.text)
    except Exception as e:
        log_test("License Server API", False, str(e))

    print("\n🏁 Smoke Test Finished.")

if __name__ == "__main__":
    run_smoke_test()
