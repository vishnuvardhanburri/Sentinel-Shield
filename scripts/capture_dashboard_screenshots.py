#!/usr/bin/env python3
"""Capture buyer screenshot pack when Playwright is available."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("[SKIP] Playwright unavailable. Install with: pip install playwright && playwright install chromium")
        return 0

    base = os.getenv("SENTINEL_FRONTEND_BASE", "http://localhost:3000")
    email = os.getenv("SENTINEL_SMOKE_EMAIL", "")
    password = os.getenv("SENTINEL_SMOKE_PASSWORD", "")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(base, wait_until="networkidle", timeout=30000)
        page.screenshot(path=str(OUT / "01-login.png"), full_page=True)
        if email and password:
            page.fill("#login-email", email)
            page.fill("#login-password", password)
            page.click("#login-btn")
            page.wait_for_timeout(1500)
            tabs = [
                ("overview", "02-overview.png"),
                ("proxy", "03-proxy.png"),
                ("risk", "04-risk.png"),
                ("audit", "05-audit.png"),
                ("enterprise", "06-enterprise.png"),
            ]
            for tab, filename in tabs:
                locator = f"#nav-{tab}"
                if page.locator(locator).count():
                    page.click(locator)
                    page.wait_for_timeout(800)
                    page.screenshot(path=str(OUT / filename), full_page=True)
        browser.close()
    print(f"Screenshots written to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
