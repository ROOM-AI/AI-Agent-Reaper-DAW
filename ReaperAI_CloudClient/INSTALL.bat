@echo off
echo ============================================
echo   Reaper AI Agent - Cloud Client Installer
echo ============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

echo [1/3] Python found!
python --version
echo.

:: Create AIAGENT DAW folder in user's home directory
echo [2/3] Creating folders in %USERPROFILE%\AIAGENT DAW...
if not exist "%USERPROFILE%\AIAGENT DAW" mkdir "%USERPROFILE%\AIAGENT DAW"
echo    Created: %USERPROFILE%\AIAGENT DAW
echo.

:: Install Python dependencies
echo [3/3] Installing Python packages (requests, watchdog)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.

echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo Files created in: %USERPROFILE%\AIAGENT DAW
echo.
echo NEXT STEPS (DO IN THIS ORDER!):
echo.
echo 1. Open Reaper (any project)
echo.
echo 2. In Reaper: Actions -^> Show action list
echo    Click "New action..." -^> "Load ReaScript..."
echo    Select: reaper_cloud_agent.lua (from this folder)
echo    Click "Run"
echo    Check console - should see: "Cloud Agent Started"
echo.
echo 3. Double-click: START_BRIDGE.bat
echo    (Keep that window open!)
echo    Write down your SESSION ID shown
echo.
echo 4. Open browser:
echo    https://feelings36lex36slo14moossolo-97692729550.europe-west1.run.app
echo    Enter your session ID
echo    Start controlling Reaper with AI!
echo.
echo ============================================
echo.
pause

