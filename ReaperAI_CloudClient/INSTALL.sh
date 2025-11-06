#!/bin/bash

echo "============================================"
echo "  Reaper AI Agent - Cloud Client Installer"
echo "============================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo ""
    echo "Install Python 3:"
    echo "  macOS: brew install python3"
    echo "  Linux: sudo apt install python3 python3-pip"
    echo ""
    exit 1
fi

echo "[1/3] Python found!"
python3 --version
echo ""

# Create AIAGENT DAW folder in user's home directory
echo "[2/3] Creating folders in ~/AIAGENT DAW..."
mkdir -p "$HOME/AIAGENT DAW"
echo "   Created: $HOME/AIAGENT DAW"
echo ""

# Install Python dependencies
echo "[3/3] Installing Python packages (requests, watchdog)..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
echo ""

echo "============================================"
echo "  Installation Complete!"
echo "============================================"
echo ""
echo "Files created in: $HOME/AIAGENT DAW"
echo ""
echo "NEXT STEPS (DO IN THIS ORDER!):"
echo ""
echo "1. Open Reaper (any project)"
echo ""
echo "2. In Reaper: Actions -> Show action list"
echo "   Click 'New action...' -> 'Load ReaScript...'"
echo "   Select: reaper_cloud_agent.lua (from this folder)"
echo "   Click 'Run'"
echo "   Check console - should see: 'Cloud Agent Started'"
echo ""
echo "3. Run: ./START_BRIDGE.sh"
echo "   (Keep that window open!)"
echo "   Write down your SESSION ID shown"
echo ""
echo "4. Open browser:"
echo "   https://feelings36lex36slo14moossolo-97692729550.europe-west1.run.app"
echo "   Enter your session ID"
echo "   Start controlling Reaper with AI!"
echo ""
echo "============================================"
echo ""

