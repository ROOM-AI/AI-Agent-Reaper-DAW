import os, time, json
from collections import defaultdict, deque
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -------------------- App & CORS --------------------
app = FastAPI(title="CursorDAW Cloud")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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

# -------------------- Health --------------------
@app.get("/health")
def health():
    return {"ok": True, "ts": time.time()}

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
    
    # Capture stdout with StringIO
    output_capture = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = output_capture
    sys.stderr = output_capture
    
    try:
        _ensure_agent_loaded()
        # Import prompt enhancer
        from prompt_enhancer import enhance_prompt
        
        # Step 1: Enhance vague prompt to be specific/technical
        reaper_state = REAPER_STATE.get(body.session_id, {})
        state_str = json.dumps(reaper_state) if reaper_state else ""
        enhanced_prompt = enhance_prompt(body.text, state_str)
        
        print(f"📝 Original: {body.text}")
        print(f"✨ Enhanced: {enhanced_prompt}")
        
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
        add_event("command_queued_for_reaper", {"commands": commands, "session_id": body.session_id}, session_id="reaper")
        
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
    """Enhance a vague prompt without executing"""
    try:
        from prompt_enhancer import enhance_prompt
        reaper_state = REAPER_STATE.get(body.session_id, {})
        state_str = json.dumps(reaper_state) if reaper_state else ""
        enhanced = enhance_prompt(body.text, state_str)
        return {"original": body.text, "enhanced": enhanced}
    except Exception as e:
        return {"error": str(e), "enhanced": body.text}

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
        add_event("command_queued_for_reaper", {"commands": commands, "session_id": body.session_id}, session_id="reaper")

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

# Inject hooks once on startup
def _ensure_agent_loaded():
    global agent
    if agent is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("local_agent", "local_agent.py")
        _agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_agent)
        _agent.set_cloud_hooks(
            state_provider=_state_provider,
            command_sink=_command_sink,
            feedback_provider=_feedback_provider,
            memory_load=_memory_load,
            memory_save=_memory_save,
        )
        agent = _agent

@app.get("/api/reaper/poll")
def reaper_poll(session_id: str = "default"):
    """Lua script polls this for commands"""
    if session_id not in REAPER_SESSIONS:
        REAPER_SESSIONS[session_id] = []
    
    if REAPER_SESSIONS[session_id]:
        cmd = REAPER_SESSIONS[session_id].pop(0)
        add_event("command_sent_to_reaper", {"command": cmd, "session_id": session_id}, session_id="reaper")
        return cmd
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
        add_event("command_queued_for_reaper", {"command": command, "session_id": session_id}, session_id="reaper")
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

# -------------------- Static UI --------------------
@app.get("/")
async def root():
    return FileResponse("static/index.html")

# Allow running directly (Cloud Run buildpacks or manual runs)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
