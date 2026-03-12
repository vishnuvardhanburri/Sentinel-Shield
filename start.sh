#!/usr/bin/env bash
# VISHNULABS - SENTINEL SHIELD VERSION 1

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="$BASE_DIR/logs"
PID_DIR="$LOGS_DIR/pids"

cd "$BASE_DIR"

if [[ ! -f ".env" && -f ".env.example" ]]; then
  cp .env.example .env
fi

# --- OLLAMA HEALTH CHECK ---
if ! command -v ollama &> /dev/null; then
  echo "[!] Error: Ollama not found. Sentinel Shield requires Ollama for local AI."
  echo "[!] Please install it from https://ollama.com before continuing."
  exit 1
fi

# --- OLLAMA MODEL CHECK ---
echo "[*] Verifying AI Model (llama3.1)..."
if ! ollama list | grep -q "llama3.1"; then
  echo "[!] Model 'llama3.1' not found. Pulling now (this may take a few minutes)..."
  ollama pull llama3.1
fi

mkdir -p "$LOGS_DIR" "$PID_DIR" "$BASE_DIR/chroma_db" "$BASE_DIR/vault_docs" "$BASE_DIR/vault_archive"
touch "$LOGS_DIR/monitor_output.log" "$LOGS_DIR/backend_output.log" "$LOGS_DIR/tray_output.log"

resolve_python() {
  local candidate resolved
  local -a candidates=(
    "${SENTINEL_PYTHON:-}"
    "$HOME/vault_env/bin/python"
    "$HOME/vault_env/bin/python3"
    "$BASE_DIR/backend/venv/bin/python3"
    "$BASE_DIR/backend/venv/bin/python"
    "python3"
  )

  for candidate in "${candidates[@]}"; do
    [[ -z "$candidate" ]] && continue

    if [[ "$candidate" == */* ]]; then
      [[ -x "$candidate" ]] || continue
      resolved="$candidate"
    else
      resolved="$(command -v "$candidate" 2>/dev/null || true)"
      [[ -n "$resolved" ]] || continue
    fi

    if "$resolved" - <<'PY' >/dev/null 2>&1
import importlib
required = [
    "fastapi",
    "watchdog",
    "langchain_ollama",
    "langchain_chroma",
    "plyer",
]
for module in required:
    importlib.import_module(module)
PY
    then
      echo "$resolved"
      return 0
    fi
  done

  return 1
}

PYTHON_BIN="$(resolve_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "[!] No suitable Python environment found. Set SENTINEL_PYTHON to a venv with Sentinel deps."
  exit 1
fi

start_service() {
  local name="$1"
  local script_path="$2"
  local log_path="$3"
  local pid_path="$4"

  if [[ -f "$pid_path" ]]; then
    local existing_pid
    existing_pid="$(cat "$pid_path" 2>/dev/null || true)"
    if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" >/dev/null 2>&1; then
      echo "[=] $name already running (pid $existing_pid)"
      return 0
    fi
  fi

  local detected_pid script_name
  script_name="$(basename "$script_path")"
  detected_pid="$(pgrep -f "$script_path" | head -n 1 || true)"
  if [[ -z "$detected_pid" ]]; then
    detected_pid="$(pgrep -f "$script_name" | head -n 1 || true)"
  fi
  if [[ -n "$detected_pid" ]]; then
    echo "$detected_pid" > "$pid_path"
    echo "[=] $name already running (pid $detected_pid)"
    return 0
  fi

  nohup "$PYTHON_BIN" "$script_path" >> "$log_path" 2>&1 < /dev/null &
  local new_pid=$!
  disown "$new_pid" 2>/dev/null || true
  echo "$new_pid" > "$pid_path"
  echo "[+] $name started (pid $new_pid)"
}

start_service "Monitor" "$BASE_DIR/backend/sentinel_monitor.py" "$LOGS_DIR/monitor_output.log" "$PID_DIR/monitor.pid"
start_service "API Backend" "$BASE_DIR/backend/app.py" "$LOGS_DIR/backend_output.log" "$PID_DIR/backend.pid"
start_service "Tray Icon" "$BASE_DIR/backend/tray_manager.py" "$LOGS_DIR/tray_output.log" "$PID_DIR/tray.pid"

if [[ "$OSTYPE" == "darwin"* ]]; then
  PLIST_DEST="$HOME/Library/LaunchAgents/com.sentinel.shield.plist"
  if [[ ! -f "$PLIST_DEST" ]]; then
    echo "[*] Installing Mac auto-start on boot..."
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$PLIST_DEST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sentinel.shield</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$BASE_DIR/start.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>$BASE_DIR</string>
    <key>StandardErrorPath</key>
    <string>$BASE_DIR/logs/launchd_error.log</string>
    <key>StandardOutPath</key>
    <string>$BASE_DIR/logs/launchd_output.log</string>
</dict>
</plist>
EOF
    chmod 644 "$PLIST_DEST"
    launchctl load "$PLIST_DEST" 2>/dev/null || true
  fi
fi

echo "--------------------------------------------------------"
echo "SENTINEL SHIELD VERSION 1 ACTIVE"
echo "Run start.sh once - runs forever in background"
echo "You can close Terminal now."
echo "--------------------------------------------------------"
