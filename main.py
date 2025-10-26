import os, time
from collections import defaultdict, deque
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

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

# -------------------- Cloud AI Agent (REAL Claude AI) --------------------
from anthropic import Anthropic

# Initialize Claude with your API key
claude_client = Anthropic(api_key="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")

def cloud_ai_agent(user_prompt: str) -> List[str]:
    """
    Cloud-based AI agent that uses REAL Claude to generate Reaper commands.
    Returns list of command strings that bridge will write to reaper_commands.txt
    """
    try:
        # Build prompt for Claude
        system_prompt = f"""You are an AI assistant for REAPER DAW. Generate commands to execute the user's request.

**AVAILABLE COMMANDS:**
- ADD_FX:Track <num>:<FX name> - Add an effect to a track
- SET_TRACK_VOL <track_idx> <volumeDB> - Set track volume
- SELECT_TRACK <track_idx> - Select a track
- GOTO <seconds> - Move playhead to time
- play / stop / record - Transport controls

**COMMON PLUGINS:**
- ReaVerb, ReaComp, ReaEQ (built-in)
- Pro-Q 3, Saturn 2 (FabFilter)
- ValhallaRoom, VintageVerb (Valhalla)

**USER REQUEST:** {user_prompt}

**INSTRUCTIONS:**
1. Analyze what the user wants
2. Generate the appropriate commands
3. Return ONLY the commands, one per line
4. No explanations, just commands

**EXAMPLES:**
User: "add reverb to track 1"
Output:
ADD_FX:Track 1:ReaVerb

User: "boost bass on track 2"
Output:
ADD_FX:Track 2:Pro-Q 3

User: "play the song"
Output:
play

Now generate commands for the user's request above. Return ONLY commands, no explanations."""

        # Call Claude API
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": system_prompt}]
        ).content[0].text.strip()
        
        # Parse response into command list
        commands = [line.strip() for line in response.split('\n') if line.strip() and not line.strip().startswith('#')]
        
        if not commands:
            commands = [f"AI_MESSAGE:{user_prompt}"]
        
        return commands
        
    except Exception as e:
        print(f"❌ Cloud AI Error: {e}")
        return [f"AI_MESSAGE:Error processing request: {str(e)}"]

# -------------------- Chat → plan → queue --------------------
@app.post("/api/chat")
def api_chat(body: ChatIn):
    """
    Cloud AI agent - uses FULL agent logic with Claude reasoning
    """
    try:
        # Import YOUR FULL REAL AGENT + PROMPT ENHANCER
        import ai_agent_reaper_final
        from prompt_enhancer import enhance_prompt
        
        # Step 1: Enhance vague prompt to be specific/technical
        reaper_state = REAPER_STATE.get(body.session_id, {})
        state_str = json.dumps(reaper_state) if reaper_state else ""
        enhanced_prompt = enhance_prompt(body.text, state_str)
        
        print(f"📝 Original: {body.text}")
        print(f"✨ Enhanced: {enhanced_prompt}")
        
        # Step 2: Monkey-patch file I/O to use memory
        def mock_send_reaper_commands(commands):
            """Override to queue in memory instead of writing to file"""
            if body.session_id not in REAPER_SESSIONS:
                REAPER_SESSIONS[body.session_id] = []
            for cmd in commands:
                REAPER_SESSIONS[body.session_id].append(cmd)
            return True
        
        # Replace the agent's file writing function
        ai_agent_reaper_final.send_reaper_commands = mock_send_reaper_commands
        
        # Step 3: Call the real agent with enhanced prompt
        ai_agent_reaper_final.execute_user_command(enhanced_prompt)
        
        # Get commands that were queued
        commands = REAPER_SESSIONS.get(body.session_id, [])
        
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
            "status": result["status"]
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
    add_event("reaper_state_update", state, session_id="reaper")
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
                const response = await fetch('/api/chat', {
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