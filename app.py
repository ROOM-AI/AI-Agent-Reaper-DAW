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
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "features": {
            "audio_analysis": AUDIO_ANALYSIS_AVAILABLE,
            "essentia": ESSENTIA_AVAILABLE,
            "panns": PANNS_AVAILABLE
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

