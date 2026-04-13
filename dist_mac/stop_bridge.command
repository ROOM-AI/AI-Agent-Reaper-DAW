#!/bin/bash
set -euo pipefail

# Stop any running cloud_bridge.py process
PIDS="$(pgrep -f "python.*cloud_bridge\.py" || true)"

if [ -z "$PIDS" ]; then
  echo "No running cloud_bridge.py found."
else
  echo "Stopping PIDs: $PIDS"
  kill $PIDS || true
  echo "✓ Bridge stopped"
fi

read -r -p "Press Enter to exit…"

