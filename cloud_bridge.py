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

CLOUD_URL = "https://feelings36lex36slo-97692729550.europe-west1.run.app"
SESSION_ID = "demo"

# Local files that Lua reads/writes
DOCS = Path.home() / "Documents"
COMMAND_FILE = DOCS / "reaper_commands.txt"
STATE_FILE = DOCS / "reaper_state.json"

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
                    # Send state to cloud
                    requests.post(
                        f"{CLOUD_URL}/api/reaper/state",
                        params={"session_id": SESSION_ID},
                        json=json.loads(content) if content else {},
                        timeout=3
                    )
                    self.last_sent = content
                    print(f"→ Sent state to cloud")
            except Exception as e:
                pass

def poll_commands():
    """Poll cloud for commands and write to local file"""
    while True:
        try:
            r = requests.get(
                f"{CLOUD_URL}/api/reaper/poll",
                params={"session_id": SESSION_ID},
                timeout=5
            )
            if r.text and r.text.strip() and r.text != "null":
                COMMAND_FILE.write_text(r.text)
                print(f"← Received command: {r.text[:50]}")
        except Exception as e:
            pass
        time.sleep(1.0)

if __name__ == "__main__":
    # Start watching state file
    observer = Observer()
    observer.schedule(StateFileHandler(), str(DOCS), recursive=False)
    observer.start()
    print("✓ Watching state file for changes")
    
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

