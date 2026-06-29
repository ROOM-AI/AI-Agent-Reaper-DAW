"""
FastAPI Web Server for AI Agent Reaper DAW
Run with: uvicorn app:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

@app.get("/")
async def root():
    return {
        "name": "AI Agent Reaper DAW",
        "version": "1.0.0",
        "description": "AI-powered automation for REAPER DAW",
        "endpoints": {
            "/": "This info page",
            "/health": "Check system health",
            "/query": "Send commands to the AI agent",
            "/docs": "API documentation"
        }
    }

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
        # Import here to avoid loading on startup
        from ai_agent_reaper_final import process_user_request
        
        # Call the agent
        result = process_user_request(request.prompt, session_id=request.session_id)
        
        return AgentResponse(
            status="success",
            message="Query processed successfully",
            data=result
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


