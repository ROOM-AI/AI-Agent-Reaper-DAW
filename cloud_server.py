import os, json, time, uuid, asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

APP_TOKEN = os.getenv("AGENT_AUTH_TOKEN", "")
app = FastAPI(title="Solo Agent Cloud")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def require_auth(request: Request):
    if not APP_TOKEN:
        return
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {APP_TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")

class Client:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.last_seen: float = time.time()
        self.state: Dict[str, Any] = {}

clients: Dict[str, Client] = {}
pending_rpcs: Dict[str, asyncio.Future] = {}

@app.get("/healthz")
async def healthz():
    return {"ok": True, "clients": len(clients)}

@app.get("/who")
async def who():
    out = []
    for cid, c in clients.items():
        out.append({"client_id": cid, "last_seen": c.last_seen, "has_state": bool(c.state)})
    return {"clients": out}

@app.get("/connect")
async def connect(request: Request, client_id: str = ""):
    require_auth(request)
    cid = client_id or str(uuid.uuid4())
    c = clients.get(cid) or Client()
    clients[cid] = c

    async def event_stream():
        yield f"event: hello\ndata: {json.dumps({'client_id': cid})}\n\n"
        try:
            while True:
                c.last_seen = time.time()
                try:
                    msg = await asyncio.wait_for(c.queue.get(), timeout=25)
                    yield f"data: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
                if await request.is_disconnected():
                    break
        finally:
            pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/send/{client_id}")
async def send(client_id: str, request: Request):
    require_auth(request)
    payload = await request.json()
    c = clients.get(client_id)
    if not c:
        raise HTTPException(404, "client not connected")
    await c.queue.put(payload)
    return {"ok": True}

@app.post("/state/{client_id}")
async def state(client_id: str, request: Request):
    require_auth(request)
    payload = await request.json()
    c = clients.get(client_id) or Client()
    c.state = payload
    c.last_seen = time.time()
    clients[client_id] = c
    return {"ok": True}

@app.get("/state/{client_id}")
async def get_state(client_id: str):
    c = clients.get(client_id)
    if not c:
        raise HTTPException(404, "unknown client")
    return {"ok": True, "state": c.state}

@app.post("/broadcast")
async def broadcast(request: Request):
    require_auth(request)
    payload = await request.json()
    for c in clients.values():
        await c.queue.put(payload)
    return {"ok": True}

# -------------------- Minimal RPC bridging --------------------
@app.post("/rpc/call")
async def rpc_call(request: Request):
    """Sends an RPC instruction to a connected client and waits for reply.
    Body: { client_id, op, path, args? }
    Returns: { ok, data? or error }
    """
    require_auth(request)
    body = await request.json()
    client_id: str = body.get("client_id", "")
    if not client_id or client_id not in clients:
        raise HTTPException(404, "client not connected")

    req_id = body.get("req_id") or str(uuid.uuid4())
    payload = {
        "type": "rpc",
        "req_id": req_id,
        "op": body.get("op"),
        "path": body.get("path"),
        "args": body.get("args", {}),
    }

    # Create future and enqueue request
    fut: asyncio.Future = asyncio.get_event_loop().create_future()
    if req_id in pending_rpcs:
        # extremely unlikely, but ensure uniqueness
        req_id = str(uuid.uuid4())
        payload["req_id"] = req_id
    pending_rpcs[req_id] = fut
    await clients[client_id].queue.put(payload)

    try:
        result = await asyncio.wait_for(fut, timeout=15)
        return result
    except asyncio.TimeoutError:
        pending_rpcs.pop(req_id, None)
        raise HTTPException(504, "rpc timeout")

@app.post("/rpc/reply/{client_id}")
async def rpc_reply(client_id: str, request: Request):
    """Client posts a reply for a previously sent RPC.
    Body: { req_id, ok, data? or error }
    """
    require_auth(request)
    body = await request.json()
    req_id: Optional[str] = body.get("req_id")
    if not req_id:
        raise HTTPException(400, "missing req_id")

    fut = pending_rpcs.pop(req_id, None)
    if fut and not fut.done():
        fut.set_result(body)
    return {"ok": True}


