# cloud_bridge_debug.py - Debug version with console output
import requests
import time
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLOUD_URL = os.getenv("CLOUD_URL", "https://feelings36lex36slo14moossolo-97692729550.europe-west1.run.app")
# Strip any leading @ and trailing spaces from URL
CLOUD_URL = CLOUD_URL.strip().lstrip('@')
COMMAND_FILE = os.getenv("COMMAND_FILE", r"C:\Users\moosb\AIAGENT DAW\reaper_commands.txt")
STATE_FILE = r"C:\Users\moosb\AIAGENT_DAW\reaper_state.txt"
SESSION_ID = os.getenv("SESSION_ID", "demo")

print("🌉 Bridge starting...")
print(f"☁️ Cloud: {CLOUD_URL}")
print(f"📁 Commands: {COMMAND_FILE}")
print(f"📁 State: {STATE_FILE}")
print(f"✅ Bridge active! Press Ctrl+C to stop.\n")

last_state = ""
loop_count = 0

def _translate(cmd: str) -> str:
    try:
        parts = cmd.strip().split()
        if not parts:
            return cmd
        if parts[0] == "ADD_FX" and len(parts) >= 3:
            t = int(parts[1])
            fx = " ".join(parts[2:])
            return f"ADD_FX:Track {t+1}:{fx}"
        if parts[0] == "SET_FX_PARAM" and len(parts) >= 5:
            t = int(parts[1]); fx = parts[2]; p = parts[3]; v = parts[4]
            return f"SET_FX_PARAM:Track {t+1}:FX {fx}:Param {p}:{v}"
        return cmd
    except Exception:
        return cmd

while True:
    try:
        # 1. Poll cloud for commands
        r = requests.get(f"{CLOUD_URL}/api/reaper/poll?session_id={SESSION_ID}", timeout=5)
        if r.status_code == 200:
            payload = (r.text or "").strip()
            cmd = payload.strip('"')
            if cmd and cmd.lower() != "null":
                out = _translate(cmd)
                with open(COMMAND_FILE, 'a', encoding='utf-8') as f:
                    f.write(out + '\n')
                print(f"📥 Command received: {cmd}")
                if out != cmd:
                    print(f"↪️  Translated to: {out}")
                print(f"✅ Written to {COMMAND_FILE}")
        
        # 2. Send state to cloud (every 2 seconds)
        loop_count += 1
        if loop_count >= 2:
            loop_count = 0
            
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state_text = f.read()
                if state_text and state_text != last_state:
                    last_state = state_text
                    resp = requests.post(
                        f"{CLOUD_URL}/api/reaper/state",
                        json={"session_id": SESSION_ID, "state_text": state_text},
                        timeout=5
                    )
                    if resp.status_code == 200:
                        print("📤 State sent (text dump)")
    
    except requests.exceptions.Timeout:
        print("⏱️ Timeout polling cloud")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    time.sleep(1.0)

