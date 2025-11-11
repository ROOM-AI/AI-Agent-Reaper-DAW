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

import numpy as np

try:
    import soundfile as sf
    import librosa
    AUDIO_TOOLS_AVAILABLE = True
except ImportError:
    AUDIO_TOOLS_AVAILABLE = False

CLOUD_URL = "https://feelings36lex36slo14moossolo-97692729550.europe-west1.run.app"
SESSION_ID = "demo"  # Default session - change this if multiple users

# Local files that Lua reads/writes - MUST match Lua script paths!
# Auto-detect base directory (matches Lua logic)
BASE_DIR_STR = os.getenv("REAPER_AGENT_DIR")
if not BASE_DIR_STR:
    home = os.getenv("USERPROFILE") or os.getenv("HOME") or "."
    BASE_DIR_STR = os.path.join(home, "AIAGENT DAW")
BASE_DIR = Path(BASE_DIR_STR)
COMMAND_FILE = BASE_DIR / "reaper_commands.txt"
STATE_FILE = BASE_DIR / "reaper_state.txt"
TEMP_AUDIO_DIR = BASE_DIR / "temp_audio"

print("=" * 50)
print("  CursorDAW Cloud Bridge")
print("=" * 50)
print(f"Cloud: {CLOUD_URL}")
print(f"Session: {SESSION_ID}")
print(f"Base directory: {BASE_DIR}")
print(f"Command file: {COMMAND_FILE}")
print(f"State file: {STATE_FILE}")
print("=" * 50)
print()
print("NOTE: Only ONE user can use 'demo' session at a time.")
print("If sharing, edit SESSION_ID in cloud_bridge.py")
print()

_last_state_sent = ""
_last_send_ts = 0.0
MIN_SEND_INTERVAL = 1.5  # seconds, to avoid spam on partial writes

# Ensure directory and files exist
BASE_DIR.mkdir(parents=True, exist_ok=True)
COMMAND_FILE.touch(exist_ok=True)
STATE_FILE.touch(exist_ok=True)
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def _send_state_if_changed(force: bool = False):
    global _last_state_sent
    global _last_send_ts
    try:
        if not STATE_FILE.exists():
            return
        # Let file writes settle briefly to avoid reading partial content
        time.sleep(0.05)

        # Basic rate limit unless forced
        now_ts = time.time()
        if not force and (now_ts - _last_send_ts) < MIN_SEND_INTERVAL:
            return

        content = STATE_FILE.read_text()
        if content and (force or content != _last_state_sent):
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
            _last_send_ts = now_ts
            print(f"→ Sent state to cloud (session: {SESSION_ID})")
    except Exception as e:
        print(f"⚠️ State send error: {e}")

class StateFileHandler(FileSystemEventHandler):
    """Watch for state file changes and send to cloud"""
    def on_modified(self, event):
        # Only react to the state file, ignore other changes in BASE_DIR
        try:
            if Path(event.src_path).resolve() == STATE_FILE.resolve():
                _send_state_if_changed()
        except Exception:
            _send_state_if_changed()

    def on_created(self, event):
        try:
            if Path(event.src_path).resolve() == STATE_FILE.resolve():
                _send_state_if_changed()
        except Exception:
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

                        # If cloud requested a state refresh, force-send after Lua writes it
                        if cmd_text.strip().upper() == "GET_STATE":
                            # Give Lua a short window to export
                            time.sleep(0.4)
                            _send_state_if_changed(force=True)
        except KeyboardInterrupt:
            raise  # Let Ctrl+C work
        except Exception as e:
            print(f"⚠️ Poll error: {e}")
        time.sleep(1.0)

def state_pump():
    """Periodic fallback to push state even if FS events are missed"""
    while True:
        _send_state_if_changed()
        time.sleep(2.0)

def _prepare_upload_file(wav_path: Path) -> Path:
    """
    Downsample + downmix large exports to keep uploads under Cloud Run limits.
    Returns path to file to upload (may be original path).
    """
    if not AUDIO_TOOLS_AVAILABLE:
        return wav_path
    try:
        audio, sr = librosa.load(str(wav_path), sr=None, mono=False)
    if audio is None or np.size(audio) == 0:
            return wav_path

    if audio.ndim > 1:
        audio = np.mean(audio, axis=0)

        target_sr = 16000
        if sr != target_sr:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
            sr = target_sr

        temp_path = wav_path.with_name(wav_path.stem + "_16k.wav")
        sf.write(str(temp_path), audio, sr, subtype="PCM_16")
        size_mb = temp_path.stat().st_size / (1024 * 1024)
        orig_mb = wav_path.stat().st_size / (1024 * 1024)
        print(f"🎚️ Prepared upload {temp_path.name}: {size_mb:.2f}MB (orig {orig_mb:.2f}MB)")
        return temp_path
    except Exception as e:
        print(f"⚠️ Downsample failed ({wav_path.name}): {e}")
        return wav_path


def upload_audio_worker():
    """Watch local temp_audio exports and upload new WAV files to cloud"""
    print("✓ Audio upload thread running")
    seen_files = set()
    session_dir = Path("/tmp/uploads") / SESSION_ID
    session_dir.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            if TEMP_AUDIO_DIR.exists():
                for wav_path in TEMP_AUDIO_DIR.glob("track_*/*.wav"):
                    resolved = wav_path.resolve()
                    if str(resolved) in seen_files:
                        continue

                    track_idx = None
                    parent = wav_path.parent.name
                    if parent.startswith("track_"):
                        parts = parent.split("_")
                        if len(parts) >= 2 and parts[1].isdigit():
                            track_idx = parts[1]

                    try:
                        upload_path = _prepare_upload_file(wav_path)
                        if upload_path != wav_path:
                            target = session_dir / upload_path.name
                            target.write_bytes(upload_path.read_bytes())
                            try:
                                upload_path.unlink()
                            except Exception:
                                pass
                            upload_path = target
                        else:
                            target = session_dir / wav_path.name
                            target.write_bytes(wav_path.read_bytes())
                            upload_path = target

                        with upload_path.open("rb") as f:
                            files = {"file": (upload_path.name, f, "audio/wav")}
                            params = {"session_id": SESSION_ID}
                            if track_idx is not None:
                                params["track_idx"] = track_idx
                            resp = requests.post(
                                f"{CLOUD_URL}/api/upload/audio",
                                params=params,
                                files=files,
                                timeout=60,
                            )
                        if resp.status_code == 200:
                            seen_files.add(str(resolved))
                            size_mb = upload_path.stat().st_size / (1024 * 1024)
                            print(f"→ Uploaded {upload_path.name} ({size_mb:.2f} MB) for session {SESSION_ID}")
                        else:
                            print(f"⚠️ Upload failed ({resp.status_code}): {resp.text[:120]}")
                        try:
                            upload_path.unlink()
                        except Exception:
                            pass
                    except FileNotFoundError:
                        continue  # File removed between glob and open
                    except Exception as e:
                        print(f"⚠️ Upload error: {e}")
        except Exception as outer_err:
            print(f"⚠️ Audio watcher error: {outer_err}")
        time.sleep(1.5)

if __name__ == "__main__":
    # Start watching state file
    observer = Observer()
    observer.schedule(StateFileHandler(), str(BASE_DIR), recursive=False)
    observer.start()
    print(f"✓ Watching {STATE_FILE} for changes")
    
    # Start periodic state pump fallback
    threading.Thread(target=state_pump, daemon=True).start()
    threading.Thread(target=upload_audio_worker, daemon=True).start()
    
    # Kick an initial state to the cloud: request export if file is empty, otherwise force-send
    def _kick_initial_state():
        try:
            time.sleep(0.2)  # allow observer/thread startup
            content = STATE_FILE.read_text() if STATE_FILE.exists() else ""
            if not content.strip():
                COMMAND_FILE.write_text("GET_STATE\n")
                print("→ Requested initial GET_STATE")
                time.sleep(0.5)  # wait for Lua to export
            _send_state_if_changed(force=True)
        except Exception as e:
            print(f"⚠️ Initial state kick error: {e}")
    threading.Thread(target=_kick_initial_state, daemon=True).start()
    
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

