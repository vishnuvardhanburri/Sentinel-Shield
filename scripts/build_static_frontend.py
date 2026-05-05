#!/usr/bin/env python3
"""Build the buyer-facing static dashboard for Vercel/static hosts."""
from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "frontend" / "site"
OUT_DIR = ROOT / "frontend" / "dist"


def main() -> int:
    if not SITE_DIR.exists():
        raise SystemExit(f"Static site source missing: {SITE_DIR}")

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    shutil.copytree(SITE_DIR, OUT_DIR)

    # Vercel static output should resolve clean URLs and deep links.
    for route in ("demo", "ops", "pricing"):
        route_dir = OUT_DIR / route
        index_file = route_dir / "index.html"
        if not index_file.exists():
            raise SystemExit(f"Missing route index: {index_file}")

    print(f"Static frontend build: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
