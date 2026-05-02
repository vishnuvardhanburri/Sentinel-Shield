#!/usr/bin/env python3
"""Enterprise launch wrapper: start services and validate health."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("Sentinel Shield Enterprise Deploy")
    print("Target: runs locally in under 15 minutes on a prepared machine.")
    print("Dashboard: http://localhost:3000")
    print("API:       http://localhost:8000")
    print("Docs:      http://localhost:8000/api/docs")
    print("")
    print("Starting services and running health validation...")
    return subprocess.call([sys.executable, "scripts/launch_ready.py"], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
