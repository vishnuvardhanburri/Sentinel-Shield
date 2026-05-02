#!/usr/bin/env python3
"""Prepare investor demo data and launch the live dashboard."""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    subprocess.run([sys.executable, "scripts/seed_demo_data.py"], cwd=ROOT, check=False)
    print("Investor demo seeded with synthetic security activity.")
    print("Opening dashboard at http://localhost:3000")
    webbrowser.open("http://localhost:3000")
    time.sleep(1)
    return subprocess.call([sys.executable, "scripts/launch_ready.py"], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
