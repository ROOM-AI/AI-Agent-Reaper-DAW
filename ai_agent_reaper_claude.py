import json
import time
import os
from anthropic import Anthropic
import os

# Initialize Anthropic Claude
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

COMMAND_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_commands.txt"
STATE_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_state.txt"
MEMORY_FILE = r"C:\Users\moosb\AIAGENT DAW\agent_memory.txt"
FEEDBACK_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_feedback.txt"
DEBUG_LOG_FILE = r"C:\Users\moosb\AIAGENT DAW\agent_debug.log"

# Conversation history for context
conversation_history = []

def load_memory():
    """Load persistent conversation history from file"""
    global conversation_history
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            conversation_history = [line.strip() for line in f if line.strip()]
        print(f"📚 Loaded {len(conversation_history)} past interactions from memory")
    except:
        print("📚 Starting fresh memory")
        conversation_history = []

def save_memory():
    """Save conversation history to file (keep last 50 interactions)"""
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            for entry in conversation_history[-50:]:
                f.write(entry + "\n")
    except Exception as e:
        print(f"⚠️ Couldn't save memory: {e}")

def send_reaper_commands(commands):
    """Send commands to Reaper by writing to file"""
    try:
        with open(COMMAND_FILE, 'w') as f:
            for cmd in commands:
                f.write(cmd + '\n')
        time.sleep(0.3)
        return True
    except Exception as e:
        print(f"Error sending commands: {e}")
        return False

def get_reaper_state():
    """Get current Reaper project state"""
    send_reaper_commands(["GET_STATE"])
    time.sleep(0.3)
    
    try:
        with open(STATE_FILE, "r") as f:
            return f.read()
    except:
        return "State unavailable"

def load_action_list():
    """Load Reaper action IDs from the complete action list"""
    known_actions = {}
    
    # Load the HUGE complete list (6,309 actions!)
    try:
        with open(r"C:\Users\moosb\AIAGENT DAW\lol reaper_actions_good.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("REAPER") or line.startswith("Format:") or line.startswith("Generated:"):
                    continue
                if "|" in line:
                    parts = line.split("|", 1)
                    if len(parts) == 2:
                        action_id = parts[0].strip()
                        description = parts[1].strip()
                        known_actions[action_id] = description
        print(f"✅ Loaded complete action database: {len(known_actions)} actions!")
    except Exception as e:
        print(f"❌ Error loading action list: {e}")
    
    return known_actions

def filter_relevant_actions(user_input, all_actions, max_actions=100):
    """Filter actions relevant to user's request to reduce token usage"""
    keywords = user_input.lower().split()
    
    # Always include essential transport/control actions
    essential_ids = ["1007", "1016", "1013", "40280", "40281", "40339", "40340", "40075", "40289"]
    relevant = {aid: desc for aid, desc in all_actions.items() if aid in essential_ids}
    
    # Score actions by keyword matches
    scored = []
    for aid, desc in all_actions.items():
        if aid in relevant:
            continue
        desc_lower = desc.lower()
        score = sum(1 for kw in keywords if kw in desc_lower)
        if score > 0:
            scored.append((score, aid, desc))
    
    # Sort by relevance and take top N
    scored.sort(reverse=True)
    for score, aid, desc in scored[:max_actions - len(relevant)]:
        relevant[aid] = desc
    
    return relevant

def plan_actions(user_input, state, known_actions):
    """Phase 1: Plan what actions to take (chain of thought)"""
    # Filter to only relevant actions (saves massive tokens!)
    relevant_actions = filter_relevant_actions(user_input, known_actions, max_actions=150)
    actions_text = "\n".join([f"{aid}: {desc}" for aid, desc in relevant_actions.items()])
    
    print(f"🔍 Filtered to {len(relevant_actions)} relevant actions from {len(known_actions)} total")
    
    system_prompt = f"""You are an AI that controls Reaper DAW. You can see the complete project state and must PLAN actions before executing.

**CURRENT PROJECT STATE:**
{state}

**AVAILABLE ACTIONS (filtered for relevance):**
{actions_text}

**CUSTOM COMMANDS:**
- SELECT_TRACK <trackIdx> - select track
- VOL_DIP <trackIdx> <tStart> <tEnd> <value0-1> - volume automation
- SET_TRACK_VOL <trackIdx> <volumeDB> - set track volume
- ADD_FX <trackIdx> <pluginName> - add FX plugin
- SET_FX_PARAM <trackIdx> <fxIdx> <paramIdx> <value0-1> - set FX parameter
- GOTO <seconds> - jump to position

**YOUR TASK:**
1. Read the user's request: "{user_input}"
2. Analyze the current state
3. Create a step-by-step plan
4. Output ONLY a JSON object with this format:

{{
  "reasoning": "Brief explanation of what you need to do and why",
  "steps": [
    {{"command": "SELECT_TRACK 4", "description": "Select track 4"}},
    {{"command": "40280", "description": "Toggle solo for selected track"}}
  ]
}}

Be precise. Use exact action IDs. Consider current state (don't toggle if already in desired state).

CRITICAL: Return ONLY the JSON object. No explanation before or after. Start your response with {{ and end with }}."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": system_prompt}]
    )
    
    return response.content[0].text.strip()

def verify_result(user_input, initial_state, final_state, executed_commands):
    """Phase 3: Verify if the goal was achieved"""
    
    system_prompt = f"""You executed commands in Reaper DAW. Verify if the goal was achieved.

**USER REQUESTED:** {user_input}

**STATE BEFORE:**
{initial_state[:1000]}

**COMMANDS EXECUTED:**
{executed_commands}

**STATE AFTER:**
{final_state[:1000]}

**YOUR TASK:**
Respond with ONLY a JSON object:
{{
  "success": true/false,
  "explanation": "Brief explanation of what happened",
  "issues": "Any problems or suggestions for improvement"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": system_prompt}]
    )
    
    return response.content[0].text.strip()

def execute_user_command(user_input):
    """Main Cursor-style agentic loop: Plan → Execute → Verify"""
    print(f"\n🎤 User: {user_input}")
    
    # Get initial state
    print("📊 Reading Reaper state...")
    initial_state = get_reaper_state()
    
    # Load actions
    known_actions = load_action_list()
    print(f"💪 Loaded {len(known_actions)} action descriptions")
    
    # PHASE 1: PLAN
    print("\n🧠 Planning actions...")
    plan_response = plan_actions(user_input, initial_state, known_actions)
    print(f"📋 Plan: {plan_response}")
    
    try:
        plan = json.loads(plan_response)
        reasoning = plan.get("reasoning", "")
        steps = plan.get("steps", [])
        
        print(f"\n💭 Reasoning: {reasoning}")
        print(f"📝 Steps: {len(steps)}")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step.get('description', 'Unknown')}: {step.get('command', 'Unknown')}")
    except json.JSONDecodeError:
        print("❌ AI didn't return valid JSON plan")
        return
    
    # PHASE 2: EXECUTE
    print(f"\n⚡ Executing {len(steps)} step(s)...")
    commands = [step.get("command", "") for step in steps]
    success = send_reaper_commands(commands)
    
    if not success:
        print("❌ Failed to send commands")
        return
    
    print("✅ Commands sent to Reaper")
    time.sleep(0.5)  # Wait for execution
    
    # PHASE 3: VERIFY
    print("\n🔍 Verifying results...")
    final_state = get_reaper_state()
    verify_response = verify_result(user_input, initial_state, final_state, commands)
    
    try:
        verification = json.loads(verify_response)
        success = verification.get("success", False)
        explanation = verification.get("explanation", "")
        issues = verification.get("issues", "")
        
        if success:
            print(f"✅ Success: {explanation}")
        else:
            print(f"⚠️ Partial success: {explanation}")
        
        if issues:
            print(f"📌 Notes: {issues}")
    except json.JSONDecodeError:
        print(f"📋 Verification response: {verify_response}")
    
    # Save to memory
    history_entry = f"User: '{user_input}' → {reasoning} → {', '.join([s.get('description', '') for s in steps])}"
    conversation_history.append(history_entry)
    save_memory()
    
    print("\n✨ Done!\n")

if __name__ == "__main__":
    print("=" * 60)
    print("AI Agent for Reaper DAW - Claude Sonnet 4.5")
    print("Cursor-style: Plan → Execute → Verify")
    print("=" * 60)
    print("\nMake sure:")
    print("1. Reaper is running")
    print("2. reaper_agent.lua is loaded and running")
    print("=" * 60)
    
    load_memory()
    
    print("\n✨ Ready! AI will show reasoning before acting\n")
    
    while True:
        user_input = input("\n💬 You: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        execute_user_command(user_input)

