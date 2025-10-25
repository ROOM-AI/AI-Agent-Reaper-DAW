"""
Minimal FastAPI app for Railway deployment
Only includes the essential AI agent functionality
"""

import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="AI Agent DAW")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

class ChatRequest(BaseModel):
    text: str
    session_id: str = "demo"

@app.get("/")
async def root():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>AI Agent DAW</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
        .container { max-width: 800px; margin: 0 auto; }
        input, button { padding: 10px; margin: 5px; width: 200px; }
        button { background: #007bff; color: white; border: none; cursor: pointer; }
        #response { margin-top: 20px; padding: 10px; background: #333; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 AI Agent DAW 🎵</h1>
        <input type="text" id="message" placeholder="Type your message..." />
        <button onclick="sendMessage()">Send</button>
        <div id="response"></div>
    </div>
    
    <script>
        async function sendMessage() {
            const message = document.getElementById('message').value;
            if (!message) return;
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: message })
                });
                
                const data = await response.json();
                document.getElementById('response').innerHTML = 
                    '<strong>You:</strong> ' + message + '<br>' +
                    '<strong>Agent:</strong> ' + data.response;
            } catch (error) {
                document.getElementById('response').innerHTML = 'Error: ' + error.message;
            }
        }
    </script>
</body>
</html>
    """)

@app.post("/chat")
async def chat(request: ChatRequest):
    """Simple AI agent response"""
    try:
        # Import and use the real agent
        from ai_agent_reaper_final import execute_user_command
        
        # Capture agent output
        import sys
        from io import StringIO
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            execute_user_command(request.text)
        finally:
            sys.stdout = old_stdout
        
        agent_output = captured_output.getvalue()
        
        return {
            "response": f"AI Agent processed: {request.text}",
            "reasoning": agent_output[-500:] if agent_output else "No output captured"
        }
        
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "reasoning": "Agent failed to process"
        }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
