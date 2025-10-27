# cloud_bridge.pyw - Runs invisible, no window!
import requests
import time
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Suppress all output (no console)
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

CLOUD_URL = os.getenv("CLOUD_URL", "https://feelings36lex36slo14moossolo-97692729550.europe-west1.run.app")
COMMAND_FILE = os.getenv("COMMAND_FILE", r"C:\Users\moosb\AIAGENT DAW\reaper_commands.txt")
SESSION_ID = os.getenv("SESSION_ID", "demo")

while True:
    try:
        # Poll cloud for commands
        r = requests.get(f"{CLOUD_URL}/api/reaper/poll?session_id={SESSION_ID}", timeout=5)
        
        # Check if we got a command
        if r.status_code == 200 and r.text and r.text.strip() != "" and r.text != "null":
            # Write command to file (append with newline so multiple commands work)
            with open(COMMAND_FILE, 'a') as f:
                f.write(r.text.strip() + '\n')
    except Exception as e:
        # Silent fail - no console window
        pass
    
    time.sleep(1.0)

