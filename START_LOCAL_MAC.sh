#!/bin/bash

echo "======================================"
echo "  AI Agent for Reaper - Local Mode"
echo "======================================"
echo ""
echo "Make sure Reaper is running with reaper_agent.lua loaded!"
echo ""
echo "Starting in 3 seconds..."
sleep 3

cd "$(dirname "$0")"

echo ""
echo "[1/2] Starting bridge (connects Reaper to Agent)..."
osascript -e 'tell app "Terminal" to do script "cd \"'"$(pwd)"'\" && python3 cloud_bridge.py"'

sleep 2

echo "[2/2] Starting AI Agent..."
python3 "local agent.py"










