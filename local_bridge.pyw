import os, sys, time, json, uuid, hashlib
from pathlib import Path
import requests

SERVER = os.getenv("REAPER_AGENT_SERVER", "").rstrip("/")
TOKEN  = os.getenv("AGENT_AUTH_TOKEN", "")
CLIENT_ID = os.getenv("AGENT_CLIENT_ID", "") or str(uuid.uuid4())[:8]

BASE_DIR = Path(os.getenv("REAPER_AGENT_DIR", str(Path.home() / "AIAGENT_DAW")))
BASE_DIR.mkdir(parents=True, exist_ok=True)

COMMAND_FILE = BASE_DIR / "reaper_commands.txt"
STATE_FILE   = BASE_DIR / "reaper_state.txt"
FEEDBACK_FILE= BASE_DIR / "reaper_feedback.txt"
LOG_FILE     = BASE_DIR / "bridge.log"
TEMP_AUDIO_DIR = BASE_DIR / "temp_audio"
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

def log(s: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + s + "\n")
    except Exception:
        pass

def post_state(blob: dict) -> bool:
    try:
        r = requests.post(f"{SERVER}/state/{CLIENT_ID}", headers=HEADERS, json=blob, timeout=10)
        return r.ok
    except Exception as e:
        log(f"post_state error: {e}")
        return False

def sse_connect():
    url = f"{SERVER}/connect?client_id={CLIENT_ID}"
    with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
        r.raise_for_status()
        buf = ""
        for line in r.iter_lines(decode_unicode=True):
            if line is None:
                continue
            if line == "":
                if buf.startswith("data:"):
                    data = buf[5:].strip()
                    yield "message", data
                elif buf.startswith("event:"):
                    evt = buf.split("\n")[0].split(":",1)[1].strip()
                    yield evt, "{}"
                buf = ""
            else:
                if buf:
                    buf += "\n" + line
                else:
                    buf = line

def write_commands(cmds):
    if not isinstance(cmds, list):
        cmds = [cmds]

    # Rewrite ELEVEN_VOCALS into INSERT_AUDIO by calling cloud bytes endpoint.
    # This prevents Reaper Lua from ever seeing the unknown ELEVEN_VOCALS command.
    processed = []
    for c in cmds:
        line = (c or "").strip()
        if not line:
            continue
        if line.startswith("ELEVEN_VOCALS"):
            # ELEVEN_VOCALS <trackIdx> <startTime> <json_payload>
            parts = line.split(maxsplit=3)
            if len(parts) >= 4:
                track_idx = parts[1]
                start_time = parts[2]
                payload_raw = parts[3].strip()
                try:
                    payload = json.loads(payload_raw)
                    if not isinstance(payload, dict):
                        raise ValueError("payload must be JSON object")
                    payload.setdefault("session_id", "demo")

                    # Call the server that local_bridge.pyw is connected to
                    url = f"{SERVER}/api/vocals/elevenlabs"
                    log(f"[ELEVEN] requesting vocals bytes: {url}")
                    headers = dict(HEADERS)
                    agent_key = os.getenv("AGENT_API_KEY", "")
                    if agent_key:
                        headers["X-API-KEY"] = agent_key
                    r = requests.post(url, headers=headers, json=payload, timeout=180)
                    try:
                        r.raise_for_status()
                    except requests.HTTPError as he:
                        body_preview = ""
                        try:
                            body_preview = (r.text or "")[:1200]
                        except Exception:
                            body_preview = ""
                        log(f"[ELEVEN] HTTP {r.status_code} body: {body_preview}")
                        raise he
                    audio_bytes = r.content
                    if not audio_bytes or len(audio_bytes) < 1024:
                        raise ValueError("empty audio bytes returned")

                    fname = r.headers.get("X-Filename") or f"vocals_{int(time.time())}.mp3"
                    safe_name = fname.replace("/", "_").replace("\\", "_")
                    out_path = (TEMP_AUDIO_DIR / safe_name).resolve()
                    out_path.write_bytes(audio_bytes)
                    log(f"[ELEVEN] saved {out_path} ({len(audio_bytes)} bytes)")

                    processed.append(f'INSERT_AUDIO {track_idx} "{out_path}" {start_time}')
                except Exception as e:
                    log(f"[ELEVEN] failed: {e}")
                    # IMPORTANT: never pass ELEVEN_VOCALS through to Lua, or Reaper will log "Unknown command".
                    # Drop the command on failure; user can retry once fixed.
                    continue
            else:
                log("[ELEVEN] bad ELEVEN_VOCALS format; dropping")
                continue
        elif line.startswith("EL1_SONG"):
            # EL1_SONG <startTime> <json_payload>
            # Full song via ElevenLabs + stem separation
            import base64
            
            parts = line.split(maxsplit=2)
            if len(parts) >= 3:
                start_time = parts[1]
                payload_raw = parts[2].strip()
                try:
                    payload = json.loads(payload_raw)
                    if not isinstance(payload, dict):
                        raise ValueError("payload must be JSON object")
                    payload.setdefault("session_id", "demo")

                    url = f"{SERVER}/api/el1/generate"
                    log(f"[EL1] requesting full song + stems: {url}")
                    headers = dict(HEADERS)
                    agent_key = os.getenv("AGENT_API_KEY", "")
                    if agent_key:
                        headers["X-API-KEY"] = agent_key
                    
                    r = requests.post(url, headers=headers, json=payload, timeout=600)
                    try:
                        r.raise_for_status()
                    except requests.HTTPError as he:
                        body_preview = ""
                        try:
                            body_preview = (r.text or "")[:1200]
                        except Exception:
                            body_preview = ""
                        log(f"[EL1] HTTP {r.status_code} body: {body_preview}")
                        raise he
                    
                    result = r.json()
                    
                    # Track mapping for 6 stems
                    stem_tracks = {"vocals": 0, "drums": 1, "bass": 2, "guitar": 3, "piano": 4, "other": 5}
                    stems_data = result.get("stems", {})
                    timestamp = int(time.time())
                    
                    for stem_name, track_idx in stem_tracks.items():
                        stem_b64 = stems_data.get(stem_name, "")
                        if stem_b64:
                            try:
                                stem_bytes = base64.b64decode(stem_b64)
                                if len(stem_bytes) > 1024:
                                    filename = f"{stem_name}_{timestamp}.mp3"
                                    out_path = (TEMP_AUDIO_DIR / filename).resolve()
                                    out_path.write_bytes(stem_bytes)
                                    log(f"[EL1] saved {stem_name}: {out_path}")
                                    processed.append(f'INSERT_AUDIO {track_idx} "{out_path}" {start_time}')
                            except Exception as stem_err:
                                log(f"[EL1] failed to save {stem_name}: {stem_err}")
                    
                    # Full song to track 4
                    full_b64 = result.get("full_song", "")
                    if full_b64:
                        try:
                            full_bytes = base64.b64decode(full_b64)
                            full_path = (TEMP_AUDIO_DIR / f"fullsong_{timestamp}.mp3").resolve()
                            full_path.write_bytes(full_bytes)
                            log(f"[EL1] saved full song: {full_path}")
                            processed.append(f'INSERT_AUDIO 6 "{full_path}" {start_time}')
                        except Exception as full_err:
                            log(f"[EL1] failed to save full song: {full_err}")
                    
                    log("[EL1] Complete! 6 stems → tracks 0-5, full song → track 6")
                    
                except Exception as e:
                    log(f"[EL1] failed: {e}")
                    continue
            else:
                log("[EL1] bad EL1_SONG format; dropping")
                continue
        else:
            processed.append(line)

    with open(COMMAND_FILE, "w", encoding="utf-8") as f:
        for c in processed:
            f.write(c.strip() + "\n")

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def main_loop():
    if not SERVER:
        log("Missing REAPER_AGENT_SERVER. Set the env var and re-run.")
        return
    log(f"Bridge started. Server={SERVER}, client_id={CLIENT_ID}")
    last_state_hash = ""

    try:
        requests.get(f"{SERVER}/healthz", timeout=5)
    except Exception as e:
        log(f"healthz failed: {e}")

    while True:
        try:
            for evt, payload in sse_connect():
                if evt == "hello":
                    log(f"Connected (client_id={CLIENT_ID})")
                elif evt == "message":
                    try:
                        data = json.loads(payload)
                    except Exception:
                        log(f"bad json: {payload[:120]}")
                        continue
                    if data.get("type") == "cloud_cmd":
                        cmds = data.get("commands") or []
                        write_commands(cmds)
                        log(f"wrote {len(cmds)} command(s)")
                    elif data.get("type") == "rpc":
                        handle_rpc(data)
                elif evt == "ping":
                    pass

                if STATE_FILE.exists():
                    raw = read_text(STATE_FILE)
                    h = hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()
                    if h != last_state_hash and len(raw) > 0:
                        post_state({"state_text": raw, "ts": time.time(), "track_count": raw.count("\n--- Track ")})
                        last_state_hash = h
        except Exception as e:
            log(f"SSE error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        pass

# -------------------- RPC handlers --------------------
def _safe_path(rel: str) -> Path:
    p = (BASE_DIR / rel).resolve()
    if not str(p).startswith(str(BASE_DIR.resolve())):
        raise ValueError("path outside base")
    return p

def handle_rpc(msg: dict):
    req_id = msg.get("req_id")
    op = msg.get("op")
    rel = (msg.get("path") or "").replace("\\", "/").lstrip("/")
    args = msg.get("args") or {}
    try:
        if op == "read_text":
            p = _safe_path(rel)
            data = {"text": read_text(p)}
            _rpc_reply(req_id, ok=True, data=data)
        elif op == "write_text":
            p = _safe_path(rel)
            txt = args.get("text", "")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(txt, encoding="utf-8")
            _rpc_reply(req_id, ok=True, data={"written": len(txt)})
        elif op == "exists":
            p = _safe_path(rel)
            _rpc_reply(req_id, ok=True, data={"exists": p.exists()})
        elif op == "listdir":
            p = _safe_path(rel)
            if not p.exists() or not p.is_dir():
                _rpc_reply(req_id, ok=False, error="not_dir")
            else:
                _rpc_reply(req_id, ok=True, data={"entries": sorted(os.listdir(p))})
        elif op == "append_text":
            p = _safe_path(rel)
            txt = args.get("text", "")
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(txt)
            _rpc_reply(req_id, ok=True, data={"appended": len(txt)})
        else:
            _rpc_reply(req_id, ok=False, error="unknown_op")
    except Exception as e:
        _rpc_reply(req_id, ok=False, error=str(e))

def _rpc_reply(req_id: str, ok: bool, data: dict = None, error: str = None):
    payload = {"req_id": req_id, "ok": ok}
    if ok and data is not None:
        payload["data"] = data
    if not ok and error is not None:
        payload["error"] = error
    try:
        requests.post(f"{SERVER}/rpc/reply/{CLIENT_ID}", headers=HEADERS, json=payload, timeout=10)
    except Exception as e:
        log(f"rpc reply error: {e}")


