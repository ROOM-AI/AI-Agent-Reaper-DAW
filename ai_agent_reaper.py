import json
import time
import os
from openai import OpenAI
import os

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

COMMAND_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_commands.txt"
STATE_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_state.txt"
MEMORY_FILE = r"C:\Users\moosb\AIAGENT DAW\agent_memory.txt"
FEEDBACK_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_feedback.txt"
DEBUG_LOG_FILE = r"C:\Users\moosb\AIAGENT DAW\agent_debug.log"

# Conversation history for context (persistent across sessions)
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
            # Keep only last 50 to avoid bloat
            for entry in conversation_history[-50:]:
                f.write(entry + "\n")
    except Exception as e:
        print(f"⚠️ Couldn't save memory: {e}")

def _debug_write(line: str) -> None:
    try:
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")
    except Exception:
        pass

def get_track_state_from_dump(state_text: str, track_idx: int):
    """Return {'mute': bool, 'solo': bool, 'line': str} or None by scanning the dump."""
    lines = state_text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith(f"--- Track {track_idx}:"):
            # Look ahead a few lines for the Mute/Solo line
            for j in range(i + 1, min(i + 8, len(lines))):
                if "Mute:" in lines[j] and "Solo:" in lines[j]:
                    mute_segment = lines[j].split("Mute:")[-1].split("|")[0].strip()
                    solo_segment = lines[j].split("Solo:")[-1].strip()
                    mute = mute_segment.upper().startswith("YES")
                    solo = solo_segment.upper().startswith("YES")
                    return {"mute": mute, "solo": solo, "line": lines[j].strip()}
            return None
    return None

def validate_commands(commands, state):
    """Validate commands before sending - catch AI mistakes"""
    validated = []
    warnings = []
    
    # Extract track count from state
    max_track = -1
    for line in state.split('\n'):
        if line.startswith("--- Track "):
            track_num = int(line.split("Track ")[1].split(":")[0])
            max_track = max(max_track, track_num)
    
    for cmd in commands:
        # Validate SELECT_TRACK
        if cmd.startswith("SELECT_TRACK"):
            track_idx = int(cmd.split()[1])
            if track_idx > max_track:
                warnings.append(f"⚠️  Track {track_idx} doesn't exist (max is {max_track})")
                continue  # Skip this command

        # Validate SOLO/MUTE toggles by checking desired state against dump when possible
        if cmd.isdigit() and int(cmd) in (40280, 40294):
            # find last SELECT_TRACK before this command to know target
            # naive backscan
            target_track = None
            for back in range(len(validated) - 1, -1, -1):
                if validated[back].startswith("SELECT_TRACK"):
                    target_track = int(validated[back].split()[1])
                    break
            if target_track is not None:
                ts = get_track_state_from_dump(state, target_track)
                if ts:
                    if int(cmd) == 40294 and ts["mute"] is False:
                        # user probably wants mute/unmute; can't infer intent here, just log
                        warnings.append(f"ℹ️  Track {target_track} currently unmuted; 40294 will toggle to muted")
                    if int(cmd) == 40280 and ts["solo"] is False:
                        warnings.append(f"ℹ️  Track {target_track} currently not soloed; 40280 will toggle to solo")
        
        validated.append(cmd)
    
    return validated, warnings

def send_reaper_commands(commands, state=None):
    """Send commands to Reaper by writing to file"""
    try:
        # Validate first if state available
        if state:
            commands, warnings = validate_commands(commands, state)
            for warning in warnings:
                print(warning)
            if not commands:
                print("❌ All commands were invalid!")
                return False
        
        with open(COMMAND_FILE, 'w') as f:
            for cmd in commands:
                f.write(cmd + '\n')
        time.sleep(0.3)  # Give Reaper time to process
        return True
    except Exception as e:
        print(f"Error sending commands: {e}")
        return False

def read_feedback():
    """Read execution feedback from Reaper"""
    try:
        time.sleep(0.1)  # Brief delay for Lua to write feedback
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, 'r') as f:
                feedback = f.read().strip()
            os.remove(FEEDBACK_FILE)  # Clear after reading
            return feedback
        return None
    except Exception as e:
        return None

def get_reaper_state():
    """Get current Reaper project state"""
    # Request state export
    send_reaper_commands(["GET_STATE"])
    time.sleep(0.3)  # Give Reaper time to write state
    
    try:
        with open(STATE_FILE, "r") as f:
            return f.read()
    except:
        return "State unavailable"

def load_action_list():
    """Load Reaper action IDs from files"""
    # Load known actions with descriptions (synthetic + curated)
    known_actions = {}
    try:
        # Load synthetic actions
        with open("reaper_actions_synthetic.txt", "r") as f:
            for line in f:
                if "|" in line and not line.startswith("#"):
                    action_id, description = line.strip().split("|", 1)
                    known_actions[action_id] = description
    except:
        pass
    
    try:
        # Also load curated actions (merge/override)
        with open("reaper_actions.txt", "r") as f:
            for line in f:
                if "|" in line:
                    action_id, description = line.strip().split("|", 1)
                    known_actions[action_id] = description
    except:
        pass
    
    # Load ALL numeric action IDs
    all_action_ids = []
    try:
        with open("reaper_all_numeric_actions.txt", "r") as f:
            for line in f:
                action_id = line.strip()
                if action_id:
                    all_action_ids.append(action_id)
    except:
        pass
    
    return known_actions, all_action_ids

def search_relevant_actions(user_input, known_actions, max_results=50):
    """Search for relevant actions based on user input keywords - prioritize core actions"""
    keywords = user_input.lower().split()
    scored_actions = []
    
    # Core action IDs that are always useful (40xxx range = main actions)
    core_action_bonus = 100
    
    for action_id, description in known_actions.items():
        desc_lower = description.lower()
        score = 0
        
        # Bonus for core actions (40000-42000 range)
        if action_id.isdigit() and 40000 <= int(action_id) <= 42000:
            score += core_action_bonus
        
        # Bonus for 1xxx range (transport actions)
        if action_id.isdigit() and 1000 <= int(action_id) <= 2000:
            score += core_action_bonus
        
        # Bonus for simple low numbers (6, 7, 8, etc. are core toggle actions)
        if action_id.isdigit() and int(action_id) < 100:
            score += core_action_bonus
        
        # Penalty for per-track actions (we use SELECT_TRACK instead)
        if "track 0" in desc_lower or "track 1" in desc_lower or "track 2" in desc_lower:
            score -= 50
        
        # Penalty for MIDI CC/OSC only actions
        if "midi cc" in desc_lower or "osc only" in desc_lower:
            score -= 30
        
        # Score based on keyword matches
        for keyword in keywords:
            if keyword in desc_lower:
                # Exact word match
                if keyword in desc_lower.split():
                    score += 20
                else:
                    score += 10
        
        if score > 0:
            scored_actions.append((score, action_id, description))
    
    # Sort by score and return top results
    scored_actions.sort(reverse=True, key=lambda x: x[0])
    return [(aid, desc) for _, aid, desc in scored_actions[:max_results]]

def ask_ai(user_input, debug=False):
    """Ask OpenAI to interpret user's intent for Reaper"""
    
    # Get current Reaper state
    print("📊 Reading Reaper state...")
    state = get_reaper_state()
    
    # Load all available Reaper actions
    known_actions, all_action_ids = load_action_list()
    known_actions_text = "\n".join([f"{aid}: {desc}" for aid, desc in known_actions.items()])
    
    print(f"💪 AI has access to {len(all_action_ids)} total action IDs ({len(known_actions)} with descriptions)")
    
    if debug:
        print("\n=== DEBUG: What AI sees ===")
        print(f"User input: {user_input}")
        print(f"\nKnown actions with descriptions:")
        for aid, desc in list(known_actions.items())[:10]:
            print(f"  {aid}: {desc}")
        print(f"  ... and {len(known_actions)-10} more")
        print(f"\nState snippet:")
        for line in state.split('\n')[:20]:
            print(f"  {line}")
        print("=========================\n")
    
    system_prompt = f"""You are an AI that controls Reaper DAW with FULL PROJECT VISIBILITY.

Like Cursor reads an entire codebase, you can see EVERYTHING about this project before acting.

**COMPLETE PROJECT STATE:**
{state}

**RECENT CONVERSATION HISTORY (last 10):**
{chr(10).join(conversation_history[-10:]) if conversation_history else "No previous commands"}

**CRITICAL INSTRUCTIONS:** 
- READ THE PROJECT STATE COMPLETELY - you can see all tracks, FX chains, parameters, automation, everything
- READ THE CONVERSATION HISTORY - it shows exactly what was done (tracks, time ranges, parameters, values)
- Make INFORMED decisions based on the full context
- For "revert"/"undo"/"bring it back", look at the last action in history and reverse it:
  * If last action was VOL_DIP with value 0.5, revert with value 1.0 on SAME track and time range
  * If last action set FX param to 0.8, revert it to previous value (assume 0.5 if unknown)
  * For other actions, use action 40029 (Undo)
- Use the state above to make informed decisions
- Don't add FX if already present on the track
- Target the correct FX index based on what's loaded
- If track already has the plugin, just adjust its parameters
- When user doesn't specify time range but history shows they were working on a specific range, USE THAT RANGE

**VOLUME/DB RULES:**
- Volume in REAPER is in dB, NOT percentage
- 0dB = unity gain (normal volume)
- -6dB = roughly half volume feel
- -12dB = quiet
- "turn down" means -3 to -6dB, NOT 50%
- Use VOL_DIP with value like 0.7-0.8 for "turn down" (NOT 0.5)
- For "revert" or "undo", use action 40029 (Undo)

**AVAILABLE ACTION IDS:**
You have access to {len(all_action_ids)} total Reaper action IDs.

Core actions with descriptions:
{known_actions_text}

You can also use ANY of these {len(all_action_ids)} numeric action IDs (experiment to find the right ones):
Common ranges: 1000-1999 (transport/playback), 40000-42000 (tracks/items), 65000+ (FX)

When user asks for something not in the core list, intelligently guess which action ID might work based on common Reaper patterns.

**CUSTOM PARAMETRIC COMMANDS** (use for precise control):
VOL_DIP <trackIdx> <tStart> <tEnd> <value0-1> - create volume automation curve
  - value < 1.0 = quieter, value > 1.0 = louder
  - Example: VOL_DIP 0 16 32 0.5 (track 0, 16s→32s, drop to 50%)

SELECT_TRACK <trackIdx> - select a specific track (use before actions that need selection)
  - Example: SELECT_TRACK 1

SET_TRACK_VOL <trackIdx> <volumeDB> - set track volume in dB (works directly, no selection needed)
  - Example: SET_TRACK_VOL 0 0 (set track 0 to 0dB)
  - Example: SET_TRACK_VOL 1 -6 (set track 1 to -6dB)

CLEAR_AUTOMATION <trackIdx> <envelopeName> - remove all automation points (works directly, no selection needed)
  - envelopeName: Volume, Pan, Mute, etc. (default: Volume)
  - Example: CLEAR_AUTOMATION 0 Volume (remove all volume automation from track 0)
  - Example: CLEAR_AUTOMATION 1 Pan (remove pan automation from track 1)

ADD_FX <trackIdx> <pluginName> - add plugin by name and open it
  - Example: ADD_FX 1 ReaEQ

SET_FX_PARAM <trackIdx> <fxIdx> <paramIdx> <value0-1> - set plugin parameter
  - fxIdx: 0=first plugin on track, 1=second, etc.
  - paramIdx: parameter number (0, 1, 2...)
  - Common patterns: Mix often param 0 or last, Gain/Level usually 0-2
  - Example: SET_FX_PARAM 0 0 0 0.7 (track 0, first FX, first param, 70%)

GOTO <seconds> - jump to position
  - Example: GOTO 30

**HOW TO RESPOND:**
- Use action IDs for standard operations (play, mute, add track, envelopes, etc.)
- Use custom commands only for parametric control (automation curves, plugin loading)
- Respond with JSON array of commands (mix action IDs and custom commands)

**Examples:**
User: "play"
Response: ["1007"]

User: "add a track and mute it"  
Response: ["40142", "40294"]

User: "show volume envelope"
Response: ["40406"]

User: "drop volume to 30% from 16 to 32 seconds"
Response: ["VOL_DIP 0 16 32 0.3"]

User: "go to 20 seconds and start recording"
Response: ["GOTO 20", "1013"]

User: "add reverb to track 2"
Response: ["ADD_FX 2 ReaVerb"]

User: "mute track 1, solo track 2, then play"
Response: ["40294", "40280", "1007"]

User: "turn up the mix on the first plugin"
Response: ["SET_FX_PARAM 0 0 0 0.8"]

User: "boost the highs" (assuming EQ is first FX)
Response: ["SET_FX_PARAM 0 0 2 0.7"]

User: "more reverb decay"
Response: ["SET_FX_PARAM 0 0 1 0.8"]

User: "open abbey road and turn up the mix"
Response: ["ADD_FX 0 Abbey Road", "SET_FX_PARAM 0 0 0 0.7"]

User: "turn up the mix" (when state shows Abbey Road is FX 0 on track 0)
Response: ["SET_FX_PARAM 0 0 0 0.8"]

User: "boost the highs" (when state shows ReaEQ is FX 1 on track 0)
Response: ["SET_FX_PARAM 0 1 2 0.7"]

User: "set track 0 volume to 0dB"
Response: ["SET_TRACK_VOL 0 0"]

User: "remove all volume automation from track 0"
Response: ["CLEAR_AUTOMATION 0 Volume"]

User: "make track 1 volume 0db and clear its automation"
Response: ["SET_TRACK_VOL 1 0", "CLEAR_AUTOMATION 1 Volume"]

**HOW TO RESPOND:**
- For INFORMATIONAL questions (what, which, how many), respond with SHORT plain text answer
- For ACTION commands (do something, change something, play, add), respond ONLY with JSON array - NO explanations, NO code blocks, JUST the JSON array

**LEARNING FROM EXPERIENCE:**
- You have 3863 action IDs available - you don't know what most of them do yet
- READ CONVERSATION HISTORY to learn what actions do based on user feedback
- When user says "that worked" or "yes" → remember which action ID you just used
- When user says "wrong" or "didn't work" → avoid that action ID for that purpose
- Build knowledge over time through trial and feedback
- If unsure, try a logical action ID based on patterns (e.g., 40xxx range = track operations, 1xxx = transport)

**KNOWN ACTIONS (learned so far):**
- 1007 = Play
- 1016 = Stop  
- 40280 = TOGGLE solo (flips solo state)
- 40294 = TOGGLE mute (flips mute state)
- 40291 = Show FX chain for touched track (use SELECT_TRACK first)

**CRITICAL - TOGGLE ACTIONS:**
- 40280 and 40294 are TOGGLES - they flip the current state
- BEFORE using toggle, READ THE STATE to see current mute/solo status
- If user says "mute track 7" but state shows "Mute: YES" → don't toggle (already muted!)
- If user says "unmute track 7" but state shows "Mute: no" → don't toggle (already unmuted!)
- Only toggle if the current state is OPPOSITE of what user wants

**CRITICAL RULE - TRACK NUMBERS (THIS IS THE #1 BUG TO FIX):**
- USER'S NUMBER = YOUR NUMBER (NO MATH, NO CONVERSION!)
- User says "track 7" → you write SELECT_TRACK 7 (NOT 6!)
- User says "track 8" → you write SELECT_TRACK 8 (NOT 7!)
- User says "tracks 7 and 8" → you write SELECT_TRACK 7, then SELECT_TRACK 8 (NOT 6 and 7!)
- NEVER subtract 1, NEVER add 1, NEVER do ANY math on track numbers
- Just copy the exact number the user said

**COMMANDS:**
- Many actions require track selection/touch - use SELECT_TRACK first
- Use SET_TRACK_VOL and CLEAR_AUTOMATION for direct track manipulation
- NEVER wrap JSON in code blocks - return raw JSON array only

Examples:
User: "what plugins are on track 1?"
Response: Track 1 has ReaEQ (Cockos) as the first FX.

User: "play from the start"
Response: ["GOTO 0", "1007"]

User: "which track is selected?"
Response: Track 0 is currently selected.

User: "open fx chain for track 1"
Response: ["SELECT_TRACK 1", "40291"]

User: "solo track 8"
Response: ["SELECT_TRACK 8", "40280"]

User: "mute track 2"
Response: ["SELECT_TRACK 2", "40294"]

User: "mute track 2 and add reverb"
Response: ["SELECT_TRACK 2", "40294", "ADD_FX 2 ReaVerb"]

User: "unmute tracks 7 and 8" (when state shows both are muted)
Response: ["SELECT_TRACK 7", "40294", "SELECT_TRACK 8", "40294"]

User: "unmute track 7" (when state shows "Track 7: ... Mute: no")
Response: Track 7 is already unmuted.

User: "mute track 2" (when state shows "Track 2: ... Mute: YES")
Response: Track 2 is already muted."""

    # Log prompt to file for debugging
    with open("last_prompt.txt", "w", encoding="utf-8") as f:
        f.write(f"=== USER INPUT ===\n{user_input}\n\n")
        f.write(f"=== SYSTEM PROMPT (first 2000 chars) ===\n{system_prompt[:2000]}\n\n")
    
    # GPT-5 uses Responses API, not Chat Completions
    response = client.responses.create(
        model="gpt-5",
        input=f"{system_prompt}\n\nUser: {user_input}",
        reasoning={"effort": "medium"},  # medium = good balance for agentic tasks
        text={"verbosity": "low"}  # low = concise, less hallucination
    )
    
    # Log response
    with open("last_prompt.txt", "a", encoding="utf-8") as f:
        f.write(f"=== AI RESPONSE ===\n{response.output_text}\n")
    
    return response.output_text.strip()

def execute_user_command(user_input):
    """Main function: take user input, get AI decision, execute commands"""
    print(f"\n🎤 User: {user_input}")
    
    # Get current state for validation
    print("📊 Reading Reaper state...")
    current_state = get_reaper_state()
    _debug_write("====== NEW TURN ======")
    _debug_write(f"USER: {user_input}")
    _debug_write("STATE (first 20 lines):")
    for ln in current_state.split("\n")[:20]:
        _debug_write(ln)
    
    # Ask AI what to do
    print("🤖 Asking AI...")
    ai_response = ask_ai(user_input, debug=True)  # Enable debug to see what AI sees
    print(f"💭 AI response: {ai_response}")
    _debug_write(f"AI RAW: {ai_response}")
    
    # Parse AI response - could be JSON (commands) or text (info)
    # Strip code blocks if AI wrapped it despite instructions
    response_clean = ai_response.strip()
    if response_clean.startswith("```"):
        # Remove code block markers
        response_clean = response_clean.split("```")[1]
        if response_clean.startswith("json"):
            response_clean = response_clean[4:]
        response_clean = response_clean.strip()
    
    try:
        commands = json.loads(response_clean)
        if not isinstance(commands, list):
            commands = [commands]
        
        # Execute commands
        print(f"\n⚡ Sending {len(commands)} command(s) to Reaper...")
        _debug_write(f"COMMANDS: {commands}")
        known_actions, _ = load_action_list()
        for i, cmd in enumerate(commands, 1):
            # Show friendly name for action IDs
            if cmd.isdigit():
                desc = known_actions.get(cmd, "Unknown action")
                print(f"  {i}. Action {cmd}: {desc}")
            else:
                print(f"  {i}. {cmd}")
        
        success = send_reaper_commands(commands, current_state)
        
        if success:
            print("✅ Commands sent to Reaper")
            
            # Read feedback from Reaper
            feedback = read_feedback()
            if feedback:
                print("\n📋 Reaper feedback:")
                for line in feedback.split('\n'):
                    print(f"   {line}")
            
            # Add detailed context to conversation history
            cmd_details = []
            for cmd in commands:
                if cmd.startswith("VOL_DIP"):
                    parts = cmd.split()
                    cmd_details.append(f"Modified volume on track {parts[1]} from {parts[2]}s to {parts[3]}s at {float(parts[4])*100:.0f}%")
                elif cmd.startswith("SELECT_TRACK"):
                    parts = cmd.split()
                    cmd_details.append(f"Selected track {parts[1]}")
                elif cmd.startswith("SET_TRACK_VOL"):
                    parts = cmd.split()
                    cmd_details.append(f"Set track {parts[1]} volume to {parts[2]}dB")
                elif cmd.startswith("CLEAR_AUTOMATION"):
                    parts = cmd.split()
                    env_name = parts[2] if len(parts) > 2 else "Volume"
                    cmd_details.append(f"Cleared {env_name} automation on track {parts[1]}")
                elif cmd.startswith("SET_FX_PARAM"):
                    parts = cmd.split()
                    cmd_details.append(f"Set FX#{parts[2]} param {parts[3]} to {float(parts[4])*100:.0f}% on track {parts[1]}")
                elif cmd.startswith("ADD_FX"):
                    parts = cmd.split()
                    plugin_name = " ".join(parts[2:])
                    cmd_details.append(f"Added plugin '{plugin_name}' to track {parts[1]}")
                else:
                    cmd_details.append(f"Action {cmd}")
            
            history_entry = f"User: '{user_input}' → {' + '.join(cmd_details)}"
            conversation_history.append(history_entry)
            save_memory()  # Save after each command
        else:
            print("❌ Failed to send commands")
    except json.JSONDecodeError:
        # Not JSON - it's an informational response
        print(f"\n🤖 {ai_response}")
        # Save the conversation
        history_entry = f"User: '{user_input}' -> AI answered: {ai_response}"
        conversation_history.append(history_entry)
        save_memory()
        print("\n✨ Done!\n")
        return
    
    print("\n✨ Done!\n")

# Run it
if __name__ == "__main__":
    print("=" * 60)
    print("AI Agent for Reaper DAW - Full Context Mode")
    print("=" * 60)
    print("\nMake sure:")
    print("1. Reaper is running")
    print("2. reaper_agent.lua is loaded and running in Reaper")
    print("   (Actions → Load ReaScript → select reaper_agent.lua)")
    print("=" * 60)
    
    # Load persistent memory from previous sessions
    load_memory()
    
    print("\n✨ Ready! AI has full project visibility (like Cursor)\n")
    
    # Interactive mode - just type what you want
    while True:
        user_input = input("\n💬 You: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        execute_user_command(user_input)

