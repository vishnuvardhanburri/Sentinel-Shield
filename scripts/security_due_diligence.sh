#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/logs/due_diligence"
mkdir -p "$OUT"

echo "[Sovereign] Generating dependency due-diligence artifacts..."

if command -v pnpm >/dev/null 2>&1; then
  (cd "$ROOT/frontend" && pnpm audit --json > "$OUT/frontend_pnpm_audit.json" || true)
fi

PYTHON_BIN="${PYTHON_BIN:-$ROOT/.runtime_venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" -m pip install --quiet pip-audit cyclonedx-bom >/dev/null 2>&1 || true
"$PYTHON_BIN" -m pip_audit -r "$ROOT/requirements.txt" -f json -o "$OUT/backend_pip_audit.json" || true
"$PYTHON_BIN" -m cyclonedx_py requirements "$ROOT/requirements.txt" -o "$OUT/backend_sbom.cdx.json" || true

cat > "$OUT/README.md" <<'EOF'
# Sovereign Shield Security Due Diligence

Artifacts in this folder are generated locally for buyer review:

- `backend_sbom.cdx.json`: CycloneDX backend software bill of materials.
- `backend_pip_audit.json`: Python dependency vulnerability scan.
- `frontend_pnpm_audit.json`: Frontend dependency audit when pnpm is available.

Review any reported vulnerabilities before production exposure.
EOF

echo "[Sovereign] Due-diligence artifacts written to $OUT"
