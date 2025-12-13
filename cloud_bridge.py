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
FEEDBACK_FILE = BASE_DIR / "reaper_feedback.txt"
TEMP_AUDIO_DIR = BASE_DIR / "temp_audio"
LYRICS_CACHE_DIR = BASE_DIR / "AI-Agent-Reaper-DAW" / "lyrics_cache"

print("=" * 50)
print("  CursorDAW Cloud Bridge")
print("=" * 50)
print(f"Cloud: {CLOUD_URL}")
print(f"Session: {SESSION_ID}")
print(f"Base directory: {BASE_DIR}")
print(f"Command file: {COMMAND_FILE}")
print(f"State file: {STATE_FILE}")
print(f"Feedback file: {FEEDBACK_FILE}")
print("=" * 50)
print()
print("NOTE: Only ONE user can use 'demo' session at a time.")
print("If sharing, edit SESSION_ID in cloud_bridge.py")
print()

_last_state_sent = ""
_last_send_ts = 0.0
_last_feedback_sent = ""
_last_feedback_ts = 0.0
MIN_SEND_INTERVAL = 1.5  # seconds, to avoid spam on partial writes

# Ensure directory and files exist
BASE_DIR.mkdir(parents=True, exist_ok=True)
COMMAND_FILE.touch(exist_ok=True)
STATE_FILE.touch(exist_ok=True)
FEEDBACK_FILE.touch(exist_ok=True)
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
LYRICS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _trim_state(content: str, max_chars: int = 60000) -> str:
    """Trim large state to prevent upload timeouts while keeping all tracks visible."""
    if len(content) <= max_chars:
        return content
    
    # Find all track sections
    lines = content.split('\n')
    header_lines = []
    track_sections = []
    current_track = []
    in_tracks = False
    
    for line in lines:
        if line.startswith('--- Track '):
            if current_track:
                track_sections.append('\n'.join(current_track))
            current_track = [line]
            in_tracks = True
        elif in_tracks:
            current_track.append(line)
        else:
            header_lines.append(line)
    
    if current_track:
        track_sections.append('\n'.join(current_track))
    
    header = '\n'.join(header_lines)
    
    # Trim each track evenly to fit
    if track_sections:
        available = max_chars - len(header) - 200
        per_track = max(1500, available // len(track_sections))
        trimmed_tracks = [t[:per_track] for t in track_sections]
        result = header + '\n' + '\n'.join(trimmed_tracks)
    else:
        result = content[:max_chars]
    
    if len(content) > len(result):
        result += f"\n\n... [{len(content) - len(result):,} chars trimmed for upload] ..."
    
    print(f"📦 State trimmed: {len(content):,} → {len(result):,} chars")
    return result


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
        
        # Trim large states to prevent upload timeouts
        content = _trim_state(content)
        
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
                timeout=5,  # Slightly longer timeout for trimmed state
            )
            _last_state_sent = content
            _last_send_ts = now_ts
            print(f"→ Sent state to cloud (session: {SESSION_ID})")
    except Exception as e:
        print(f"⚠️ State send error: {e}")


def _send_feedback_if_changed(force: bool = False):
    """Send feedback (including MIDI notes) to cloud"""
    global _last_feedback_sent
    global _last_feedback_ts
    try:
        if not FEEDBACK_FILE.exists():
            return
        time.sleep(0.05)

        now_ts = time.time()
        if not force and (now_ts - _last_feedback_ts) < MIN_SEND_INTERVAL:
            return

        content = FEEDBACK_FILE.read_text()
        
        if content and (force or content != _last_feedback_sent):
            feedback_payload = {
                "session_id": SESSION_ID,
                "feedback": content
            }
            requests.post(
                f"{CLOUD_URL}/api/reaper/feedback",
                json=feedback_payload,
                timeout=5,
            )
            _last_feedback_sent = content
            _last_feedback_ts = now_ts
            
            # Check if it contains MIDI notes
            if "MIDI_NOTES:" in content:
                note_count = content.count(";") + 1 if "MIDI_NOTES:" in content else 0
                print(f"→ Sent feedback with {note_count} MIDI notes to cloud")
            else:
                print(f"→ Sent feedback to cloud")
    except Exception as e:
        print(f"⚠️ Feedback send error: {e}")


class StateFileHandler(FileSystemEventHandler):
    """Watch for state and feedback file changes and send to cloud"""
    def on_modified(self, event):
        try:
            path = Path(event.src_path).resolve()
            if path == STATE_FILE.resolve():
                _send_state_if_changed()
            elif path == FEEDBACK_FILE.resolve():
                _send_feedback_if_changed()
        except Exception:
            pass

    def on_created(self, event):
        try:
            path = Path(event.src_path).resolve()
            if path == STATE_FILE.resolve():
                _send_state_if_changed()
            elif path == FEEDBACK_FILE.resolve():
                _send_feedback_if_changed()
        except Exception:
            pass

# Try to load drum index for ID-based sample resolution
try:
    from drum_index import get_path_by_id, load_index, get_cloud_summary
    _drum_index = load_index()
    DRUMS_AVAILABLE = _drum_index is not None
    if DRUMS_AVAILABLE:
        total = len(_drum_index.get("samples", {}))
        print(f"🥁 Drum index loaded: {total} samples")
except ImportError:
    DRUMS_AVAILABLE = False
    print("⚠️ Drum index not available - run: python drum_index.py F:\\")

def resolve_sample_id(sample_id):
    """Get full file path by sample ID"""
    if not DRUMS_AVAILABLE:
        return None
    
    path = get_path_by_id(sample_id)
    # If index was built on D:\ but samples are now on F:\, try drive-swap fallback.
    try:
        if path and isinstance(path, str) and len(path) >= 3 and path[1:3] == ":\\":
            if path[0].upper() == "D" and not Path(path).exists():
                alt = "F" + path[1:]
                if Path(alt).exists():
                    path = alt
    except Exception:
        pass
    if path:
        print(f"   🥁 Resolved ID {sample_id}: {os.path.basename(path)}")
    return path

def process_commands_locally(cmd_text):
    """
    Process commands before sending to Reaper.
    Resolves sample IDs to actual local file paths.
    """
    lines = cmd_text.strip().split('\n')
    processed = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('LOAD_SAMPLER'):
            # LOAD_SAMPLER <track> <sample_id> <base_note> [note_start] [note_end]
            # Convert to: LOAD_SAMPLER <track> "<full_path>" <base_note> [note_start] [note_end]
            parts = line.split()
            if len(parts) >= 4:
                track = parts[1]
                try:
                    sample_id = int(parts[2])
                    sample_path = resolve_sample_id(sample_id)
                    if sample_path:
                        # Rebuild command with full path
                        rest = ' '.join(parts[3:])  # base_note and optional range
                        processed.append(f'LOAD_SAMPLER {track} "{sample_path}" {rest}')
                        print(f"   🎹 Sampler: ID {sample_id} -> {sample_path}")
                    else:
                        print(f"   ⚠️ Sample ID {sample_id} not found, skipping")
                except ValueError:
                    # Not a number, might already be a path - pass through
                    processed.append(line)
            else:
                processed.append(line)
        
        elif line.startswith('USE_SAMPLE'):
            # USE_SAMPLE <track> <sample_id> <start_time> -> INSERT_AUDIO
            parts = line.split()
            if len(parts) >= 4:
                track = parts[1]
                try:
                    sample_id = int(parts[2])
                    start_time = parts[3]
                    sample_path = resolve_sample_id(sample_id)
                    if sample_path:
                        processed.append(f'INSERT_AUDIO {track} "{sample_path}" {start_time}')
                    else:
                        print(f"   ⚠️ Sample ID {sample_id} not found, skipping")
                except ValueError:
                    processed.append(line)
            else:
                processed.append(line)
        
        elif line.startswith('DRUM_SAMPLE'):
            # Legacy - pass through
            processed.append(line)
        
        elif line.startswith('EXPORT_AUDIO'):
            # EXPORT_AUDIO <track> <cloud_path>
            # Convert cloud Linux path to local Windows path
            parts = line.split()
            if len(parts) >= 3:
                track = parts[1]
                cloud_path = ' '.join(parts[2:])
                # Extract just the folder name (e.g., "track_4_1765067377")
                folder_name = cloud_path.split('/')[-1]
                if not folder_name:
                    folder_name = f"track_{track}_{int(time.time())}"
                # Create local path
                local_path = TEMP_AUDIO_DIR / folder_name
                local_path.mkdir(parents=True, exist_ok=True)
                processed.append(f'EXPORT_AUDIO {track} "{local_path}"')
                print(f"   📤 Export: track {track} -> {local_path}")
            else:
                processed.append(line)

        elif line.startswith('ELEVEN_VOCALS'):
            # ELEVEN_VOCALS <trackIdx> <startTime> <json_payload>
            # Local bridge calls cloud /api/vocals/elevenlabs to fetch MP3 bytes,
            # saves to temp_audio, then rewrites to INSERT_AUDIO for Lua.
            #
            # Example:
            # ELEVEN_VOCALS 1 0.0 {"session_id":"demo","lyrics":"...","tempo":140,"key":"C","mood":"reflective"}
            parts = line.split(maxsplit=3)
            if len(parts) >= 4:
                track_idx = parts[1]
                start_time = parts[2]
                payload_raw = parts[3].strip()
                try:
                    payload = json.loads(payload_raw)
                    if not isinstance(payload, dict):
                        raise ValueError("payload must be JSON object")
                    payload.setdefault("session_id", SESSION_ID)

                    url = f"{CLOUD_URL}/api/vocals/elevenlabs"
                    print(f"🎤 [ELEVEN] Requesting vocals-only MP3 from cloud...")
                    headers = {}
                    # Optional: if you protect cloud with AGENT_API_KEY, set AGENT_API_KEY locally too.
                    agent_key = os.getenv("AGENT_API_KEY", "")
                    if agent_key:
                        headers["X-API-KEY"] = agent_key
                    r = requests.post(url, json=payload, timeout=180, headers=headers)
                    r.raise_for_status()
                    audio_bytes = r.content
                    if not audio_bytes or len(audio_bytes) < 1024:
                        raise ValueError("Empty audio bytes returned")

                    fname = r.headers.get("X-Filename") or f"vocals_{int(time.time())}.mp3"
                    safe_name = fname.replace("/", "_").replace("\\", "_")
                    out_path = (TEMP_AUDIO_DIR / safe_name).resolve()
                    out_path.write_bytes(audio_bytes)
                    print(f"✅ [ELEVEN] Saved: {out_path} ({len(audio_bytes)/1024:.1f} KB)")

                    processed.append(f'INSERT_AUDIO {track_idx} "{out_path}" {start_time}')
                except Exception as e:
                    print(f"⚠️ [ELEVEN] Failed to generate/download vocals: {e}")
                    # IMPORTANT: never pass ELEVEN_VOCALS through to Lua, or Reaper will log "Unknown command".
                    # Drop the command on failure; the user can re-run once the issue is fixed.
                    continue
            else:
                # Bad format; drop it so Lua never sees it
                print("⚠️ [ELEVEN] Bad ELEVEN_VOCALS format; dropping command.")
                continue
        
        else:
            processed.append(line)
    
    return '\n'.join(processed)

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
                    
                    # Process commands locally (resolve sample IDs, convert cloud paths)
                    if any(kw in cmd_text for kw in ['USE_SAMPLE', 'DRUM_SAMPLE', 'LOAD_SAMPLER', 'EXPORT_AUDIO', 'ELEVEN_VOCALS']):
                        print(f"[BRIDGE] Processing commands locally...")
                        cmd_text = process_commands_locally(cmd_text)
                    
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
                        # Count commands (newline-separated)
                        cmd_count = len([c for c in cmd_text.strip().split('\n') if c.strip()])
                        if cmd_count > 1:
                            print(f"← Received {cmd_count} commands:")
                            for i, c in enumerate(cmd_text.strip().split('\n')[:5], 1):
                                print(f"   {i}. {c.strip()[:60]}")
                            if cmd_count > 5:
                                print(f"   ... and {cmd_count - 5} more")
                        else:
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

def lyrics_cache_worker():
    """Poll cloud for lyrics to cache locally"""
    print("✓ Lyrics cache thread running")
    while True:
        try:
            r = requests.get(
                f"{CLOUD_URL}/api/lyrics/pending",
                params={"session_id": SESSION_ID},
                timeout=5
            )
            if r.status_code == 200:
                data = r.json()
                pending = data.get("lyrics", [])
                for item in pending:
                    track_name = item.get("track_name", "")
                    lyrics = item.get("lyrics", [])
                    if track_name and lyrics:
                        # Save to local cache
                        # Sanitize track name for filename
                        safe_name = "".join(c if c.isalnum() or c in " -_()[]." else "_" for c in track_name)
                        cache_file = LYRICS_CACHE_DIR / f"{safe_name}.json"
                        try:
                            with open(cache_file, 'w', encoding='utf-8') as f:
                                json.dump({
                                    "track_name": track_name,
                                    "analyzed_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                                    "lyrics": lyrics
                                }, f, indent=2)
                            print(f"💾 Cached lyrics locally: {track_name} ({len(lyrics)} words)")
                        except Exception as e:
                            print(f"⚠️ Failed to cache lyrics for {track_name}: {e}")
        except Exception as e:
            # Only log if not a timeout/connection error
            if "timeout" not in str(e).lower() and "connection" not in str(e).lower():
                print(f"⚠️ Lyrics poll error: {e}")
        time.sleep(3.0)  # Poll every 3 seconds

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
    # Use temp directory that works on both Windows and Linux
    import tempfile
    session_dir = Path(tempfile.gettempdir()) / "daw_uploads" / SESSION_ID
    session_dir.mkdir(parents=True, exist_ok=True)
    scan_count = 0
    while True:
        try:
            if TEMP_AUDIO_DIR.exists():
                # Periodic scan logging (every ~30 seconds)
                scan_count += 1
                if scan_count % 20 == 1:  # Log occasionally
                    folders = list(TEMP_AUDIO_DIR.glob("track_*"))
                    if folders:
                        print(f"📂 Watching {len(folders)} export folder(s) in {TEMP_AUDIO_DIR}")
                
                for wav_path in TEMP_AUDIO_DIR.glob("track_*/*.wav"):
                    resolved = wav_path.resolve()
                    if str(resolved) in seen_files:
                        continue
                    
                    print(f"🔍 Found new audio: {wav_path}")

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
    threading.Thread(target=lyrics_cache_worker, daemon=True).start()
    
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

