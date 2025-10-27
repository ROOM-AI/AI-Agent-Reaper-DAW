"""
Cloud-adapted AI Agent for REAPER DAW
Adapted from ai_agent_reaper_final.py to work in cloud environment
- Reads state from memory (REAPER_STATE dict) instead of files
- Writes commands to memory (REAPER_SESSIONS dict) instead of files
- Keeps full Claude reasoning and action logic
"""

import json
import time
import re
import os
from typing import Dict, List, Any, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Anthropic Claude
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Cloud state storage (passed from main.py)
REAPER_STATE = {}
REAPER_SESSIONS = {}

def get_reaper_state(session_id: str = "demo") -> Dict:
    """Get current Reaper state from memory"""
    return REAPER_STATE.get(session_id, {})

def queue_commands(session_id: str, commands: List[str]):
    """Queue commands for Reaper to execute"""
    if session_id not in REAPER_SESSIONS:
        REAPER_SESSIONS[session_id] = []
    for cmd in commands:
        REAPER_SESSIONS[session_id].append(cmd)

def plan_actions_cloud(user_input: str, state: Dict, session_id: str = "demo") -> List[str]:
    """
    Cloud version of plan_actions - uses Claude to generate commands
    Simplified for cloud (no local file access)
    """
    
    # Build state summary
    track_count = state.get("tracks", 0)
    position = state.get("position", 0)
    playing = state.get("playing", False)
    track_list = state.get("track_list", [])
    
    # Build track info
    tracks_info = ""
    for track in track_list:
        fx_list = ", ".join([fx.get("name", "Unknown") for fx in track.get("fx", [])])
        tracks_info += f"\nTrack {track.get('num', 0)}: {track.get('name', 'Unnamed')} | Vol: {track.get('volume_db', 0):.1f}dB | FX: {fx_list or 'None'}"
    
    system_prompt = f"""You are an AI assistant for REAPER DAW. Generate commands to execute the user's request.

**CURRENT REAPER STATE:**
- Tracks: {track_count}
- Position: {position:.2f}s
- Playing: {playing}
- Track Details:{tracks_info}

**AVAILABLE COMMANDS:**
- ADD_FX:Track <num>:<FX name> - Add effect to track
- SET_TRACK_VOL <track_idx> <volumeDB> - Set track volume  
- SELECT_TRACK <track_idx> - Select track
- GOTO <seconds> - Move playhead
- play / stop / record - Transport controls

**COMMON PLUGINS:**
- ReaVerb, ReaComp, ReaEQ (built-in Reaper)
- Pro-Q 3, Saturn 2, Pro-MB, Pro-C 2 (FabFilter)
- ValhallaRoom, VintageVerb, ValhallaDelay (Valhalla)
- CLA-76, SSL Channel (Waves)
- ElectraX, Serum (Instruments)

**USER REQUEST:** {user_input}

**INSTRUCTIONS:**
1. Analyze the current state and user request
2. Generate appropriate commands
3. Be specific with track numbers (use actual tracks that exist)
4. Return ONLY commands, one per line
5. No explanations, markdown, or extra text

**EXAMPLE:**
User: "add reverb to track 1"
Commands:
ADD_FX:Track 1:ValhallaRoom

User: "make track 2 louder"  
Commands:
SET_TRACK_VOL 1 3.0

Now generate commands for: {user_input}
Return ONLY the commands."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": system_prompt}]
        ).content[0].text.strip()
        
        # Parse commands
        commands = []
        for line in response.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('```'):
                commands.append(line)
        
        if not commands:
            commands = [f"AI_MESSAGE:Processed: {user_input}"]
        
        return commands
        
    except Exception as e:
        print(f"❌ Cloud Agent Error: {e}")
        return [f"AI_MESSAGE:Error: {str(e)}"]

def execute_user_command_cloud(user_input: str, session_id: str = "demo", reaper_state_dict: Dict = None, reaper_sessions_dict: Dict = None) -> Dict:
    """
    Cloud version of execute_user_command
    Returns dict with status and commands generated
    """
    global REAPER_STATE, REAPER_SESSIONS
    
    # Use passed-in dicts (shared with main.py)
    if reaper_state_dict is not None:
        REAPER_STATE = reaper_state_dict
    if reaper_sessions_dict is not None:
        REAPER_SESSIONS = reaper_sessions_dict
    
    try:
        # Get current state
        state = get_reaper_state(session_id)
        
        if not state:
            return {
                "status": "error",
                "message": "No Reaper state available. Is Reaper running?",
                "commands": []
            }
        
        # Generate commands using Claude
        commands = plan_actions_cloud(user_input, state, session_id)
        
        # Queue commands
        queue_commands(session_id, commands)
        
        return {
            "status": "success",
            "message": f"Generated {len(commands)} command(s)",
            "commands": commands
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "commands": []
        }

