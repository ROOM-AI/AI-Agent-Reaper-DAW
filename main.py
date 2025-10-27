import os, time, json
from collections import defaultdict, deque
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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
    try:
        # Import prompt enhancer
        from prompt_enhancer import enhance_prompt
        
        # Step 1: Enhance vague prompt to be specific/technical
        reaper_state = WRAP_STATE.get(body.session_id, {})
        state_str = json.dumps(reaper_state) if reaper_state else ""
        enhanced_prompt = enhance_prompt(body.text, state_str)
        
        print(f"📝 Original: {body.text}")
        print(f"✨ Enhanced: {enhanced_prompt}")
        
        # Step 2: Execute using cloud wrapper (keeps your 6k line agent intact)
        result = execute_user_command_cloud(
            user_input=enhanced_prompt,
            session_id=body.session_id,
            reaper_state_dict=WRAP_STATE,
            reaper_sessions_dict=WRAP_SESSIONS
        )
        
        # Get commands that were queued by the agent (wrapper sessions)
        commands = get_queued_commands(body.session_id)

        # Also forward those commands into the bridge queue used by /api/reaper/poll
        if commands:
            if body.session_id not in REAPER_SESSIONS:
                REAPER_SESSIONS[body.session_id] = []
            REAPER_SESSIONS[body.session_id].extend(commands)
        
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
            "reply": f"✅ {result['message']}",
            "plan": plan,
            "commands": commands,
            "status": result["status"],
            "agent_reasoning": enhanced_prompt
        }
        
    except Exception as e:
        # Fallback response
        plan = {
            "plan_id": f"plan-{int(time.time()*1000)}",
            "steps": [
                {"id":"s1","action":"ERROR","error":str(e)}
            ]
        }
        add_event("error", {"prompt": body.text, "error": str(e)}, session_id=body.session_id)
        return {"reply": f"❌ Error: {str(e)}", "plan": plan, "status": "error"}

# -------------------- Chat (RAW) → real agent, no enhancer --------------------
@app.post("/api/chat_raw")
def api_chat_raw(body: ChatIn):
    try:
        # Directly run the FULL agent with the raw user text
        result = execute_user_command_cloud(
            user_input=body.text,
            session_id=body.session_id,
            reaper_state_dict=WRAP_STATE,
            reaper_sessions_dict=WRAP_SESSIONS
        )

        # Pull commands and mirror to bridge queue
        commands = get_queued_commands(body.session_id)
        if commands:
            if body.session_id not in REAPER_SESSIONS:
                REAPER_SESSIONS[body.session_id] = []
            REAPER_SESSIONS[body.session_id].extend(commands)

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
            "reply": f"✅ {result['message']}",
            "plan": plan,
            "commands": commands,
            "status": result["status"]
        }
    except Exception as e:
        plan = {
            "plan_id": f"plan-{int(time.time()*1000)}",
            "steps": [
                {"id": "s1", "action": "ERROR", "error": str(e)}
            ]
        }
        add_event("error", {"prompt": body.text, "error": str(e)}, session_id=body.session_id)
        return {"reply": f"❌ Error: {str(e)}", "plan": plan, "status": "error"}

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

# Wire the REAL agent with cloud hooks (no wrapper)
import ai_agent_reaper_final as agent

def _state_provider(session_id: str) -> str:
    state = REAPER_STATE.get(session_id, {})
    # Prefer raw text dump if present
    if isinstance(state, dict) and isinstance(state.get("state_text"), str):
        return state["state_text"]
    try:
        return json.dumps(state) if state else ""
    except Exception:
        return ""

def _command_sink(commands, session_id: str) -> bool:
    try:
        if not isinstance(commands, list):
            commands = [commands]
        if session_id not in REAPER_SESSIONS:
            REAPER_SESSIONS[session_id] = []
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
agent.set_cloud_hooks(
    state_provider=_state_provider,
    command_sink=_command_sink,
    feedback_provider=_feedback_provider,
    memory_load=_memory_load,
    memory_save=_memory_save,
)

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
    REAPER_STATE[session_id] = state
    add_event("reaper_state_update", state, session_id=session_id)
    return {"status": "received"}

# -------------------- Static UI for investors --------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>CursorDAW Cloud</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { background: #2a2a2a; border: 1px solid #444; border-radius: 8px; padding: 20px; }
        .input-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #ccc; }
        input, textarea, button { 
            width: 100%; padding: 10px; border: 1px solid #555; border-radius: 4px; 
            background: #333; color: #fff; margin-bottom: 10px;
        }
        button { background: #007bff; border: none; cursor: pointer; }
        button:hover { background: #0056b3; }
        .status { text-align: center; padding: 10px; background: #333; border-radius: 4px; margin-bottom: 20px; }
        .messages { height: 300px; overflow-y: auto; border: 1px solid #555; padding: 10px; background: #222; }
        .message { margin-bottom: 10px; padding: 8px; border-radius: 4px; }
        .user { background: #007bff; }
        .agent { background: #28a745; }
        .events { height: 300px; overflow-y: auto; border: 1px solid #555; padding: 10px; background: #222; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 CursorDAW Cloud</h1>
            <div class="status" id="status">Connecting...</div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>Chat</h3>
                <div class="messages" id="messages"></div>
                <div class="input-group">
                    <textarea id="messageInput" placeholder="Type your message..." rows="3"></textarea>
                    <button onclick="sendMessage()">Send</button>
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
        
        function updateStatus(message, connected = false) {
            document.getElementById('status').textContent = message;
            isConnected = connected;
        }
        
        function addMessage(text, type = 'user') {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + type;
            messageDiv.textContent = text;
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
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;
            
            addMessage(message, 'user');
            input.value = '';
            
            if (!isConnected) {
                addMessage('Not connected to server', 'agent');
                return;
            }
            
            try {
                const response = await fetch('/api/chat_raw', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: 'demo', text: message })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    addMessage('Queued ' + (data.plan?.steps?.length || 0) + ' steps', 'agent');
                    
                    // Show agent reasoning if available
                    if (data.agent_reasoning) {
                        addMessage('Agent reasoning: ' + data.agent_reasoning, 'agent');
                    }
                    
                    addEvent('Message sent: ' + message);
                } else {
                    addMessage('Error: ' + response.status, 'agent');
                }
            } catch (error) {
                addMessage('Network error: ' + error.message, 'agent');
            }
        }
        
        // Check connection on load
        checkConnection();
        
        // Enter key support
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    </script>
</body>
</html>
""", status_code=200)