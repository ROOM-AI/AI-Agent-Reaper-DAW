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
    Replace the stub "plan" below with a call into your ai_agent_reaper_final.py
    (e.g., import your planner and build step objects your Lua expects).
    """
    plan = {
        "plan_id": f"plan-{int(time.time()*1000)}",
        "steps": [
            {"id":"s1","action":"ADD_FX","target":"Track 2","plugin":"FabFilter Pro-Q 3",
             "params":{"band1":{"type":"HShelf","gain_db":0.8,"freq_hz":9000}}},
            {"id":"s2","action":"SET_FX_PARAM","target":"Track 2","plugin":"ValhallaVintageVerb",
             "params":{"mix":0.18,"decay_s":2.4}},
            {"id":"s3","action":"VERIFY","checks":["LUFS","spectral_centroid","reverb_rt60"]}
        ]
    }
    for step in plan["steps"]:
        QUEUES[body.session_id].append({
            "step_id": step["id"],
            "session_id": body.session_id,
            "command": step
        })
    add_event("plan_created", {"prompt": body.text, **plan}, session_id=body.session_id)
    return {"reply": f"Queued {len(plan['steps'])} steps for {body.session_id}.", "plan": plan}

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
<!doctype html><meta charset="utf-8">
<title>CursorDAW – Cloud Demo</title>
<style>
  body{font:14px/1.5 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width:840px; margin:32px auto; padding:0 16px}
  #log{font-family:ui-monospace,Menlo,Consolas,monospace;white-space:pre-wrap;border:1px solid #ddd;padding:12px;border-radius:8px;height:360px;overflow:auto;background:#f9f9f9}
  .row{display:flex;gap:8px;margin:8px 0}
  input,button{padding:8px 10px;border-radius:4px;border:1px solid #ddd}
  button{background:#007bff;color:white;border:none;cursor:pointer}
  button:hover{background:#0056b3}
</style>
<h1>🎵 CursorDAW – Cloud</h1>
<div class="row">
  <label>Session:</label>
  <input id="sid" value="demo">
</div>
<div class="row">
  <input id="msg" placeholder="Tell the agent what to do…" style="flex:1">
  <button onclick="send()">Send</button>
</div>
<div id="log"></div>
<script>
const log = document.getElementById('log');
const sid = document.getElementById('sid');
const msg = document.getElementById('msg');
let since = null;

function line(s){ log.textContent += s + "\n"; log.scrollTop = log.scrollHeight; }

async function send(){
  const session_id = sid.value.trim() || "demo";
  const text = msg.value.trim(); if(!text) return;
  msg.value = "";
  try{
    const r = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({session_id, text})
    });
    const j = await r.json();
    line(`> ${text}`);
    line(JSON.stringify(j.plan, null, 2));
  }catch(e){ line("ERR: " + e); }
}

async function tick(){
  const session_id = sid.value.trim() || "demo";
  try{
    const url = since ? `/public/events?session_id=${encodeURIComponent(session_id)}&since=${since}` :
                        `/public/events?session_id=${encodeURIComponent(session_id)}`;
    const r = await fetch(url); const arr = await r.json();
    if(arr.length){ since = arr[arr.length-1].t; for(const e of arr){
      const t = new Date(e.t*1000).toLocaleTimeString();
      line(`[${t}] ${e.kind}: ${JSON.stringify(e.data)}`);
    }}
  }catch(e){/* ignore */}
  setTimeout(tick, 900);
}
tick();

msg.addEventListener('keypress', e => { if(e.key === 'Enter') send(); });
</script>
""", status_code=200)