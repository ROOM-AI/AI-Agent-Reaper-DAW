"""
FastAPI Web Server for AI Agent Reaper DAW
Run with: uvicorn app:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import subprocess
import json
import os
from pathlib import Path

app = FastAPI(title="AI Agent Reaper DAW", version="1.0.0")

# CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = "default"

class AgentResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None

@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Reaper DAW</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .chat-container {
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            margin-bottom: 20px;
            background: #f9f9f9;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 8px;
        }
        .user-message {
            background: #007bff;
            color: white;
            margin-left: 50px;
        }
        .agent-message {
            background: #28a745;
            color: white;
            margin-right: 50px;
        }
        .input-container {
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        button {
            padding: 12px 24px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #0056b3;
        }
        .status {
            text-align: center;
            margin-top: 20px;
            padding: 10px;
            border-radius: 8px;
            background: #e9ecef;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 AI Agent Reaper DAW 🎵</h1>
        <div class="chat-container" id="chatContainer">
            <div class="message agent-message">
                <strong>AI Agent:</strong> Hello! I'm your AI assistant for REAPER DAW. I can help you with mixing, mastering, and audio production. What would you like me to do?
            </div>
        </div>
        <div class="input-container">
            <input type="text" id="userInput" placeholder="Try: 'add reverb to track 1' or 'boost the bass'" />
            <button onclick="sendMessage()">Send</button>
        </div>
        <div class="status" id="status">Ready to help with your DAW!</div>
    </div>

    <script>
        function addMessage(content, isUser = false) {
            const chatContainer = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'agent-message'}`;
            messageDiv.innerHTML = `<strong>${isUser ? 'You' : 'AI Agent'}:</strong> ${content}`;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;

            addMessage(message, true);
            input.value = '';
            
            const status = document.getElementById('status');
            status.textContent = 'AI Agent is thinking...';
            status.style.background = '#fff3cd';

            try {
                const response = await fetch('/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        prompt: message,
                        session_id: 'web_interface'
                    })
                });

                const data = await response.json();
                
                if (data.status === 'success') {
                    addMessage(data.message);
                    status.textContent = 'Command processed successfully!';
                    status.style.background = '#d4edda';
                } else {
                    addMessage('Sorry, there was an error: ' + data.message);
                    status.textContent = 'Error occurred';
                    status.style.background = '#f8d7da';
                }
            } catch (error) {
                addMessage('Connection error: ' + error.message);
                status.textContent = 'Connection failed';
                status.style.background = '#f8d7da';
            }
        }

        document.getElementById('userInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "features": {
            "audio_analysis": False,
            "essentia": False,
            "panns": False
        }
    }

@app.post("/query", response_model=AgentResponse)
async def process_query(request: AgentRequest):
    """
    Process a query through the AI agent.
    Example: {"prompt": "add reverb to track 1"}
    """
    try:
        # For demo purposes, return a mock response
        # In production, you'd import and use the actual agent
        demo_responses = {
            "add reverb": "✅ Added reverb to track 1 using Valhalla VintageVerb",
            "boost bass": "✅ Boosted bass frequencies with Pro-Q 3 EQ",
            "add compression": "✅ Added SSL Channel compression to track 1",
            "pan left": "✅ Panned track 1 to the left",
            "add electrax": "✅ Added ElectraX synthesizer to track 1"
        }
        
        # Find matching response
        response_text = "✅ Command processed: " + request.prompt
        for key, value in demo_responses.items():
            if key in request.prompt.lower():
                response_text = value
                break
        
        return AgentResponse(
            status="success",
            message=response_text,
            data={"demo": True, "original_prompt": request.prompt}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/track/{track_id}")
async def get_track_info(track_id: int):
    """Get info about a specific track"""
    # You'd implement REAPER state reading here
    return {"track_id": track_id, "status": "info_coming_soon"}

@app.get("/tracks")
async def list_tracks():
    """List all tracks in current session"""
    return {"tracks": "list_coming_soon"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

