"""
CursorDAW Cloud Bridge - Bidirectional file-based bridge
Connects local Reaper (via files) to cloud (via HTTP)
"""
import requests
import time
import os
import json
import threading
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

_last_state_sent = ""

# Ensure files exist
COMMAND_FILE.touch(exist_ok=True)
STATE_FILE.touch(exist_ok=True)

def _send_state_if_changed():
    global _last_state_sent
    try:
        if not STATE_FILE.exists():
            return
        content = STATE_FILE.read_text()
        if content and content != _last_state_sent:
            # Prefer raw text as 'state_text' so server can display it
            try:
                data = json.loads(content)
                # If JSON, still include the pretty text for logs
                state_payload = data if isinstance(data, dict) else {"state_text": str(data)}
            except Exception:
                state_payload = {"state_text": content}
            state_payload["session_id"] = SESSION_ID
            requests.post(
                f"{CLOUD_URL}/api/reaper/state",
                json=state_payload,
                timeout=3,
            )
            _last_state_sent = content
            print(f"→ Sent state to cloud (session: {SESSION_ID})")
    except Exception as e:
        print(f"⚠️ State send error: {e}")

class StateFileHandler(FileSystemEventHandler):
    """Watch for state file changes and send to cloud"""
    def on_modified(self, event):
        # Any file change in BASE_DIR triggers a check; internal de-dupe prevents spam
        _send_state_if_changed()

    def on_created(self, event):
        _send_state_if_changed()

def poll_commands():
    """Poll cloud for commands and write to local file (with simple de-dupe)"""
    print(f"Starting polling loop...")
    last_cmd_text = ""
    last_cmd_time = 0.0
    while True:
        try:
            r = requests.get(
                f"{CLOUD_URL}/api/reaper/poll",
                params={"session_id": SESSION_ID},
                timeout=5
            )
            if r.status_code == 200 and r.text and r.text.strip():
                # Server might return JSON string (e.g., "1007") or an object/array
                raw = r.text.strip()
                if raw and raw != "null" and raw != '""':
                    cmd_text = raw
                    try:
                        parsed = json.loads(raw)
                        # If it's a dict with 'command', use that; if it's a list, join lines; else str(parsed)
                        if isinstance(parsed, dict) and 'command' in parsed:
                            cmd_text = str(parsed['command'])
                        elif isinstance(parsed, (list, tuple)):
                            cmd_text = "\n".join(str(x) for x in parsed if x)
                        else:
                            cmd_text = str(parsed)
                    except Exception:
                        # Strip surrounding quotes if present
                        if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
                            cmd_text = raw[1:-1]
                    # Ensure trailing newline so Lua processes a single line cleanly
                    if not cmd_text.endswith("\n"):
                        cmd_text = cmd_text + "\n"
                    # Skip immediate duplicates (identical command back-to-back within ~1s)
                    now_ts = time.time()
                    if cmd_text.strip() == last_cmd_text.strip() and (now_ts - last_cmd_time) < 1.0:
                        # Still update last seen to extend window slightly
                        last_cmd_time = now_ts
                    else:
                        COMMAND_FILE.write_text(cmd_text)
                        print(f"← Received command: {cmd_text.strip()[:80]}")
                        last_cmd_text = cmd_text
                        last_cmd_time = now_ts
        except KeyboardInterrupt:
            raise  # Let Ctrl+C work
        except Exception as e:
            print(f"⚠️ Poll error: {e}")
        time.sleep(1.0)

def state_pump():
    """Periodic fallback to push state even if FS events are missed"""
    while True:
        _send_state_if_changed()
        time.sleep(1.0)

if __name__ == "__main__":
    # Start watching state file
    observer = Observer()
    observer.schedule(StateFileHandler(), str(BASE_DIR), recursive=False)
    observer.start()
    print(f"✓ Watching {STATE_FILE} for changes")
    
    # Start periodic state pump fallback
    threading.Thread(target=state_pump, daemon=True).start()
    
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

