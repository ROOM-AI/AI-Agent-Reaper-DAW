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

# -------------------- Chat → plan → queue --------------------
@app.post("/api/chat")
def api_chat(body: ChatIn):
    """
    Use the real AI agent from ai_agent_reaper_final.py
    """
    try:
        # Import the real agent function
        from ai_agent_reaper_final import execute_user_command
        
        # Create a mock print function to capture output
        agent_output = []
        original_print = print
        
        def capture_print(*args, **kwargs):
            message = ' '.join(str(arg) for arg in args)
            agent_output.append(message)
            original_print(*args, **kwargs)  # Still print to console
        
        # Temporarily replace print to capture agent output
        import builtins
        builtins.print = capture_print
        
        try:
            # Execute the real agent command
            execute_user_command(body.text)
        finally:
            # Restore original print
            builtins.print = original_print
        
        # Create a response from the agent output
        agent_response = "\n".join(agent_output[-10:])  # Last 10 lines
        
        # For now, create a simple plan based on the agent's reasoning
        plan = {
            "plan_id": f"plan-{int(time.time()*1000)}",
            "steps": [
                {"id":"s1","action":"AI_AGENT_PROCESSING","target":"AI Agent","reasoning":agent_response}
            ]
        }
        
        # Add the plan to the queue
        for step in plan["steps"]:
            QUEUES[body.session_id].append({
                "step_id": step["id"],
                "session_id": body.session_id,
                "command": step
            })
        
        add_event("plan_created", {"prompt": body.text, **plan}, session_id=body.session_id)
        return {"reply": f"AI Agent processed: {body.text}", "plan": plan, "agent_reasoning": agent_response}
        
    except Exception as e:
        # Fallback to simple response if agent fails
        plan = {
            "plan_id": f"plan-{int(time.time()*1000)}",
            "steps": [
                {"id":"s1","action":"FALLBACK","target":"System","error":str(e)}
            ]
        }
        add_event("plan_created", {"prompt": body.text, **plan}, session_id=body.session_id)
        return {"reply": f"Agent processing failed: {str(e)}", "plan": plan}

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