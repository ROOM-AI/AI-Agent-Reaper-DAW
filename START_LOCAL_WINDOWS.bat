@echo off
echo ======================================
echo   AI Agent for Reaper - Local Mode
echo ======================================
echo.
echo Make sure Reaper is running with reaper_agent.lua loaded!
echo.
echo Starting in 3 seconds...
timeout /t 3 >nul

cd /d "%~dp0"

echo.
echo [1/2] Starting bridge (connects Reaper to Agent)...
start "Reaper Bridge" cmd /k python cloud_bridge.py

timeout /t 2 >nul

echo [2/2] Starting AI Agent...
python "local agent.py"

pause























