@echo off
echo ========================================
echo  AI Agent Reaper DAW - Cloud Bridge
echo ========================================
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo ========================================
echo  Bridge is starting...
echo  KEEP THIS WINDOW OPEN!
echo ========================================
echo.
python cloud_bridge.py
pause

