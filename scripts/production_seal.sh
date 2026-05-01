#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[Sentinel] Production Seal v2.0 starting..."

rm -rf logs/audit/*.jsonl logs/exports/* logs/risk/* logs/*.log logs/pids 2>/dev/null || true
mkdir -p logs/audit logs/exports logs/risk

if [[ -f sentinel_state.json ]]; then
  rm -f sentinel_state.json
fi

python3 - <<'PY'
import os
import secrets
from pathlib import Path

env = Path(".env")
lines = []
if env.exists():
    lines = env.read_text().splitlines()

values = {
    "JWT_SECRET_KEY": secrets.token_urlsafe(48),
    "LICENSE_MASTER_SECRET": secrets.token_urlsafe(48),
    "ACTOR_HASH_SALT": secrets.token_urlsafe(32),
    "LEDGER_MASTER_SALT": secrets.token_urlsafe(32),
    "MASTER_SALT": secrets.token_urlsafe(32),
}

seen = set()
out = []
for line in lines:
    if "=" not in line or line.lstrip().startswith("#"):
        out.append(line)
        continue
    key = line.split("=", 1)[0]
    if key in values:
        out.append(f"{key}={values[key]}")
        seen.add(key)
    else:
        out.append(line)

for key, value in values.items():
    if key not in seen:
        out.append(f"{key}={value}")

env.write_text("\n".join(out).strip() + "\n")
PY

set -a
source .env
set +a

echo "[Sentinel] Installing pytest if needed..."
python3 -m venv .seal_venv
.seal_venv/bin/python -m pip install --upgrade pip
.seal_venv/bin/python -m pip install -r requirements.txt -r backend/requirements.txt
.seal_venv/bin/python -m pip install pytest

echo "[Sentinel] Running full test suite..."
.seal_venv/bin/python -m pytest

find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name ".DS_Store" -o -name "*.pyc" \) -delete 2>/dev/null || true
rm -rf .seal_venv

echo "[Sentinel] Creating enterprise production seal commit..."
git add .
if git diff --cached --quiet; then
  echo "[Sentinel] No changes to commit."
else
  git commit -m "chore: enterprise production seal applied"
fi

echo "[Sentinel] Production Seal v2.0 complete. Secrets rotated, tests passed, final state committed."
