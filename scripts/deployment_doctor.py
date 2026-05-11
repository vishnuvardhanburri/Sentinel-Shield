#!/usr/bin/env python3
"""Local deployment doctor for Sovereign Shield."""
import json
import os
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def port_open(port: int) -> bool:
    sock = socket.socket()
    sock.settimeout(0.4)
    ok = sock.connect_ex(("127.0.0.1", port)) == 0
    sock.close()
    return ok


def main() -> int:
    env_ready = (ROOT / ".env").exists() or all(
        os.getenv(key)
        for key in ("JWT_SECRET_KEY", "LICENSE_MASTER_SECRET", "ACTOR_HASH_SALT", "LEDGER_MASTER_SALT")
    )
    frontend_port = port_open(3000)
    frontend_build = (ROOT / "frontend" / "dist" / "index.html").exists()
    checks = [
        {"name": "env_config", "ok": env_ready, "required": True},
        {"name": "backend_port_8000", "ok": port_open(8000), "required": True},
        {
            "name": "frontend_ready",
            "ok": frontend_port or frontend_build,
            "required": True,
            "detail": "port 3000 listening" if frontend_port else "static dashboard build artifact present" if frontend_build else "no port or build artifact",
        },
        {
            "name": "ollama_port_11434",
            "ok": port_open(11434),
            "required": False,
            "detail": "required for live local-LLM demos; skipped in CI if Ollama is not installed",
        },
        {"name": "runtime_venv", "ok": (ROOT / ".runtime_venv").exists() or (ROOT / ".buyer_venv").exists(), "required": False},
        {"name": "docker_compose", "ok": (ROOT / "docker-compose.yml").exists(), "required": True},
        {"name": "deployment_pack", "ok": (ROOT / "logs" / "deployment_pack").exists(), "required": False},
    ]
    required_ok = all(c["ok"] for c in checks if c.get("required"))
    score = round(sum(1 for c in checks if c["ok"]) / len(checks) * 100, 2)
    print(json.dumps({"score": score, "status": "READY" if required_ok else "ACTION_REQUIRED", "checks": checks}, indent=2))
    return 0 if required_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
