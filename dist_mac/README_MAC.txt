=====================================
  CursorDAW Bridge - Mac Setup
=====================================

WHAT IS THIS?
CursorDAW lets you control Reaper with AI.
Type "make a chill trap beat" and watch it happen.

-------------------------------------
SETUP (5 minutes)
-------------------------------------

STEP 1: Install Reaper (if you don't have it)
   Download: https://www.reaper.fm/download.php
   (Free to try, $60 license)

STEP 2: Copy the Lua script to Reaper
   - Copy "reaper_agent.lua" to your Reaper Scripts folder
   - Usually: ~/Library/Application Support/REAPER/Scripts/
   - Or find it: Reaper menu > Options > Show REAPER resource path > Scripts

STEP 3: Run the Lua script in Reaper
   - Reaper menu > Actions > Show action list
   - Click "Load ReaScript" (bottom right)
   - Select "reaper_agent.lua"
   - Click "Run"
   - You should see a small "Agent Running" window

STEP 4: Start the Bridge

   OPTION A - Double-click (if it works):
     1. Double-click "start_bridge.command"
     2. If macOS blocks it: Right-click > Open > Open Anyway
     3. If "permission denied": use Option B
   
   OPTION B - Terminal (always works):
     cd ~/Downloads/CursorDAW_Demo_Mac
     bash start_bridge.command
   
   The script automatically:
   - Creates a private Python environment (no admin/sudo)
   - Installs dependencies there (not in system Python)
   - Logs to ~/Library/Application Support/CursorDAWBridge/logs/
   
   Keep the terminal open while using CursorDAW!
   
   To stop: Press Ctrl+C, or run: bash stop_bridge.command

STEP 5: Open the AI interface
   - Go to: https://feelings36lex36slo14moossolo-97692729550.europe-west1.run.app
   - Your session ID is shown in the terminal
   - Type something like "create 4 tracks for a lo-fi beat"

-------------------------------------
FILES INCLUDED
-------------------------------------
start_bridge.command  - Double-click to start (creates venv, installs deps)
stop_bridge.command   - Double-click to stop the bridge
cloud_bridge.py       - The bridge script
reaper_agent.lua      - Reaper script (copy to Reaper)
README_MAC.txt        - This file

-------------------------------------
QUICK START (after first setup)
-------------------------------------
1. Open Reaper, run the Lua script (Actions > reaper_agent.lua)
2. Terminal: bash start_bridge.command
3. Open browser to the AI interface
4. Make music!

-------------------------------------
HOW TO MAKE MUSIC
-------------------------------------

TWO WAYS TO USE THE AI:

1. ENHANCE PROMPT (recommended for beginners)
   - Type a vague idea: "chill lo-fi beat"
   - Click "Enhance" button
   - AI rewrites it into specific commands
   - Review the enhanced prompt, then click "Send"
   
   This is great for:
   - Full songs: "make a sad trap song with 808s"
   - Quick ideas: "add some piano chords"
   - Fixing prompts: "make it more emotional"

2. DIRECT COMMANDS (for power users)
   - Type exactly what you want
   - Click "Send" directly (skip Enhance)
   - Example: "add a synth melody on track 3 in C minor"

EXAMPLE WORKFLOW:
1. Type: "dark ambient piano with reverb"
2. Click ENHANCE - AI expands it to detailed commands
3. Review the enhanced version
4. Click SEND - commands go to Reaper
5. Listen and iterate!

TIP: You can enhance multiple times to refine your idea.

-------------------------------------
TROUBLESHOOTING
-------------------------------------
- "python3 not found"? Install Python from python.org
- "No module named requests"? Run: pip3 install requests watchdog numpy
- Reaper not responding? Make sure the Lua script is running

-------------------------------------
QUESTIONS?
-------------------------------------
DM @moosb on Discord or open an issue on GitHub.

Enjoy making music with AI!

