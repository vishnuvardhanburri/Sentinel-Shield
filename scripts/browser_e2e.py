#!/usr/bin/env python3
"""Browser-level dashboard smoke test using Playwright when available."""
import os
import sys


def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("[SKIP] playwright is not installed. Install with: pip install playwright && playwright install chromium")
        return

    base = os.getenv("SENTINEL_FRONTEND_BASE", "http://localhost:3000")
    email = os.getenv("SENTINEL_SMOKE_EMAIL", "")
    password = os.getenv("SENTINEL_SMOKE_PASSWORD", "")
    if not email or not password:
        print("[SKIP] Set SENTINEL_SMOKE_EMAIL and SENTINEL_SMOKE_PASSWORD for browser E2E.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(base, wait_until="networkidle", timeout=30000)
        page.fill("#login-email", email)
        page.fill("#login-password", password)
        page.click("#login-btn")
        page.wait_for_timeout(1500)
        if page.locator("#change-password-btn").count():
            raise SystemExit("[FAIL] Smoke user still requires password rotation.")
        page.wait_for_selector("#nav-proxy", timeout=15000)
        page.click("#nav-proxy")
        page.wait_for_selector("text=Universal Proxy Hook", timeout=10000)
        page.click("#nav-enterprise")
        page.wait_for_selector("text=Enterprise Center", timeout=10000)
        page.click("#nav-audit")
        page.wait_for_selector("text=Immutable Audit Ledger", timeout=10000)
        browser.close()
    print("[OK] Browser E2E dashboard flow passed.")


if __name__ == "__main__":
    main()
