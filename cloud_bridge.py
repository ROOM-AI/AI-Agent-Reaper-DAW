"""
CursorDAW Cloud Bridge - Bidirectional file-based bridge
Connects local Reaper (via files) to cloud (via HTTP)
"""
import requests
import time
import os
import json
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

CLOUD_URL = "https://feelings36lex36slo14moossolo-97692729550.europe-west1.run.app"
SESSION_ID = "demo"

# Local files that Lua reads/writes - MUST match Lua script paths!
BASE_DIR = Path(r"C:\Users\moosb\AIAGENT DAW")
COMMAND_FILE = BASE_DIR / "reaper_commands.txt"
STATE_FILE = BASE_DIR / "reaper_state.txt"

print("=" * 50)
print("  CursorDAW Cloud Bridge")
print("=" * 50)
print(f"Cloud: {CLOUD_URL}")
print(f"Session: {SESSION_ID}")
print(f"Command file: {COMMAND_FILE}")
print(f"State file: {STATE_FILE}")
print("=" * 50)
print()

# Ensure files exist
COMMAND_FILE.touch(exist_ok=True)
STATE_FILE.touch(exist_ok=True)

class StateFileHandler(FileSystemEventHandler):
    """Watch for state file changes and send to cloud"""
    def __init__(self):
        self.last_sent = ""
    
    def on_modified(self, event):
        if event.src_path == str(STATE_FILE):
            try:
                content = STATE_FILE.read_text()
                if content and content != self.last_sent:
                    # Parse JSON and add session_id
                    try:
                        state_data = json.loads(content) if content else {}
                    except:
                        state_data = {"raw_state": content}
                    
                    # Add session_id to the body (not as query param)
                    state_data["session_id"] = SESSION_ID
                    
                    # Send state to cloud
                    requests.post(
                        f"{CLOUD_URL}/api/reaper/state",
                        json=state_data,
                        timeout=3
                    )
                    self.last_sent = content
                    print(f"→ Sent state to cloud (session: {SESSION_ID})")
            except Exception as e:
                print(f"⚠️ State send error: {e}")

def poll_commands():
    """Poll cloud for commands and write to local file"""
    print(f"Starting polling loop...")
    while True:
        try:
            r = requests.get(
                f"{CLOUD_URL}/api/reaper/poll",
                params={"session_id": SESSION_ID},
                timeout=5
            )
            if r.status_code == 200 and r.text and r.text.strip():
                # Server might return string or JSON - handle both
                response = r.text.strip()
                if response and response != "null" and response != '""' and response != "":
                    # Write command to file for Lua to read
                    COMMAND_FILE.write_text(response)
                    print(f"← Received command: {response[:80]}")
        except KeyboardInterrupt:
            raise  # Let Ctrl+C work
        except Exception as e:
            print(f"⚠️ Poll error: {e}")
        time.sleep(1.0)

if __name__ == "__main__":
    # Start watching state file
    observer = Observer()
    observer.schedule(StateFileHandler(), str(BASE_DIR), recursive=False)
    observer.start()
    print(f"✓ Watching {STATE_FILE} for changes")
    
    # Start polling for commands
    print("✓ Polling cloud for commands")
    print()
    print("Bridge is running. Keep this window open.")
    print("Press Ctrl+C to stop.")
    print()
    
    try:
        poll_commands()
    except KeyboardInterrupt:
        observer.stop()
        print("\nBridge stopped.")
    observer.join()

