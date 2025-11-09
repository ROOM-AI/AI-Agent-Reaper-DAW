@echo off
echo ======================================
echo   Installing Python Dependencies
echo ======================================
echo.
echo This will install required packages:
echo - anthropic (Claude AI)
echo - openai (Whisper for lyrics)
echo - requests, numpy, scipy
echo - watchdog (file monitoring)
echo.
pause

pip install anthropic openai python-dotenv watchdog requests numpy scipy

echo.
echo ======================================
echo   Installation Complete!
echo ======================================
echo.
echo Next steps:
echo 1. Create .env file with your API keys
echo 2. Load reaper_agent.lua in Reaper
echo 3. Run START_LOCAL_WINDOWS.bat
echo.
pause













