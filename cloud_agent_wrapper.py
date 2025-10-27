"""
Cloud wrapper for ai_agent_reaper_final.py
Redirects file I/O to memory while keeping the original agent intact
"""

import json
import time
from typing import Dict, List, Any, Optional

# Global state storage (shared with main.py)
REAPER_STATE = {}  # session_id -> state dict
REAPER_SESSIONS = {}  # session_id -> [commands]
REAPER_FEEDBACK = {}  # session_id -> feedback string
REAPER_MEMORY = {}  # session_id -> memory dict

def create_cloud_wrapper(session_id: str = "demo"):
    """
    Create a cloud-compatible version of ai_agent_reaper_final
    Returns a module with file I/O redirected to memory
    """
    import ai_agent_reaper_final
    import types
    
    # Create a new module that inherits everything from the original
    cloud_agent = types.ModuleType('cloud_agent')
    
    # Copy all attributes from the original agent
    for attr_name in dir(ai_agent_reaper_final):
        if not attr_name.startswith('_'):
            setattr(cloud_agent, attr_name, getattr(ai_agent_reaper_final, attr_name))
    
    # Override the file I/O functions to use memory instead
    def cloud_send_reaper_commands(commands):
        """Send commands to Reaper (cloud version - stores in memory)"""
        try:
            if session_id not in REAPER_SESSIONS:
                REAPER_SESSIONS[session_id] = []
            
            for cmd in commands:
                REAPER_SESSIONS[session_id].append(cmd)
            
            # Simulate the original delay
            time.sleep(0.3)
            
            # Log debug info (if log_debug exists)
            if hasattr(cloud_agent, 'log_debug'):
                cloud_agent.log_debug(f"Sent: {commands}")
            
            return True
        except Exception as e:
            if hasattr(cloud_agent, 'log_debug'):
                cloud_agent.log_debug(f"Send error: {e}")
            return False
    
    def cloud_get_reaper_state():
        """Get current Reaper state (cloud version - reads from memory).
        Prefer raw text dump if provided as 'state_text'.
        """
        try:
            state = REAPER_STATE.get(session_id, {})
            if not state:
                return "State unavailable"

            # If bridge sent a raw text dump, return it directly
            if isinstance(state, dict) and isinstance(state.get('state_text'), str):
                return state['state_text']

            # Otherwise stringify whatever we have (JSON pretty print)
            if isinstance(state, dict):
                return json.dumps(state, indent=2)
            return str(state)
        except Exception as e:
            if hasattr(cloud_agent, 'log_debug'):
                cloud_agent.log_debug(f"State error: {e}")
            return "State unavailable"
    
    def cloud_get_reaper_feedback():
        """Read feedback from Reaper (cloud version - reads from memory)"""
        try:
            feedback = REAPER_FEEDBACK.get(session_id, "").strip()
            if feedback:
                if hasattr(cloud_agent, 'log_debug'):
                    cloud_agent.log_debug(f"Feedback: {feedback}")
            return feedback
        except Exception as e:
            if hasattr(cloud_agent, 'log_debug'):
                cloud_agent.log_debug(f"Feedback error: {e}")
            return ""
    
    def cloud_save_memory(memory_data):
        """Save memory data (cloud version - stores in memory)"""
        try:
            REAPER_MEMORY[session_id] = memory_data
            if hasattr(cloud_agent, 'log_debug'):
                cloud_agent.log_debug(f"Memory saved: {len(str(memory_data))} chars")
            return True
        except Exception as e:
            if hasattr(cloud_agent, 'log_debug'):
                cloud_agent.log_debug(f"Memory save error: {e}")
            return False
    
    def cloud_load_memory():
        """Load memory data (cloud version - reads from memory)"""
        try:
            return REAPER_MEMORY.get(session_id, {})
        except Exception as e:
            if hasattr(cloud_agent, 'log_debug'):
                cloud_agent.log_debug(f"Memory load error: {e}")
            return {}
    
    # Replace the file-based functions with cloud versions
    cloud_agent.send_reaper_commands = cloud_send_reaper_commands
    cloud_agent.get_reaper_state = cloud_get_reaper_state
    cloud_agent.get_reaper_feedback = cloud_get_reaper_feedback
    
    # Add memory functions if they exist in the original
    if hasattr(ai_agent_reaper_final, 'save_memory'):
        cloud_agent.save_memory = cloud_save_memory
    if hasattr(ai_agent_reaper_final, 'load_memory'):
        cloud_agent.load_memory = cloud_load_memory
    
    return cloud_agent

def execute_user_command_cloud(user_input: str, session_id: str = "demo", reaper_state_dict: Dict = None, reaper_sessions_dict: Dict = None) -> Dict:
    """
    Execute user command using the cloud-wrapped agent
    Returns dict with status and commands generated
    """
    global REAPER_STATE, REAPER_SESSIONS, REAPER_FEEDBACK, REAPER_MEMORY
    
    # Use passed-in dicts (shared with main.py)
    if reaper_state_dict is not None:
        REAPER_STATE = reaper_state_dict
    if reaper_sessions_dict is not None:
        REAPER_SESSIONS = reaper_sessions_dict
    
    try:
        # Create cloud-wrapped agent for this session
        cloud_agent = create_cloud_wrapper(session_id)
        
        # Get current state
        state_str = cloud_agent.get_reaper_state()
        
        if state_str == "State unavailable":
            return {
                "status": "error",
                "message": "No Reaper state available. Is Reaper running?",
                "commands": []
            }
        
        # Execute the user command using the original agent logic
        # This calls the full 6k line execute_user_command function
        cloud_agent.execute_user_command(user_input)
        
        # Get commands that were queued
        commands = REAPER_SESSIONS.get(session_id, [])
        
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

def update_reaper_state(session_id: str, state_data: Dict):
    """Update Reaper state for a session"""
    global REAPER_STATE
    REAPER_STATE[session_id] = state_data

def get_queued_commands(session_id: str) -> List[str]:
    """Get queued commands for a session"""
    return REAPER_SESSIONS.get(session_id, [])

def clear_commands(session_id: str):
    """Clear queued commands for a session"""
    if session_id in REAPER_SESSIONS:
        REAPER_SESSIONS[session_id] = []

