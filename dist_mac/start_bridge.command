#!/bin/bash
set -euo pipefail

# Always run relative to this file's folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="CursorDAWBridge"
APP_SUPPORT="$HOME/Library/Application Support/$APP_NAME"
VENV_DIR="$APP_SUPPORT/venv"
LOG_DIR="$APP_SUPPORT/logs"
LOG_FILE="$LOG_DIR/bridge.log"

mkdir -p "$APP_SUPPORT" "$LOG_DIR"

echo "======================================="
echo "  CursorDAW Bridge - Mac"
echo "======================================="
echo ""
echo "App Support: $APP_SUPPORT"
echo "Logs:        $LOG_FILE"
echo ""

# Find Python 3 in common locations
PYTHON3=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON3="$(command -v python3)"
elif [ -x "/usr/bin/python3" ]; then
  PYTHON3="/usr/bin/python3"
elif [ -x "/opt/homebrew/bin/python3" ]; then
  PYTHON3="/opt/homebrew/bin/python3"
elif [ -x "/usr/local/bin/python3" ]; then
  PYTHON3="/usr/local/bin/python3"
fi

if [ -z "$PYTHON3" ]; then
  echo "❌ Python 3 not found."
  echo "Install from https://www.python.org/downloads/ OR: brew install python"
  /usr/bin/osascript -e 'display dialog "CursorDAW Bridge needs Python 3. Install it from python.org or Homebrew." buttons {"OK"}' >/dev/null 2>&1 || true
  exit 1
fi

echo "✓ Python: $("$PYTHON3" --version)"

# Create isolated venv (user-space, no admin)
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo ""
  echo "Creating virtualenv (private install, no sudo)…"
  "$PYTHON3" -m venv "$VENV_DIR" || {
    echo "❌ Failed to create venv."
    echo "Fix: install Python from python.org or Homebrew."
    exit 1
  }
fi

VENV_PY="$VENV_DIR/bin/python"

# Install deps only if missing
echo ""
echo "Checking dependencies in venv…"
if ! "$VENV_PY" -c "import requests, watchdog" >/dev/null 2>&1; then
  echo "Installing dependencies into venv…"
  "$VENV_PY" -m pip install --upgrade pip setuptools wheel >/dev/null
  "$VENV_PY" -m pip install requests watchdog
  echo "✓ Dependencies installed"
else
  echo "✓ Dependencies OK"
fi

echo ""
echo "Starting bridge… (Ctrl+C to stop)"
echo "---------------------------------------"
echo ""

# Run and log
set +e
"$VENV_PY" "$SCRIPT_DIR/cloud_bridge.py" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

echo ""
echo "Bridge stopped (exit code: $EXIT_CODE)"
echo "Log saved to: $LOG_FILE"
echo ""
read -r -p "Press Enter to exit…"
