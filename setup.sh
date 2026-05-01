#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "[Sentinel] Bootstrapping full localhost ecosystem..."

if command -v pnpm >/dev/null 2>&1; then
  pnpm dev:full
else
  echo "[Sentinel] pnpm not found; using Docker Compose directly."
  docker compose --profile airgap --profile cloud up --build
fi
