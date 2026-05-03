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
    checks = [
        {"name": "env_file", "ok": (ROOT / ".env").exists()},
        {"name": "backend_port_8000", "ok": port_open(8000)},
        {"name": "frontend_port_3000", "ok": port_open(3000)},
        {"name": "ollama_port_11434", "ok": port_open(11434)},
        {"name": "runtime_venv", "ok": (ROOT / ".runtime_venv").exists()},
        {"name": "docker_compose", "ok": (ROOT / "docker-compose.yml").exists()},
        {"name": "deployment_pack", "ok": (ROOT / "logs" / "deployment_pack").exists()},
    ]
    score = round(sum(1 for c in checks if c["ok"]) / len(checks) * 100, 2)
    print(json.dumps({"score": score, "status": "READY" if score >= 75 else "ACTION_REQUIRED", "checks": checks}, indent=2))
    return 0 if score >= 60 else 1


if __name__ == "__main__":
    raise SystemExit(main())
