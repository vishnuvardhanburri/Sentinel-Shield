#!/usr/bin/env bash
# Sentinel Shield Professional Startup (VishnuLabs)
# ------------------------------------------------
# This script starts the background services and opens the landing dashboard.

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

# 1. Start Services
if [[ -f "./shield.sh" ]]; then
    ./shield.sh start
fi

# 2. Open Marketing/Professional Dashboard
if [[ -f "./marketing_demo/demo_dashboard.html" ]]; then
    open "./marketing_demo/demo_dashboard.html"
fi

# 3. Clean up terminal
exit 0
