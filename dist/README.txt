=====================================
  CursorDAW Bridge - Quick Setup
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
   - Usually: Documents\REAPER Media\Scripts\
   - Or find it: Reaper menu > Options > Show REAPER resource path > Scripts

STEP 3: Run the Lua script in Reaper
   - Reaper menu > Actions > Show action list
   - Click "Load ReaScript" (bottom right)
   - Select "reaper_agent.lua"
   - Click "Run"
   - You should see a small "Agent Running" window

STEP 4: Run CursorDAW_Bridge.exe
   - Double-click CursorDAW_Bridge.exe
   - A console window opens and stays open
   - It auto-generates your unique session ID
   - Keep this window open while using CursorDAW

STEP 5: Open the AI interface
   - Go to: https://feelings36lex36slo14moossolo-97692729550.europe-west1.run.app
   - Your session ID is shown in the bridge window
   - Type something like "create 4 tracks for a lo-fi beat"

-------------------------------------
FILES INCLUDED
-------------------------------------
CursorDAW_Bridge.exe  - The bridge app (run this)
reaper_agent.lua      - Reaper script (copy to Reaper)
README.txt            - This file

-------------------------------------
OPTIONAL: Add your samples
-------------------------------------
If you have drum samples on an external drive (D:, E:, F:, etc.),
the bridge auto-detects them and builds a sample index.

To manually add sample folders:
1. Open bridge_config.json (created after first run)
2. Edit "sample_paths" to include your folders
3. Delete drum_index.json
4. Restart the bridge

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
- Bridge won't start? Make sure no other copy is running
- Reaper not responding? Make sure the Lua script is running
- Commands not working? Check both windows for errors

-------------------------------------
QUESTIONS?
-------------------------------------
DM @moosb on Discord or open an issue on GitHub.

Enjoy making music with AI!

