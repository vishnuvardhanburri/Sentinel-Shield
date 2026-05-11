#!/usr/bin/env python3
"""Static doctor for Sovereign Shield cross-platform readiness."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


CHECKS = [
    ("shared SDK", ROOT / "packages/sdk/src/client.ts"),
    ("shared RBAC", ROOT / "packages/sdk/src/rbac.ts"),
    ("shared audit client", ROOT / "packages/sdk/src/audit.ts"),
    ("design tokens", ROOT / "packages/design-system/src/tokens.ts"),
    ("Next.js web shell", ROOT / "apps/web/app/page.tsx"),
    ("Tauri desktop shell", ROOT / "apps/desktop/src-tauri/tauri.conf.json"),
    ("React Native mobile shell", ROOT / "apps/mobile/App.tsx"),
    ("mobile secure storage", ROOT / "apps/mobile/src/secureStorage.ts"),
    ("cross-platform release workflow", ROOT / ".github/workflows/cross-platform-release.yml"),
    ("cross-platform architecture doc", ROOT / "docs/CROSS_PLATFORM_ARCHITECTURE.md"),
]

BACKEND_CONTRACTS = [
    '"/api/v2/auth/refresh"',
    '"/api/v2/devices/sessions"',
    '"/api/v2/devices/sessions/revoke"',
    '"/api/v2/enterprise/quarantine/action"',
    '"/api/v2/enterprise/kill-switch"',
]


def main() -> int:
    app_source = (ROOT / "backend/app.py").read_text(encoding="utf-8")
    results = []
    for name, path in CHECKS:
        results.append({"name": name, "ok": path.exists(), "path": str(path.relative_to(ROOT))})
    for contract in BACKEND_CONTRACTS:
        results.append({"name": f"backend contract {contract}", "ok": contract in app_source, "path": "backend/app.py"})

    ok = all(item["ok"] for item in results)
    print(json.dumps({
        "status": "CROSS_PLATFORM_READY" if ok else "CROSS_PLATFORM_INCOMPLETE",
        "checks": results,
    }, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
