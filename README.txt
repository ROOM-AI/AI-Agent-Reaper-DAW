CURSORDAW CLOUD DEMO - 2 MINUTE SETUP!

Requirements: 
- Python 3
- Reaper DAW

Quick Start:
1. Install Python dependencies:
   pip install requests watchdog

2. Start the bridge (keep this window open):
   python cloud_bridge.py

3. Open Reaper
   Actions → Show action list → Load → cursordaw_demo.lua → Run

4. Visit: https://feelings36lex36slo-97692729550.europe-west1.run.app
   Type commands and control your DAW!

Commands supported: play, stop, record, add track

How it works:
- Python bridge connects your local Reaper to the cloud
- Lua watches local files, executes commands
- Keep the bridge running (one CMD window)

Troubleshooting:
- If "module not found": run pip install -r requirements.txt
- If commands don't work: check Reaper console for errors
- Session ID is "demo" by default

