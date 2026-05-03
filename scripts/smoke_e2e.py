#!/usr/bin/env python3
"""
Sovereign Shield end-to-end smoke proof.

Unauthenticated checks always run. Authenticated checks run when
SENTINEL_SMOKE_EMAIL and SENTINEL_SMOKE_PASSWORD are provided.
"""
import os
import sys
import json
from typing import Dict
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


API_BASE = os.getenv("SENTINEL_API_BASE", "http://localhost:8000").rstrip("/")


def fail(message: str):
    print(f"[FAIL] {message}")
    sys.exit(1)


def ok(message: str):
    print(f"[OK] {message}")


class Response:
    def __init__(self, status_code: int, body: bytes, headers):
        self.status_code = status_code
        self.text = body.decode("utf-8", errors="replace")
        self.headers = {k.lower(): v for k, v in dict(headers).items()}

    def json(self):
        return json.loads(self.text)


def request(method: str, path: str, **kwargs) -> Response:
    headers = kwargs.get("headers", {})
    data = None
    if "json" in kwargs:
        data = json.dumps(kwargs["json"]).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}
    req = urlrequest.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            return Response(resp.status, resp.read(), resp.headers)
    except HTTPError as exc:
        return Response(exc.code, exc.read(), exc.headers)
    except (URLError, TimeoutError) as exc:
        fail(f"{method} {path} failed: {exc}")


def assert_status(resp: Response, expected: int, label: str):
    if resp.status_code != expected:
        fail(f"{label}: expected {expected}, got {resp.status_code}: {resp.text[:300]}")
    ok(label)


def unauthenticated_checks():
    health = request("GET", "/health")
    assert_status(health, 200, "Backend health endpoint is reachable")

    root = request("GET", "/")
    assert_status(root, 200, "Root endpoint is reachable")
    if root.json().get("signature") != "BY XAVIRA TECH LABS":
        fail("Root endpoint is not branded as Xavira Tech Labs")
    ok("Xavira Tech Labs branding is active")

    probe = request("GET", "/.env")
    assert_status(probe, 404, "Suspicious /.env probe is blocked")

    protected = request("POST", "/ask", json={"prompt": "hello"})
    if protected.headers.get("x-frame-options") != "DENY":
        fail("Security header X-Frame-Options: DENY missing on protected response")
    ok("Security headers are present on protected routes")


def authenticated_checks(headers: Dict[str, str]):
    diagnostics = request("GET", "/api/v2/system/diagnostics", headers=headers)
    assert_status(diagnostics, 200, "Self-diagnostic API is authenticated and reachable")

    proxy = request(
        "POST",
        "/api/v2/proxy/inspect",
        headers=headers,
        json={
            "text": "Aadhaar 2345 6789 0123 and PAN ABCDE1234F are in this prompt.",
            "source_app": "smoke-e2e",
            "auto_redact": True,
        },
    )
    assert_status(proxy, 200, "Universal proxy inspect is reachable")
    protected_text = proxy.json().get("protected_text", "")
    if "2345 6789 0123" in protected_text or "ABCDE1234F" in protected_text:
        fail("Proxy did not mask Aadhaar/PAN test values")
    ok("Proxy masks Aadhaar/PAN values")

    heatmap = request("GET", "/api/v2/risk/heatmap", headers=headers)
    assert_status(heatmap, 200, "Risk heatmap API is reachable")

    audit = request("GET", "/audit/log?limit=5", headers=headers)
    assert_status(audit, 200, "Audit ledger API is reachable")


def main():
    unauthenticated_checks()

    email = os.getenv("SENTINEL_SMOKE_EMAIL", "")
    password = os.getenv("SENTINEL_SMOKE_PASSWORD", "")
    if not email or not password:
        print("[SKIP] Authenticated checks skipped. Set SENTINEL_SMOKE_EMAIL and SENTINEL_SMOKE_PASSWORD.")
        return

    login = request("POST", "/api/v2/auth/login", json={"email": email, "password": password})
    assert_status(login, 200, "Login succeeds with smoke credentials")
    token = login.json().get("access_token")
    if not token:
        fail("Login response did not include access_token")
    if login.json().get("force_password_change"):
        fail("Smoke user must change password before protected-route checks")

    authenticated_checks({"Authorization": f"Bearer {token}"})


if __name__ == "__main__":
    main()
