import os, time, json
from collections import defaultdict, deque
from typing import Optional, Dict, Any, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv
import asyncio
import threading, uuid

# Load environment variables
load_dotenv()

# -------------------- App & CORS --------------------
app = FastAPI(title="CursorDAW Cloud")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

API_KEY = os.getenv("AGENT_API_KEY", "")  # set this on Railway

# -------------------- In-memory state --------------------
EVENTS: List[Dict[str, Any]] = []
QUEUES: Dict[str, deque] = defaultdict(deque)

def add_event(kind: str, data: Any, session_id: Optional[str] = None):
    EVENTS.append({"t": time.time(), "kind": kind, "session_id": session_id, "data": data})
    if len(EVENTS) > 5000:
        del EVENTS[:4000]

def require_key(x_api_key: str):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(401, "bad api key")

# -------------------- Models --------------------
class ChatIn(BaseModel):
    session_id: str = "demo"
    text: str

class ReportIn(BaseModel):
    session_id: str
    step_id: str
    ok: bool
    meta: Optional[Dict[str, Any]] = None

class AdminCmd(BaseModel):
    session_id: str
    command: Dict[str, Any]  # {"id":"s1","action":"ADD_FX", ...}


# -------------------- ElevenLabs vocals-only --------------------
class ElevenVoxRequest(BaseModel):
    session_id: str = "demo"
    lyrics: str
    tempo: int = 120
    key: str = "C"
    mood: str = "soulful"
    melody_midi: Optional[List[int]] = None
    music_length_ms: Optional[int] = None
    # NEW: Full chord progression and song structure for better vocal sync
    chord_progression: Optional[List[Dict[str, Any]]] = None  # [{"bar": 1, "beat": 1, "chord": "Am"}, ...]
    song_structure: Optional[List[Dict[str, Any]]] = None  # [{"section": "Verse", "start_bar": 1, "end_bar": 16}, ...]
    song_length_seconds: Optional[float] = None
    instruments: Optional[List[str]] = None  # ["Piano", "808 Bass", "Hi-hats"]


@app.post("/api/vocals/elevenlabs")
def elevenlabs_vocals_bytes(body: ElevenVoxRequest, request: Request):
    """
    Generate VOCALS-ONLY (a cappella) via ElevenLabs Eleven Music and return MP3 bytes directly.

    This is the Option-B transport you chose: cloud returns bytes; local bridge saves to a file
    and then Reaper Lua imports it with INSERT_AUDIO.
    """
    # Optional auth: if AGENT_API_KEY is set, require header X-API-KEY
    if API_KEY:
        x_api_key = request.headers.get("X-API-KEY", "")
        if x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="bad api key")

    try:
        from elevenlabs_vocals import VocalBrief, build_vocals_prompt, compose_vocals_mp3

        brief = VocalBrief(
            lyrics=body.lyrics,
            bpm=int(body.tempo) if body.tempo else None,
            key=body.key,
            style=body.mood,
            melody_midi=body.melody_midi,
            voice_tags=["lead vocal", "a cappella", "vocals only"],
            # NEW: Full musical context for better vocal sync
            chord_progression=body.chord_progression,
            song_structure=body.song_structure,
            song_length_seconds=body.song_length_seconds,
            instruments=body.instruments,
        )
        prompt = build_vocals_prompt(brief)
        length_ms = body.music_length_ms
        if length_ms is None:
            # Rough default: 30 seconds
            length_ms = 30000

        audio_bytes, filename, meta = compose_vocals_mp3(
            prompt=prompt,
            length_ms=int(length_ms),
            retries=3,
            retry_backoff_s=1.5,
        )

        add_event(
            "elevenlabs_vocals_generated",
            {
                "filename": filename,
                "bytes": len(audio_bytes),
                "tempo": body.tempo,
                "key": body.key,
            },
            session_id=body.session_id,
        )

        # Return raw MP3 bytes
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "X-Filename": filename,
                "X-Bytes": str(len(audio_bytes)),
            },
        )
    except Exception as e:
        # Preserve more detail for debugging (SDK errors often have useful fields).
        detail = {"error": str(e), "type": type(e).__name__}
        try:
            body = getattr(e, "body", None)
            if body is not None:
                detail["body"] = body
            status_code = getattr(e, "status_code", None)
            if status_code is not None:
                detail["status_code"] = status_code
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=detail)

# -------------------- Health --------------------
@app.get("/health")
def health():
    return {"ok": True, "ts": time.time()}


# -------------------- M1 - MIDI FOUNDATION MODEL --------------------
# In-memory storage for generated MIDI files (for download)
MIDI_STORAGE: Dict[str, bytes] = {}

@app.get("/api/midi/{midi_id}")
def download_midi(midi_id: str):
    """Download a generated MIDI file by ID."""
    from fastapi.responses import Response
    if midi_id not in MIDI_STORAGE:
        return {"error": "MIDI not found"}
    return Response(
        content=MIDI_STORAGE[midi_id],
        media_type="audio/midi",
        headers={"Content-Disposition": f"attachment; filename={midi_id}.mid"}
    )

@app.post("/api/m1")
def api_m1(session_id: str = "demo", request: Request = None):
    """
    M1 - Completely separate endpoint for MIDI Foundation Model.
    No agent. No enhance_prompt. Just calls the model and queues commands.
    """
    import requests
    import base64
    import os
    import uuid
    
    MIDI_API = "https://192-222-51-140.tail9f8b6b.ts.net"
    
    print(f"🎹 [M1] Endpoint called for session {session_id}")
    
    try:
        # Call MIDI model
        print(f"🎹 [M1] Calling {MIDI_API}/generate ...")
        resp = requests.post(
            f"{MIDI_API}/generate",
            json={"max_tokens": 4096, "temperature": 0.9},  # More tokens = more notes
            timeout=600  # 10 min timeout for longer generations
        )
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("success") or not data.get("midi_b64"):
            return {"status": "error", "message": "No MIDI returned from model"}
        
        # Decode and store with unique ID
        midi_bytes = base64.b64decode(data["midi_b64"])
        midi_id = f"m1_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        MIDI_STORAGE[midi_id] = midi_bytes
        
        # Clean up old MIDI files (keep last 50)
        if len(MIDI_STORAGE) > 50:
            oldest_keys = list(MIDI_STORAGE.keys())[:-50]
            for k in oldest_keys:
                del MIDI_STORAGE[k]
        
        # Queue commands with DOWNLOAD_MIDI command (local agent will fetch via URL)
        commands = [
            f'DOWNLOAD_MIDI 1 "{midi_id}" 0.0',
            'INSERT_INSTRUMENT 1 ReaSynth',
            'INSERT_INSTRUMENT 2 ReaSynth', 
            'INSERT_INSTRUMENT 3 ReaSynth',
            'INSERT_INSTRUMENT 4 ReaSynth',
        ]
        if session_id not in REAPER_SESSIONS:
            REAPER_SESSIONS[session_id] = []
        for cmd in commands:
            REAPER_SESSIONS[session_id].append(cmd)
        
        return {
            "status": "success",
            "message": f"Generated {data.get('num_notes', 0)} notes, queued {len(commands)} commands",
            "midi_id": midi_id,
            "commands": commands,
        }
    except Exception as e:
        print(f"❌ [M1] Error: {e}")
        return {"status": "error", "message": str(e)}


# -------------------- EL1 Full Song + Stems --------------------
class EL1SongRequest(BaseModel):
    session_id: str = "demo"
    lyrics: str
    title: str = "Untitled"
    song_length_seconds: float = 120.0
    description: str = ""  # Original user request for context
    start_time: float = 0.0  # Reaper start time for INSERT_AUDIO
    # Optional overrides (ElevenLabs decides if not provided)
    genre: Optional[str] = None
    mood: Optional[str] = None
    tempo: Optional[int] = None
    key: Optional[str] = None
    vocal_style: Optional[str] = None


# ==================== MODEL O ====================
# MODEL O: Handles ALL ElevenLabs communication.
# When user types EL1, MODEL O:
# 1. Calls ElevenLabs (generates song + stems)
# 2. Waits for all MP3s to return
# 3. Queues INSERT_AUDIO_B64 commands with audio bytes directly
# Bridge just decodes and imports - zero requests back to cloud.

# Track in-flight MODEL O jobs per session to avoid accidental duplicates
_MODELO_LOCK = threading.Lock()
_MODELO_INFLIGHT: Dict[str, str] = {}  # session_id -> job_id


def _modelo_worker(job_id: str, session_id: str, start_time: float, brief_dict: Dict[str, Any]):
    """
    MODEL O worker: calls ElevenLabs, extracts stems, queues audio bytes to bridge.
    Bridge receives INSERT_AUDIO_B64 commands and just decodes + saves + imports.
    """
    import traceback
    import base64
    import zipfile
    import io
    
    try:
        from elevenlabs_fullsong import FullSongBrief, generate_and_stem_zip, ElevenLabsBadPromptError
        
        print(f"🎵 [MODEL O] {job_id} starting ElevenLabs generation...", flush=True)
        add_event("modelo_started", {"job_id": job_id, "title": brief_dict.get("title")}, session_id=session_id)
        
        brief = FullSongBrief(
            lyrics=brief_dict.get("lyrics", ""),
            title=brief_dict.get("title", "Untitled"),
            song_length_seconds=brief_dict.get("song_length_seconds", 120.0),
            additional_instructions=brief_dict.get("description", ""),
            genre=brief_dict.get("genre") or "pop",
            mood=brief_dict.get("mood") or "uplifting",
            tempo=brief_dict.get("tempo") or 120,
            key=brief_dict.get("key") or "C",
            vocal_style=brief_dict.get("vocal_style") or "mixed",
        )
        
        # Call ElevenLabs - this takes 3-8 minutes
        zip_bytes, metadata = generate_and_stem_zip(brief)
        print(f"✅ [MODEL O] {job_id} got ZIP from ElevenLabs: {len(zip_bytes)/1024:.1f} KB", flush=True)
        
        # Extract stems and queue INSERT_AUDIO_B64 commands for each
        stem_tracks = {
            "vocals": 0, "drums": 1, "bass": 2,
            "guitar": 3, "piano": 4, "other": 5, "fullsong": 6
        }
        
        if session_id not in REAPER_SESSIONS:
            REAPER_SESSIONS[session_id] = []
        
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            print(f"   [MODEL O] ZIP contents: {zf.namelist()}", flush=True)
            
            for filename in zf.namelist():
                stem_bytes = zf.read(filename)
                if len(stem_bytes) < 1024:
                    continue
                
                file_lower = filename.lower().replace('.mp3', '')
                track_idx = stem_tracks.get(file_lower)
                
                if track_idx is not None:
                    # Base64 encode the audio bytes
                    b64_audio = base64.b64encode(stem_bytes).decode('ascii')
                    
                    # Queue command: INSERT_AUDIO_B64 <track> <start> <base64_bytes>
                    cmd = f"INSERT_AUDIO_B64 {track_idx} {start_time} {b64_audio}"
                    REAPER_SESSIONS[session_id].append(cmd)
                    
                    print(f"📤 [MODEL O] Queued {file_lower} ({len(stem_bytes)/1024:.1f} KB) → track {track_idx}", flush=True)
        
        add_event("modelo_done", {"job_id": job_id, "stems_queued": len(stem_tracks)}, session_id=session_id)
        print(f"✅ [MODEL O] {job_id} complete! All stems queued for bridge.", flush=True)
        
    except Exception as e:
        print(f"🛑 [MODEL O] {job_id} failed: {e}", flush=True)
        traceback.print_exc()
        add_event("modelo_failed", {"job_id": job_id, "error": str(e)[:500]}, session_id=session_id)
    finally:
        # Clear inflight marker so the user can try again.
        try:
            with _MODELO_LOCK:
                if _MODELO_INFLIGHT.get(session_id) == job_id:
                    _MODELO_INFLIGHT.pop(session_id, None)
        except Exception:
            pass


@app.post("/api/modelo/el1")
def modelo_el1(body: EL1SongRequest, request: Request):
    """
    MODEL O endpoint for EL1.
    Starts worker that calls ElevenLabs and queues audio bytes to bridge.
    Returns immediately - bridge will receive INSERT_AUDIO_B64 commands when ready.
    """
    # Optional auth
    if API_KEY:
        x_api_key = request.headers.get("X-API-KEY", "")
        if x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="bad api key")
    
    # Prevent multiple EL1 jobs for the same session (common if user clicks twice).
    with _MODELO_LOCK:
        existing = _MODELO_INFLIGHT.get(body.session_id)
        if existing:
            return {
                "status": "busy",
                "job_id": existing,
                "message": "MODEL O is already generating for this session. Please wait for stems to appear.",
            }
        job_id = f"modelo_{uuid.uuid4().hex[:8]}"
        _MODELO_INFLIGHT[body.session_id] = job_id

    brief_dict = {
        "lyrics": body.lyrics,
        "title": body.title,
        "song_length_seconds": body.song_length_seconds,
        "description": body.description,
        "genre": body.genre,
        "mood": body.mood,
        "tempo": body.tempo,
        "key": body.key,
        "vocal_style": body.vocal_style,
    }
    
    # Start MODEL O worker thread
    t = threading.Thread(
        target=_modelo_worker,
        args=(job_id, body.session_id, body.start_time, brief_dict),
        daemon=True,
    )
    t.start()
    
    print(f"🧾 [MODEL O] {job_id} started for '{body.title}'", flush=True)
    
    return {"status": "started", "job_id": job_id, "message": "MODEL O is working. Stems will appear in bridge when ready."}


# Legacy sync endpoint (kept for backwards compatibility - but will timeout on long jobs)
@app.post("/api/el1/generate")
def el1_generate_fullsong(body: EL1SongRequest, request: Request):
    """
    EL1 Mode: Generate full song via ElevenLabs + separate into stems.
    
    Returns a ZIP file containing all stems as MP3 files.
    Same format as ElevenLabs stem separation API.
    """
    import zipfile
    import io
    
    # Optional auth
    if API_KEY:
        x_api_key = request.headers.get("X-API-KEY", "")
        if x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="bad api key")
    
    try:
        from elevenlabs_fullsong import FullSongBrief, generate_and_stem_zip, ElevenLabsBadPromptError
        
        # Build brief with only what's provided (let ElevenLabs decide the rest)
        brief = FullSongBrief(
            lyrics=body.lyrics,
            title=body.title,
            song_length_seconds=body.song_length_seconds,
            additional_instructions=body.description,
            # Only set these if explicitly provided
            genre=body.genre or "pop",
            mood=body.mood or "uplifting",
            tempo=body.tempo or 120,
            key=body.key or "C",
            vocal_style=body.vocal_style or "mixed"
        )
        
        # Get ZIP directly (no re-packaging, much simpler!)
        zip_bytes, metadata = generate_and_stem_zip(brief)
        
        add_event(
            "el1_song_generated",
            {
                "title": body.title,
                "genre": body.genre,
                "tempo": body.tempo,
                "zip_size": len(zip_bytes),
            },
            session_id=body.session_id,
        )
        
        # Return ZIP directly - same as vocals endpoint returns MP3
        print(f"📤 [EL1] Returning ZIP: {len(zip_bytes)/1024:.1f} KB")
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "X-Filename": f"el1_stems_{body.session_id}.zip",
                "X-Bytes": str(len(zip_bytes)),
            },
        )
        
    except ElevenLabsBadPromptError as e:
        # Non-transient: don't pretend it's a server failure.
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "bad_prompt",
                "message": str(e),
                "prompt_suggestion": getattr(e, "prompt_suggestion", None),
                "status_code": getattr(e, "status_code", None),
                "body": getattr(e, "body", None),
            },
        )
    except Exception as e:
        detail = {"error": str(e), "type": type(e).__name__}
        try:
            body_attr = getattr(e, "body", None)
            if body_attr is not None:
                detail["body"] = body_attr
            status_code = getattr(e, "status_code", None)
            if status_code is not None:
                detail["status_code"] = status_code
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=detail)


# -------------------- Public read-only for investors --------------------
@app.get("/public/events")
def public_events(since: Optional[float] = None, session_id: Optional[str] = None):
    arr = EVENTS
    if session_id:
        arr = [e for e in arr if e["session_id"] == session_id]
    if since is not None:
        arr = [e for e in arr if e["t"] > since]
    return arr[-200:]

# -------------------- Chat → plan → queue --------------------
@app.post("/api/chat")
def api_chat(body: ChatIn):
    """
    Cloud AI agent - uses FULL agent logic with Claude reasoning
    """
    import io
    import sys
    
    raw_text = (body.text or "").strip()
    
    # ============================================================
    # M1 - HARDCODED - RUNS FIRST BEFORE ANYTHING ELSE
    # ============================================================
    if raw_text.lower().startswith("m1 ") or raw_text.lower().startswith("m1:"):
        import requests
        import base64
        import os
        import uuid
        
        MIDI_API = "https://192-222-51-140.tail9f8b6b.ts.net"
        
        print(f"🎹 [M1] CALLING MIDI MODEL...")
        
        try:
            # Call MIDI model - wait up to 10 minutes
            resp = requests.post(
                f"{MIDI_API}/generate",
                json={"max_tokens": 512, "temperature": 0.9},  # Shorter for faster generation
                timeout=600
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("success") or not data.get("midi_b64"):
                return {"reply": f"❌ M1: No MIDI returned", "status": "error", "commands": []}
            
            # Decode and save MIDI
            midi_bytes = base64.b64decode(data["midi_b64"])
            midi_dir = os.path.join(os.path.dirname(__file__), "generated_midi")
            os.makedirs(midi_dir, exist_ok=True)
            midi_path = os.path.join(midi_dir, f"m1_{int(time.time())}.mid")
            with open(midi_path, "wb") as f:
                f.write(midi_bytes)
            
            # Queue commands to REAPER_SESSIONS
            commands = [
                f'INSERT_AUDIO 1 "{midi_path}" 0.0',
                'INSERT_INSTRUMENT 1 ReaSynth',
                'INSERT_INSTRUMENT 2 ReaSynth',
                'INSERT_INSTRUMENT 3 ReaSynth',
                'INSERT_INSTRUMENT 4 ReaSynth',
            ]
            if body.session_id not in REAPER_SESSIONS:
                REAPER_SESSIONS[body.session_id] = []
            for cmd in commands:
                REAPER_SESSIONS[body.session_id].append(cmd)
            
            return {
                "reply": f"🎹 M1: {data.get('num_notes', 0)} notes → queued {len(commands)} commands",
                "status": "success",
                "commands": commands,
                "plan": {"plan_id": f"m1-{int(time.time()*1000)}", "steps": []},
            }
        except Exception as e:
            return {"reply": f"❌ M1 Error: {e}", "status": "error", "commands": []}
    
    # ============================================================
    # EVERYTHING ELSE (agent, enhance_prompt, etc.)
    # ============================================================
    
    # Capture stdout with StringIO
    output_capture = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = output_capture
    sys.stderr = output_capture
    
    try:
        _ensure_agent_loaded()
        # Import prompt enhancer
        from prompt_enhancer import enhance_prompt, generate_song_commands
        if raw_text.startswith("# MODEL O is generating"):
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            return {
                "reply": "⏳ MODEL O is already generating. Stems will import when ready.",
                "plan": {"plan_id": f"plan-{int(time.time()*1000)}", "steps": []},
                "commands": [],
                "status": "success",
                "agent_reasoning": raw_text,
                "full_output": "",
            }
        
        # Step 1: Enhance vague prompt to be specific/technical
        reaper_state = REAPER_STATE.get(body.session_id, {})
        state_str = json.dumps(reaper_state) if reaper_state else ""
        enhanced_prompt = enhance_prompt(body.text, state_str)
        
        # Check if enhancer wants to analyze existing MIDI first
        if enhanced_prompt == "ANALYZE_MIDI_FIRST":
            print("🎼 Compose-around mode - need MIDI from client")
            # For cloud: we need the client to send MIDI data
            # Check if there's MIDI in the state
            midi_notes = None
            if reaper_state and isinstance(reaper_state, dict):
                # Look for MIDI notes in state (client should include this)
                midi_notes = reaper_state.get('midi_notes_track_0')
            
            if midi_notes:
                enhanced_prompt = enhance_prompt(body.text, state_str, midi_notes=midi_notes)
            else:
                # Fall back to regular song generation
                print("⚠️ No MIDI data in state, generating new song...")
                enhanced_prompt = generate_song_commands(body.text)
        
        print(f"📝 Original: {body.text}")
        print(f"✨ Enhanced ({len(enhanced_prompt)} chars): {enhanced_prompt[:500]}..." if len(enhanced_prompt) > 500 else f"✨ Enhanced: {enhanced_prompt}")
        
        # Debug: Check if it looks like commands
        first_line = enhanced_prompt.strip().split('\n')[0] if enhanced_prompt else ""
        print(f"🔍 First line: '{first_line[:80]}'")
        is_command = any(first_line.startswith(p) for p in ('SET_TEMPO', 'INSERT_INSTRUMENT', 'INSERT_AUDIO', 'MIDI_'))
        print(f"🔍 Looks like command: {is_command}")

        # EL1/MODEL O: the enhancer may start a background worker and return a status message.
        # In that case, do NOT execute the Reaper agent (there are no DAW commands to run yet).
        if isinstance(enhanced_prompt, str) and (
            enhanced_prompt.strip().startswith("# MODEL O is generating")
            or "MODEL O is working" in enhanced_prompt
            or enhanced_prompt.strip().startswith("🎵 [EL1]")
        ):
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            agent_output = output_capture.getvalue()
            plan = {"plan_id": f"plan-{int(time.time()*1000)}", "steps": []}
            add_event("plan_created", {"prompt": body.text, **plan}, session_id=body.session_id)
            return {
                "reply": enhanced_prompt,
                "plan": plan,
                "commands": [],
                "status": "success",
                "agent_reasoning": enhanced_prompt,
                "full_output": agent_output,
            }
        
        # M1 MODE / Direct commands: if enhanced prompt contains Reaper commands,
        # queue them directly instead of passing to agent
        DIRECT_COMMAND_PREFIXES = (
            'SET_TEMPO', 'INSERT_INSTRUMENT', 'MIDI_CREATE_ITEM', 'MIDI_INSERT_NOTE',
            'ADD_FX', 'SET_FX_PARAM', 'INSERT_AUDIO', 'VOL_DIP', 'USE_SAMPLE', 'LOAD_SAMPLER'
        )
        if isinstance(enhanced_prompt, str):
            lines = [l.strip() for l in enhanced_prompt.strip().split('\n') if l.strip()]
            # Check if first non-empty line is a command
            if lines and any(lines[0].startswith(prefix) for prefix in DIRECT_COMMAND_PREFIXES):
                print(f"🎹 Direct mode - queueing {len(lines)} commands directly")
                # Queue commands directly (skip agent)
                if body.session_id not in REAPER_SESSIONS:
                    REAPER_SESSIONS[body.session_id] = []
                for cmd in lines:
                    if any(cmd.startswith(prefix) for prefix in DIRECT_COMMAND_PREFIXES):
                        REAPER_SESSIONS[body.session_id].append(cmd)
                        add_event("command_queued", {"command": cmd}, session_id=body.session_id)
                
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                agent_output = output_capture.getvalue()
                
                plan = {
                    "plan_id": f"plan-{int(time.time()*1000)}",
                    "steps": [
                        {"id": f"s{i}", "action": "REAPER_COMMAND", "command": cmd}
                        for i, cmd in enumerate(lines) if any(cmd.startswith(p) for p in DIRECT_COMMAND_PREFIXES)
                    ]
                }
                add_event("plan_created", {"prompt": body.text, **plan}, session_id=body.session_id)
                
                return {
                    "reply": f"🎹 MIDI Foundation Model: Queued {len(lines)} commands",
                    "plan": plan,
                    "commands": lines,
                    "status": "success",
                    "agent_reasoning": f"M1 mode - direct command execution",
                    "full_output": agent_output,
                }
        
        # Step 2: Execute using REAL agent with cloud hooks
        agent._CURRENT_SESSION_ID = body.session_id
        agent.execute_user_command(enhanced_prompt)
        
        # Get commands that were queued by the agent (via hooks)
        commands = REAPER_SESSIONS.get(body.session_id, [])
        result = {
            "status": "success",
            "message": f"Generated {len(commands)} command(s)"
        }
        
        # Restore stdout and get captured output
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        agent_output = output_capture.getvalue()
        
        # Create plan for UI
        plan = {
            "plan_id": f"plan-{int(time.time()*1000)}",
            "steps": [
                {"id": f"s{i}", "action": "REAPER_COMMAND", "command": cmd}
                for i, cmd in enumerate(commands)
            ]
        }
        
        add_event("plan_created", {"prompt": body.text, **plan}, session_id=body.session_id)
        # Tag with the actual session so UI filters show it
        add_event("command_queued_for_reaper", {"commands": commands, "session_id": body.session_id}, session_id=body.session_id)
        
        return {
            "reply": agent_output if agent_output else f"✅ {result['message']}",
            "plan": plan,
            "commands": commands,
            "status": result["status"],
            "agent_reasoning": enhanced_prompt,
            "full_output": agent_output
        }
        
    except Exception as e:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        error_output = output_capture.getvalue()
        
        # Fallback response
        plan = {
            "plan_id": f"plan-{int(time.time()*1000)}",
            "steps": [
                {"id":"s1","action":"ERROR","error":str(e)}
            ]
        }
        add_event("error", {"prompt": body.text, "error": str(e)}, session_id=body.session_id)
        return {"reply": f"❌ Error: {str(e)}\n\n{error_output}", "plan": plan, "status": "error"}

# -------------------- Chat (RAW) → real agent, no enhancer --------------------
@app.post("/api/enhance")
def api_enhance(body: ChatIn):
    """Enhance a vague prompt to be specific/technical (no execution)"""
    try:
        raw_text = (body.text or "").strip().lower()
        
        # M1 (MIDI Foundation Model) - no enhancement, just generation
        # Tell user to use Send instead
        if raw_text.startswith("m1 ") or raw_text.startswith("m1:"):
            return {
                "original": body.text, 
                "enhanced": body.text,  # Keep original
                "status": "success",
                "message": "🎹 M1 mode: Click Send to generate. No enhancement needed."
            }
        
        from prompt_enhancer import enhance_prompt
        reaper_state = REAPER_STATE.get(body.session_id, {})
        state_str = json.dumps(reaper_state) if reaper_state else ""
        enhanced = enhance_prompt(body.text, state_str)
        
        # Log for debugging
        print(f"[ENHANCE] Original: {body.text[:100]}")
        print(f"[ENHANCE] Enhanced: {enhanced[:100]}")
        
        return {"original": body.text, "enhanced": enhanced, "status": "success"}
    except Exception as e:
        print(f"[ENHANCE ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"original": body.text, "enhanced": body.text, "status": "error", "error": f"{type(e).__name__}: {str(e)}"}

@app.post("/api/chat_raw")
def api_chat_raw(body: ChatIn):
    import io
    import sys
    import logging
    
    # Capture stdout with StringIO (simpler approach)
    output_capture = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = output_capture
    sys.stderr = output_capture
    
    try:
        _ensure_agent_loaded()
        # Directly run the FULL agent with the raw user text
        agent._CURRENT_SESSION_ID = body.session_id
        agent.execute_user_command(body.text)
        
        # Get commands that were queued by the agent (via hooks)
        commands = REAPER_SESSIONS.get(body.session_id, [])
        result = {
            "status": "success",
            "message": f"Generated {len(commands)} command(s)"
        }
        
        # Restore stdout and get captured output
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        agent_output = output_capture.getvalue()

        plan = {
            "plan_id": f"plan-{int(time.time()*1000)}",
            "steps": [
                {"id": f"s{i}", "action": "REAPER_COMMAND", "command": cmd}
                for i, cmd in enumerate(commands)
            ]
        }

        add_event("plan_created", {"prompt": body.text, **plan}, session_id=body.session_id)
        # Tag with the actual session so UI filters show it
        add_event("command_queued_for_reaper", {"commands": commands, "session_id": body.session_id}, session_id=body.session_id)

        return {
            "reply": agent_output if agent_output else f"✅ {result['message']}",
            "plan": plan,
            "commands": commands,
            "status": result["status"],
            "full_output": agent_output
        }
    except Exception as e:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        error_output = output_capture.getvalue()
        
        plan = {
            "plan_id": f"plan-{int(time.time()*1000)}",
            "steps": [
                {"id": "s1", "action": "ERROR", "error": str(e)}
            ]
        }
        add_event("error", {"prompt": body.text, "error": str(e)}, session_id=body.session_id)
        return {"reply": f"❌ Error: {str(e)}\n\n{error_output}", "plan": plan, "status": "error"}

@app.post("/api/chat_raw_async")
def api_chat_raw_async(body: ChatIn):
    """Start agent in background and return immediately to avoid 504s."""
    _ensure_agent_loaded()
    plan_id = f"plan-{uuid.uuid4().hex[:8]}"
    RUNNING_TASKS[plan_id] = {"session_id": body.session_id, "text": body.text, "started_ts": time.time(), "status": "running"}

    def _runner():
        import io, sys
        class _EventingWriter(io.TextIOBase):
            def __init__(self, session_id: str):
                self._buf = ""
                self._sid = session_id
            def write(self, s: str):
                if not isinstance(s, str):
                    s = str(s)
                self._buf += s
                while "\n" in self._buf:
                    line, self._buf = self._buf.split("\n", 1)
                    if line.strip():
                        add_event("agent_stdout", {"line": line}, session_id=self._sid)
                return len(s)
            def flush(self):
                return
        try:
            # Tee stdout/stderr to SSE
            old_out, old_err = sys.stdout, sys.stderr
            tee = _EventingWriter(body.session_id)
            sys.stdout = tee
            sys.stderr = tee
            agent._CURRENT_SESSION_ID = body.session_id  # type: ignore
            agent.execute_user_command(body.text)        # type: ignore
            # Flush any remaining partial line
            try:
                if getattr(tee, "_buf", "").strip():
                    add_event("agent_stdout", {"line": tee._buf}, session_id=body.session_id)
            except Exception:
                pass
            RUNNING_TASKS[plan_id]["status"] = "done"
        except Exception as e:
            RUNNING_TASKS[plan_id]["status"] = f"error: {e}"
            add_event("error", {"prompt": body.text, "error": str(e)}, session_id=body.session_id)
        finally:
            try:
                # Restore stdio
                sys.stdout = old_out
                sys.stderr = old_err
            except Exception:
                pass
            # Emit a completion marker so UI can pull final logs if needed
            add_event("agent_completed", {"plan_id": plan_id}, session_id=body.session_id)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    add_event("plan_started_async", {"plan_id": plan_id, "text": body.text}, session_id=body.session_id)
    queued = list(REAPER_SESSIONS.get(body.session_id, []))
    return {"status": "started", "plan_id": plan_id, "queued_commands": queued}

@app.get("/api/progress")
def api_progress(session_id: str, plan_id: str = ""):
    """Lightweight progress probe: queue length and task status."""
    qlen = len(REAPER_SESSIONS.get(session_id, []))
    status = RUNNING_TASKS.get(plan_id, {}).get("status") if plan_id else None
    return {"session_id": session_id, "queued_commands": qlen, "status": status or "unknown"}
# -------------------- Lua client: pull next command --------------------
@app.get("/v1/next")
def v1_next(session_id: str, x_api_key: Optional[str] = Header(default="")):
    require_key(x_api_key)
    q = QUEUES[session_id]
    if q:
        cmd = q.popleft()
        add_event("command_dispatched", cmd, session_id=session_id)
        return {"command": cmd}
    return {"command": None}

# -------------------- Lua client: report result --------------------
@app.post("/v1/report")
def v1_report(body: ReportIn, x_api_key: Optional[str] = Header(default="")):
    require_key(x_api_key)
    add_event("step_result", body.dict(), session_id=body.session_id)
    return {"ok": True}

# -------------------- Admin: queue manual command (for testing) --------------------
@app.post("/v1/admin/queue")
def admin_queue(body: AdminCmd, x_api_key: Optional[str] = Header(default="")):
    require_key(x_api_key)
    cmd = {
        "step_id": body.command.get("id", f"s{int(time.time())}"),
        "session_id": body.session_id,
        "command": body.command
    }
    QUEUES[body.session_id].append(cmd)
    add_event("command_queued", cmd, session_id=body.session_id)
    return {"queued": True}

# -------------------- Reaper Cloud Connection --------------------
REAPER_SESSIONS = {}  # session_id -> [commands]
REAPER_STATE = {}  # session_id -> state dict
RUNNING_TASKS = {}  # plan_id -> metadata

# Lazy-load the heavy agent module so the container can start fast
agent = None  # type: ignore

def _state_provider(session_id: str) -> str:
    # Try current state; if missing/stale, request and wait briefly
    def _to_text(st: Dict[str, Any]) -> str:
        if isinstance(st, dict) and isinstance(st.get("state_text"), str):
            text = st["state_text"]
            print(f"[STATE_PROVIDER] Returning state_text: {len(text)} chars, first 200: {text[:200]}")
            return text
        try:
            result = json.dumps(st) if st else ""
            print(f"[STATE_PROVIDER] Returning JSON: {len(result)} chars")
            return result
        except Exception:
            print(f"[STATE_PROVIDER] Returning empty (exception)")
            return ""

    now = time.time()
    st = REAPER_STATE.get(session_id, {})
    last_ts = 0.0
    if isinstance(st, dict):
        last_ts = float(st.get("_server_received_ts", 0.0))
    
    print(f"[STATE_PROVIDER] session={session_id}, now={now:.2f}, last_ts={last_ts:.2f}, diff={now-last_ts:.2f}s")

    # Always request fresh state for verification (ensures we never read stale state)
    if not st or (now - last_ts) > 0:
        if session_id not in REAPER_SESSIONS:
            REAPER_SESSIONS[session_id] = []
        REAPER_SESSIONS[session_id].append("GET_STATE")
        add_event("state_requested", {"via": "provider", "session_id": session_id}, session_id=session_id)
        print(f"[STATE_PROVIDER] Requesting fresh state, waiting up to 2s...")
        deadline = now + 2.0
        while time.time() < deadline:
            st2 = REAPER_STATE.get(session_id, {})
            if isinstance(st2, dict) and float(st2.get("_server_received_ts", 0.0)) > last_ts:
                new_ts = float(st2.get("_server_received_ts", 0.0))
                print(f"[STATE_PROVIDER] Got fresh state! new_ts={new_ts:.2f}, waited {time.time()-now:.2f}s")
                return _to_text(st2)
            time.sleep(0.1)
        # Timeout: return whatever we have
        print(f"[STATE_PROVIDER] Timeout after 2s, returning cached state")
        return _to_text(st)
    print(f"[STATE_PROVIDER] Returning cached state (not stale)")
    return _to_text(st)

def _command_sink(commands, session_id: str) -> bool:
    try:
        if not isinstance(commands, list):
            commands = [commands]
        if session_id not in REAPER_SESSIONS:
            REAPER_SESSIONS[session_id] = []
        # Queue commands from agent
        REAPER_SESSIONS[session_id].extend(commands)
        # Emit events for UI (one per command for visibility)
        for c in commands:
            add_event("command_queued_for_reaper", {"command": c, "session_id": session_id}, session_id=session_id)
        return True
    except Exception:
        return False

def _feedback_provider(session_id: str) -> str:
    # Optional: implement feedback loop later
    return ""

_MEMORY = {}
def _memory_load(session_id: str):
    return _MEMORY.get(session_id, {})

def _memory_save(session_id: str, data: Dict[str, Any]) -> bool:
    _MEMORY[session_id] = data or {}
    return True

def _lyrics_sink(track_name: str, lyrics: List[Dict], session_id: str) -> bool:
    """Store lyrics for bridge to fetch and cache locally"""
    try:
        if session_id not in PENDING_LYRICS:
            PENDING_LYRICS[session_id] = []
        
        PENDING_LYRICS[session_id].append({
            "track_name": track_name,
            "lyrics": lyrics,
            "stored_ts": time.time()
        })
        
        print(f"📝 Queued {len(lyrics)} words for '{track_name}' → bridge will cache locally")
        add_event("lyrics_queued_for_bridge", {"track_name": track_name, "word_count": len(lyrics)}, session_id=session_id)
        return True
    except Exception as e:
        print(f"⚠️ Failed to queue lyrics: {e}")
        return False

# Inject hooks once on startup
def _ensure_agent_loaded():
    global agent
    if agent is None:
        try:
            import importlib.util
            # Load legacy robust agent (old.py)
            spec = importlib.util.spec_from_file_location("old", "old.py")
            _agent = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_agent)
            _agent.set_cloud_hooks(
                state_provider=_state_provider,
                command_sink=_command_sink,
                feedback_provider=_feedback_provider,
                memory_load=_memory_load,
                memory_save=_memory_save,
                lyrics_sink=_lyrics_sink,
            )
            agent = _agent
        except Exception as e:
            print(f"❌ Failed to load agent (old.py): {e}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise to see in logs, but at least we printed traceback

@app.get("/api/reaper/poll")
def reaper_poll(session_id: str = "default"):
    """Lua script polls this for commands - returns ALL pending commands at once"""
    if session_id not in REAPER_SESSIONS:
        REAPER_SESSIONS[session_id] = []
    
    if REAPER_SESSIONS[session_id]:
        # Return ALL pending commands as newline-separated string
        all_cmds = REAPER_SESSIONS[session_id][:]
        REAPER_SESSIONS[session_id].clear()
        for cmd in all_cmds:
            add_event("command_sent_to_reaper", {"command": cmd, "session_id": session_id}, session_id=session_id)
        # Join with newlines so bridge/Lua can process each line
        return "\n".join(all_cmds)
    return ""  # Empty = no command

@app.post("/api/reaper/execute")
def reaper_execute(cmd: dict):
    """AI agent calls this to queue commands for Reaper"""
    command = cmd.get("command", "")
    session_id = cmd.get("session_id", "default")
    
    if command:
        if session_id not in REAPER_SESSIONS:
            REAPER_SESSIONS[session_id] = []
        REAPER_SESSIONS[session_id].append(command)
        add_event("command_queued_for_reaper", {"command": command, "session_id": session_id}, session_id=session_id)
    return {"status": "queued", "command": command, "session_id": session_id}

@app.post("/api/reaper/state")
def reaper_state(state: dict):
    """Reaper sends state updates here"""
    session_id = state.get("session_id", "demo")
    state_copy = dict(state)
    state_copy["_server_received_ts"] = time.time()
    REAPER_STATE[session_id] = state_copy
    add_event("reaper_state_update", state, session_id=session_id)
    return {"status": "received"}

# Store feedback (including MIDI notes) from Reaper
REAPER_FEEDBACK = {}

# Store pending lyrics for bridge to fetch and cache locally
PENDING_LYRICS = {}  # session_id -> [{"track_name": ..., "lyrics": [...]}]

@app.post("/api/reaper/feedback")
def reaper_feedback(data: dict):
    """Reaper sends feedback (including MIDI notes) here"""
    session_id = data.get("session_id", "demo")
    feedback = data.get("feedback", "")
    REAPER_FEEDBACK[session_id] = {
        "feedback": feedback,
        "received_ts": time.time()
    }
    
    # If feedback contains MIDI notes, also store them in state for easy access
    if "MIDI_NOTES:" in feedback:
        midi_line = [l for l in feedback.split('\n') if 'MIDI_NOTES:' in l]
        if midi_line:
            midi_notes = midi_line[-1].split("MIDI_NOTES:")[-1].strip()
            if session_id not in REAPER_STATE:
                REAPER_STATE[session_id] = {}
            REAPER_STATE[session_id]['midi_notes_track_0'] = midi_notes
            print(f"📝 Stored {len(midi_notes.split(';'))} MIDI notes for session {session_id}")
    
    add_event("reaper_feedback", {"feedback": feedback[:500]}, session_id=session_id)
    return {"status": "received"}

# -------------------- Lyrics caching for bridge --------------------
@app.post("/api/lyrics/store")
def lyrics_store(data: dict):
    """Agent stores extracted lyrics here for bridge to fetch"""
    session_id = data.get("session_id", "demo")
    track_name = data.get("track_name", "")
    lyrics = data.get("lyrics", [])
    
    if not track_name:
        return {"status": "error", "message": "track_name required"}
    
    if session_id not in PENDING_LYRICS:
        PENDING_LYRICS[session_id] = []
    
    # Add to pending queue
    PENDING_LYRICS[session_id].append({
        "track_name": track_name,
        "lyrics": lyrics,
        "stored_ts": time.time()
    })
    
    print(f"📝 Stored {len(lyrics)} words for '{track_name}' (session {session_id})")
    add_event("lyrics_stored", {"track_name": track_name, "word_count": len(lyrics)}, session_id=session_id)
    return {"status": "stored", "track_name": track_name, "word_count": len(lyrics)}

@app.get("/api/lyrics/pending")
def lyrics_pending(session_id: str = "demo"):
    """Bridge polls this to get lyrics to cache locally"""
    pending = PENDING_LYRICS.get(session_id, [])
    if pending:
        # Return all pending and clear
        PENDING_LYRICS[session_id] = []
        return {"lyrics": pending}
    return {"lyrics": []}

# -------------------- Vocal Generation Pipeline --------------------
class VocalsRequest(BaseModel):
    session_id: str = "demo"
    topic: str = "life and feelings"
    mood: str = "emotional"
    beat_commands: Optional[str] = None  # If provided, use these. Otherwise generate new beat.
    beat_prompt: Optional[str] = None    # If no beat_commands, generate from this prompt
    runpod_endpoint: Optional[str] = None  # DiffSinger RunPod URL (when ready)
    experiment_name: Optional[str] = None  # Name of trained DiffSinger model (for local inference)
    use_local: bool = True  # Try local inference if experiment_name provided

@app.post("/api/vocals/generate")
def generate_vocals_endpoint(body: VocalsRequest):
    """
    Generate vocals for a beat:
    1. If beat_commands provided, use those
    2. Otherwise generate beat from beat_prompt
    3. Generate lyrics fitting the beat
    4. Generate vocal melody
    5. (When ready) Call DiffSinger on RunPod
    
    Returns all components for review/debugging.
    """
    try:
        from prompt_enhancer import (
            generate_song_commands,
            generate_vocals_for_beat,
            generate_lyrics,
            generate_vocal_melody,
            analyze_beat_for_vocals,
            format_for_diffsinger
        )
        
        # Step 1: Get or generate beat
        if body.beat_commands:
            beat_commands = body.beat_commands
            print(f"🎵 Using provided beat commands ({len(beat_commands.split(chr(10)))} lines)")
        elif body.beat_prompt:
            print(f"🎵 Generating beat from: {body.beat_prompt}")
            beat_commands = generate_song_commands(body.beat_prompt)
        else:
            # Generate a default beat
            beat_commands = generate_song_commands(f"a {body.mood} instrumental track")
        
        # Step 2: Generate vocals
        vocals = generate_vocals_for_beat(
            beat_commands=beat_commands,
            topic=body.topic,
            mood=body.mood,
            runpod_endpoint=body.runpod_endpoint,
            experiment_name=body.experiment_name,
            use_local=body.use_local
        )
        
        add_event("vocals_generated", {
            "topic": body.topic,
            "mood": body.mood,
            "note_count": len(vocals.get('melody', [])),
            "lyrics_preview": vocals.get('lyrics', '')[:200]
        }, session_id=body.session_id)
        
        return {
            "status": "success",
            "beat_commands": beat_commands,
            "vocals": vocals
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/api/vocals/lyrics_only")
def generate_lyrics_only(topic: str, mood: str = "emotional", tempo: int = 120, key: str = "C"):
    """Generate just lyrics (no beat or melody)"""
    try:
        from prompt_enhancer import generate_lyrics
        lyrics = generate_lyrics(topic, mood, tempo=tempo, key=key)
        return {"status": "success", "lyrics": lyrics}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/vocals/melody_only")  
def generate_melody_only(lyrics: str, tempo: int = 120, key: str = "C"):
    """Generate vocal melody for existing lyrics"""
    try:
        from prompt_enhancer import generate_vocal_melody, format_for_diffsinger
        melody = generate_vocal_melody(lyrics, tempo=tempo, key=key)
        diffsinger_input = format_for_diffsinger(lyrics, melody, tempo)
        return {
            "status": "success", 
            "melody": melody,
            "diffsinger_input": diffsinger_input
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/upload/audio")
async def upload_audio(session_id: str = "demo", track_idx: Optional[str] = None, file: UploadFile = File(...)):
    """
    Bridge uploads rendered audio here so Cloud Run can process lyrics/analysis.
    Files are saved under /tmp/uploads/<session_id>/[track_<idx>/] for the agent to pick up.
    """
    MAX_UPLOAD_MB = 30  # keep comfortably below Cloud Run's ~32MB limit
    MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

    upload_root = Path("/tmp/uploads") / session_id
    if track_idx:
        upload_root = upload_root / f"track_{track_idx}"
    upload_root.mkdir(parents=True, exist_ok=True)

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Upload too large ({len(data)/(1024*1024):.1f}MB). Convert/export in smaller range before retrying."
        )

    file_path = upload_root / file.filename
    file_path.write_bytes(data)
    size_mb = len(data) / (1024 * 1024)
    add_event(
        "audio_uploaded",
        {
            "filename": file.filename,
            "size_mb": round(size_mb, 3),
            "track_idx": track_idx,
            "session_id": session_id,
        },
        session_id=session_id,
    )
    return {"uploaded": str(file_path), "size_mb": size_mb}

# -------------------- Debug endpoints (file presence, counts) --------------------
@app.get("/debug/files")
def debug_files():
    files = [
        "reaper_actions.txt",
        "reaper_plugins_list.txt",
        "action_index.json",
        "ai_agent_reaper_final.py",
        "cloud_agent_wrapper.py",
        "main.py",
    ]
    listing = []
    try:
        listing = os.listdir(".")
    except Exception:
        pass
    return {
        "cwd": os.getcwd(),
        "exists": {name: os.path.exists(name) for name in files},
        "ls": listing[:200],
    }

@app.get("/debug/actions")
def debug_actions():
    try:
        _ensure_agent_loaded()
        actions = agent.load_action_list()
        plugins = agent.load_plugin_list()
        # Return only a small sample to keep payload small
        sample = list(actions.items())[:5]
        return {
            "actions_count": len(actions),
            "plugins_count": len(plugins),
            "sample_actions": sample,
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/state")
def debug_state(session_id: str = "demo"):
    """View current stored state for debugging verification issues"""
    st = REAPER_STATE.get(session_id, {})
    if not st:
        return {"error": "No state found", "session_id": session_id}
    
    state_text = st.get("state_text", "")
    server_ts = st.get("_server_received_ts", 0.0)
    age = time.time() - server_ts if server_ts else 999
    
    return {
        "session_id": session_id,
        "state_age_seconds": round(age, 2),
        "state_length_chars": len(state_text),
        "state_preview": state_text[:500] if state_text else "(no state_text)",
        "full_state_first_1000": state_text[:1000] if state_text else "(no state_text)",
        "server_received_ts": server_ts,
        "all_keys": list(st.keys())
    }

# -------------------- Live event stream (SSE) --------------------
@app.get("/api/events/stream")
async def events_stream(session_id: Optional[str] = None, since: Optional[float] = None):
    """
    Server-Sent Events stream of agent/bridge lifecycle.
    Filters by session_id if provided. Use curl -N to follow.
    """
    async def gen():
        last_ts = since or 0.0
        while True:
            # Snapshot to minimize contention
            snapshot = list(EVENTS)
            new_events = [e for e in snapshot if e.get("t", 0) > last_ts and (session_id is None or e.get("session_id") == session_id)]
            if new_events:
                for e in new_events:
                    yield f"data: {json.dumps(e)}\n\n"
                last_ts = new_events[-1]["t"]
            await asyncio.sleep(0.5)
    return StreamingResponse(gen(), media_type="text/event-stream")
# -------------------- Static UI for investors --------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>CursorDAW Cloud</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
        }
        
        .header { 
            text-align: center; 
            margin-bottom: 40px;
            animation: fadeInDown 0.6s ease-out;
        }
        
        .header h1 {
            font-size: 2.8em;
            font-weight: 700;
            margin-bottom: 20px;
            background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 0 30px rgba(102, 126, 234, 0.5);
        }
        
        .input-group { 
            margin-bottom: 20px; 
        }
        
        label { 
            display: block; 
            margin-bottom: 8px; 
            color: #a8b3cf;
            font-weight: 500;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        input, textarea { 
            width: 100%; 
            padding: 12px 16px; 
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px; 
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            color: #fff; 
            margin-bottom: 10px;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        input:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
        }
        
        button { 
            padding: 12px 24px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            position: relative;
            overflow: hidden;
        }
        
        button::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }
        
        button:hover::before {
            width: 300px;
            height: 300px;
        }
        
        button span { position: relative; z-index: 1; }
        
        button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4); }
        
        .button-row { 
            display: flex; 
            gap: 12px; 
            margin-top: 15px;
        }
        
        .button-row button { 
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .enhance-btn { 
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
        }
        .enhance-btn:hover { 
            box-shadow: 0 8px 25px rgba(245, 87, 108, 0.4) !important;
        }
        
        .sync-btn { 
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%) !important;
        }
        .sync-btn:hover { 
            box-shadow: 0 8px 25px rgba(79, 172, 254, 0.4) !important;
        }
        
        .status { 
            text-align: center; 
            padding: 15px; 
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px; 
            margin-bottom: 25px;
            font-weight: 600;
            font-size: 1.1em;
            color: #a8b3cf;
            animation: pulse 2s ease-in-out infinite;
        }
        
        .grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 25px;
            animation: fadeIn 0.8s ease-out;
        }
        
        .card { 
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px; 
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(102, 126, 234, 0.2);
        }
        
        .card h3 {
            margin-bottom: 20px;
            font-size: 1.4em;
            color: #fff;
            border-bottom: 2px solid rgba(102, 126, 234, 0.3);
            padding-bottom: 10px;
        }
        
        .messages { 
            height: 500px; 
            overflow-y: auto; 
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 15px; 
            background: rgba(0, 0, 0, 0.2);
            margin-bottom: 15px;
        }
        
        .messages::-webkit-scrollbar { width: 8px; }
        .messages::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.05); border-radius: 10px; }
        .messages::-webkit-scrollbar-thumb { background: rgba(102, 126, 234, 0.5); border-radius: 10px; }
        .messages::-webkit-scrollbar-thumb:hover { background: rgba(102, 126, 234, 0.7); }
        
        .message { 
            margin-bottom: 15px; 
            padding: 15px 18px; 
            border-radius: 12px;
            animation: slideIn 0.3s ease-out;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }
        
        .user { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin-left: 40px;
            border-bottom-right-radius: 4px;
        }
        
        .agent { 
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            margin-right: 40px;
            max-width: 100%; 
            overflow-x: auto;
            border-bottom-left-radius: 4px;
        }
        
        .events { 
            height: 300px; 
            overflow-y: auto; 
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 15px; 
            background: rgba(0, 0, 0, 0.2);
            font-size: 0.9em;
            color: #a8b3cf;
        }
        
        .events::-webkit-scrollbar { width: 8px; }
        .events::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.05); border-radius: 10px; }
        .events::-webkit-scrollbar-thumb { background: rgba(79, 172, 254, 0.5); border-radius: 10px; }
        .events::-webkit-scrollbar-thumb:hover { background: rgba(79, 172, 254, 0.7); }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .message.user { margin-left: 10px; }
            .message.agent { margin-right: 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 CursorDAW Cloud</h1>
            <div class="input-group">
                <label>Session ID (from your bridge):</label>
                <input type="text" id="sessionInput" placeholder="Enter session ID from bridge window..." value="demo">
            </div>
            <div class="status" id="status">Connecting...</div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>Chat</h3>
                <div class="messages" id="messages"></div>
                <div class="input-group">
                    <textarea id="messageInput" placeholder="Type your message..." rows="3"></textarea>
                    <div class="button-row">
                        <button onclick="sendMessage()"><span>Send</span></button>
                        <button class="enhance-btn" onclick="enhancePrompt()"><span>✨ Enhance</span></button>
                        <button class="sync-btn" onclick="syncState()"><span>Sync State</span></button>
                        <button class="m1-btn" onclick="generateM1()" style="background: linear-gradient(135deg, #9b59b6, #8e44ad); margin-left: 10px;"><span>🎹 M1 Generate</span></button>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>Events</h3>
                <div class="events" id="events"></div>
            </div>
        </div>
    </div>

    <script>
        let isConnected = false;
        let agentLogBuffer = [];
        
        // Load session ID from localStorage or default to 'demo'
        window.onload = function() {
            const savedSessionId = localStorage.getItem('sessionId') || 'demo';
            document.getElementById('sessionInput').value = savedSessionId;
        };
        
        // Save session ID whenever it changes
        document.getElementById('sessionInput')?.addEventListener('change', function(e) {
            const sessionId = e.target.value.trim();
            localStorage.setItem('sessionId', sessionId);
            addEvent('✓ Session ID saved: ' + sessionId);
        });
        
        function getSessionId() {
            return document.getElementById('sessionInput').value.trim() || 'demo';
        }
        
        function updateStatus(message, connected = false) {
            document.getElementById('status').textContent = message;
            isConnected = connected;
        }
        
        function addMessage(text, type = 'user') {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + type;
            
            // Use pre tag to preserve formatting/line breaks
            const preElement = document.createElement('pre');
            preElement.style.whiteSpace = 'pre-wrap';
            preElement.style.margin = '0';
            preElement.style.fontFamily = 'inherit';
            preElement.style.fontSize = '14px';
            preElement.textContent = text;
            
            messageDiv.appendChild(preElement);
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function addEvent(text) {
            const eventsDiv = document.getElementById('events');
            const eventDiv = document.createElement('div');
            eventDiv.textContent = new Date().toLocaleTimeString() + ': ' + text;
            eventsDiv.appendChild(eventDiv);
            eventsDiv.scrollTop = eventsDiv.scrollHeight;
        }
        
        async function checkConnection() {
            try {
                const response = await fetch('/health');
                if (response.ok) {
                    const data = await response.json();
                    updateStatus('Connected - ' + new Date(data.ts * 1000).toLocaleTimeString(), true);
                    return true;
                }
            } catch (error) {
                updateStatus('Disconnected', false);
            }
            return false;
        }
        
        // M1 - Direct MIDI Foundation Model call
        async function generateM1() {
            addEvent('🎹 M1: Calling MIDI Foundation Model...');
            addMessage('🎹 Generating MIDI with Foundation Model...', 'user');
            
            try {
                const response = await fetch('/api/m1?session_id=' + getSessionId(), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    addEvent('🎹 M1: ' + data.message);
                    addMessage('🎹 ' + data.message, 'agent');
                } else {
                    addEvent('❌ M1 Error: ' + data.message);
                    addMessage('❌ M1 Error: ' + data.message, 'agent');
                }
            } catch (error) {
                addEvent('❌ M1 Network Error: ' + error.message);
                addMessage('❌ Network error: ' + error.message, 'agent');
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            let message = input.value.trim();
            if (!message) return;
            
            addMessage(message, 'user');
            input.value = '';
            
            if (!isConnected) {
                addMessage('Not connected to server', 'agent');
                return;
            }
            
            try {
                // Non-blocking execution so the UI can stream live events
                const response = await fetch('/api/chat_raw_async', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: getSessionId(), text: message })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    addEvent('🟣 Agent started (plan ' + (data.plan_id || 'n/a') + '), queued=' + (data.queued_commands?.length || 0));
                    addMessage('Agent started. Watch Events for live steps…', 'agent');
                } else {
                    addMessage('Error: ' + response.status, 'agent');
                }
            } catch (error) {
                addMessage('Network error: ' + error.message, 'agent');
            }
        }

        async function enhancePrompt() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) {
                addEvent('⚠️ Enter some text first');
                return;
            }
            
            addEvent('✨ Enhancing prompt...');
            const maxAttempts = 3;
            for (let attempt = 1; attempt <= maxAttempts; attempt++) {
                try {
                    const response = await fetch('/api/enhance', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: getSessionId(), text: message })
                    });
                    
                    if (!response.ok) {
                        throw new Error('HTTP ' + response.status);
                    }
                    
                    const data = await response.json();
                    
                    // Check for error status from API
                    if (data.status === 'error') {
                        addEvent('❌ Enhancement failed: ' + (data.error || 'Unknown error'));
                        console.error('Enhance error:', data);
                        return;
                    }
                    
                    // M1 mode - no enhancement, just tell user to click Send
                    if (data.message && data.message.includes('M1 mode')) {
                        addEvent(data.message);
                        return;
                    }
                    
                    if (data.enhanced && data.enhanced !== message) {
                        input.value = data.enhanced;
                        addEvent('✅ Prompt enhanced! Review and click Send');
                        console.log('Original:', message);
                        console.log('Enhanced:', data.enhanced);
                    } else {
                        addEvent('💡 Prompt already specific enough');
                    }
                    return;
                } catch (error) {
                    const msg = (error && error.message) ? error.message : String(error);
                    if (attempt < maxAttempts) {
                        addEvent(`⚠️ Enhance failed (${msg}) — retrying (${attempt}/${maxAttempts - 1})...`);
                        await new Promise(r => setTimeout(r, 600 * Math.pow(2, attempt - 1)));
                        continue;
                    }
                    addEvent('❌ Enhancement error: ' + msg + ' (network/DNS — try again)');
                }
            }
        }

        async function syncState() {
            try {
                const res = await fetch('/api/reaper/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: 'GET_STATE', session_id: getSessionId() })
                });
                if (res.ok) {
                    addEvent('Forced state sync queued');
                } else {
                    addEvent('State sync failed: ' + res.status);
                }
            } catch (e) {
                addEvent('State sync error: ' + e.message);
            }
        }
        
        // Live event stream via SSE
        let es = null;
        function startEventStream() {
            const sid = getSessionId();
            if (es) { try { es.close(); } catch(e){} }
            addEvent('🔌 Connecting event stream for session ' + sid + '…');
            es = new EventSource('/api/events/stream?session_id=' + encodeURIComponent(sid));
            es.onmessage = (evt) => {
                try {
                    const e = JSON.parse(evt.data);
                    const kind = e.kind || 'event';
                    // Compact rendering for common kinds
                    if (kind === 'agent_stdout' && e.data?.line) {
                        agentLogBuffer.push(e.data.line);
                        addEvent('🧠 ' + e.data.line);
                    } else if (kind === 'agent_completed') {
                        addEvent('✅ agent completed');
                        if (agentLogBuffer.length) {
                            addMessage(agentLogBuffer.join('\\n'), 'agent');
                            agentLogBuffer = [];
                        }
                    } else if (kind === 'command_sent_to_reaper' && e.data?.command) {
                        addEvent('➡️ ' + kind + ': ' + e.data.command);
                    } else if (kind === 'command_queued_for_reaper' && e.data?.commands) {
                        // show each queued command
                        try {
                            (e.data.commands || []).forEach((c) => addEvent('📝 queued: ' + c));
                        } catch (_) {
                            addEvent('📝 queued ' + (e.data.commands?.length || 0) + ' cmd(s)');
                        }
                    } else if (kind === 'command_queued_for_reaper' && e.data?.command) {
                        addEvent('📝 queued: ' + e.data.command);
                    } else if (kind === 'reaper_state_update') {
                        addEvent('📊 state update');
                    } else if (kind === 'plan_started_async') {
                        addEvent('🟣 plan started ' + (e.data?.plan_id || ''));
                    } else if (kind === 'plan_created') {
                        addEvent('✅ plan created');
                    } else {
                        addEvent(kind);
                    }
                } catch (err) {
                    addEvent('event parse error');
                }
            };
            es.onerror = () => {
                addEvent('⚠️ stream error, retrying in 2s…');
                try { es.close(); } catch(e){}
                setTimeout(startEventStream, 2000);
            };
        }
        
        // Check connection on load and start stream
        checkConnection().then(startEventStream);
        
        // Enter key support
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Restart stream when session changes
        document.getElementById('sessionInput').addEventListener('change', () => {
            startEventStream();
        });
    </script>
</body>
</html>
""", status_code=200)

# Allow running directly (Cloud Run buildpacks or manual runs)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)