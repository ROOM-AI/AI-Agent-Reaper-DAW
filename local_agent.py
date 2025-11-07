import json
import time
import os
import re
import shutil
import numpy as np
import heapq
from pathlib import Path
from contextlib import contextmanager
from anthropic import Anthropic
from openai import OpenAI
from scipy.spatial.distance import cosine, euclidean

# -------------------- Cloud hook support --------------------
_CLOUD_STATE_PROVIDER = None  # callable(session_id) -> str state_text
_CLOUD_COMMAND_SINK = None    # callable(commands: List[str] | str, session_id) -> bool
_CLOUD_FEEDBACK_PROVIDER = None  # callable(session_id) -> str
_CLOUD_MEMORY_LOAD = None     # callable(session_id) -> dict
_CLOUD_MEMORY_SAVE = None     # callable(session_id, data: dict) -> bool
_CURRENT_SESSION_ID = "demo"

def set_cloud_hooks(
    state_provider=None,
    command_sink=None,
    feedback_provider=None,
    memory_load=None,
    memory_save=None,
):
    """Inject cloud I/O hooks so the real agent can run in server context"""
    global _CLOUD_STATE_PROVIDER, _CLOUD_COMMAND_SINK, _CLOUD_FEEDBACK_PROVIDER
    global _CLOUD_MEMORY_LOAD, _CLOUD_MEMORY_SAVE
    _CLOUD_STATE_PROVIDER = state_provider or _CLOUD_STATE_PROVIDER
    _CLOUD_COMMAND_SINK = command_sink or _CLOUD_COMMAND_SINK
    _CLOUD_FEEDBACK_PROVIDER = feedback_provider or _CLOUD_FEEDBACK_PROVIDER
    _CLOUD_MEMORY_LOAD = memory_load or _CLOUD_MEMORY_LOAD
    _CLOUD_MEMORY_SAVE = memory_save or _CLOUD_MEMORY_SAVE

def set_current_session(session_id: str):
    """Set the active session id for cloud hook calls"""
    global _CURRENT_SESSION_ID
    _CURRENT_SESSION_ID = session_id or "demo"

# Clipboard for auto-copying enhanced prompts
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

# Audio analysis imports (install with: pip install librosa soundfile)
try:
    import librosa
    import soundfile as sf
    AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    AUDIO_ANALYSIS_AVAILABLE = False
    print("⚠️ Audio analysis disabled - install: pip install librosa soundfile")

# Essentia for advanced effect detection (optional)
try:
    import essentia.standard as es
    ESSENTIA_AVAILABLE = True
    print("✅ Essentia loaded - enhanced effect detection ready")
except ImportError:
    ESSENTIA_AVAILABLE = False
    # Don't print warning - it's optional

# PANNs for audio type classification (best accuracy)
PANNS_AVAILABLE = False
panns_model = None

try:
    from panns_inference import AudioTagging
    import torch
    import urllib.request
    
    # Create panns_data directory and download files FIRST
    panns_dir = Path.home() / "panns_data"
    panns_dir.mkdir(exist_ok=True)
    
    # Download class labels if missing
    class_labels_path = panns_dir / "class_labels_indices.csv"
    if not class_labels_path.exists():
        print("📥 Downloading PANNs class labels...")
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/qiuqiangkong/audioset_tagging_cnn/master/metadata/class_labels_indices.csv",
            str(class_labels_path)
        )
        print("✅ Class labels downloaded")
    
    # Now load the model
    print("🎯 Loading PANNs audio classification model (may download ~80MB first time)...")
    panns_model = AudioTagging(checkpoint_path=None, device='cuda' if torch.cuda.is_available() else 'cpu')
    PANNS_AVAILABLE = True
    print("✅ PANNs loaded - accurate audio type classification ready")
    
except ImportError:
    print("⚠️ PANNs not available - install: pip install panns-inference torch")
except Exception as e:
    print(f"⚠️ PANNs load failed: {e}")
    print(f"   Continuing without PANNs - will use librosa fallback for classification")

# CLAP and MERT removed - using pure librosa analysis
# Agent will reason about audio using librosa data in JSON format
CLAP_AVAILABLE = False

# MERT removed - using pure librosa analysis instead
MERT_AVAILABLE = False

# Initialize API clients
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", "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"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "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"))

# Parameter conversion helpers
def db_to_normalized(target_db, min_db=-30, max_db=30):
    """Convert dB value to normalized 0-1 range"""
    return (target_db - min_db) / (max_db - min_db)

def normalized_to_db(normalized, min_db=-30, max_db=30):
    """Convert normalized 0-1 value to dB"""
    return min_db + (normalized * (max_db - min_db))

COMMAND_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_commands.txt"
STATE_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_state.txt"
MEMORY_FILE = r"C:\Users\moosb\AIAGENT DAW\agent_memory.txt"
FEEDBACK_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_feedback.txt"
DEBUG_LOG_FILE = r"C:\Users\moosb\AIAGENT DAW\agent_debug.log"
KNOWLEDGE_BASE_FILE = r"C:\Users\moosb\AIAGENT DAW\sound_knowledge_base.json"
USER_PREFERENCES_FILE = r"C:\Users\moosb\AIAGENT DAW\user_preferences.json"
LYRICS_CACHE_DIR = r"C:\Users\moosb\AIAGENT DAW\lyrics_cache"
TEMP_AUDIO_DIR = r"C:\Users\moosb\AIAGENT DAW\temp_audio"
STATE_HISTORY_FILE = r"C:\Users\moosb\AIAGENT DAW\state_history.json"
REFERENCE_AUDIO_DIR = r"C:\Users\moosb\AIAGENT DAW\references"
STRUCTURED_MEMORY_FILE = r"C:\Users\moosb\AIAGENT DAW\structured_memory.json"

# Production terms for CLAP semantic matching
PRODUCTION_TERMS = [
    # Saturation/Distortion
    "tape saturation warmth",
    "tube saturation vintage",
    "heavy distortion aggressive",
    "light overdrive gritty",
    "clean transparent no saturation",
    "analog warmth subtle distortion",
    "fuzzy distortion rock",
    "crunchy saturation bluesy",
    "bitcrusher lo-fi distortion",
    "harmonic exciter enhancement",
    
    # Reverb/Space
    "hall reverb large space",
    "plate reverb bright metallic",
    "room reverb intimate close",
    "spring reverb twangy vintage",
    "dry no reverb tight",
    "cathedral reverb epic ambient",
    "chamber reverb smooth",
    "reverse reverb dreamy",
    "gated reverb punchy",
    "shimmer reverb ethereal",
    
    # Compression
    "heavily compressed punchy attack",
    "moderately compressed controlled dynamics",
    "natural dynamics uncompressed open",
    "parallel compression blended",
    "multiband compression balanced",
    "optical compression smooth vintage",
    "fet compression aggressive fast",
    "limiter brickwall loud",
    "expander noise reduction",
    "sidechain compression pumping",
    
    # Tone/EQ
    "bright crispy high end sparkle",
    "dark moody low end rumble",
    "warm rich midrange presence",
    "muddy low mids cluttered",
    "airy open high frequencies",
    "boomy bass heavy",
    "harsh piercing highs",
    "smooth silky balanced tone",
    "vintage eq colored",
    "parametric eq precise cuts",
    
    # Auto-tune/Pitch
    "heavy auto-tune robotic effect",
    "subtle auto-tune natural correction",
    "no pitch correction organic raw",
    "hard tuned t-pain style",
    "vibrato heavy emotional",
    "pitch shift up octave bright",
    "pitch shift down deep",
    "formant shift alien voice",
    "harmony layer added",
    "detune chorus thick",
    
    # Delay/Echo
    "slapback delay rockabilly",
    "ping pong delay stereo wide",
    "long delay ambient trails",
    "short delay thickening",
    "no delay direct",
    "tape delay warped vintage",
    "digital delay clean repeats",
    "analog delay warm degradation",
    "reverse delay psychedelic",
    "modulated delay chorus-like",
    
    # Modulation Effects
    "chorus shimmering watery",
    "flanger jet whoosh",
    "phaser swirling psychedelic",
    "tremolo volume pulsing",
    "vibrato pitch wobble",
    "rotary speaker leslie organ",
    "no modulation static",
    "wah wah filter funky",
    "ring modulator metallic robotic",
    "ensemble multi-chorus thick",
    
    # Other Production Styles
    "lo-fi vintage crackle",
    "hi-fi crystal clear modern",
    "aggressive loud rock",
    "chill relaxed ambient",
    "punchy rhythmic dance",
    "ethereal dreamy synth",
    "gritty urban hip-hop",
    "acoustic natural folk",
    "electronic synthetic beep",
    "vocal forward intimate",
    "instrumental layered complex",
    "minimalist sparse clean",
    "orchestral grand symphonic",
    "distorted industrial noise",
    "harmonically rich overtones",
    "transient sharp attack",
    "sustained long decay",
    "stereo wide imaging",
    "mono centered focused",
    "processed effected heavily"
]

# Semantic production knowledge base
SEMANTIC_KNOWLEDGE_BASE = {
    "tape saturation warmth": {
        "description": "Adds harmonic richness and low-mid presence",
        "plugins": ["Saturn 2"],
        "settings": {"Saturn 2": {"drive": 0.35, "mode": "tape"}},
        "priority": "high",
        "conflicts": ["clean transparent no saturation", "bright crispy high end sparkle"]
    },
    "tube saturation vintage": {
        "description": "Vintage tube warmth",
        "plugins": ["Saturn 2"],
        "settings": {"Saturn 2": {"drive": 0.4, "mode": "tube"}},
        "priority": "high",
        "conflicts": ["clean transparent no saturation"]
    },
    "heavy distortion aggressive": {
        "description": "Aggressive distortion",
        "plugins": ["Saturn 2"],
        "settings": {"Saturn 2": {"drive": 0.7, "mode": "distortion"}},
        "priority": "medium",
        "conflicts": ["clean transparent no saturation"]
    },
    "hall reverb large space": {
        "description": "Large spacious reverb",
        "plugins": ["Valhalla VintageVerb"],
        "settings": {"Valhalla VintageVerb": {"decay": 0.75, "mix": 0.35, "type": "hall"}},
        "priority": "medium",
        "conflicts": ["dry no reverb tight"]
    },
    "plate reverb bright metallic": {
        "description": "Bright plate reverb",
        "plugins": ["Valhalla VintageVerb"],
        "settings": {"Valhalla VintageVerb": {"decay": 0.6, "mix": 0.3, "type": "plate"}},
        "priority": "medium",
        "conflicts": ["dry no reverb tight"]
    },
    "heavily compressed punchy attack": {
        "description": "Punchy compression",
        "plugins": ["ReaComp"],
        "settings": {"ReaComp": {"ratio": 0.6, "threshold": 0.65}},
        "priority": "high",
        "conflicts": ["natural dynamics uncompressed open"]
    },
    "bright crispy high end sparkle": {
        "description": "Bright high end",
        "plugins": ["Pro-Q 3"],
        "settings": {"Pro-Q 3": {"boost_10khz": 3.0}},
        "priority": "high",
        "conflicts": ["dark moody low end rumble", "tape saturation warmth"]
    },
    "dark moody low end rumble": {
        "description": "Dark with enhanced low end",
        "plugins": ["Pro-Q 3"],
        "settings": {"Pro-Q 3": {"boost_100hz": 4.0, "cut_8khz": -3.0}},
        "priority": "high",
        "conflicts": ["bright crispy high end sparkle"]
    },
    "warm rich midrange presence": {
        "description": "Warm midrange boost",
        "plugins": ["Pro-Q 3"],
        "settings": {"Pro-Q 3": {"boost_800hz": 2.5}},
        "priority": "high",
        "conflicts": []
    },
    "heavy auto-tune robotic effect": {
        "description": "Robotic auto-tune",
        "plugins": ["Auto-Tune Pro"],
        "settings": {"Auto-Tune Pro": {"retune_speed": 0.1, "humanize": 0.0}},
        "priority": "medium",
        "conflicts": ["no pitch correction organic raw"]
    },
    "dry no reverb tight": {
        "description": "No reverb, tight and dry",
        "plugins": [],
        "settings": {},
        "priority": "low",
        "conflicts": ["hall reverb large space", "plate reverb bright metallic"]
    },
    "clean transparent no saturation": {
        "description": "Clean unprocessed signal",
        "plugins": [],
        "settings": {},
        "priority": "low",
        "conflicts": ["tape saturation warmth", "tube saturation vintage", "heavy distortion aggressive"]
    }
}

conversation_history = []
sound_knowledge = None
user_preferences = None
lyrics_cache = {}
state_history = []  # Stores state snapshots for revert functionality

def log_debug(message):
    """Write debug info to file"""
    try:
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except:
        pass


@contextmanager
def open_file_when_ready(path, mode='rb', timeout=15.0, poll_interval=0.5):
    """Wait until a file can be opened, yielding the handle and wait duration."""
    start_time = time.time()
    last_error = None
    target_path = Path(path)

    while time.time() - start_time < timeout:
        if target_path.exists():
            try:
                file_obj = open(target_path, mode)
                waited = time.time() - start_time
                try:
                    yield file_obj, waited
                finally:
                    file_obj.close()
                return
            except (PermissionError, OSError) as err:
                last_error = err
        else:
            last_error = FileNotFoundError(f"File not found: {target_path}")
        time.sleep(poll_interval)

    if last_error:
        raise TimeoutError(f"File not readable after {timeout}s: {target_path}") from last_error
    raise TimeoutError(f"File not readable after {timeout}s: {target_path}")


def load_sound_knowledge():
    """Load sound design knowledge base"""
    global sound_knowledge
    try:
        with open(KNOWLEDGE_BASE_FILE, "r", encoding="utf-8") as f:
            sound_knowledge = json.load(f)
        print(f"🎨 Loaded sound knowledge base")
    except Exception as e:
        print(f"⚠️ Couldn't load sound knowledge: {e}")
        sound_knowledge = None

def load_user_preferences():
    """Load user's plugin preferences and workflow rules"""
    global user_preferences
    try:
        with open(USER_PREFERENCES_FILE, "r", encoding="utf-8") as f:
            user_preferences = json.load(f)
        print(f"⚙️ Loaded user preferences")
    except Exception as e:
        print(f"⚠️ Couldn't load user preferences: {e}")
        user_preferences = None

def load_memory():
    global conversation_history
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            conversation_history = [line.strip() for line in f if line.strip()]
        print(f"📚 Loaded {len(conversation_history)} past interactions")
    except:
        print("📚 Starting fresh memory")
        conversation_history = []

def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            for entry in conversation_history[-50:]:
                f.write(entry + "\n")
    except Exception as e:
        print(f"⚠️ Couldn't save memory: {e}")

# Structured memory for learning
structured_memory = []

def load_structured_memory():
    """Load structured memory from file"""
    global structured_memory
    try:
        if Path(STRUCTURED_MEMORY_FILE).exists():
            with open(STRUCTURED_MEMORY_FILE, "r") as f:
                structured_memory = json.load(f)
                log_debug(f"Loaded {len(structured_memory)} structured memory entries")
    except Exception as e:
        log_debug(f"Failed to load structured memory: {e}")
        structured_memory = []

def save_structured_memory_entry(goal, success, actions_tried, final_outcome, failed_action_ids):
    """Save a structured memory entry for learning"""
    global structured_memory
    
    entry = {
        "timestamp": time.time(),
        "goal": goal,
        "success": success,
        "actions_tried": actions_tried,
        "final_outcome": final_outcome,
        "failed_action_ids": failed_action_ids,
        "retry_count": len(actions_tried)
    }
    
    structured_memory.append(entry)
    
    # Keep only last 100 entries (prevent file from growing too large)
    if len(structured_memory) > 100:
        structured_memory = structured_memory[-100:]
    
    try:
        with open(STRUCTURED_MEMORY_FILE, "w") as f:
            json.dump(structured_memory, f, indent=2)
        log_debug(f"Saved structured memory entry: {goal[:50]}... (success={success})")
    except Exception as e:
        log_debug(f"Failed to save structured memory: {e}")

def get_relevant_memory(user_goal):
    """Get relevant past experiences for current goal"""
    if not structured_memory:
        return ""
    
    # Simple keyword matching for now (could be enhanced with embeddings)
    goal_lower = user_goal.lower()
    goal_keywords = set(goal_lower.split())
    
    relevant_entries = []
    for entry in structured_memory[-20:]:  # Check last 20 entries
        entry_keywords = set(entry['goal'].lower().split())
        overlap = len(goal_keywords & entry_keywords)
        
        if overlap >= 2:  # At least 2 keywords match
            relevant_entries.append({
                "goal": entry['goal'],
                "success": entry['success'],
                "outcome": entry['final_outcome'],
                "failed_actions": entry['failed_action_ids']
            })
    
    if not relevant_entries:
        return ""
    
    memory_text = "\n**RELEVANT PAST EXPERIENCES:**\n"
    for i, entry in enumerate(relevant_entries[-3:], 1):  # Show max 3 most recent
        status = "✓ SUCCESS" if entry['success'] else "✗ FAILED"
        memory_text += f"{i}. Similar goal: '{entry['goal']}' → {status}\n"
        memory_text += f"   Outcome: {entry['outcome'][:100]}\n"
        if entry['failed_actions']:
            memory_text += f"   Failed actions: {', '.join(entry['failed_actions'][:5])}\n"
    
    memory_text += "\n**USE THIS:** Learn from past successes/failures. Don't repeat failed actions.\n"
    return memory_text

def load_state_history():
    """Load state snapshot history from file"""
    global state_history
    try:
        with open(STATE_HISTORY_FILE, "r", encoding="utf-8") as f:
            state_history = json.load(f)
        print(f"📸 Loaded {len(state_history)} state snapshots")
    except:
        state_history = []

def save_state_history():
    """Save state snapshot history to file (keep last 20)"""
    try:
        with open(STATE_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(state_history[-20:], f, indent=2)
    except Exception as e:
        print(f"⚠️ Couldn't save state history: {e}")

def save_state_snapshot(label=""):
    """Save current Reaper state as a snapshot"""
    current_state = get_reaper_state()
    if current_state == "State unavailable":
        return False
    
    snapshot = {
        "timestamp": time.time(),
        "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "label": label,
        "state": current_state
    }
    
    state_history.append(snapshot)
    save_state_history()
    log_debug(f"Snapshot saved: {label}")
    return True

def list_snapshots():
    """List available state snapshots"""
    if not state_history:
        return "No snapshots available"
    
    result = "📸 Available snapshots:\n"
    for i, snapshot in enumerate(reversed(state_history), 1):
        result += f"{i}. {snapshot['time_str']} - {snapshot['label']}\n"
    return result

def revert_to_snapshot(index=-1):
    """Revert to a previous snapshot (default: last one)
    index: -1 for last, -2 for second to last, or positive index from list_snapshots()
    """
    if not state_history:
        return False, "No snapshots to revert to"
    
    try:
        # Convert positive index (from user's perspective) to negative index
        if index > 0:
            index = -index
        
        snapshot = state_history[index]
        target_state = snapshot['state']
        current_state = get_reaper_state()
        
        if current_state == "State unavailable":
            return False, "Cannot read current state"
        
        # Generate commands to restore state
        commands = generate_revert_commands(current_state, target_state)
        
        if not commands:
            return True, f"State already matches snapshot '{snapshot['label']}'"
        
        # Execute revert commands
        if send_reaper_commands(commands):
            return True, f"Reverted to snapshot: {snapshot['label']} ({snapshot['time_str']})"
        else:
            return False, "Failed to send revert commands"
            
    except IndexError:
        return False, f"Snapshot index {index} not found"
    except Exception as e:
        return False, f"Error reverting: {e}"

def generate_revert_commands(current_state, target_state):
    """Generate commands to transform current_state into target_state"""
    commands = []
    
    # Parse both states to find differences
    # Look for FX parameter changes
    current_params = parse_fx_params(current_state)
    target_params = parse_fx_params(target_state)
    
    # Generate SET_FX_PARAM commands for changed parameters
    for (track, fx, param), target_value in target_params.items():
        current_value = current_params.get((track, fx, param))
        if current_value != target_value:
            # Convert percentage string back to normalized value
            if isinstance(target_value, str) and '%' in target_value:
                normalized = float(target_value.rstrip('%')) / 100.0
            else:
                normalized = target_value
            commands.append(f"SET_FX_PARAM {track} {fx} {param} {normalized}")
    
    # Look for removed FX (in current but not in target)
    current_fx_list = parse_fx_list(current_state)
    target_fx_list = parse_fx_list(target_state)
    
    for track, fx_index, fx_name in current_fx_list:
        if (track, fx_index, fx_name) not in target_fx_list:
            commands.append(f"REMOVE_FX {track} {fx_index}")
    
    # Look for added FX (in target but not in current) - these need to be re-added
    for track, fx_index, fx_name in target_fx_list:
        if (track, fx_index, fx_name) not in current_fx_list:
            commands.append(f"ADD_FX {track} {fx_name}")
    
    return commands

def parse_fx_params(state):
    """Extract FX parameters from state string"""
    params = {}
    current_track = None
    current_fx = None
    
    for line in state.split('\n'):
        # Track line: --- Track 0: name ---
        track_match = re.match(r'--- Track (\d+):', line)
        if track_match:
            current_track = int(track_match.group(1))
            current_fx = None
            continue
        
        # FX line: [0] FX Name
        fx_match = re.match(r'\s*\[(\d+)\]\s+(.+)', line)
        if fx_match and current_track is not None:
            current_fx = int(fx_match.group(1))
            continue
        
        # Parameter line: p0: ParamName = 50% [Description]
        param_match = re.match(r'\s*p(\d+):\s+[^=]+=\s+([^\[]+)', line)
        if param_match and current_track is not None and current_fx is not None:
            param_num = int(param_match.group(1))
            param_value = param_match.group(2).strip()
            params[(current_track, current_fx, param_num)] = param_value
    
    return params

def parse_fx_list(state):
    """Extract FX list from state string"""
    fx_list = []
    current_track = None
    
    for line in state.split('\n'):
        # Track line
        track_match = re.match(r'--- Track (\d+):', line)
        if track_match:
            current_track = int(track_match.group(1))
            continue
        
        # FX line: [0] FX Name
        fx_match = re.match(r'\s*\[(\d+)\]\s+(.+)', line)
        if fx_match and current_track is not None:
            fx_index = int(fx_match.group(1))
            fx_name = fx_match.group(2).strip()
            fx_list.append((current_track, fx_index, fx_name))
    
    return fx_list

def send_reaper_commands(commands):
    """Send commands to Reaper (cloud-aware)"""
    # Cloud hook path
    if _CLOUD_COMMAND_SINK is not None:
        try:
            if not isinstance(commands, list):
                commands = [commands]
            return _CLOUD_COMMAND_SINK(commands, _CURRENT_SESSION_ID)
        except Exception:
            return False
    
    # Local file path
    try:
        with open(COMMAND_FILE, 'w') as f:
            for cmd in commands:
                f.write(cmd + '\n')
        time.sleep(0.3)
        log_debug(f"Sent: {commands}")
        return True
    except Exception as e:
        log_debug(f"Send error: {e}")
        return False

def get_reaper_state():
    """Get current Reaper state (cloud-aware)"""
    # Cloud hook path
    if _CLOUD_STATE_PROVIDER is not None:
        try:
            state_text = _CLOUD_STATE_PROVIDER(_CURRENT_SESSION_ID)
            return state_text if isinstance(state_text, str) else str(state_text)
        except Exception:
            return "State unavailable"
    
    # Local file path
    if not send_reaper_commands(["GET_STATE"]):
        return "State unavailable"
    time.sleep(0.3)
    try:
        with open(STATE_FILE, "r") as f:
            return f.read()
    except:
        return "State unavailable"

def get_reaper_feedback():
    """Read feedback from Reaper about last command execution"""
    try:
        with open(FEEDBACK_FILE, "r") as f:
            feedback = f.read().strip()
            if feedback:
                log_debug(f"Feedback: {feedback}")
                return feedback
            return "No feedback available"
    except:
        return "No feedback available"

def clear_reaper_feedback():
    """Clear feedback file to prevent stale feedback on retries"""
    try:
        with open(FEEDBACK_FILE, "w") as f:
            f.write("")
        log_debug("Cleared feedback file")
    except Exception as e:
        log_debug(f"Failed to clear feedback: {e}")

SUCCESS_TOKENS = (
    "✓",
    "✅",
    "Success",
    "Added FX",
    "Set param",
    "VOL_DIP",
    "CLEARED AUTOMATION",
    "APPLY_FROM_JSON",
)

def feedback_contains_success(feedback_text: str) -> bool:
    """Return True if feedback clearly indicates success"""
    if not feedback_text:
        return False
    for token in SUCCESS_TOKENS:
        if token in feedback_text:
            return True
    return False

def sanity_check_actions(user_goal, planned_steps, known_actions):
    """
    Check if planned actions are semantically related to user's goal.
    Prevents agent from trying random unrelated actions when desperate.
    
    Returns: (filtered_steps, rejected_steps)
    """
    if not planned_steps:
        return [], []
    
    # Build summary of what each step does
    steps_summary = []
    for i, step in enumerate(planned_steps, 1):
        cmd = step.get('command', '')
        desc = step.get('description', '')
        
        # Get action description if it's an action ID
        if cmd.strip().isdigit():
            action_desc = known_actions.get(cmd.strip(), 'Unknown action')
            steps_summary.append(f"{i}. {desc} (action {cmd}: {action_desc})")
        else:
            steps_summary.append(f"{i}. {desc} (command: {cmd})")
    
    steps_text = "\n".join(steps_summary)
    
    # Ask Claude to sanity check
    prompt = f"""You are a sanity checker for a DAW automation agent. Check if planned actions are relevant to the user's goal.

**USER'S GOAL:** {user_goal}

**PLANNED ACTIONS:**
{steps_text}

**YOUR JOB:** For each action, determine if it's RELEVANT to the goal or IRRELEVANT/RANDOM.

**EXAMPLES OF GOOD vs BAD:**
- Goal: "delete envelope on track 3" + Action: "Show envelope then delete points" → RELEVANT ✓
- Goal: "delete envelope on track 3" + Action: "Open VST plugin" → IRRELEVANT ✗
- Goal: "delete envelope on track 3" + Action: "Mute track" → IRRELEVANT ✗
- Goal: "add reverb" + Action: "Add reverb plugin" → RELEVANT ✓
- Goal: "add reverb" + Action: "Toggle record arming" → IRRELEVANT ✗

**CRITICAL RULES:**
1. An action is RELEVANT only if it directly helps achieve the goal
2. Random UI actions (mute, solo, record, view FX chain) are NOT relevant to automation/plugin tasks
3. Be strict - "might help" = IRRELEVANT

**OUTPUT ONLY THIS JSON:**
{{{{
  "relevant_indices": [1, 2, 3],
  "irrelevant_indices": [4, 5],
  "reasoning": "Brief explanation why some were rejected"
}}}}"""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text.strip()
        
        # Parse response
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        result = json.loads(response)
        relevant_indices = set(result.get("relevant_indices", []))
        irrelevant_indices = set(result.get("irrelevant_indices", []))
        reasoning = result.get("reasoning", "")
        
        # Filter steps
        filtered_steps = []
        rejected_steps = []
        
        for i, step in enumerate(planned_steps, 1):
            if i in relevant_indices:
                filtered_steps.append(step)
            elif i in irrelevant_indices:
                rejected_steps.append(step)
            else:
                # If unclear, keep it (benefit of doubt)
                filtered_steps.append(step)
        
        if rejected_steps:
            log_debug(f"Sanity check rejected {len(rejected_steps)} actions: {reasoning}")
            print(f"🛡️ Sanity check: Rejected {len(rejected_steps)} unrelated actions")
            print(f"   Reason: {reasoning}")
        
        return filtered_steps, rejected_steps
        
    except Exception as e:
        log_debug(f"Sanity check failed: {e}")
        # On error, return all steps (don't block execution)
        return planned_steps, []

def load_action_list():
    """Load complete action database (6,309 actions!)"""
    known_actions = {}
    try:
        # Try current directory first, then fallback to old path
        action_file = Path("reaper_actions.txt")
        if not action_file.exists():
            action_file = Path(r"C:\Users\moosb\AIAGENT DAW\reaper_actions.txt")
        with open(action_file, "r", encoding="utf-8") as f:
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
        log_debug(f"Loaded {len(known_actions)} actions")
    except Exception as e:
        log_debug(f"Action load error: {e}")
    
    return known_actions

def load_plugin_list():
    """Load available plugins from Reaper with robust path fallbacks"""
    plugins = []
    used_path = None

    env_override = os.getenv("REAPER_AGENT_PLUGIN_DB")
    resource_path = os.getenv("REAPER_RESOURCE_PATH")
    here = Path(__file__).resolve().parent

    candidate_paths = [
        env_override,
        Path("reaper_plugins_list.txt"),
        here / "reaper_plugins_list.txt",
        Path.cwd() / "reaper_plugins_list.txt",
        Path(r"C:\Users\moosb\AIAGENT DAW\reaper_plugins_list.txt"),
    ]

    if resource_path:
        candidate_paths.append(Path(resource_path) / "reaper_plugins_list.txt")

    for candidate in candidate_paths:
        if not candidate:
            continue
        candidate_path = Path(candidate)
        if candidate_path.is_file() and candidate_path.stat().st_size > 0:
            try:
                with open(candidate_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("==="):
                            continue
                        if line in ("Video processor", "Container"):
                            continue
                        if line.startswith("ReWire:"):
                            continue
                        plugins.append(line)
                used_path = candidate_path
                break
            except Exception as read_error:
                log_debug(f"Plugin load error from {candidate_path}: {read_error}")

    if plugins:
        log_debug(f"Loaded {len(plugins)} plugins from {used_path}")
    else:
        log_debug("Plugin load warning: no plugins found in any known location")

    return plugins

def analyze_lyrics(track_idx, track_name):
    """Analyze vocals with Whisper API, return word timestamps"""
    global lyrics_cache
    
    # Check cache first
    if track_name in lyrics_cache:
        print(f"📝 Using cached lyrics for '{track_name}'")
        return lyrics_cache[track_name]
    
    # Check file cache
    Path(LYRICS_CACHE_DIR).mkdir(exist_ok=True)
    cache_file = Path(LYRICS_CACHE_DIR) / f"{track_name}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                lyrics_cache[track_name] = data['lyrics']
                print(f"📝 Loaded cached lyrics for '{track_name}'")
                return data['lyrics']
        except:
            pass
    
    # Export audio from Reaper
    Path(TEMP_AUDIO_DIR).mkdir(exist_ok=True)
    # Reaper exports to a FOLDER with project_name.wav inside
    temp_audio_folder = Path(TEMP_AUDIO_DIR) / f"track_{track_idx}_{int(time.time())}"
    
    print(f"📤 Exporting track {track_idx} audio...")
    if not send_reaper_commands([f"EXPORT_AUDIO {track_idx} {temp_audio_folder}"]):
        print("❌ Failed to export audio")
        return []

    # Wait for folder to be created and find the .wav file inside
    wait_timeout = 30.0
    poll_interval = 0.5
    start_time = time.time()
    temp_audio = None
    
    while time.time() - start_time < wait_timeout:
        if temp_audio_folder.exists():
            # Find any .wav file in the folder
            wav_files = list(temp_audio_folder.glob("*.wav"))
            if wav_files:
                temp_audio = wav_files[0]
                print(f"✅ Found exported audio: {temp_audio.name}")
                break
        time.sleep(poll_interval)
    
    if not temp_audio or not temp_audio.exists():
        print(f"❌ No WAV file found in export folder after {wait_timeout}s")
        return []

    # Check file size - if > 24MB, need to chunk it
    file_size_mb = temp_audio.stat().st_size / (1024 * 1024)
    MAX_SIZE_MB = 24  # Leave buffer under 25MB limit
    
    try:
        lyrics_data = []
        
        if file_size_mb > MAX_SIZE_MB:
            print(f"📦 File is {file_size_mb:.1f}MB (over {MAX_SIZE_MB}MB limit) - splitting into chunks...")
            
            # Load audio with librosa
            audio, sr = librosa.load(str(temp_audio), sr=None, mono=False)
            duration = len(audio[0] if len(audio.shape) > 1 else audio) / sr
            
            # Calculate chunk duration (aim for ~3 minute chunks)
            chunk_duration = 180  # 3 minutes in seconds
            num_chunks = int(np.ceil(duration / chunk_duration))
            
            print(f"📊 Audio is {duration:.1f}s - splitting into {num_chunks} chunks")
            
            for chunk_idx in range(num_chunks):
                start_time = chunk_idx * chunk_duration
                end_time = min((chunk_idx + 1) * chunk_duration, duration)
                
                # Extract chunk samples
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                
                if len(audio.shape) > 1:
                    audio_chunk = audio[:, start_sample:end_sample]
                else:
                    audio_chunk = audio[start_sample:end_sample]
                
                # Save chunk to temp file
                chunk_file = temp_audio_folder / f"chunk_{chunk_idx}.wav"
                sf.write(str(chunk_file), audio_chunk.T if len(audio.shape) > 1 else audio_chunk, sr)
                
                print(f"  Chunk {chunk_idx + 1}/{num_chunks}: {start_time:.1f}s - {end_time:.1f}s")
                
                # Transcribe chunk
                with open(chunk_file, 'rb') as audio_file:
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json",
                        timestamp_granularities=["word"]
                    )
                
                # Extract words and adjust timestamps
                if hasattr(transcript, 'words') and transcript.words:
                    for word_obj in transcript.words:
                        lyrics_data.append({
                            "word": word_obj.word.strip(),
                            "start": word_obj.start + start_time,  # Adjust timestamp
                            "end": word_obj.end + start_time
                        })
                
                # Clean up chunk file
                chunk_file.unlink()
            
            print(f"✅ Processed {num_chunks} chunks, found {len(lyrics_data)} words total")
            
        else:
            # File is small enough - process normally
            with open_file_when_ready(temp_audio, 'rb', timeout=wait_timeout, poll_interval=poll_interval) as (audio_file, waited):
                wait_msg = f" ({waited:.1f}s wait)" if waited >= poll_interval else ""
                print(f"✅ Audio file ready{wait_msg} ({file_size_mb:.1f}MB)")
                print(f"🔍 Analyzing vocals with Whisper API...")
                transcript = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            
            # Extract word-level timestamps
            if hasattr(transcript, 'words') and transcript.words:
                for word_obj in transcript.words:
                    lyrics_data.append({
                        "word": word_obj.word.strip(),
                        "start": word_obj.start,
                        "end": word_obj.end
                    })
        
        # Display lyrics
        print(f"\n📝 Lyrics found ({len(lyrics_data)} words):")
        for i, entry in enumerate(lyrics_data[:20]):  # Show first 20
            print(f"   [{entry['start']:.1f}s] {entry['word']}")
        if len(lyrics_data) > 20:
            print(f"   ... ({len(lyrics_data) - 20} more words)")
        
        # Save to cache
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                "track_name": track_name,
                "analyzed_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                "lyrics": lyrics_data
            }, f, indent=2)
        
        lyrics_cache[track_name] = lyrics_data
        print(f"💾 Cached lyrics for future use\n")
        
        # Clean up temp folder and files
        try:
            shutil.rmtree(temp_audio_folder)
        except:
            pass
        
        return lyrics_data
        
    except TimeoutError:
        print(f"❌ Export timeout - file not accessible after {wait_timeout}s")
        log_debug(f"Whisper wait timeout for {temp_audio}")
        return []
    except (PermissionError, FileNotFoundError) as e:
        print(f"❌ Export failed - {e}")
        log_debug(f"Whisper file access error ({temp_audio}): {e}")
        return []
    except Exception as e:
        print(f"❌ Whisper API error: {e}")
        log_debug(f"Whisper error: {e}")
        return []
        return []

def find_word_timestamp(lyrics_data, word):
    """Find timestamp for a specific word"""
    word_lower = word.lower().strip()
    for entry in lyrics_data:
        if entry['word'].lower().strip() == word_lower:
            return entry['end']  # Return end time of the word
    return None

def analyze_audio_track(track_idx, track_name, audio_path):
    """
    Analyze audio file with comprehensive effect detection.
    Uses new librosa-based detectors that output actionable data.
    """
    if not AUDIO_ANALYSIS_AVAILABLE:
        return {"error": "Audio analysis libraries not installed"}
    
    print(f"🔬 Comprehensive Audio Analysis: {track_name}\n")
    
    # Use new comprehensive analysis
    analysis = analyze_track_comprehensive(audio_path)
    
    # Save to JSON
    save_analysis_json(analysis, "current_track_analysis.json")
    
    # Print summary
    print(f"\n📊 Analysis Summary:")
    print(f"   {analysis.get('summary', 'No summary available')}")
    
    # Print structured output for backwards compatibility
    print(f"\n🔬 Analysis Results for {track_name}:")
    print(f"   Audio Type: {analysis.get('audio_type', 'unknown').replace('_', ' ').title()}")
    
    filtering = analysis['effects']['filtering']
    print(f"   Filtering: {filtering['character']}")
    if filtering['high_pass']:
        print(f"      High-pass: {filtering['high_pass']}Hz")
    if filtering['low_pass']:
        print(f"      Low-pass: {filtering['low_pass']}Hz")
    
    delay = analysis['effects']['delay']
    if delay['present']:
        print(f"   Delay: {delay['delay_time_ms']}ms, {delay['feedback']}% feedback, {delay['mix']}% mix")
    else:
        print(f"   Delay: None")
    
    reverb = analysis['effects']['reverb']
    if reverb['present']:
        print(f"   Reverb: {reverb['decay_time']:.1f}s decay, {reverb['mix']}% mix")
    else:
        print(f"   Reverb: Dry")
    
    print(f"   Distortion: {analysis['characteristics']['distortion']:.1f}% ({analysis['characteristics']['saturation']['type_hint']})")
    print(f"   Compression: {analysis['characteristics']['compression']:.1f}%")
    print(f"   Brightness: {analysis['characteristics']['brightness']:.1f}%")
    print(f"   Pitch Correction: {analysis['characteristics']['autotune']:.1f}%")
    
    # Additional data
    if 'bpm' in analysis['characteristics']:
        print(f"   BPM: {analysis['characteristics']['bpm']:.1f}")
    
    if 'spectral_indices' in analysis['characteristics']:
        idx = analysis['characteristics']['spectral_indices']
        print(f"   Spectral: Mud {idx['mud']:.0f}%, Box {idx['boxiness']:.0f}%, Presence {idx['presence']:.0f}%, Air {idx['air']:.0f}%")
    
    if 'stereo_metrics' in analysis:
        st = analysis['stereo_metrics']
        print(f"   Stereo: Corr {st['lr_corr']:.2f}, Width Low {st['width_low']:.0f}%, High {st['width_high']:.0f}%")
    
    if 'deessing_need' in analysis and analysis['deessing_need']['need_score'] > 20:
        de = analysis['deessing_need']
        print(f"   De-essing: {de['need_score']:.0f}% needed at {de['target_khz']:.1f}kHz")
    
    return analysis

def analyze_audio_track_OLD_GENERIC(track_idx, track_name, audio_path):
    """OLD generic analysis - kept for reference but not used"""
    if not AUDIO_ANALYSIS_AVAILABLE:
        return {"error": "Audio analysis libraries not installed"}
    
    print(f"🔬 Analyzing audio: {track_name}")
    
    try:
        # Load audio
        y, sr = librosa.load(audio_path, sr=None, mono=False)
        
        # Convert to mono for some analyses
        if len(y.shape) > 1:
            y_mono = librosa.to_mono(y)
            is_stereo = True
            left_channel = y[0]
            right_channel = y[1]
        else:
            y_mono = y
            is_stereo = False
            left_channel = y
            right_channel = y
        
        duration = librosa.get_duration(y=y_mono, sr=sr)
        
        # === LOUDNESS ANALYSIS ===
        rms = librosa.feature.rms(y=y_mono)[0]
        rms_db = librosa.amplitude_to_db(rms)
        avg_loudness = float(np.mean(rms_db))
        peak_db = float(librosa.amplitude_to_db(np.abs(y_mono).max()))
        
        # Dynamic range
        dynamic_range = float(peak_db - avg_loudness)
        
        # === FREQUENCY ANALYSIS ===
        # Compute spectrogram
        S = np.abs(librosa.stft(y_mono))
        freqs = librosa.fft_frequencies(sr=sr)
        
        # Energy in frequency bands
        def get_band_energy(S, freqs, low, high):
            mask = (freqs >= low) & (freqs <= high)
            return float(np.mean(S[mask, :]))
        
        sub_bass = get_band_energy(S, freqs, 20, 60)      # Sub bass
        bass = get_band_energy(S, freqs, 60, 250)          # Bass
        low_mids = get_band_energy(S, freqs, 250, 500)    # Low mids
        mids = get_band_energy(S, freqs, 500, 2000)        # Mids
        high_mids = get_band_energy(S, freqs, 2000, 5000) # High mids
        highs = get_band_energy(S, freqs, 5000, 20000)    # Highs
        
        # Convert to dB
        band_energies = {
            "sub_bass_20_60hz": float(librosa.amplitude_to_db([sub_bass])[0]),
            "bass_60_250hz": float(librosa.amplitude_to_db([bass])[0]),
            "low_mids_250_500hz": float(librosa.amplitude_to_db([low_mids])[0]),
            "mids_500_2khz": float(librosa.amplitude_to_db([mids])[0]),
            "high_mids_2_5khz": float(librosa.amplitude_to_db([high_mids])[0]),
            "highs_5_20khz": float(librosa.amplitude_to_db([highs])[0])
        }
        
        # === TRACK CLASSIFICATION ===
        # Determine what type of audio this is based on frequency distribution
        total_energy = sub_bass + bass + low_mids + mids + high_mids + highs
        
        # Calculate energy percentages per band
        bass_pct = (sub_bass + bass) / total_energy if total_energy > 0 else 0
        mids_pct = (low_mids + mids) / total_energy if total_energy > 0 else 0
        highs_pct = (high_mids + highs) / total_energy if total_energy > 0 else 0
        
        # Classify track type
        track_type = "unknown"
        
        # Vocal characteristics: focused in mids (500Hz-5kHz), less bass, moderate highs
        if mids_pct > 0.5 and bass_pct < 0.2 and band_energies["bass_60_250hz"] < -30:
            track_type = "vocal"
        # Full mix: energy across all bands, balanced
        elif bass_pct > 0.2 and mids_pct > 0.3 and highs_pct > 0.15:
            track_type = "full_mix"
        # Bass-heavy instrument (kick, bass, 808s)
        elif bass_pct > 0.4:
            track_type = "bass_instrument"
        # High-frequency instrument (hi-hats, cymbals)
        elif highs_pct > 0.4:
            track_type = "high_freq_instrument"
        else:
            track_type = "instrument"
        
        # === CONTEXT-AWARE ISSUE DETECTION ===
        issues = []
        
        # Different thresholds based on track type
        if track_type == "vocal":
            # Vocals: expect less bass, more mids, moderate highs
            # Only flag real issues, not normal vocal characteristics
            if band_energies["low_mids_250_500hz"] > band_energies["mids_500_2khz"] + 8:
                issues.append("Muddy (excess 250-500Hz)")
            if band_energies["high_mids_2_5khz"] > band_energies["mids_500_2khz"] + 10:
                issues.append("Harsh (peaks 2-5kHz)")
            # Don't flag "thin" for vocals - they're supposed to have less bass
            if band_energies["highs_5_20khz"] < band_energies["high_mids_2_5khz"] - 12:
                issues.append("Dull (lacking air)")
                
        elif track_type == "full_mix":
            # Full mix: should have balanced energy across all bands
            if band_energies["low_mids_250_500hz"] > band_energies["mids_500_2khz"] + 6:
                issues.append("Muddy (excess 250-500Hz)")
            if band_energies["high_mids_2_5khz"] > band_energies["mids_500_2khz"] + 9:
                issues.append("Harsh (peaks 2-5kHz)")
            if band_energies["bass_60_250hz"] < band_energies["mids_500_2khz"] - 10:
                issues.append("Thin (lacking bass)")
            if band_energies["highs_5_20khz"] < band_energies["mids_500_2khz"] - 12:
                issues.append("Dull (lacking air)")
                
        elif track_type == "bass_instrument":
            # Bass instruments: expect heavy low end, less highs
            # But can still have issues in low-mids or too much sub rumble
            if band_energies["low_mids_250_500hz"] > band_energies["bass_60_250hz"] + 3:
                issues.append("Muddy (too much mid-bass for bass instrument)")
            if band_energies["sub_bass_20_60hz"] > band_energies["bass_60_250hz"] + 8:
                issues.append("Excessive sub-bass rumble (below 60Hz)")
            # Bass can still be harsh if there are harmonics in the wrong place
            if band_energies["high_mids_2_5khz"] > band_energies["bass_60_250hz"] - 20:
                issues.append("Harsh upper harmonics")
            # Don't flag "lacking air" for bass - that's normal
            
        elif track_type == "high_freq_instrument":
            # Hi-hats/cymbals: expect high energy in highs
            if band_energies["low_mids_250_500hz"] > band_energies["highs_5_20khz"] - 10:
                issues.append("Muddy (unexpected low-mid energy in high-freq source)")
            # Don't flag "lacking bass" - that's expected
            
        else:
            # Generic instrument or unknown
            # Use moderate thresholds
            if band_energies["low_mids_250_500hz"] > band_energies["mids_500_2khz"] + 8:
                issues.append("Muddy (excess 250-500Hz)")
            if band_energies["high_mids_2_5khz"] > band_energies["mids_500_2khz"] + 10:
                issues.append("Harsh (peaks 2-5kHz)")
            if band_energies["highs_5_20khz"] < band_energies["mids_500_2khz"] - 15:
                issues.append("Dull (lacking air)")
        
        # === STEREO ANALYSIS ===
        stereo_width = 0.0
        if is_stereo:
            # Calculate correlation between L/R
            correlation = float(np.corrcoef(left_channel, right_channel)[0, 1])
            stereo_width = float((1.0 - correlation) * 100)  # 0% = mono, 100% = wide
        
        # === DYNAMICS ANALYSIS ===
        compression_assessment = "Natural"
        if dynamic_range < 6:
            compression_assessment = "Over-compressed"
        elif dynamic_range < 10:
            compression_assessment = "Moderately compressed"
        elif dynamic_range > 20:
            compression_assessment = "Very dynamic"
        
        # === SPECTRAL CHARACTERISTICS ===
        spectral_centroid = librosa.feature.spectral_centroid(y=y_mono, sr=sr)
        avg_brightness = float(np.mean(spectral_centroid))
        
        brightness_assessment = "Balanced"
        if avg_brightness < 1500:
            brightness_assessment = "Dark"
        elif avg_brightness > 3000:
            brightness_assessment = "Bright"
        
        # === TIER 1 ADVANCED FEATURES ===
        
        # 1. SPECTRAL ROLLOFF - detects where high frequencies drop off (catches low-pass filters!)
        rolloff = librosa.feature.spectral_rolloff(y=y_mono, sr=sr, roll_percent=0.85)
        avg_rolloff_freq = float(np.mean(rolloff))
        
        # Detect if low-pass filter is active
        filter_detection = "None detected"
        if avg_rolloff_freq < 1500:
            filter_detection = f"Aggressive low-pass around {int(avg_rolloff_freq)}Hz (underwater/muffled effect)"
        elif avg_rolloff_freq < 3000:
            filter_detection = f"Moderate low-pass around {int(avg_rolloff_freq)}Hz (telephone/lo-fi effect)"
        elif avg_rolloff_freq > 15000:
            filter_detection = "Full frequency range (no filtering)"
        
        # 2. ZERO-CROSSING RATE - detects distortion/saturation
        zcr = librosa.feature.zero_crossing_rate(y_mono)
        avg_zcr = float(np.mean(zcr))
        
        distortion_level = "Clean"
        if avg_zcr > 0.15:
            distortion_level = "Heavy distortion/saturation"
        elif avg_zcr > 0.10:
            distortion_level = "Moderate saturation"
        elif avg_zcr > 0.05:
            distortion_level = "Light saturation/warmth"
        
        # 3. HARMONIC/PERCUSSIVE SEPARATION - detects if saturation added harmonics
        y_harmonic, y_percussive = librosa.effects.hpss(y_mono)
        harmonic_energy = float(np.sum(y_harmonic**2))
        percussive_energy = float(np.sum(y_percussive**2))
        
        if percussive_energy > 0:
            harmonic_ratio = float(harmonic_energy / percussive_energy)
        else:
            harmonic_ratio = 0.0
        
        harmonic_assessment = "Natural balance"
        if harmonic_ratio > 10:
            harmonic_assessment = "Heavy harmonic content (saturation/distortion present)"
        elif harmonic_ratio > 5:
            harmonic_assessment = "Moderate harmonic content (some saturation)"
        elif harmonic_ratio > 2:
            harmonic_assessment = "Slight harmonic enhancement"
        
        # 4. SPECTRAL FLUX - detects reverb/modulation/movement
        spectral_flux = np.mean(librosa.onset.onset_strength(y=y_mono, sr=sr))
        
        reverb_assessment = "Dry"
        if spectral_flux > 15:
            reverb_assessment = "Heavy reverb/modulation (lots of spectral movement)"
        elif spectral_flux > 8:
            reverb_assessment = "Moderate reverb/space"
        elif spectral_flux > 4:
            reverb_assessment = "Light reverb/ambience"
        
        analysis_result = {
            "track_name": track_name,
            "track_type": track_type,  # vocal, full_mix, bass_instrument, etc.
            "duration_seconds": float(duration),
            "is_stereo": is_stereo,
            
            "loudness": {
                "average_rms_db": round(avg_loudness, 1),
                "peak_db": round(peak_db, 1),
                "dynamic_range_db": round(dynamic_range, 1),
                "assessment": compression_assessment
            },
            
            "frequency_balance": band_energies,
            
            "tonal_characteristics": {
                "spectral_brightness_hz": round(avg_brightness, 0),
                "assessment": brightness_assessment
            },
            
            "stereo_image": {
                "width_percentage": round(stereo_width, 1) if is_stereo else 0,
                "assessment": "Wide" if stereo_width > 60 else "Narrow" if stereo_width > 30 else "Mono"
            },
            
            "effects_detected": {
                "filtering": {
                    "rolloff_frequency_hz": round(avg_rolloff_freq, 0),
                    "assessment": filter_detection
                },
                "distortion": {
                    "zero_crossing_rate": round(avg_zcr, 3),
                    "assessment": distortion_level
                },
                "harmonics": {
                    "harmonic_to_percussive_ratio": round(harmonic_ratio, 2),
                    "assessment": harmonic_assessment
                },
                "reverb": {
                    "spectral_flux": round(spectral_flux, 2),
                    "assessment": reverb_assessment
                }
            },
            
            "issues_detected": issues,
            
            "recommendations": []
        }
        
        # Generate context-aware recommendations based on track type
        if "Muddy" in ' '.join(issues):
            if track_type == "vocal":
                analysis_result["recommendations"].append("Cut 250-350Hz by 2-3dB to reduce muddiness in vocals")
            elif track_type == "bass_instrument":
                analysis_result["recommendations"].append("Cut 300-500Hz by 3-5dB to tighten mid-bass")
            else:
                analysis_result["recommendations"].append("Cut 250-400Hz by 2-4dB")
        
        if "Harsh" in ' '.join(issues):
            if track_type == "vocal":
                analysis_result["recommendations"].append("Reduce 3-4kHz by 2-3dB to soften vocal harshness")
            else:
                analysis_result["recommendations"].append("Reduce 2-5kHz harshness by 2-3dB")
        
        if "Thin" in ' '.join(issues):
            if track_type == "full_mix":
                analysis_result["recommendations"].append("Boost bass around 80-150Hz by 2-3dB")
            else:
                analysis_result["recommendations"].append("Boost bass around 100-200Hz")
        
        if "Dull" in ' '.join(issues):
            if track_type == "vocal":
                analysis_result["recommendations"].append("Boost 8-12kHz by 2-3dB for vocal air and clarity")
            elif track_type == "full_mix":
                analysis_result["recommendations"].append("Add air shelf at 10kHz +1-2dB")
            else:
                analysis_result["recommendations"].append("Boost highs around 8-12kHz")
        
        if dynamic_range < 6:
            analysis_result["recommendations"].append("Reduce compression - dynamics too squashed")
        
        if stereo_width < 30 and is_stereo:
            if track_type == "vocal":
                analysis_result["recommendations"].append("Consider subtle stereo widening for vocals (be careful not to lose center focus)")
            else:
                analysis_result["recommendations"].append("Consider stereo widening")
        
        # Recommendations based on detected effects
        if "Aggressive low-pass" in filter_detection or "Moderate low-pass" in filter_detection:
            issues.append(f"Low-pass filtering detected ({filter_detection})")
            if track_type != "bass_instrument":
                analysis_result["recommendations"].append(f"Low-pass filter detected at {int(avg_rolloff_freq)}Hz - if unintentional, boost highs or remove filter")
            else:
                analysis_result["recommendations"].append(f"Low-pass filter at {int(avg_rolloff_freq)}Hz - may be limiting bass clarity and harmonics")
        
        if "rumble" in ' '.join(issues).lower():
            analysis_result["recommendations"].append("Cut sub-bass below 40Hz with high-pass filter")
        
        if "Heavy harmonic" in harmonic_assessment:
            if track_type == "bass_instrument":
                analysis_result["recommendations"].append("Heavy saturation/distortion detected - may add character or cause harshness")
            else:
                issues.append("Heavy harmonic distortion/saturation present")
                analysis_result["recommendations"].append("Check for excessive saturation or distortion")
        
        return analysis_result
        
    except Exception as e:
        log_debug(f"Audio analysis error: {e}")
        return {"error": str(e)}

# ========================================
# REFERENCE-BASED MIXING SYSTEM
# ========================================

def normalize_value(value, min_val, max_val):
    """Helper to normalize a value between 0 and 1."""
    if max_val > min_val:
        return (value - min_val) / (max_val - min_val)
    return 0.5

def estimate_reverb_decay(autocorrelation):
    """
    Estimate reverb decay time from autocorrelation.
    Autocorrelation peaks indicate delay times; decay is time to drop 60dB (RT60 approximation).
    """
    if autocorrelation is None or len(autocorrelation) == 0:
        return 0.5
    threshold = np.max(autocorrelation) / np.e  # Approximate decay point
    decay_indices = np.where(autocorrelation < threshold)[0]
    if len(decay_indices) == 0:
        return 0.5
    decay_lag = decay_indices[0]
    sample_rate = 22050  # Common sr
    decay_time = decay_lag / sample_rate  # In seconds
    return float(decay_time)

def estimate_reverb_mix(spectral_flux, hp_ratio):
    """
    Estimate wet/dry mix from spectral flux (modulation) and hp_ratio (tail smearing).
    High flux and smeared harmonics suggest higher wet mix.
    """
    normalized_flux = normalize_value(spectral_flux, 0, 10)
    normalized_hp = normalize_value(hp_ratio, 1, 10)
    mix_estimate = 0.5 * normalized_flux + 0.5 * normalized_hp
    return float(mix_estimate)

def map_saturation_amount(hp_ratio_diff, zcr_diff):
    """
    Map harmonic content differences to saturation drive (0-1).
    Higher hp_ratio or zcr in ref means more saturation needed.
    """
    sat_drive = 0.5 + 0.3 * hp_ratio_diff + 0.2 * zcr_diff
    return float(np.clip(sat_drive, 0, 1))

def get_clap_embedding(audio_path):
    """
    Extract CLAP audio embedding for perceptual similarity.
    Returns embedding vector or None if CLAP not available.
    """
    if not CLAP_AVAILABLE:
        return None
    
    try:
        # Load audio (CLAP expects 48kHz, will resample if needed)
        audio, sr = librosa.load(audio_path, sr=48000, mono=True)
        
        # CLAP expects audio between -1 and 1
        audio = np.clip(audio, -1.0, 1.0)
        
        # Process audio
        inputs = clap_processor(audio=audio, sampling_rate=48000, return_tensors="pt")
        
        # Get audio embedding
        with torch.no_grad():
            audio_embed = clap_model.get_audio_features(**inputs)
        
        # Convert to numpy
        embedding = audio_embed.cpu().numpy()[0]
        
        return embedding
        
    except Exception as e:
        log_debug(f"CLAP embedding error: {e}")
        return None


def analyze_production_style(audio_path, production_terms=PRODUCTION_TERMS):
    """
    Use CLAP to find which production terms best describe the audio.
    
    Args:
        audio_path: Path to reference audio
        production_terms: List of production descriptions
    
    Returns:
        List of (term, score) tuples, sorted by match score descending
    """
    if not CLAP_AVAILABLE:
        return []
    
    try:
        # Get audio embedding
        audio_embed = get_clap_embedding(audio_path)
        if audio_embed is None:
            return []
        
        # Get text embeddings
        text_inputs = clap_processor(text=production_terms, return_tensors="pt", padding=True)
        with torch.no_grad():
            text_embeds = clap_model.get_text_features(**text_inputs).cpu().numpy()
        
        # Cosine similarities
        similarities = sklearn_cosine_similarity([audio_embed], text_embeds)[0]
        
        # Sort and return top matches
        sorted_terms = sorted(zip(production_terms, similarities), key=lambda x: x[1], reverse=True)
        return sorted_terms
        
    except Exception as e:
        log_debug(f"Production style analysis error: {e}")
        return []

def get_plugin_recipe(production_term):
    """
    Given a production term, return the plugins and settings needed.
    """
    return SEMANTIC_KNOWLEDGE_BASE.get(production_term, {})

def semantic_match_to_reference(track_idx, reference_audio_path, target_audio_path,
                                target_similarity=0.75, max_iterations=10):
    """
    Semantic reference matching using CLAP text-audio matching.
    Compares SCORES for each term, not just presence.
    
    Returns:
        - CLAP similarity score
        - Plugins to add based on what reference has MORE of
    """
    if not CLAP_AVAILABLE:
        print("❌ CLAP not available")
        return {"error": "CLAP not installed"}
    
    print(f"\n🎧 CLAP Semantic Analysis")
    print(f"   Finding what production characteristics differ\n")
    
    try:
        # Get CLAP similarity
        ref_embed = get_clap_embedding(reference_audio_path)
        target_embed = get_clap_embedding(target_audio_path)
        
        if ref_embed is None or target_embed is None:
            print("❌ Failed to get CLAP embeddings")
            return {"error": "Embedding extraction failed"}
        
        current_sim = sklearn_cosine_similarity([ref_embed], [target_embed])[0][0]
        print(f"🎯 Initial CLAP similarity: {current_sim * 100:.1f}%\n")
        
        # Analyze what production styles match each track
        print(f"🔍 Analyzing reference...")
        ref_terms = analyze_production_style(reference_audio_path)
        
        print(f"🔍 Analyzing your track...")
        target_terms = analyze_production_style(target_audio_path)
        
        # Create dict for easy lookup
        ref_dict = {term: score for term, score in ref_terms}
        target_dict = {term: score for term, score in target_terms}
        
        # Find characteristics where reference has SIGNIFICANTLY MORE
        needs_adding = []
        SCORE_THRESHOLD = 0.10  # Ref needs to be 10% higher to count as "needs adding"
        
        for term, ref_score in ref_terms[:20]:  # Check top 20 from reference
            target_score = target_dict.get(term, 0.0)
            score_diff = ref_score - target_score
            
            if score_diff > SCORE_THRESHOLD:  # Ref has significantly more of this
                recipe = get_plugin_recipe(term)
                if recipe and recipe.get("plugins"):
                    needs_adding.append((term, score_diff, ref_score, target_score, recipe))
        
        if not needs_adding:
            print(f"✅ No significant differences found")
            print(f"   Tracks have similar production characteristics")
            return {"similarity": current_sim, "plugins": []}
        
        # Sort by score difference (biggest gaps first)
        needs_adding.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n📊 Production Differences (Reference has MORE of these):")
        for term, diff, ref_score, tgt_score, recipe in needs_adding[:5]:
            print(f"   • {term}")
            print(f"      Ref: {ref_score*100:.1f}% | Your track: {tgt_score*100:.1f}% | Diff: +{diff*100:.1f}%")
        
        print(f"\n🎛️ Recommended plugins (top 3 differences):")
        recommended_plugins = []
        for term, diff, ref_score, tgt_score, recipe in needs_adding[:3]:
            print(f"   ✅ {term} (add {diff*100:.1f}% more)")
            for plugin in recipe['plugins']:
                print(f"      → {plugin}: {recipe['settings'].get(plugin, {})}")
                recommended_plugins.append(plugin)
        
        print(f"\n⚠️ NOTE: Plugins identified but not yet applied")
        print(f"   Next: Need proper parameter mapping to apply these")
        
        return {
            "similarity": current_sim,
            "needs_adding": [(t, d) for t, d, _, _, _ in needs_adding[:5]],
            "recommended_plugins": recommended_plugins
        }
        
    except Exception as e:
        log_debug(f"Semantic matching error: {e}")
        print(f"❌ Error: {e}")
        return {"error": str(e)}

def extract_detailed_features(audio_path):
    """
    Enhanced feature extraction with perceptual weighting, THD analysis, and better reverb estimation.
    ALSO includes CLAP embedding for true perceptual similarity.
    Returns dict with all features needed for similarity comparison.
    """
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=False)
        
        # Handle stereo/mono
        if y.ndim == 1:
            y_mono = y
            y_stereo = np.stack([y, y], axis=0)
            is_stereo = False
        elif len(y.shape) > 1:
            y_mono = librosa.to_mono(y)
            y_stereo = y
            is_stereo = True
        else:
            y_mono = y
            y_stereo = np.stack([y, y], axis=0)
            is_stereo = False
        
        features = {}
        
        # Spectral: Use mel with A-weighting for perceptual accuracy
        S = np.abs(librosa.stft(y_mono))
        freqs = librosa.fft_frequencies(sr=sr)
        
        # A-weighted power spectrum (perceptual)
        try:
            S_weighted = librosa.perceptual_weighting(S**2, freqs, ref=1.0)
            mel_spec = librosa.feature.melspectrogram(S=S_weighted, sr=sr, n_mels=40)
        except:
            # Fallback if perceptual_weighting not available
            mel_spec = librosa.feature.melspectrogram(y=y_mono, sr=sr, n_mels=40)
        
        features['mel_bands'] = np.mean(mel_spec, axis=1)
        
        # Broad 6 bands for compatibility
        mel_spec_6 = librosa.feature.melspectrogram(y=y_mono, sr=sr, n_mels=6)
        features['band_energies'] = 20 * np.log10(np.mean(mel_spec_6, axis=1) + 1e-10)
        
        # Spectral features
        features['spectral_rolloff'] = float(np.mean(librosa.feature.spectral_rolloff(y=y_mono, sr=sr)))
        features['spectral_centroid'] = float(np.mean(librosa.feature.spectral_centroid(y=y_mono, sr=sr)))
        features['spectral_contrast'] = np.mean(librosa.feature.spectral_contrast(y=y_mono, sr=sr), axis=1)
        
        # Dynamics
        rms = librosa.feature.rms(y=y_mono)
        features['rms'] = float(np.mean(rms))
        S_db = librosa.amplitude_to_db(S + 1e-10)
        features['peak'] = float(np.max(S_db))
        features['dynamic_range'] = features['peak'] - librosa.amplitude_to_db(np.array([features['rms'] + 1e-10]))[0]
        features['crest_factor'] = features['peak'] / (librosa.amplitude_to_db(np.array([features['rms'] + 1e-10]))[0] + 1e-10)
        
        # Temporal
        features['onset_strength'] = float(np.mean(librosa.onset.onset_strength(y=y_mono, sr=sr)))
        
        # Harmonic/Percussive
        y_harm, y_perc = librosa.effects.hpss(y_mono)
        perc_energy = np.mean(np.abs(y_perc))
        features['hp_ratio'] = float(np.mean(np.abs(y_harm)) / perc_energy if perc_energy > 1e-10 else 1.0)
        
        # Zero-crossing rate
        features['zcr'] = float(np.mean(librosa.feature.zero_crossing_rate(y_mono)))
        
        # Timbre (MFCC)
        features['mfcc'] = np.mean(librosa.feature.mfcc(y=y_mono, sr=sr, n_mfcc=13), axis=1)
        
        # Chroma
        features['chroma'] = np.mean(librosa.feature.chroma_stft(y=y_mono, sr=sr), axis=1)
        
        # THD and harmonic analysis
        try:
            from scipy.fft import fft
            Y = fft(y_mono)
            mag = np.abs(Y[:len(Y)//2])
            fund_idx = np.argmax(mag[1:]) + 1  # Skip DC
            fund_mag = mag[fund_idx]
            fund_freq = freqs[min(fund_idx, len(freqs)-1)] if fund_idx < len(freqs) else 440.0
            
            # Calculate harmonics
            harmonics = []
            for i in range(2, 10):  # 2nd to 9th harmonic
                harm_freq = i * fund_freq
                harm_idx = int(harm_freq * len(mag) / (sr/2))
                if harm_idx < len(mag):
                    harmonics.append(mag[harm_idx])
                else:
                    harmonics.append(0)
            
            # THD calculation
            harm_sum = np.sqrt(sum(h**2 for h in harmonics))
            features['thd'] = float(harm_sum / fund_mag if fund_mag > 1e-10 else 0.0)
            
            # Odd/even ratio
            odd_harm = sum(h**2 for idx, h in enumerate(harmonics) if (idx + 2) % 2 == 1)
            even_harm = sum(h**2 for idx, h in enumerate(harmonics) if (idx + 2) % 2 == 0)
            features['odd_even_ratio'] = float(odd_harm / even_harm if even_harm > 1e-10 else 1.0)
        except Exception as e:
            log_debug(f"THD calculation error: {e}")
            features['thd'] = 0.0
            features['odd_even_ratio'] = 1.0
        
        # Improved reverb estimation
        energy = librosa.feature.rms(y=y_mono)[0]
        max_energy = np.max(energy)
        
        if max_energy > 1e-10:
            tail_start = np.argmax(energy < max_energy * 0.01)
            tail_energy = energy[tail_start:] if tail_start > 0 else energy
            
            if len(tail_energy) > 0:
                tail_db = librosa.amplitude_to_db(tail_energy + 1e-10) - librosa.amplitude_to_db(np.array([max_energy + 1e-10]))[0]
                rt60_indices = np.where(tail_db <= -60)[0]
                rt60_idx = rt60_indices[0] if len(rt60_indices) > 0 else len(tail_db)
                features['rt60'] = float(rt60_idx * 512 / sr)  # Convert frames to seconds
            else:
                features['rt60'] = 0.5
            
            # Wet/dry estimation
            features['wet_dry'] = float(np.mean(tail_energy) / features['rms'] if features['rms'] > 1e-10 else 0.1)
        else:
            features['rt60'] = 0.5
            features['wet_dry'] = 0.1
        
        # Pre-delay from autocorrelation
        onset_env = librosa.onset.onset_strength(y=y_mono, sr=sr)
        autocorr = librosa.autocorrelate(onset_env)
        features['autocorrelation'] = autocorr
        
        if len(autocorr) > 1:
            pre_delay_idx = np.argmax(autocorr[1:min(len(autocorr), 100)]) + 1
            features['pre_delay'] = float(pre_delay_idx * 512 / sr * 1000)  # ms
        else:
            features['pre_delay'] = 0.0
        
        # Reverb type classification
        if features['rt60'] > 3.0:
            features['reverb_type'] = 'hall'
        elif features['rt60'] > 1.5:
            features['reverb_type'] = 'room'
        else:
            features['reverb_type'] = 'plate'
        
        # Spatial (stereo)
        if is_stereo and y_stereo.shape[0] == 2:
            features['lr_correlation'] = float(np.corrcoef(y_stereo[0], y_stereo[1])[0, 1])
        else:
            features['lr_correlation'] = 1.0
        
        # Spectral flux
        features['spectral_flux'] = float(np.mean(onset_env))
        
        # CLAP embedding for perceptual similarity (the game-changer!)
        print("   🎧 Getting CLAP perceptual embedding...")
        clap_embedding = get_clap_embedding(audio_path)
        features['clap_embedding'] = clap_embedding
        
        return features
        
    except Exception as e:
        log_debug(f"Feature extraction error: {e}")
        return None

def calculate_similarity(reference_features, current_features, processing_penalty=0.0):
    """
    Perceptual similarity using CLAP embeddings (primary) + librosa features (supporting).
    CLAP understands musical character; librosa provides technical details.
    Returns 0-100% similarity score.
    """
    if not reference_features or not current_features:
        return 0.0
    
    try:
        # If CLAP embeddings available, use them as PRIMARY similarity metric
        if (reference_features.get('clap_embedding') is not None and 
            current_features.get('clap_embedding') is not None):
            
            # CLAP perceptual similarity (0-1, higher = more similar)
            clap_sim = 1 - cosine(reference_features['clap_embedding'], 
                                  current_features['clap_embedding'])
            clap_sim = max(0, min(1, clap_sim))  # Clamp to 0-1
            
            # Librosa features as SUPPORTING metrics (for detailed breakdown)
            weights = {
                'clap_perceptual': 0.65,  # CLAP is primary - it actually "hears" the audio
                'dynamics': 0.15,         # Still important for mixing
                'harmonic': 0.10,         # THD/saturation detail
                'spatial': 0.10           # Stereo width
            }
            
            # Dynamics
            dyn_diff = abs(reference_features['dynamic_range'] - current_features['dynamic_range']) / 20
            crest_diff = abs(reference_features['crest_factor'] - current_features['crest_factor']) / 20
            dyn_sim = max(0, 1 - (0.6 * dyn_diff + 0.4 * crest_diff))
            
            # Harmonic (THD-based)
            harm_diff = 0
            harm_diff += 0.4 * abs(reference_features['hp_ratio'] - current_features['hp_ratio']) / 10
            if 'thd' in reference_features and 'thd' in current_features:
                harm_diff += 0.6 * abs(reference_features['thd'] - current_features['thd'])
            harm_sim = max(0, 1 - harm_diff)
            
            # Spatial
            spat_sim = max(0, 1 - abs(reference_features['lr_correlation'] - current_features['lr_correlation']) / 2)
            
            # Weighted combination - CLAP dominates
            total_sim = (
                weights['clap_perceptual'] * clap_sim +
                weights['dynamics'] * dyn_sim +
                weights['harmonic'] * harm_sim +
                weights['spatial'] * spat_sim
            )
            
            print(f"   🎧 CLAP perceptual similarity: {clap_sim * 100:.1f}%")
            
        else:
            # Fallback to librosa-only (if CLAP not available)
            print("   ⚠️ CLAP not available - using librosa-only similarity (less accurate)")
            
            weights = {
                'spectral_shape': 0.4,
                'dynamics': 0.2,
                'spatial': 0.15,
                'harmonic': 0.15,
                'temporal': 0.10
            }
            
            # Spectral: Use mel bands with presence emphasis
            mel_diff = cosine(reference_features['mel_bands'], current_features['mel_bands'])
            presence_ref = reference_features['mel_bands'][10:20]
            presence_cur = current_features['mel_bands'][10:20]
            presence_diff = cosine(presence_ref, presence_cur) * 1.5
            spec_diff = 0.7 * mel_diff + 0.3 * (presence_diff / 1.5)
            spec_sim = max(0, 1 - np.clip(spec_diff, 0, 1))
            
            # Dynamics
            dyn_diff = abs(reference_features['dynamic_range'] - current_features['dynamic_range']) / 20
            crest_diff = abs(reference_features['crest_factor'] - current_features['crest_factor']) / 20
            dyn_sim = max(0, 1 - (0.6 * dyn_diff + 0.4 * crest_diff))
            
            # Spatial
            spat_sim = max(0, 1 - abs(reference_features['lr_correlation'] - current_features['lr_correlation']) / 2)
            
            # Harmonic
            harm_diff = 0
            harm_diff += 0.4 * abs(reference_features['hp_ratio'] - current_features['hp_ratio']) / 10
            harm_diff += 0.3 * cosine(reference_features['mfcc'], current_features['mfcc'])
            if 'thd' in reference_features and 'thd' in current_features:
                harm_diff += 0.3 * abs(reference_features['thd'] - current_features['thd'])
            harm_sim = max(0, 1 - harm_diff)
            
            # Temporal
            temp_sim = max(0, 1 - abs(reference_features['onset_strength'] - current_features['onset_strength']) / 10)
            
            # Combined similarity
            total_sim = (
                weights['spectral_shape'] * spec_sim +
                weights['dynamics'] * dyn_sim +
                weights['spatial'] * spat_sim +
                weights['harmonic'] * harm_sim +
                weights['temporal'] * temp_sim
            )
        
        # Apply processing penalty
        final_sim = (total_sim - processing_penalty) * 100
        return float(np.clip(final_sim, 0, 100))
        
    except Exception as e:
        log_debug(f"Similarity calculation error: {e}")
        return 0.0

def calculate_processing_penalty(actions):
    """
    Calculate penalty for over-processing to prevent unmusical results.
    Returns penalty value (0-1 range, subtracted from similarity).
    """
    try:
        eq_total = 0
        comp_ratio = 0
        sat_drive = 0
        
        for action in actions:
            if action.get('type') == 'eq' and 'adjustments' in action:
                for adj in action['adjustments']:
                    eq_total += abs(adj.get('gain_db', 0))
            elif action.get('type') == 'compression':
                comp_ratio = action.get('ratio', 0)
            elif action.get('type') == 'saturation':
                sat_drive = action.get('drive', 0)
        
        # Normalize penalties
        eq_penalty = min(eq_total / 72, 1.0)  # Total > 72dB is excessive (12dB * 6 bands)
        comp_penalty = max(0, (comp_ratio - 10) / 10)  # Ratio > 10:1 is excessive
        sat_penalty = max(0, (sat_drive - 0.5) / 0.5)  # Drive > 50% is excessive
        
        total_penalty = 0.05 * (eq_penalty + comp_penalty + sat_penalty)
        return float(total_penalty)
        
    except Exception as e:
        log_debug(f"Penalty calculation error: {e}")
        return 0.0

def analyze_saturation_character(features):
    """Determine saturation type from harmonic analysis."""
    try:
        thd = features.get('thd', 0.0)
        oe_ratio = features.get('odd_even_ratio', 1.0)
        
        if thd < 0.01:
            return {'type': 'none', 'amount': 0.0}
        elif oe_ratio > 2:
            sat_type = 'tube' if thd < 0.1 else 'distortion'
            return {'type': sat_type, 'amount': float(thd)}
        else:
            return {'type': 'tape', 'amount': float(thd)}
    except Exception as e:
        log_debug(f"Saturation analysis error: {e}")
        return {'type': 'none', 'amount': 0.0}

def calculate_mixing_actions(reference_features, target_features, step_size=1.0):
    """
    Enhanced action generation with priority queue, constraints, and step size.
    Returns prioritized list of actions (highest priority first).
    """
    if not reference_features or not target_features:
        return []
    
    try:
        from queue import PriorityQueue
        priorities = PriorityQueue()
        
        # EQ: Constrain to ±6dB per band, use mel_bands for precision
        band_diffs = reference_features['mel_bands'] - target_features['mel_bands']
        
        for i, diff in enumerate(band_diffs):
            if abs(diff) > 0.5:  # Softer threshold (mel spec is more sensitive)
                gain = np.clip(step_size * diff / 2, -6, 6)  # Constrained to ±6dB
                priority = abs(diff)  # Higher diff = higher priority
                priorities.put((-priority, {  # Negative for max-heap behavior
                    "type": "eq",
                    "plugin": "Pro-Q 3",
                    "band": i,
                    "gain_db": float(gain),
                    "reason": f"Adjust mel band {i} by {gain:.1f}dB"
                }))
        
        # Compression: Constrain ratio ≤10:1
        dr_diff = reference_features['dynamic_range'] - target_features['dynamic_range']
        if abs(dr_diff) > 2:  # More sensitive threshold
            ratio = np.clip(2 + step_size * (dr_diff / 5), 2, 10)
            priority = abs(dr_diff)
            priorities.put((-priority, {
                "type": "compression",
                "plugin": "ReaComp",
                "ratio": float(ratio),
                "reduction_target": float(abs(dr_diff)),
                "reason": f"Match dynamics (dr_diff: {dr_diff:.1f}dB)"
            }))
        
        # Saturation: Use THD analysis
        sat_ref = analyze_saturation_character(reference_features)
        sat_tgt = analyze_saturation_character(target_features)
        thd_diff = sat_ref['amount'] - sat_tgt['amount']
        
        if abs(thd_diff) > 0.02:  # 2% THD difference
            drive = np.clip(0.2 + step_size * thd_diff, 0, 0.5)  # Limit to 50% drive (20% THD max)
            priority = abs(thd_diff) * 50  # Scale up for priority
            priorities.put((-priority, {
                "type": "saturation",
                "plugin": "Saturn 2",
                "drive": float(drive),
                "character": sat_ref['type'],
                "reason": f"Add {sat_ref['type']} saturation (THD: {sat_ref['amount']:.2f})"
            }))
        
        # Reverb: Use improved RT60 estimation
        if 'rt60' in reference_features and 'rt60' in target_features:
            decay_diff = reference_features['rt60'] - target_features['rt60']
            
            if abs(decay_diff) > 0.3:  # 300ms difference
                decay_val = np.clip(reference_features['rt60'] / 10, 0.1, 1.0)
                mix_val = reference_features.get('wet_dry', 0.3)
                priority = abs(decay_diff) * 2
                priorities.put((-priority, {
                    "type": "reverb",
                    "plugin": "Valhalla VintageVerb",
                    "decay": float(decay_val),
                    "mix": float(mix_val),
                    "reverb_type": reference_features.get('reverb_type', 'room'),
                    "reason": f"Match {reference_features.get('reverb_type', 'room')} reverb (RT60: {reference_features['rt60']:.1f}s)"
                }))
        
        # Stereo width
        corr_diff = reference_features['lr_correlation'] - target_features['lr_correlation']
        if abs(corr_diff) > 0.15:  # More sensitive
            width_value = 0.5 - (corr_diff / 2)
            priority = abs(corr_diff) * 5
            priorities.put((-priority, {
                "type": "stereo_width",
                "plugin": "Pro-Q 3",
                "width": float(np.clip(width_value, 0, 1)),
                "reason": f"Match stereo width (corr_diff: {corr_diff:.2f})"
            }))
        
        # Extract actions in priority order
        actions = []
        while not priorities.empty():
            _, action = priorities.get()
            actions.append(action)
        
        return actions
        
    except Exception as e:
        log_debug(f"Action calculation error: {e}")
        return []

def find_reference_file(filename):
    """
    Find reference audio file in project directories.
    Searches: references/, project root, temp_audio/
    """
    search_paths = [
        Path(REFERENCE_AUDIO_DIR) / filename,
        Path(r"C:\Users\moosb\AIAGENT DAW") / filename,
        Path(TEMP_AUDIO_DIR) / filename
    ]
    
    for path in search_paths:
        if path.exists():
            return str(path)
    
    # Try with common extensions
    for ext in ['.wav', '.mp3', '.flac']:
        for base_path in [Path(REFERENCE_AUDIO_DIR), Path(r"C:\Users\moosb\AIAGENT DAW")]:
            path = base_path / f"{filename}{ext}"
            if path.exists():
                return str(path)
    
    return None

def mel_band_to_frequency(mel_band_index, n_mels=40, sr=22050):
    """Convert mel band index to approximate center frequency in Hz"""
    # Mel scale conversion
    mel_points = librosa.mel_frequencies(n_mels=n_mels + 2, fmin=0, fmax=sr/2)
    if mel_band_index < len(mel_points) - 1:
        return float((mel_points[mel_band_index] + mel_points[mel_band_index + 1]) / 2)
    return float(mel_points[-1])

def actions_to_reaper_commands(actions, track_idx):
    """
    Convert action dicts to actual Reaper commands.
    Returns list of command strings.
    """
    commands = []
    eq_bands_used = 0  # Track which Pro-Q bands we've used
    
    for action in actions:
        action_type = action.get('type')
        
        if action_type == 'eq':
            # EQ adjustment
            if eq_bands_used == 0:
                # First EQ action - add Pro-Q 3
                commands.append(f"ADD_FX {track_idx} FabFilter Pro-Q 3")
            
            # Map mel band to frequency
            mel_band = action.get('band', 0)
            freq_hz = mel_band_to_frequency(mel_band)
            gain_db = action.get('gain_db', 0)
            
            # Use Pro-Q band (we have 24 bands available, use them sequentially)
            if eq_bands_used < 24:
                band_idx = eq_bands_used
                
                # Pro-Q 3 band parameters (13 params per band):
                # p(band*13 + 0): Used (on/off)
                # p(band*13 + 1): Frequency
                # p(band*13 + 2): Gain
                # p(band*13 + 8): Type (bell/shelf/etc)
                
                param_base = band_idx * 13
                
                # Enable band
                commands.append(f"SET_FX_PARAM {track_idx} 0 {param_base} 1.0")
                
                # Set frequency (normalized 20Hz-20kHz)
                freq_normalized = (np.log10(freq_hz) - np.log10(20)) / (np.log10(20000) - np.log10(20))
                freq_normalized = np.clip(freq_normalized, 0, 1)
                commands.append(f"SET_FX_PARAM {track_idx} 0 {param_base + 1} {freq_normalized:.4f}")
                
                # Set gain (±12dB range typically, 0.5 = 0dB)
                gain_normalized = np.clip((gain_db + 12) / 24, 0, 1)
                commands.append(f"SET_FX_PARAM {track_idx} 0 {param_base + 2} {gain_normalized:.4f}")
                
                # Set to Bell type (0.17 typically)
                commands.append(f"SET_FX_PARAM {track_idx} 0 {param_base + 8} 0.17")
                
                eq_bands_used += 1
        
        elif action_type == 'compression':
            # Add compressor
            commands.append(f"ADD_FX {track_idx} ReaComp")
            
            # ReaComp params (approximate - would need exact mapping)
            ratio = action.get('ratio', 4.0)
            # Ratio param: usually 0-1 where 0.2 = 2:1, 0.4 = 4:1, 0.8 = 10:1
            ratio_normalized = ratio / 12  # Rough approximation
            commands.append(f"SET_FX_PARAM {track_idx} 1 1 {ratio_normalized:.4f}")  # Param 1 is often ratio
            
            # Threshold (around -20dB)
            commands.append(f"SET_FX_PARAM {track_idx} 1 0 0.6")  # Param 0 is often threshold
        
        elif action_type == 'saturation':
            # Add Saturn
            commands.append(f"ADD_FX {track_idx} FabFilter Saturn 2")
            drive = action.get('drive', 0.3)
            
            # Saturn drive param (would need exact index from state)
            # Assuming param 0 or similar
            commands.append(f"SET_FX_PARAM {track_idx} 2 0 {drive:.4f}")
        
        elif action_type == 'reverb':
            # Add Valhalla VintageVerb
            commands.append(f"ADD_FX {track_idx} Valhalla VintageVerb")
            
            decay = action.get('decay', 0.5)
            mix_val = action.get('mix', 0.3)
            
            # Valhalla params (would need exact mapping)
            commands.append(f"SET_FX_PARAM {track_idx} 3 0 {decay:.4f}")  # Decay param
            commands.append(f"SET_FX_PARAM {track_idx} 3 1 {mix_val:.4f}")  # Mix param
        
        elif action_type == 'stereo_width':
            # Could use various plugins - for now skip or use Pro-Q mid-side
            pass
    
    return commands

def download_streaming_audio(url, output_dir="temp_audio"):
    """
    Download audio from streaming URL using yt-dlp.
    Supports: YouTube, TikTok, Instagram, SoundCloud, Spotify, and many more.
    Returns path to downloaded audio file or None if failed.
    """
    try:
        import yt_dlp
        
        output_path = Path(output_dir) / "youtube_reference"
        output_path.mkdir(parents=True, exist_ok=True)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'outtmpl': str(output_path / '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
        }
        
        print(f"📥 Downloading audio from URL...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Replace extension with .wav
            wav_file = Path(filename).with_suffix('.wav')
            
        if wav_file.exists():
            print(f"✅ Downloaded: {wav_file.name}")
            return str(wav_file)
        else:
            print(f"❌ Download failed")
            return None
            
    except ImportError:
        print(f"❌ yt-dlp not installed. Install with: pip install yt-dlp")
        return None
    except Exception as e:
        print(f"❌ YouTube download error: {e}")
        log_debug(f"YouTube download error: {e}")
        return None

def match_to_reference(track_idx, reference_audio_path, max_iterations=15, target_similarity=85.0):
    """
    Iteratively adjust track to match reference audio.
    Supports YouTube URLs, file paths, and filenames in references/ folder.
    Returns final similarity score and list of actions taken.
    """
    # Check if it's a streaming URL (YouTube, TikTok, Instagram, SoundCloud, etc.)
    url_platforms = ["youtube.com", "youtu.be", "tiktok.com", "instagram.com", "soundcloud.com", "spotify.com"]
    if any(platform in reference_audio_path.lower() for platform in url_platforms):
        print(f"🎵 Streaming URL detected!")
        downloaded_path = download_streaming_audio(reference_audio_path)
        if not downloaded_path:
            return {"error": "Audio download failed"}
        reference_audio_path = downloaded_path
    
    # Check if reference exists as absolute path first
    ref_path = Path(reference_audio_path)
    
    if ref_path.exists() and ref_path.is_file():
        # Full path provided and exists
        reference_audio_path = str(ref_path)
    elif not ref_path.is_absolute():
        # Relative path or just filename - search for it
        found_path = find_reference_file(reference_audio_path)
        if found_path:
            reference_audio_path = found_path
            print(f"📁 Found reference: {reference_audio_path}")
        else:
            print(f"❌ Reference file not found: {reference_audio_path}")
            print(f"   Searched in: references/, project root")
            print(f"   Put your reference audio in: {REFERENCE_AUDIO_DIR}")
            return {"error": "Reference file not found"}
    else:
        # Absolute path but doesn't exist
        print(f"❌ Reference file not found: {reference_audio_path}")
        print(f"   File does not exist at specified path")
        return {"error": "Reference file not found"}
    
    print(f"\n🎯 Starting reference matching for track {track_idx}")
    print(f"📁 Reference: {reference_audio_path}")
    
    if not AUDIO_ANALYSIS_AVAILABLE:
        print("❌ Audio analysis not available - install librosa")
        return {"error": "librosa not installed"}
    
    # Export track first to get audio file for analysis
    print(f"📤 Exporting track {track_idx}...")
    Path(TEMP_AUDIO_DIR).mkdir(exist_ok=True)
    track_audio_folder = Path(TEMP_AUDIO_DIR) / f"track_{track_idx}_{int(time.time())}"
    
    send_reaper_commands(["1007"])  # Play
    time.sleep(0.5)
    
    if not send_reaper_commands([f"EXPORT_AUDIO {track_idx} {track_audio_folder}"]):
        print("❌ Failed to export track")
        return {"error": "Export failed"}
    
    time.sleep(2.0)
    
    wav_files = list(track_audio_folder.glob("*.wav")) if track_audio_folder.exists() else []
    if not wav_files:
        print("❌ No exported audio found")
        return {"error": "No audio file"}
    
    track_audio_path = str(wav_files[0])
    
    # Use pure librosa-based matching with comprehensive effect detection
    result = librosa_based_reference_matching(
        track_idx, 
        reference_audio_path, 
        track_audio_path,
        target_similarity=target_similarity,
        max_iterations=max_iterations
    )
    
    # Cleanup
    try:
        for folder in Path(TEMP_AUDIO_DIR).glob(f"track_{track_idx}_*"):
            shutil.rmtree(folder)
    except:
        pass
    
    return result

def match_to_reference_OLD_FREQUENCY_BASED(track_idx, reference_audio_path, max_iterations=15, target_similarity=85.0):
    """
    OLD APPROACH - Frequency-based matching (too technical, doesn't work well)
    Kept for reference but not used anymore.
    """
    try:
        # Extract reference features
        print(f"🔬 Analyzing reference audio...")
        reference_features = extract_detailed_features(reference_audio_path)
        
        if not reference_features:
            print("❌ Failed to extract reference features")
            return {"error": "Could not analyze reference"}
        
        # Export current track audio
        print(f"📤 Exporting track {track_idx}...")
        Path(TEMP_AUDIO_DIR).mkdir(exist_ok=True)
        track_audio_folder = Path(TEMP_AUDIO_DIR) / f"track_{track_idx}_{int(time.time())}"
        
        send_reaper_commands(["1007"])  # Play
        time.sleep(0.5)
        
        if not send_reaper_commands([f"EXPORT_AUDIO {track_idx} {track_audio_folder}"]):
            print("❌ Failed to export track")
            return {"error": "Export failed"}
        
        time.sleep(2.0)
        
        wav_files = list(track_audio_folder.glob("*.wav")) if track_audio_folder.exists() else []
        if not wav_files:
            print("❌ No exported audio found")
            return {"error": "No audio file"}
        
        track_audio_path = str(wav_files[0])
        
        # Iterative matching loop
        iteration = 0
        best_similarity = 0.0
        actions_history = []
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Iteration {iteration}/{max_iterations}")
            
            # Analyze current track
            print(f"   Analyzing current state...")
            current_features = extract_detailed_features(track_audio_path)
            
            if not current_features:
                print("   ❌ Failed to analyze current track")
                break
            
            # Calculate similarity
            similarity = calculate_similarity(reference_features, current_features)
            print(f"   📊 Similarity: {similarity:.1f}%")
            
            if similarity > best_similarity:
                best_similarity = similarity
            
            # Check if we've reached target
            if similarity >= target_similarity:
                print(f"\n✅ Target similarity reached: {similarity:.1f}% >= {target_similarity}%")
                break
            
            # Calculate next actions
            print(f"   🧠 Calculating adjustments...")
            actions = calculate_mixing_actions(reference_features, current_features)
            
            if not actions:
                print(f"   ⚠️ No more actions to take - stopping at {similarity:.1f}%")
                break
            
            # Convert actions to Reaper commands
            print(f"   ⚡ Applying {len(actions)} adjustment(s)...")
            
            # Show what we're doing
            for action in actions[:5]:  # Show first 5
                print(f"      • {action['type']}: {action['reason']}")
            if len(actions) > 5:
                print(f"      ... and {len(actions) - 5} more adjustments")
            
            # Translate to Reaper commands
            reaper_commands = actions_to_reaper_commands(actions, track_idx)
            
            if reaper_commands:
                # Save snapshot before changes
                save_state_snapshot(f"ref_match_iter_{iteration}")
                
                # Execute commands
                if send_reaper_commands(reaper_commands):
                    print(f"   ✅ Applied {len(reaper_commands)} commands to Reaper")
                    time.sleep(2.0)  # Wait for plugins to load
                else:
                    print(f"   ❌ Failed to send commands")
                    break
            
            # Store in history
            for action in actions:
                actions_history.append({
                    "iteration": iteration,
                    "similarity_before": similarity,
                    "action": action
                })
            
            # Re-export after changes for next iteration
            track_audio_folder = Path(TEMP_AUDIO_DIR) / f"track_{track_idx}_{int(time.time())}"
            if not send_reaper_commands([f"EXPORT_AUDIO {track_idx} {track_audio_folder}"]):
                break
            time.sleep(2.0)
            wav_files = list(track_audio_folder.glob("*.wav")) if track_audio_folder.exists() else []
            if wav_files:
                track_audio_path = str(wav_files[0])
            else:
                break
        
        print(f"\n🏁 Reference matching complete!")
        print(f"   Final similarity: {best_similarity:.1f}%")
        print(f"   Iterations: {iteration}")
        print(f"   Actions taken: {len(actions_history)}")
        
        # Cleanup temp folders
        try:
            for folder in Path(TEMP_AUDIO_DIR).glob(f"track_{track_idx}_*"):
                shutil.rmtree(folder)
        except:
            pass
        
        return {
            "final_similarity": best_similarity,
            "iterations": iteration,
            "actions_history": actions_history,
            "target_reached": best_similarity >= target_similarity
        }
        
    except Exception as e:
        log_debug(f"Reference matching error: {e}")
        print(f"❌ Error during reference matching: {e}")
        return {"error": str(e)}

# ==================== LIBROSA-BASED REFERENCE MATCHING SYSTEM ====================
# Pure librosa audio analysis - no MERT, no CLAP similarity scores
# Detects actual, actionable production characteristics

# ========== COMPREHENSIVE EFFECT DETECTORS ==========

def detect_frequency_filtering(audio_path):
    """
    Detect filtering using percentile-based cutoffs so both HP and LP are always estimated.
    - high_pass: frequency at 5% cumulative energy
    - low_pass: frequency at 95% cumulative energy
    - character: telephone/bandpass/high_passed/low_passed/full_range
    - confidence: 0-1 based on steepness around the cutoffs
    """
    try:
        y, sr = librosa.load(audio_path, sr=44100, mono=True, duration=30)
        S = np.abs(librosa.stft(y, n_fft=4096, hop_length=1024))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
        spec = np.mean(S, axis=1)

        # Power normalization and cumulative distribution
        power = spec.astype(float) + 1e-12
        power /= np.sum(power)
        cdf = np.cumsum(power)

        # Percentile cutoffs
        def freq_at_percentile(p):
            idx = np.searchsorted(cdf, p)
            idx = int(np.clip(idx, 0, len(freqs) - 1))
            return float(freqs[idx])

        hp = freq_at_percentile(0.05)
        lp = freq_at_percentile(0.95)

        # Confidence from local slope around the cutoffs
        def local_slope(idx_window):
            i0 = max(1, idx_window - 2)
            i1 = min(len(power) - 2, idx_window + 2)
            x = freqs[i0:i1+1]
            yv = librosa.power_to_db(power[i0:i1+1] * np.max(spec) + 1e-12, ref=np.max(spec) + 1e-12)
            if len(x) < 3:
                return 0.0
            # simple slope magnitude proxy
            return float(np.abs((yv[-1] - yv[0]) / (x[-1] - x[0] + 1e-6)))

        hp_idx = int(np.searchsorted(freqs, hp))
        lp_idx = int(np.searchsorted(freqs, lp))
        slope_hp = local_slope(hp_idx)
        slope_lp = local_slope(lp_idx)
        confidence = float(np.clip((slope_hp + slope_lp) * 1000.0, 0.0, 1.0))

        # Character classification
        character = "full_range"
        if hp > 150 and lp < 6000:
            # Some degree of band-limiting
            if 200 <= hp <= 500 and 2000 <= lp <= 4500:
                character = "telephone"
            else:
                character = "bandpass"
        elif hp > 150:
            character = "high_passed"
        elif lp < 12000:
            character = "low_passed"

        return {
            "high_pass": int(hp),
            "low_pass": int(lp),
            "character": character,
            "confidence": confidence
        }
    except Exception as e:
        log_debug(f"Frequency filtering detection error: {e}")
        return {"high_pass": None, "low_pass": None, "character": "unknown", "confidence": 0.0}

def detect_distortion_amount(audio_path):
    """
    Detect distortion/saturation level (0-100) and type hint.
    Uses harmonic analysis - more harmonics = more distortion.
    Returns dict with amount, even/odd harmonic ratio, and type hint.
    """
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=30)
        
        # Harmonic analysis
        y_harm, y_perc = librosa.effects.hpss(y)
        
        # Calculate THD (Total Harmonic Distortion) approximation
        harmonic_energy = np.mean(np.abs(y_harm))
        
        # Zero-crossing rate (distortion creates more crossings)
        zcr = np.mean(librosa.feature.zero_crossing_rate(y))
        
        # Even vs odd harmonics (for type detection)
        # Get FFT to analyze harmonic content
        fft = np.fft.rfft(y_harm)
        freqs_fft = np.fft.rfftfreq(len(y_harm), 1/sr)
        
        # Fundamental frequency estimate (crude)
        f0_idx = np.argmax(np.abs(fft[10:100])) + 10  # Skip DC, look in ~200-2kHz
        f0 = freqs_fft[f0_idx] if f0_idx < len(freqs_fft) else 100
        
        # Even harmonics (2f0, 4f0, 6f0) vs odd (3f0, 5f0, 7f0)
        even_energy = 0.0
        odd_energy = 0.0
        
        for n in range(2, 8):
            harmonic_freq = f0 * n
            idx = np.argmin(np.abs(freqs_fft - harmonic_freq))
            if idx < len(fft):
                if n % 2 == 0:
                    even_energy += np.abs(fft[idx])
                else:
                    odd_energy += np.abs(fft[idx])
        
        # Ratio (tube = more even, tape = more odd)
        if odd_energy > 0:
            even_odd_ratio = even_energy / odd_energy
        else:
            even_odd_ratio = 1.0
        
        # Type hint
        type_hint = "neutral"
        if even_odd_ratio > 1.3:
            type_hint = "tube-like"  # Even harmonics dominate
        elif even_odd_ratio < 0.7:
            type_hint = "tape-like"  # Odd harmonics dominate
        
        # Combine metrics (normalize to 0-100)
        distortion_amount = min(100, (harmonic_energy * 1000 + zcr * 100))
        
        return {
            "amount": float(distortion_amount),
            "even_odd_ratio": float(even_odd_ratio),
            "type_hint": type_hint
        }
    
    except Exception as e:
        log_debug(f"Distortion detection error: {e}")
        return {"amount": 0.0, "even_odd_ratio": 1.0, "type_hint": "neutral"}

def detect_delay_settings(audio_path):
    """
    Detect delay presence and actual settings (time in ms, feedback estimate).
    Uses autocorrelation to find rhythmic repetitions.
    """
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=30)
        
        # Autocorrelation to find repetitions
        autocorr = librosa.autocorrelate(y)
        
        # Find peaks (excluding the first one at lag=0)
        from scipy.signal import find_peaks
        peaks, properties = find_peaks(autocorr[sr//10:], height=np.max(autocorr)*0.15)
        
        if len(peaks) > 0:
            # First significant peak = delay time
            first_peak_samples = peaks[0] + sr//10  # Add back the offset
            delay_time_ms = int((first_peak_samples / sr) * 1000)
            
            # Estimate feedback from peak height decay
            peak_heights = properties['peak_heights']
            if len(peak_heights) > 1:
                # Ratio of second to first peak
                feedback = min(100, int((peak_heights[1] / peak_heights[0]) * 100))
            else:
                feedback = 30  # Default moderate feedback
            
            # Estimate mix from overall energy with/without delay
            mix = min(50, int(np.mean(peak_heights) / np.max(autocorr) * 100))
            
            return {
                "present": True,
                "delay_time_ms": delay_time_ms,
                "feedback": feedback,
                "mix": mix
            }
        else:
            return {
                "present": False,
                "delay_time_ms": 0,
                "feedback": 0,
                "mix": 0
            }
    
    except Exception as e:
        log_debug(f"Delay detection error: {e}")
        return {"present": False, "delay_time_ms": 0, "feedback": 0, "mix": 0}

def detect_reverb_settings(audio_path):
    """
    Detect reverb presence and settings using envelope decay and clarity metrics.
    - T60 (approx) from envelope decay slope (Hilbert envelope, dB/s)
    - C50/C80 clarity (early vs late energy)
    - Predelay (rough): time to 95%->80% drop from peak after onset
    - Mix estimate from late/early ratio
    Returns dict with present, decay_time, predelay_ms, c50_db, c80_db, mix, confidence.
    """
    try:
        y, sr = librosa.load(audio_path, sr=44100, mono=True, duration=30)

        # Onsets to segment analysis windows
        onset_samples = librosa.onset.onset_detect(y=y, sr=sr, units='samples')
        if len(onset_samples) < 2:
            # fallback: treat the whole file as one segment
            onset_samples = np.array([0, min(len(y)-1, int(2.0*sr))])

        # Hilbert envelope
        from scipy.signal import hilbert
        env = np.abs(hilbert(y)) + 1e-9

        t60_list = []
        c50_list = []
        c80_list = []
        predelay_list = []
        late_early_list = []

        # Analyze up to N segments to avoid long processing
        N = min(20, len(onset_samples)-1)
        for i in range(N):
            start = onset_samples[i]
            end = onset_samples[i+1]
            # analyze up to 2s after onset
            end = min(end, start + int(2.0 * sr))
            if end - start < int(0.1 * sr):
                continue

            seg_env = env[start:end]
            seg_env_db = 20.0 * np.log10(seg_env / np.max(seg_env))
            t = np.arange(len(seg_env_db)) / sr

            # Fit linear decay on the portion below -5 dB from peak to -25 dB
            mask = (seg_env_db < -5) & (seg_env_db > -35)
            if np.sum(mask) > int(0.05 * len(seg_env_db)):
                x = t[mask]
                ydb = seg_env_db[mask]
                # linear fit y = a*x + b
                a, b = np.polyfit(x, ydb, 1)
                if a < -1e-3:  # negative slope => decay
                    t60 = -60.0 / a
                    if 0.1 <= t60 <= 10.0:
                        t60_list.append(t60)

            # Predelay estimate: time to fall from 0 dB to -1 dB then to -6 dB
            idx_m1 = np.argmax(seg_env_db < -1.0)
            idx_m6 = np.argmax(seg_env_db < -6.0)
            if idx_m1 > 0 and idx_m6 > idx_m1:
                predelay_ms = (idx_m6 - idx_m1) * 1000.0 / sr
                predelay_list.append(predelay_ms)

            # Clarity: early (0-50ms/80ms) vs late energy
            win = min(len(seg_env), int(1.0 * sr))  # 1s window
            seg = seg_env[:win]
            idx50 = min(len(seg)-1, int(0.050 * sr))
            idx80 = min(len(seg)-1, int(0.080 * sr))
            E_total = np.sum(seg**2) + 1e-12
            E_early50 = np.sum(seg[:idx50]**2) + 1e-12
            E_early80 = np.sum(seg[:idx80]**2) + 1e-12
            E_late50 = np.sum(seg[idx50:]**2) + 1e-12
            E_late80 = np.sum(seg[idx80:]**2) + 1e-12
            c50 = 10.0 * np.log10(E_early50 / E_late50)
            c80 = 10.0 * np.log10(E_early80 / E_late80)
            c50_list.append(c50)
            c80_list.append(c80)
            late_early_list.append(float(E_late80 / E_early80))

        # Aggregate
        decay_time = float(np.median(t60_list)) if t60_list else 0.0
        c50_db = float(np.median(c50_list)) if c50_list else 0.0
        c80_db = float(np.median(c80_list)) if c80_list else 0.0
        predelay_ms = float(np.median(predelay_list)) if predelay_list else 0.0
        late_early = float(np.median(late_early_list)) if late_early_list else 0.0

        # Essentia dynamic complexity can hint reverberance (higher late energy)
        if ESSENTIA_AVAILABLE:
            try:
                audio_es = es.MonoLoader(filename=audio_path)()
                dyn = es.DynamicComplexity(frameSize=2048, hopSize=512)
                dc_val, _ = dyn(audio_es)
            except Exception:
                dc_val = 0.0
        else:
            dc_val = 0.0

        # Presence decision & mix estimate
        present = (decay_time >= 0.6) or (c50_db < -3.0) or (late_early > 0.8)
        # Map late/early ratio to mix (rough 0-50%)
        mix = int(np.clip((late_early - 0.5) * 100, 0, 50))
        confidence = float(np.clip((decay_time/3.0) + (-(c50_db)/6.0) + (late_early/2.0) + (dc_val/10.0), 0.0, 1.0))

        return {
            "present": bool(present),
            "decay_time": round(decay_time, 2),
            "predelay_ms": round(predelay_ms, 1),
            "c50_db": round(c50_db, 2),
            "c80_db": round(c80_db, 2),
            "mix": int(mix),
            "confidence": confidence
        }

    except Exception as e:
        log_debug(f"Reverb detection error: {e}")
        return {"present": False, "decay_time": 0.0, "predelay_ms": 0.0, "c50_db": 0.0, "c80_db": 0.0, "mix": 0, "confidence": 0.0}

def classify_audio_type(audio_path):
    """
    Classify audio type using PANNs (most accurate).
    Falls back to librosa if PANNs not available.
    Maps AudioSet classes to: vocal, synth_pad, synth_lead, guitar, bass, drums, mix, unknown
    """
    try:
        # PANNs classification (best accuracy: 85-95%)
        if PANNS_AVAILABLE:
            # Load audio at 32kHz (PANNs requirement)
            y, sr = librosa.load(audio_path, sr=32000, mono=True, duration=30)
            y = y[np.newaxis, :]  # Add batch dimension
            
            # Run inference
            clipwise_output, _ = panns_model.inference(y)
            scores = clipwise_output[0]  # Shape: (527,) - one score per AudioSet class
            
            # AudioSet class indices (from PANNs labels)
            # Map relevant classes to our categories
            AUDIOSET_MAPPING = {
                # Index: (AudioSet class, our category)
                0: ("Speech", "vocal"),
                1: ("Male speech, man speaking", "vocal"),
                2: ("Female speech, woman speaking", "vocal"),
                3: ("Child speech, kid speaking", "vocal"),
                137: ("Singing", "vocal"),
                138: ("Choir", "vocal"),
                300: ("Synthesizer", "synth"),
                38: ("Music", None),  # Too generic
                421: ("Guitar", "guitar"),
                422: ("Electric guitar", "guitar"),
                423: ("Bass guitar", "bass"),
                424: ("Acoustic guitar", "guitar"),
                426: ("Drum", "drums"),
                427: ("Drum kit", "drums"),
                428: ("Drum machine", "drums"),
                429: ("Snare drum", "drums"),
                430: ("Rimshot", "drums"),
                431: ("Bass drum", "drums"),
                442: ("Cymbal", "drums"),
            }
            
            # Collect scores for each of our categories
            category_scores = {
                "vocal": 0.0,
                "synth": 0.0,
                "guitar": 0.0,
                "bass": 0.0,
                "drums": 0.0
            }
            
            for idx, (audioset_class, our_category) in AUDIOSET_MAPPING.items():
                if our_category and idx < len(scores):
                    category_scores[our_category] = max(category_scores[our_category], scores[idx])
            
            # Find highest scoring category
            best_category = max(category_scores.items(), key=lambda x: x[1])
            
            # DEBUG: Show top scores from AudioSet
            top_indices = np.argsort(scores)[-10:][::-1]  # Top 10
            print(f"  🔍 PANNs top detections:")
            for idx in top_indices:
                print(f"     Class {idx}: {scores[idx]:.3f}")
            print(f"  📊 Category scores: {category_scores}")
            print(f"  🎯 Best: {best_category[0]} ({best_category[1]:.3f})")
            
            # Mix detection: Multiple categories scoring high
            high_scores = [cat for cat, score in category_scores.items() if score > 0.3]
            if len(high_scores) >= 2:
                return "mix"
            
            # Synth pad vs lead distinction (use librosa features)
            if best_category[0] == "synth" and best_category[1] > 0.4:
                # Load again for feature analysis
                y_analysis, sr_analysis = librosa.load(audio_path, sr=22050, mono=True, duration=30)
                onset_env = librosa.onset.onset_strength(y=y_analysis, sr=sr_analysis)
                onset_rate = np.sum(onset_env > np.mean(onset_env) * 1.5) / (len(y_analysis) / sr_analysis)
                
                # Pad = sustained, few onsets; Lead = more movement
                if onset_rate < 0.5:
                    return "synth_pad"
                else:
                    return "synth_lead"
            
            # Lower threshold for vocals (they're often more subtle)
            threshold = 0.15 if best_category[0] == "vocal" else 0.25
            return best_category[0] if best_category[1] > threshold else "unknown"
        
        # Fallback: Simple librosa classification
        else:
            y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=30)
            
            # Basic features
            y_harm, y_perc = librosa.effects.hpss(y)
            hp_ratio = np.sum(y_harm**2) / (np.sum(y_perc**2) + 1e-10)
            centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            onset_strength = np.mean(onset_env)
            
            # Simple classification
            if hp_ratio < 2 and onset_strength > 8:
                return "drums"
            elif centroid < 500 and hp_ratio > 3:
                return "bass"
            elif hp_ratio > 4 and onset_strength < 3:
                return "synth_pad" if centroid < 1500 else "synth_lead"
            elif hp_ratio > 5 and 1500 < centroid < 4000:
                return "vocal"
            else:
                return "instrument"
    
    except Exception as e:
        log_debug(f"Audio type classification error: {e}")
        return "unknown"

def detect_bpm_and_beats(audio_path):
    """
    Detect tempo (BPM) and beat times (seconds).
    Uses Essentia if available; falls back to librosa.
    """
    try:
        if ESSENTIA_AVAILABLE:
            audio = es.MonoLoader(filename=audio_path)()
            rhythm = es.RhythmExtractor2013(method='multifeature')
            bpm, beats, _, _, _ = rhythm(audio)
            return float(bpm), [float(t) for t in beats]
        else:
            y, sr = librosa.load(audio_path, sr=44100, mono=True, duration=30)
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            # Safely convert tempo to scalar
            tempo = float(np.asarray(tempo).ravel()[0]) if np.size(tempo) else 0.0
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            return tempo, [float(t) for t in beat_times]
    except Exception as e:
        log_debug(f"BPM detection error: {e}")
        return 0.0, []

def map_delay_ms_to_note_value(delay_ms, bpm):
    """
    Map delay time in ms to closest musical note value given BPM.
    Returns {'label': '1/4', 'ms_target': 375, 'error_ms': 5}.
    """
    if bpm <= 0 or delay_ms <= 0:
        return {"label": None, "ms_target": 0, "error_ms": 0}
    # Note multipliers relative to quarter note
    note_defs = {
        "1": 4.0, "1/2": 2.0, "1/4": 1.0, "1/8": 0.5, "1/16": 0.25, "1/32": 0.125,
        "1/4 dotted": 1.5, "1/8 dotted": 0.75, "1/16 dotted": 0.375,
        "1/4 triplet": 2.0/3.0, "1/8 triplet": 1.0/3.0, "1/16 triplet": 1.0/6.0
    }
    q_ms = 60000.0 / bpm  # quarter note in ms
    best = None
    best_err = 1e9
    best_ms = 0
    for label, mult in note_defs.items():
        ms = q_ms * mult
        err = abs(ms - delay_ms)
        if err < best_err:
            best = label
            best_err = err
            best_ms = ms
    return {"label": best, "ms_target": int(best_ms), "error_ms": int(best_err)}

def compute_spectral_indices(audio_path):
    """
    Compute practical spectral indices: mud (200-500Hz), boxiness (500-800Hz),
    presence (3-6kHz), air (8-11kHz), plus flatness and rolloff.
    Returns 0-100 scaled scores.
    """
    try:
        # Use higher sr to reach up to ~11kHz for 'air'
        y, sr = librosa.load(audio_path, sr=44100, mono=True, duration=30)
        S = np.abs(librosa.stft(y, n_fft=4096))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)

        def band_db(low, high):
            mask = (freqs >= low) & (freqs < high)
            if not np.any(mask):
                return -120.0
            val = np.mean(S[mask, :])
            return float(librosa.amplitude_to_db([val], ref=np.max(S)+1e-9)[0])

        mud_db = band_db(200, 500)
        box_db = band_db(500, 800)
        pres_db = band_db(3000, 6000)
        air_db = band_db(8000, 11000)
        mid_db = band_db(800, 2000)

        def rel_score(band_db, ref_db):
            # Positive if band louder than ref; scale ~10dB -> 100
            return float(np.clip((band_db - ref_db + 10) * 5, 0, 100))

        indices = {
            "mud": rel_score(mud_db, mid_db),
            "boxiness": rel_score(box_db, mid_db),
            "presence": rel_score(pres_db, mid_db),
            "air": rel_score(air_db, pres_db)
        }

        # Essentia extras if available
        if ESSENTIA_AVAILABLE:
            audio = es.MonoLoader(filename=audio_path, sampleRate=44100)()
            w = es.Windowing(type='hann')
            spec = es.Spectrum()
            flat = es.Flatness()
            roll = es.RollOff(minBandwidth=20.0, sampleRate=44100)
            # Single-frame overview
            frame = w(audio[:4096])
            spectrum = spec(frame)
            indices["flatness"] = float(flat(spectrum)) * 100.0
            indices["rolloff_hz"] = float(roll(spectrum))
        else:
            # Librosa approximations
            flatness = librosa.feature.spectral_flatness(y=y)
            indices["flatness"] = float(np.mean(flatness)) * 100.0
            rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
            indices["rolloff_hz"] = float(np.mean(rolloff))

        return indices
    except Exception as e:
        log_debug(f"Spectral indices error: {e}")
        return {"mud": 0, "boxiness": 0, "presence": 0, "air": 0, "flatness": 0, "rolloff_hz": 0}

def detect_compression_amount(audio_path):
    """
    Detect compression using p95-p5 of short-term RMS (Gemini's method).
    Returns dict with compression_percent and dynamic_range_db (real measurement).
    Fixes false positives on sustained synths.
    """
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=30)
        
        # Short-term RMS (frame ~50ms)
        frame_length = int(0.050 * sr)
        hop_length = int(0.030 * sr)
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        
        if len(rms) == 0:
            return {"compression_percent": 0.0, "dynamic_range_db": 30.0}
        
        # Convert to dB
        rms_db = librosa.amplitude_to_db(rms + 1e-12, ref=np.max(rms) + 1e-12)
        
        # Filter out silence (below -50dB)
        rms_db_active = rms_db[rms_db > -50]
        
        if len(rms_db_active) < 10:
            return {"compression_percent": 0.0, "dynamic_range_db": 30.0}
        
        # Dynamic range = p95 - p5 (Gemini's method)
        p95 = np.percentile(rms_db_active, 95)
        p5 = np.percentile(rms_db_active, 5)
        dynamic_range_db = float(p95 - p5)
        
        # Map to compression percent
        # 3dB = heavily compressed (95%), 30dB = dynamic (0%)
        compression_percent = float(np.clip(100.0 - ((dynamic_range_db - 3.0) / 27.0) * 100.0, 0.0, 100.0))
        
        return {
            "compression_percent": round(compression_percent, 1),
            "dynamic_range_db": round(dynamic_range_db, 1)
        }
    
    except Exception as e:
        log_debug(f"Compression detection error: {e}")
        return {"compression_percent": 0.0, "dynamic_range_db": 30.0}

def detect_brightness(audio_path):
    """
    Detect brightness level (0-100).
    Uses spectral centroid - higher = brighter.
    """
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=30)
        
        # Spectral centroid (center of mass of spectrum)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        
        # Normalize to 0-100 (typical range 1000-4000 Hz)
        brightness = min(100, (np.mean(centroid) - 1000) / 30)
        
        return float(max(0, brightness))
    
    except Exception as e:
        log_debug(f"Brightness detection error: {e}")
        return 50.0

def detect_autotune_presence(audio_path):
    """
    Detect autotune/pitch correction presence (0-100).
    Looks for unnatural pitch quantization.
    """
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=30)
        
        # Pitch tracking
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        
        # Extract pitch values
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        if len(pitch_values) < 10:
            return 0.0
        
        # Autotune creates quantized pitches (less variation within notes)
        pitch_diff = np.diff(pitch_values)
        stability = 1 / (np.std(pitch_diff) + 1)
        
        # High stability = likely autotuned
        autotune_amount = min(100, stability * 20)
        
        return float(autotune_amount)
    
    except Exception as e:
        log_debug(f"Autotune detection error: {e}")
        return 0.0

def detect_stereo_metrics(audio_path):
    """
    Detect stereo imaging characteristics.
    Returns L/R correlation, M/S balance, width in low/high frequencies.
    """
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=False, duration=30)
        
        # Check if stereo
        if y.ndim == 1 or y.shape[0] == 1:
            return {
                "lr_corr": 1.0,
                "ms_balance": 0.5,
                "width_low": 0.0,
                "width_high": 0.0
            }
        
        left = y[0]
        right = y[1]
        
        # L/R correlation (-1 to 1, 1=mono, 0=uncorrelated, -1=inverted)
        lr_corr = float(np.corrcoef(left, right)[0, 1])
        
        # Mid/Side
        mid = (left + right) / np.sqrt(2)
        side = (left - right) / np.sqrt(2)
        
        # M/S balance (0=all side, 1=all mid)
        mid_energy = np.mean(np.abs(mid))
        side_energy = np.mean(np.abs(side))
        ms_balance = float(mid_energy / (mid_energy + side_energy + 1e-10))
        
        # Width in low vs high frequencies
        S_side = np.abs(librosa.stft(side))
        freqs = librosa.fft_frequencies(sr=sr)
        
        low_mask = freqs < 500
        high_mask = freqs > 2000
        
        width_low = float(np.mean(S_side[low_mask]) * 100) if np.any(low_mask) else 0.0
        width_high = float(np.mean(S_side[high_mask]) * 100) if np.any(high_mask) else 0.0
        
        return {
            "lr_corr": float(lr_corr),
            "ms_balance": float(ms_balance),
            "width_low": float(width_low),
            "width_high": float(width_high)
        }
    
    except Exception as e:
        log_debug(f"Stereo metrics error: {e}")
        return {"lr_corr": 1.0, "ms_balance": 0.5, "width_low": 0.0, "width_high": 0.0}

def detect_deessing_need(audio_path):
    """
    Detect if de-essing is needed.
    Analyzes sibilant frequency range (5-9 kHz) variance vs overall.
    Returns need_score (0-100) and target_khz.
    """
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=30)
        
        # Get spectrogram
        S = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)
        
        # Sibilant range (5-9 kHz)
        sib_mask = (freqs >= 5000) & (freqs <= 9000)
        
        if not np.any(sib_mask):
            return {"need_score": 0.0, "target_khz": 7.0}
        
        # Variance in sibilant range vs overall
        sib_energy = np.mean(S[sib_mask], axis=0)
        full_energy = np.mean(S, axis=0)
        
        sib_var = np.var(sib_energy)
        full_var = np.var(full_energy)
        
        # High variance in sibilant range = harsh sibilance
        if full_var > 0:
            need_score = float(np.clip((sib_var / full_var) * 100, 0, 100))
        else:
            need_score = 0.0
        
        # Target frequency (peak in sibilant range)
        sib_avg = np.mean(S[sib_mask], axis=1)
        target_idx = np.argmax(sib_avg)
        target_freq = freqs[sib_mask][target_idx] if target_idx < len(freqs[sib_mask]) else 7000
        target_khz = float(target_freq / 1000.0)
        
        return {
            "need_score": float(need_score),
            "target_khz": float(target_khz)
        }
    
    except Exception as e:
        log_debug(f"De-essing detection error: {e}")
        return {"need_score": 0.0, "target_khz": 7.0}

def analyze_track_comprehensive(audio_path):
    """
    Comprehensive track analysis using librosa (+ Essentia if available).
    Returns detailed, actionable analysis in structured JSON format.
    """
    analysis = {
        "audio_file": audio_path,
        "timestamp": time.time(),
        "effects": {},
        "characteristics": {},
        "summary": ""
    }
    
    # Classify audio type first
    print(f"   🎵 Audio type...", end="", flush=True)
    audio_type = classify_audio_type(audio_path)
    analysis['audio_type'] = audio_type
    print(f" ✓ {audio_type.replace('_', ' ').title()}")
    analysis['summary'] = f"{audio_type.replace('_', ' ').title()}: "
    
    print(f"   🎚️ Frequency filtering...", end="", flush=True)
    filtering = detect_frequency_filtering(audio_path)
    analysis['effects']['filtering'] = filtering
    
    filter_char = filtering['character']
    if filter_char == "telephone":
        print(f" ✓ Telephone effect detected")
        analysis['summary'] += "Telephone effect (bandpass filtering). "
    elif filter_char == "bandpass":
        hp = filtering['high_pass']
        lp = filtering['low_pass']
        print(f" ✓ Bandpass {hp}Hz-{lp}Hz")
        analysis['summary'] += f"Bandpass filtered {hp}-{lp}Hz. "
    elif filter_char == "high_passed":
        print(f" ✓ High-pass at {filtering['high_pass']}Hz")
        analysis['summary'] += f"High-passed at {filtering['high_pass']}Hz. "
    elif filter_char == "low_passed":
        print(f" ✓ Low-pass at {filtering['low_pass']}Hz")
        analysis['summary'] += f"Low-passed at {filtering['low_pass']}Hz. "
    else:
        print(f" ✓ Full range")
        analysis['summary'] += "Full frequency range. "
    
    # BPM & beats (for delay mapping)
    bpm, beat_times = detect_bpm_and_beats(audio_path)
    analysis['characteristics']['bpm'] = float(bpm)

    print(f"   🔁 Delay...", end="", flush=True)
    delay = detect_delay_settings(audio_path)
    analysis['effects']['delay'] = delay
    if delay['present']:
        # Map ms to musical note value if BPM exists
        note_map = map_delay_ms_to_note_value(delay['delay_time_ms'], bpm) if bpm > 0 else {"label": None}
        analysis['effects']['delay']['note_value'] = note_map.get('label')
        analysis['effects']['delay']['note_ms_target'] = note_map.get('ms_target', 0)
        print(f" ✓ {delay['delay_time_ms']}ms, {delay['feedback']}% feedback" + (f", {note_map['label']}" if note_map.get('label') else ""))
        analysis['summary'] += f"Delay: {delay['delay_time_ms']}ms with {delay['feedback']}% feedback. "
    else:
        print(f" ✓ None")
        analysis['summary'] += "No delay. "
    
    print(f"   🌊 Reverb...", end="", flush=True)
    reverb = detect_reverb_settings(audio_path)
    analysis['effects']['reverb'] = reverb
    if reverb['present']:
        print(f" ✓ {reverb['decay_time']:.1f}s decay, {reverb['mix']}% mix")
        analysis['summary'] += f"Reverb: {reverb['decay_time']:.1f}s decay. "
    else:
        print(f" ✓ Dry")
        analysis['summary'] += "Dry (no reverb). "
    
    print(f"   🔥 Distortion...", end="", flush=True)
    distortion_data = detect_distortion_amount(audio_path)
    analysis['characteristics']['distortion'] = distortion_data['amount']
    analysis['characteristics']['saturation'] = {
        "even_odd_ratio": distortion_data['even_odd_ratio'],
        "type_hint": distortion_data['type_hint']
    }
    print(f" ✓ {distortion_data['amount']:.1f}% ({distortion_data['type_hint']})")
    if distortion_data['amount'] > 40:
        analysis['summary'] += f"Heavy {distortion_data['type_hint']} distortion ({distortion_data['amount']:.0f}%). "
    elif distortion_data['amount'] > 20:
        analysis['summary'] += f"Moderate {distortion_data['type_hint']} saturation ({distortion_data['amount']:.0f}%). "
    
    print(f"   💥 Compression...", end="", flush=True)
    compression_data = detect_compression_amount(audio_path)
    analysis['characteristics']['compression'] = compression_data['compression_percent']
    analysis['characteristics']['dynamic_range_db'] = compression_data['dynamic_range_db']
    print(f" ✓ {compression_data['compression_percent']:.1f}% (DR: {compression_data['dynamic_range_db']:.1f}dB)")
    if compression_data['compression_percent'] > 70:
        analysis['summary'] += f"Heavily compressed ({compression_data['compression_percent']:.0f}%, {compression_data['dynamic_range_db']:.0f}dB DR). "
    
    print(f"   ✨ Brightness...", end="", flush=True)
    brightness = detect_brightness(audio_path)
    analysis['characteristics']['brightness'] = brightness
    print(f" ✓ {brightness:.1f}%")
    if brightness > 70:
        analysis['summary'] += "Bright sound. "
    elif brightness < 30:
        analysis['summary'] += "Dark/warm sound. "
    
    # Spectral indices (mud/boxiness/presence/air)
    indices = compute_spectral_indices(audio_path)
    analysis['characteristics']['spectral_indices'] = indices
    
    print(f"   🎤 Pitch correction...", end="", flush=True)
    autotune = detect_autotune_presence(audio_path)
    analysis['characteristics']['autotune'] = autotune
    print(f" ✓ {autotune:.1f}%")
    if autotune > 30:
        analysis['summary'] += f"Pitch correction detected ({autotune:.0f}%). "
    
    # Stereo metrics
    print(f"   🎧 Stereo imaging...", end="", flush=True)
    stereo = detect_stereo_metrics(audio_path)
    analysis['stereo_metrics'] = stereo
    if stereo['lr_corr'] < 0.8:
        print(f" ✓ Wide ({stereo['lr_corr']:.2f} corr)")
        analysis['summary'] += "Wide stereo image. "
    else:
        print(f" ✓ Mono/narrow ({stereo['lr_corr']:.2f} corr)")
    
    # De-essing need
    print(f"   ✂️ De-essing...", end="", flush=True)
    deess = detect_deessing_need(audio_path)
    analysis['deessing_need'] = deess
    if deess['need_score'] > 40:
        print(f" ✓ Needed ({deess['need_score']:.0f}% at {deess['target_khz']:.1f}kHz)")
        analysis['summary'] += f"Harsh sibilance (de-ess at {deess['target_khz']:.1f}kHz). "
    else:
        print(f" ✓ Not needed")
    
    return analysis

def save_analysis_json(analysis, filename="current_audio_analysis.json"):
    """
    Save analysis to JSON file for agent to read.
    """
    try:
        json_path = Path(filename)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        return str(json_path)
    except Exception as e:
        log_debug(f"Failed to save analysis JSON: {e}")
        return None

def load_analysis_json(filename="current_audio_analysis.json"):
    """
    Load analysis from JSON file.
    """
    try:
        json_path = Path(filename)
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        log_debug(f"Failed to load analysis JSON: {e}")
        return None

def calculate_track_differences(ref_analysis, target_analysis):
    """
    Calculate what needs to be added to target to match reference.
    Works with new JSON structure. Returns actionable differences + summary.
    """
    differences = {
        "summary": "",
        "needs": []
    }
    
    # Filtering differences
    ref_filter = ref_analysis['effects']['filtering']
    tgt_filter = target_analysis['effects']['filtering']
    differences['filtering'] = {
        "ref_character": ref_filter['character'],
        "target_character": tgt_filter['character'],
        "needs_telephone": ref_filter['character'] == "telephone" and tgt_filter['character'] != "telephone",
        "ref_high_pass": ref_filter['high_pass'],
        "ref_low_pass": ref_filter['low_pass'],
        "target_high_pass": tgt_filter.get('high_pass'),
        "target_low_pass": tgt_filter.get('low_pass')
    }
    
    if differences['filtering']['needs_telephone']:
        differences['needs'].append(f"Telephone effect ({ref_filter['high_pass']}-{ref_filter['low_pass']}Hz)")
        differences['summary'] += f"Reference has telephone filtering, yours doesn't. "
    else:
        # Suggest HP/LP adjustments if significantly different
        if ref_filter['high_pass'] and tgt_filter.get('high_pass'):
            if abs(ref_filter['high_pass'] - tgt_filter['high_pass']) > 50:
                differences['filtering']['needs_adjust_hp'] = True
                differences['needs'].append(f"Set HP to {ref_filter['high_pass']}Hz")
        if ref_filter['low_pass'] and tgt_filter.get('low_pass'):
            if abs(ref_filter['low_pass'] - tgt_filter['low_pass']) > 500:
                differences['filtering']['needs_adjust_lp'] = True
                differences['needs'].append(f"Set LP to {ref_filter['low_pass']}Hz")
    
    # Delay differences
    ref_delay = ref_analysis['effects']['delay']
    tgt_delay = target_analysis['effects']['delay']
    differences['delay'] = {
        "needs_delay": ref_delay['present'] and not tgt_delay['present'],
        "delay_time_ms": ref_delay['delay_time_ms'] if ref_delay['present'] else 0,
        "feedback": ref_delay['feedback'] if ref_delay['present'] else 0,
        "mix": ref_delay['mix'] if ref_delay['present'] else 0,
        "needs_adjust": ref_delay['present'] and tgt_delay['present'] and abs(ref_delay['delay_time_ms'] - tgt_delay['delay_time_ms']) > 30,
    }
    
    if differences['delay']['needs_delay']:
        differences['needs'].append(f"Delay ({ref_delay['delay_time_ms']}ms)")
        differences['summary'] += f"Reference has {ref_delay['delay_time_ms']}ms delay, yours is dry. "
    
    # Reverb differences  
    ref_reverb = ref_analysis['effects']['reverb']
    tgt_reverb = target_analysis['effects']['reverb']
    differences['reverb'] = {
        "needs_reverb": ref_reverb['present'] and not tgt_reverb['present'],
        "decay_time": ref_reverb['decay_time'] if ref_reverb['present'] else 0,
        "mix": ref_reverb['mix'] if ref_reverb['present'] else 0,
        "needs_adjust": ref_reverb['present'] and tgt_reverb['present'] and abs(ref_reverb['decay_time'] - tgt_reverb['decay_time']) > 0.3,
    }
    
    if differences['reverb']['needs_reverb']:
        differences['needs'].append(f"Reverb ({ref_reverb['decay_time']:.1f}s decay)")
        differences['summary'] += f"Reference has reverb, yours is dry. "
    
    # Percentage differences
    differences['distortion'] = ref_analysis['characteristics']['distortion'] - target_analysis['characteristics']['distortion']
    differences['compression'] = ref_analysis['characteristics'].get('compression', 0) - target_analysis['characteristics'].get('compression', 0)
    differences['dynamic_range_db'] = ref_analysis['characteristics'].get('dynamic_range_db', 30) - target_analysis['characteristics'].get('dynamic_range_db', 30)
    differences['brightness'] = ref_analysis['characteristics']['brightness'] - target_analysis['characteristics']['brightness']
    differences['autotune'] = ref_analysis['characteristics']['autotune'] - target_analysis['characteristics']['autotune']
    
    # Include audio type context
    differences['ref_audio_type'] = ref_analysis.get('audio_type', 'unknown')
    differences['target_audio_type'] = target_analysis.get('audio_type', 'unknown')
    
    if abs(differences['brightness']) > 15:
        if differences['brightness'] > 0:
            differences['needs'].append(f"Brighten by +{differences['brightness']:.0f}%")
            differences['summary'] += "Reference is brighter. "
        else:
            differences['needs'].append(f"Darken by {differences['brightness']:.0f}%")
            differences['summary'] += "Reference is darker. "
    
    return differences

def apply_production_adjustments(track_idx, differences, iteration=1):
    """
    Apply plugin adjustments based on detected differences.
    Uses exact plugin names from reaper_plugins_list.txt.
    Actually sets parameters using SET_FX_PARAM commands.
    Returns list of commands to send to Reaper.
    """
    commands = []
    actions_taken = []
    fx_index = 0  # Track which FX slot we're using
    THRESHOLD = 5  # minimum % difference to act on for generic dims
    
    # Telephone/Bandpass filtering
    if differences['filtering']['needs_telephone']:
        hp = differences['filtering']['ref_high_pass'] or 300
        lp = differences['filtering']['ref_low_pass'] or 3000
        print(f"   ✅ Adding telephone effect ({hp}Hz-{lp}Hz)")
        
        # Add Pro-Q 3
        commands.append(f"ADD_FX {track_idx} VST3: Pro-Q 3 (FabFilter)")
        
        # High-pass filter (Band 1)
        # Enable band
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 0 1.0")
        # Set frequency
        hp_normalized = (np.log10(hp) - np.log10(20)) / (np.log10(20000) - np.log10(20))
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 1 {hp_normalized:.4f}")
        # Set to High Cut type (0.83)
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 8 0.17")
        # Set slope to brickwall
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 9 1.0")
        
        # Low-pass filter (Band 2)
        # Enable band
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 13 1.0")
        # Set frequency
        lp_normalized = (np.log10(lp) - np.log10(20)) / (np.log10(20000) - np.log10(20))
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 14 {lp_normalized:.4f}")
        # Set to Low Cut type (0.17)
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 21 0.83")
        # Set slope to brickwall
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 22 1.0")
        
        actions_taken.append(f"telephone ({hp}Hz-{lp}Hz)")
        fx_index += 1
    
    # Delay
    if differences['delay']['needs_delay'] or differences['delay'].get('needs_adjust'):
        delay_ms = differences['delay']['delay_time_ms']
        feedback = differences['delay']['feedback']
        mix = differences['delay']['mix']
        print(f"   ✅ Adding delay ({delay_ms}ms, {feedback}% feedback)")
        commands.append(f"ADD_FX {track_idx} VST3: ValhallaDelay (Valhalla DSP, LLC)")
        
        # Valhalla Delay params (estimated - would need exact mapping)
        # For now use detected values
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 2 {mix / 100.0:.4f}")  # Mix
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 1 {feedback / 100.0:.4f}")  # Feedback
        # Time param - rough estimate
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 0 0.5")  # Would need tempo for accurate sync
        
        actions_taken.append(f"delay ({delay_ms}ms)")
        fx_index += 1
    
    # Reverb
    if differences['reverb']['needs_reverb'] or differences['reverb'].get('needs_adjust'):
        decay_time = differences['reverb']['decay_time']
        mix = differences['reverb']['mix']
        print(f"   ✅ Adding reverb ({decay_time:.1f}s decay)")
        commands.append(f"ADD_FX {track_idx} VST3: ValhallaVintageVerb (Valhalla DSP, LLC)")
        
        # Valhalla VintageVerb params (estimated)
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 0 {min(1.0, decay_time / 5.0):.4f}")  # Decay
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 1 {mix / 100.0:.4f}")  # Mix
        
        actions_taken.append(f"reverb ({decay_time:.1f}s)")
        fx_index += 1
    
    # Compression
    if differences.get('compression', 0) > THRESHOLD:
        compression_amount = differences['compression']
        print(f"   ✅ Adding compression (+{compression_amount:.1f}%)")
        commands.append(f"ADD_FX {track_idx} VST: SSLChannel Stereo (x86) (Waves)")
        
        # SSL Channel compression params (typical):
        # Threshold, ratio, etc.
        
        # Set threshold based on amount (-30dB to -10dB range)
        threshold_db = -30 + (min(1.0, compression_amount / 100.0) * 20)
        threshold_normalized = (threshold_db + 60) / 60  # Assuming -60 to 0 dB range
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 0 {threshold_normalized:.4f}")
        
        # Set ratio (2:1 to 6:1 based on amount)
        ratio_value = 2.0 + (min(1.0, compression_amount / 100.0) * 4.0)
        ratio_normalized = ratio_value / 20.0  # Normalize to plugin range
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 1 {ratio_normalized:.4f}")
        
        actions_taken.append(f"compression ({compression_amount:.0f}%)")
        fx_index += 1
    
    # Brightness (via EQ)
    if abs(differences.get('brightness', 0)) > THRESHOLD:
        brightness_diff = differences['brightness']
        if brightness_diff > 0:
            print(f"   ✅ Brightening (+{brightness_diff:.1f}%)")
        else:
            print(f"   ✅ Darkening ({brightness_diff:.1f}%)")
        
        commands.append(f"ADD_FX {track_idx} VST3: Pro-Q 3 (FabFilter)")
        
        # Pro-Q 3 band parameters (13 params per band):
        # p(band*13 + 0): Used (on/off)
        # p(band*13 + 1): Frequency
        # p(band*13 + 2): Gain
        # p(band*13 + 8): Type (bell/shelf)
        
        # Use band 0 for high shelf at 8kHz
        band_idx = 0
        param_base = band_idx * 13
        
        # Enable band
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} {param_base} 1.0")
        
        # Set frequency to 8kHz (high shelf for brightness)
        freq_hz = 8000
        freq_normalized = (np.log10(freq_hz) - np.log10(20)) / (np.log10(20000) - np.log10(20))
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} {param_base + 1} {freq_normalized:.4f}")
        
        # Set gain based on brightness difference (-6dB to +6dB)
        gain_db = brightness_diff / 100.0 * 6.0  # Scale to ±6dB
        gain_normalized = np.clip((gain_db + 12) / 24, 0, 1)
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} {param_base + 2} {gain_normalized:.4f}")
        
        # Set to High Shelf type (0.67 typically for Pro-Q)
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} {param_base + 8} 0.67")
        
        actions_taken.append(f"eq_brightness ({brightness_diff:.0f}%)")
        fx_index += 1
    
    # Autotune
    if differences.get('autotune', 0) > THRESHOLD:
        autotune_amount = differences['autotune']
        print(f"   ✅ Adding pitch correction (+{autotune_amount:.1f}%)")
        commands.append(f"ADD_FX {track_idx} VST3: Waves Tune Real-Time Stereo (Waves)")
        
        # Waves Tune Real-Time params (typical):
        # Retune speed, amount, etc.
        
        # Set retune speed based on amount (fast = 0-20ms, slow = 100-200ms)
        # Higher autotune amount = faster retune
        retune_speed_normalized = 1.0 - min(1.0, autotune_amount / 100.0)  # 1.0 = slow, 0.0 = fast
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 0 {retune_speed_normalized:.4f}")
        
        # Set correction amount to high
        commands.append(f"SET_FX_PARAM {track_idx} {fx_index} 1 0.9")
        
        actions_taken.append(f"autotune ({autotune_amount:.0f}%)")
        fx_index += 1
    
    return commands, actions_taken

def librosa_based_reference_matching(track_idx, reference_audio_path, track_audio_path, 
                                     max_iterations=15, target_similarity=85.0):
    """
    Pure librosa-based reference matching with comprehensive effect detection.
    Analyzes both tracks, detects specific differences, applies plugins.
    """
    print(f"\n🎵 Librosa-Based Reference Matching")
    print(f"   Deep audio analysis + actionable effect detection\n")
    
    try:
        # Analyze reference track
        print(f"📊 Analyzing reference track...")
        ref_analysis = analyze_track_comprehensive(reference_audio_path)
        
        # Save reference analysis to JSON
        ref_json_path = save_analysis_json(ref_analysis, "reference_audio_analysis.json")
        if ref_json_path:
            print(f"   💾 Saved reference analysis to {ref_json_path}")
        
        print(f"\n📊 Analyzing your track...")
        target_analysis = analyze_track_comprehensive(track_audio_path)
        
        # Save target analysis to JSON
        target_json_path = save_analysis_json(target_analysis, "target_audio_analysis.json")
        if target_json_path:
            print(f"   💾 Saved target analysis to {target_json_path}")
        
        # Calculate differences
        differences = calculate_track_differences(ref_analysis, target_analysis)
        
        # Save differences to JSON
        diff_json_path = save_analysis_json(differences, "audio_differences.json")
        if diff_json_path:
            print(f"   💾 Saved differences to {diff_json_path}")
        
        print(f"\n🔄 What needs to be added:")
        if differences.get('needs'):
            for need in differences['needs']:
                print(f"   • {need}")
        else:
            print(f"   ✅ Tracks are very similar")
        
        if differences.get('summary'):
            print(f"\n📝 Analysis: {differences['summary']}")
        
        # Auto-apply based on differences
        print(f"\n⚙️ Auto-applying adjustments to track {track_idx}...")
        commands, actions = apply_production_adjustments(track_idx, differences)

        if commands:
            print(f"\n📤 Sending {len(commands)} command(s) to Reaper...")
            success = send_reaper_commands(commands)
            if success:
                print(f"✅ Applied: {', '.join(actions)}")
            else:
                print(f"❌ Failed to apply some commands")
        else:
            print(f"✅ No changes needed (tracks already very similar)")

        print(f"\n✅ Analysis complete! JSON files saved.")
        print(f"   📄 reference_audio_analysis.json")
        print(f"   📄 target_audio_analysis.json")
        print(f"   📄 audio_differences.json")

        return {
            "reference_analysis": ref_analysis,
            "target_analysis": target_analysis,
            "differences": differences,
            "actions_taken": actions if commands else [],
            "commands_sent": len(commands),
            "success": bool(commands),
            "message": "Analysis + auto-apply complete"
        }
    
    except Exception as e:
        log_debug(f"MERT-based matching error: {e}")
        print(f"❌ Error: {e}")
        return {"error": str(e)}

# ==================== END MERT SYSTEM ====================

def smart_index_search(user_input, index_path=r"C:\Users\moosb\AIAGENT DAW\action_index.json", max_results=100):
    """
    Fast search using pre-built index with synonym support
    Returns: dict of {action_id: description}
    """
    import json
    import re
    
    # Load index
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
    except Exception as e:
        log_debug(f"Index load error: {e}")
        return {}
    
    # Synonym mapping for better matching
    synonyms = {
        "open": ["show", "display", "view"],
        "show": ["open", "display", "view"],
        "fx": ["effect", "plugin", "chain"],
        "effect": ["fx", "plugin"],
        "plugin": ["fx", "effect"],
        "automation": ["envelope", "automate", "automated"],
        "envelope": ["automation", "automate"],
        "remove": ["delete", "clear", "erase"],
        "delete": ["remove", "clear", "erase"],
        "clear": ["remove", "delete", "erase"],
        "add": ["insert", "create", "new"],
        "insert": ["add", "create", "new"],
        "track": ["tracks", "selected"],
        "solo": ["unsolo", "toggle"],
        "mute": ["unmute", "toggle"],
        "bypass": ["disable", "turn"],
        "volume": ["vol", "level", "gain"],
        "pan": ["panning", "balance"],
        "reverb": ["verb", "room", "space"],
        "delay": ["echo", "repeat"],
        "compress": ["compression", "compressor"],
        "eq": ["equalizer", "equalize"],
        "record": ["rec", "recording"],
        "play": ["playback", "start"],
        "stop": ["pause", "halt"],
        "split": ["cut", "slice"],
        "render": ["export", "bounce"],
        "normalize": ["normalise", "level"],
    }
    
    # Extract keywords and track number
    user_lower = user_input.lower()
    keywords = user_lower.split()
    
    # Expand keywords with synonyms
    expanded_keywords = set(keywords)
    for kw in keywords:
        if kw in synonyms:
            expanded_keywords.update(synonyms[kw])
    
    keywords = list(expanded_keywords)
    
    # Extract track number (e.g., "track 3" or "track 03")
    track_match = re.search(r'\btrack\s*(\d+)\b', user_lower)
    track_num = None
    if track_match:
        track_num = int(track_match.group(1))
        track_padded = f"{track_num:02d}"  # "3" -> "03"
        keywords.append(track_padded)
        keywords.append("selected")  # Many track-specific actions use "selected"
    
    # Search index keys with stricter matching
    matched_actions = {}
    
    # Calculate minimum keywords needed (at least 2, or 60% of total keywords)
    min_keywords_required = max(2, int(len(keywords) * 0.6))
    
    for key, action_data in index.items():
        key_lower = key.lower()
        score = 0
        
        # Count keyword matches in the key
        for kw in keywords:
            if kw in key_lower:
                score += 1
        
        # Only include if enough keywords match (stricter filtering)
        if score >= min_keywords_required:
            action_id = action_data['id']
            description = action_data['desc']
            matched_actions[action_id] = description
    
    # ALWAYS include essential actions regardless of search
    essential_ids = ["1007", "1016", "1013", "40280", "40294", "40340", "40291"]
    for key, action_data in index.items():
        if action_data['id'] in essential_ids:
            matched_actions[action_data['id']] = action_data['desc']
    
    # If no matches, return essential actions
    if not matched_actions:
        log_debug("No index matches, using essentials")
        for key, action_data in index.items():
            if action_data['id'] in essential_ids:
                matched_actions[action_data['id']] = action_data['desc']
    
    # Limit results
    if len(matched_actions) > max_results:
        # Keep essentials + top scored
        essentials = {aid: desc for aid, desc in matched_actions.items() if aid in essential_ids}
        others = {aid: desc for aid, desc in matched_actions.items() if aid not in essential_ids}
        others = dict(list(others.items())[:max_results - len(essentials)])
        matched_actions = {**essentials, **others}
    
    log_debug(f"Index search found {len(matched_actions)} actions for: {user_input}")
    return matched_actions

def filter_relevant_actions(user_input, all_actions, max_actions=50):
    """Smart filter with EXACT track number matching"""
    import re
    
    keywords = user_input.lower().split()
    
    # Extract track number if mentioned (e.g., "track 7" → 7)
    track_match = re.search(r'\btrack\s*(\d+)\b', user_input.lower())
    requested_track = int(track_match.group(1)) if track_match else None
    
    # ALWAYS include essential actions
    essential_ids = [
        "1007", "1016", "1013", "1008",  # Transport: Play, Stop, Record, Pause
        "40280", "40281",  # Track: Mute/Solo (selected tracks)
        "40339", "40340",  # Track: Unmute/Unsolo all
        "40297", "40296",  # Track: Toggle mute/solo (selected)
        "40340",  # Add FX to selected
        "40291", "40293",  # Track: View FX/routing
    ]
    
    relevant = {aid: desc for aid, desc in all_actions.items() if aid in essential_ids}
    
    # Score remaining actions by keyword + track number matches
    scored = []
    for aid, desc in all_actions.items():
        if aid in relevant:
            continue
        
        desc_lower = desc.lower()
        score = 0
        
        # Keyword matching
        for kw in keywords:
            if kw in desc_lower:
                score += 2
        
        # EXACT track number boost (HUGE bonus if matches!)
        if requested_track:
            # Match "track 07" or "track 7"
            track_in_desc = re.search(r'\btrack\s*0?(\d+)\b', desc_lower)
            if track_in_desc:
                desc_track_num = int(track_in_desc.group(1))
                if desc_track_num == requested_track:
                    score += 100  # MASSIVE boost for exact match!
                elif abs(desc_track_num - requested_track) <= 2:
                    score += 10  # Small boost for nearby tracks
        
        # Penalize MIDI CC/OSC only actions (usually not what user wants)
        if "midi cc/osc only" in desc_lower:
            score -= 5
        
        if score > 0:
            scored.append((score, aid, desc))
    
    # Sort by relevance and take top N
    scored.sort(reverse=True)
    for score, aid, desc in scored[:max_actions - len(relevant)]:
        relevant[aid] = desc
    
    return relevant

def plan_actions(user_input, state, known_actions, available_plugins, previous_issues="", feedback="", lyric_context="", analysis_context="", retry_history=[], conversation_history=[], failed_commands=set()):
    """Phase 1: AI Plans what to do"""
    
    # Use smart index search instead of old filter (MUCH faster!)
    relevant_actions = smart_index_search(user_input, max_results=100)
    
    # Check if user explicitly mentioned an action ID (e.g., "use 40005", "action 40005", "40005")
    explicit_action_ids = re.findall(r'\b(\d{4,})\b', user_input)
    for action_id in explicit_action_ids:
        if action_id in known_actions and action_id not in relevant_actions:
            relevant_actions[action_id] = known_actions[action_id]
            print(f"   ✅ Added explicit action {action_id}: {known_actions[action_id]}")
    
    # If this is a retry, force-add any suggested actions from previous_issues
    if previous_issues:
        # Extract action IDs mentioned in previous_issues (e.g., "action 40205", "action 6")
        suggested_actions = re.findall(r'action\s+(\d+)', previous_issues)
        for action_id in suggested_actions:
            if action_id in known_actions and action_id not in relevant_actions:
                relevant_actions[action_id] = known_actions[action_id]
                print(f"   💡 Added suggested action {action_id} from retry guidance")
    
    # Sort for readability (track numbers in order)
    sorted_actions = sorted(relevant_actions.items(), key=lambda x: (x[1], x[0]))
    actions_text = "\n".join([f"{aid}: {desc}" for aid, desc in sorted_actions])
    
    # Search for relevant plugins based on user input (fuzzy matching with scoring)
    user_lower = user_input.lower()
    user_words = [w for w in user_lower.split() if len(w) > 2 and w not in ['open', 'add', 'and', 'the']]
    
    scored_plugins = []
    for plugin in available_plugins:
        plugin_lower = plugin.lower()
        score = 0
        # Score by keyword matches (more matches = higher score)
        for word in user_words:
            if word in plugin_lower:
                score += 2  # Exact substring match
            elif any(word[:min(len(word), 4)] in plugin_lower for word in [word]):
                score += 1  # Partial match (first 4 chars)
        
        if score > 0:
            scored_plugins.append((score, plugin))
    
    # Sort by score (highest first) and take top 50
    scored_plugins.sort(reverse=True, key=lambda x: x[0])
    relevant_plugins = [p for _, p in scored_plugins[:50]]
    
    plugins_text = "\n".join(relevant_plugins) if relevant_plugins else "No specific plugins matched"
    
    print(f"🔍 Using {len(relevant_actions)} relevant actions (from {len(known_actions)} total)")
    print(f"🎛️ Found {len(relevant_plugins)} relevant plugins")
    
    # Build retry history section (for retry_alert)
    history_section = ""
    if retry_history:
        history_section = "\n**RETRY HISTORY (what you tried and what happened):**\n"
        for entry in retry_history:
            history_section += f"- {entry}\n"
        history_section += "\n**USE THIS HISTORY:** Learn from what worked and what overshot. Converge toward target, don't repeat failed approaches.\n"
    
    feedback_section = f"\n**FEEDBACK FROM LAST COMMANDS:**\n{feedback}\n\n**IMPORTANT**: Look at the feedback above to see what ACTUALLY executed. Only retry the commands that failed or are missing. Don't repeat successful commands!\n" if feedback else ""
    lyric_section = lyric_context if lyric_context else ""
    analysis_section = analysis_context if analysis_context else ""
    
    # Add relevant memory from past similar tasks
    memory_section = get_relevant_memory(user_input)
    
    # Add conversation history for context
    conversation_section = ""
    if conversation_history and len(conversation_history) > 0:
        recent_history = conversation_history[-10:]  # Last 10 messages
        conversation_section = "\n**CONVERSATION HISTORY (remember this context):**\n"
        for i, entry in enumerate(recent_history, 1):
            conversation_section += f"{i}. {entry}\n"
        conversation_section += "\n**USE THIS:** Remember what the user asked for. Don't forget the original request.\n"
    
    # Add failed commands warning
    failed_cmd_section = ""
    if failed_commands:
        failed_cmd_section = "\n**⚠️ COMMAND STRINGS THAT ALREADY FAILED (DO NOT REPEAT THESE EXACT VARIANTS):**\n"
        for cmd in failed_commands:
            failed_cmd_section += f"- {cmd}\n"
        failed_cmd_section += "\n**CRITICAL**: Avoid repeating the exact commands above. You may still use the same action with different parameters if appropriate.\n"
    
    # Add user preferences if available
    user_prefs_section = ""
    if user_preferences:
        user_prefs_section = f"""
**USER'S PLUGIN PREFERENCES (FOLLOW THESE STRICTLY):**
{json.dumps(user_preferences, indent=2)}

**CRITICAL - READ USER PREFERENCES ABOVE:**
- When user says "EQ" → ONLY use {user_preferences.get('plugin_preferences', {}).get('EQ', {}).get('always_use', 'Pro-Q 3')}
- When user says "distortion" → ONLY use {', '.join(user_preferences.get('plugin_preferences', {}).get('Distortion', {}).get('always_use', ['Manny M']))}
- When user says "reverb" → ONLY use {user_preferences.get('plugin_preferences', {}).get('Reverb', {}).get('always_use', 'Valhalla Room')}
- When user says "saturation" → ONLY use {user_preferences.get('plugin_preferences', {}).get('Saturation', {}).get('always_use', 'Saturn 2')}

**DO NOT substitute with other plugins - these are the user's preferred tools.**
"""
    
    # Add production effects reference if available
    production_effects_section = ""
    if sound_knowledge and 'production_effects' in sound_knowledge:
        production_effects_section = f"""
**PRODUCTION EFFECTS KNOWLEDGE BASE:**
{json.dumps(sound_knowledge['production_effects'], indent=2)}

**CRITICAL INSTRUCTIONS FOR PRODUCTION EFFECTS:**
When user requests effects like "underwater", "drake style", "lo-fi", "sidechain", etc:

1. **Find the effect** in the knowledge base above
2. **Execute CRITICAL steps ONLY** (marked critical: true) - ignore optional steps initially
3. **DO NOT work around with existing plugins** - if the knowledge base says "remove existing pitch shifters", DO IT
4. **Use EXACT parameters** from the knowledge base - don't guess or substitute

**UNDERWATER EXAMPLE - KEEP IT SIMPLE:**
- User says: "make it underwater"
- **The entire effect:** LOW-PASS filter at 1000Hz with BRICKWALL slope. That's it. One filter.
- **CORRECT approach (simple):**
  1. ADD_FX Pro-Q 3
  2. Configure: Enable band, set to "High Cut (Low-Pass)" filter type, 1000Hz, slope "Brickwall" or "96 dB/oct"
  3. DONE - verify it works with audio analysis
  4. If user wants MORE (reverb, pitch, etc.), add those AFTER the basic effect works
- **Why Brickwall:** Pro-Q 3 has slopes from 6dB/oct up to Brickwall. For underwater, you need the STEEPEST possible cutoff (Brickwall or 96dB/oct) to aggressively remove all highs. 24dB/oct is too gentle. Check plugin_encyclopedia for Pro-Q 3 slope options.
- **WRONG approaches (what NOT to do):**
  * Using Little AlterBoy or pitch shifters → Pitch does NOT create muffling
  * Using high-shelf with negative gain → That's GRADUAL reduction, not STEEP cutoff
  * Using ReaEQ without knowing if it has low-pass → Just use Pro-Q 3
  * Adding reverb/formant/multiple plugins → Overcomplicating, do the simple low-pass FIRST

**CRITICAL RULES FOR UNDERWATER:**
1. Do NOT add Little AlterBoy for underwater - it's a pitch shifter, not a filter
2. Do NOT use "high-shelf" filter type - use "LOW-PASS" or "High-Cut" filter type
3. Keep it simple: Add one EQ, set one low-pass filter, verify it works, then add extras if needed

**KEY PRINCIPLE:** Underwater = LOW-PASS filter at 1kHz. Everything else is optional enhancement. Don't overcomplicate.
"""
    
    # Load audio analysis JSON if available
    audio_analysis_section = ""
    ref_analysis = load_analysis_json("reference_audio_analysis.json")
    target_analysis = load_analysis_json("target_audio_analysis.json")
    diff_analysis = load_analysis_json("audio_differences.json")
    
    if ref_analysis or target_analysis or diff_analysis:
        audio_analysis_section = "\n**AUDIO ANALYSIS DATA:**\n"
        
        if ref_analysis:
            audio_analysis_section += f"\n📊 REFERENCE TRACK ANALYSIS:\n"
            audio_analysis_section += f"Summary: {ref_analysis.get('summary', 'N/A')}\n"
            audio_analysis_section += f"Full data: {json.dumps(ref_analysis, indent=2)}\n"
        
        if target_analysis:
            audio_analysis_section += f"\n📊 YOUR TRACK ANALYSIS:\n"
            audio_analysis_section += f"Summary: {target_analysis.get('summary', 'N/A')}\n"
            audio_analysis_section += f"Full data: {json.dumps(target_analysis, indent=2)}\n"
        
        if diff_analysis:
            audio_analysis_section += f"\n🔄 DIFFERENCES (What to add to match reference):\n"
            audio_analysis_section += f"Summary: {diff_analysis.get('summary', 'N/A')}\n"
            if diff_analysis.get('needs'):
                audio_analysis_section += f"Needs: {', '.join(diff_analysis['needs'])}\n"
            audio_analysis_section += f"Full data: {json.dumps(diff_analysis, indent=2)}\n"
        
        audio_analysis_section += "\n**USE THIS DATA:**\n"
        audio_analysis_section += "- Discuss audio characteristics naturally (brightness, filtering, delay, etc.)\n"
        audio_analysis_section += "- Generate commands based on detected differences\n"
        audio_analysis_section += "- Reference specific values (e.g., 'needs 375ms delay', 'telephone filtering 300-3000Hz')\n\n"
    
    # Build issues section at TOP for retries (so agent sees it FIRST!)
    retry_alert = ""
    if previous_issues:
        retry_alert = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║ 🚨 RETRY ALERT - READ THIS FIRST! 🚨                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝

**WHAT FAILED ON PREVIOUS ATTEMPT:**
{previous_issues}

{history_section}

**CRITICAL INSTRUCTION FOR THIS RETRY:**
- DO NOT repeat the same command that just failed!
- The message above tells you what didn't work and what to try instead
- Follow those instructions EXACTLY
- If it says "PIVOT to Method 2", use Method 2, NOT Method 1 again

╔═══════════════════════════════════════════════════════════════════════════════╗
"""

    system_prompt = f"""
YOU ARE: An autonomous Reaper DAW controller. Your job: translate the user's request into the smallest correct set of commands that deterministically changes the project to the exact target state.

===============================================================================
OUTPUT CONTRACT (STRICT)
===============================================================================
- Respond with **ONLY valid JSON** and nothing else.
- Schema:
{{
  "reasoning": "CHAIN OF THOUGHT: short, explicit decision path you took (2–7 lines; no fluff)",
  "already_complete": true/false,
  "steps": [
    {{"command": "<exact command string>", "description": "<short human description>"}}
  ]
}}
- If already_complete=true → steps must be [].
- Do not include commentary, markdown, or prose outside of this JSON.

===============================================================================
RUNTIME CONTEXT (VARIABLES PROVIDED BY CALLER)
===============================================================================
{retry_alert}
{failed_cmd_section}
{conversation_section}
{memory_section}
{user_prefs_section}

USER REQUEST (VERBATIM - SATISFY THIS EXACTLY):
{user_input}

CURRENT PROJECT STATE (SOURCE OF TRUTH):
{state}
{audio_analysis_section}

AVAILABLE ACTIONS (use exact names/IDs shown):
{actions_text}

AVAILABLE PLUGINS (use EXACT names from this list only):
{plugins_text}
{production_effects_section}

OPTIONAL PRIOR FEEDBACK / NOTES:
{feedback_section}{lyric_section}{analysis_section}

===============================================================================
PRIME DIRECTIVE — NEUTRALIZE BEFORE ADDING
===============================================================================
If the current state would conflict with the requested change, you MUST neutralize it first.
- Volume automation: If any Volume automation exists and user wants new Volume automation → CLEAR_AUTOMATION first, then add new automation (VOL_DIP or FX_PARAM_AUTO).
- Tonal blockers: If an existing EQ/HP/LP/comp setting prevents the requested goal (e.g., harsh HP at 250 Hz while user wants warmth in 200–500 Hz) → remove/disable/retune that blocker first, then apply the new processing.
- Duplicates: Never add the same FX twice. If an FX of the same function already exists, configure it instead of adding another (unless the user explicitly asks for a second instance).

===============================================================================
DECISION PROCESS (FOLLOW THIS ORDER)
===============================================================================

Step 0: PRE-FLIGHT GUARDS
- Check user_input: must exist and contain real text.
- Check state snapshot: must include tracks, FX, and automation sections if relevant. Warn if <5KB.
- Check plugin list: must not be empty.
- Confirm consistent track numbering (0-based or 1-based across Reaper + agent).
- If any guard fails, emit a remediation step (e.g., "refresh full state" or "load plugin database") and stop.

────────────────────────────────────────────
Step 1: UNDERSTAND THE REQUEST
- What exactly does the user want (automation, EQ, reverb, distortion, edit, etc.)?
- Which track(s)? What time range?
- What are the units: Hz, dB, %, ms, semitones, ratios?
- If an essential detail is missing and can't be inferred from the state, 
  set already_complete=false and describe the missing field — do NOT invent values.

────────────────────────────────────────────
Step 2: ANALYZE CURRENT STATE
- Inspect the target track:
  • What FX already exist?
  • Any automation lanes active?
  • Any FX or bands already achieving the requested effect?
- Note blockers: HP/LP filters or automation that would fight the goal.

────────────────────────────────────────────
Step 3: IDENTIFY THE GAP
- Current State: what exists now.
- Goal State: what should exist after.
- Gap: what must change.
Example:
  • Current: Track 1 has Pro-Q 3, no automation.
  • Goal: add band-pass 300–3 kHz, volume dip 10–12 s @ 30%.
  • Gap: need to configure EQ bands, add volume automation.

────────────────────────────────────────────
Step 4: NEUTRALIZE CONFLICTS
- If new Volume automation is requested and existing automation exists → CLEAR_AUTOMATION first.
- If tonal blockers exist (e.g., HP @ 250 Hz but user wants warmth) → remove or retune.
- Never add the same plugin twice; reconfigure the existing one if present.

────────────────────────────────────────────
Step 5: DETERMINE SHORTEST PATH
- Reuse existing FX whenever possible.
- If user names a specific plugin, use only that plugin.
- Parameter normalization:
  • Frequencies (log scale): norm ≈ (log10(f)-log10(f_min))/(log10(f_max)-log10(f_min))
  • Gains (±R dB): norm = (dB+R)/(2R)
  • Percent: p% → p/100
  • Semitones: derive from state range or two observed anchors; use exact integers when requested.
- Instant vs ramp:
  • Instant: two commands (hold until t-ε, jump at t)
  • Ramp: FX_PARAM_AUTO t1→t2 start→end

────────────────────────────────────────────
Step 6: GENERATE COMMANDS (MINIMAL SET ONLY)
- Use the FEWEST commands that achieve the goal.
- Order: Clear conflicts → Add/Reuse FX → Configure params → Automate
- Each command should be atomic and idempotent.
**DO NOT:**
- Add "extra" steps "just in case"
- Configure parameters the user didn't ask for
- Over-engineer with 8 steps when 2 would work
**STOP WHEN:**
- Goal is achieved exactly as requested
- Feedback shows success tokens (✓, ✅)

────────────────────────────────────────────
Step 7: EXECUTE & VERIFY
- Treat success as OR of:
  1) Reaper feedback tokens (✓, ✅, "Success", "Added FX", "VOL_DIP …")
  2) State diff showing expected change.
- If success token seen → do one state refresh max, never re-execute.
- Verification cues:
  • VOL_DIP → new automation window visible.
  • ADD_FX → plugin name appears with parameters.
  • SET_FX_PARAM → parameter value changed in state.
  • FX_PARAM_AUTO → appears in "AUTOMATED PARAMETERS".

────────────────────────────────────────────
Step 8: RETRY & PIVOT (MAX 2 RETRIES ON SAME APPROACH)
- Never repeat a confirmed-success step.
- If feedback shows ✓ or ✅ → STOP immediately, task is done.
- If inconclusive (thin state) → refresh state ONCE, then accept and move on.
- If method fails TWICE → pivot to different approach, don't try a third time:
  • CLEAR_AUTOMATION failed 2x → try envelope delete action instead.
  • Wrong param idx 2x → read pN from state, use exact index.
  • Plugin not found 2x → use fallback (ReaEQ, ReaVerb, ReaComp).
- Numerical convergence: interpolate between two known points; never guess randomly.
**STOP RETRYING IF:**
- Feedback confirms success (✓ or ✅ in response)
- Goal is achieved exactly as specified
- Same method failed twice (pivot to different approach)

────────────────────────────────────────────
Step 9: IDEMPOTENCE & RE-ENTRY
- CLEAR on empty envelope → safe no-op.
- ADD_FX when plugin exists → skip add, just configure.
- Re-runs must yield identical final state.

────────────────────────────────────────────
Step 10: OBSERVABILITY & LOGGING
- Log per step: track, fxIdx, paramIdx, command, feedback_hit, state_len_before/after, verified_in_state, retry_decision.
- Warn if:
  • state < 5 KB
  • "Volume Automation" missing after a volume change
  • plugin list empty

────────────────────────────────────────────
Quick References
• Flat volume baseline → CLEAR_AUTOMATION + VOL_DIP full track @ 1.0
• Dip 10–12 s @ 30% → CLEAR_AUTOMATION + VOL_DIP 10 12 0.3
• Telephone FX → HP ~300 Hz + LP ~3 kHz (steep)
• Underwater FX → LP ~1 kHz (brickwall)
• Warmth → +2–4 dB @ 200–500 Hz + 20–35% tape saturation
• Air → High shelf +2–4 dB @ 8–12 kHz
• Fallbacks: EQ = ReaEQ; Reverb = ReaVerb; Saturation = Kramer/J37; Comp = ReaComp

===============================================================================
COMMANDS YOU MAY EMIT (use exact strings; examples shown)
===============================================================================
- SELECT_TRACK <trackIdx>
- CLEAR_AUTOMATION <trackIdx> Volume
- VOL_DIP <trackIdx> <tStart> <tEnd> <value0-1>        # inserts 4 points
- SET_TRACK_VOL <trackIdx> <volumeDB>
- ADD_FX <trackIdx> <ExactPluginNameFromList>
- REMOVE_FX <trackIdx> <fxIdx>
- SET_FX_PARAM <trackIdx> <fxIdx> <paramIdx> <value0-1>
- FX_PARAM_AUTO <trackIdx> <fxIdx> <paramIdx> <tStart> <tEnd> <startValue> <endValue>
- GET_LYRICS <trackIdx>
- ANALYZE_TRACK <trackIdx>                              # ONLY if analysis not already included above
- APPLY_FROM_JSON <trackIdx> [jsonPath]
- GOTO <seconds>

Notes:
- For multi-plugin requests, create separate steps in the requested order.
- For an FX that already exists, do not ADD_FX; only configure.

===============================================================================
FX CATEGORIES & USAGE GUARDRAILS
===============================================================================
- EQ (tone shaping & filters): names containing "EQ", "Pro-Q", "ReaEQ", "SSL", "API", "Neve", "Pultec"
  • Filter types you must distinguish:
    - Low-Pass (High-Cut): removes highs aggressively (underwater, muffled)
    - High-Pass (Low-Cut): removes lows (rumble cleanup)
    - Band-Pass: allows a band; combine HP+LP (telephone)
    - Bell/Parametric: specific frequency cut/boost
    - Shelf: gradual tilt (air/body)
- Distortion/Saturation (harmonics/grit), NOT exciters or EQ:
  • Manny M, Kramer Tape, J37 Tape, Abbey Road Saturator, FabFilter Saturn/Saturn 2, Soundtoys Decapitator/Devil-Loc/Radiator, Lo‑Fi/BitCrusher, etc.
  • NOT: Aphex Exciter (that’s an exciter), API‑550 (EQ), Pro‑Q (EQ), Abbey Road Vinyl (not pure distortion).
- Dynamics: names with "Comp", "1176", "LA‑2A", "SSL Comp", "Limiter", etc.
- Space: names with "Reverb", "Room", "Plate", "Hall", "Delay", "Echo".
- Analyzers/Visualizers (read‑only; NEVER “fix” with these):
  • Names with "PAZ", "SPAN", "Spectrum", "Analyzer", "Meter".

===============================================================================
COMMON INTENT→TECHNIQUE MAP (FAST PATHS)
===============================================================================
- “Underwater” → Low-Pass ~800–1000 Hz, steep slope via EQ.
- “Telephone” → Band-pass 300–3000 Hz: HP ~300 + LP ~3k, steep.
- “Warmth” → +2–4 dB around 200–500 Hz and/or 20–35% tape/tube saturation.
- “Air/Brightness” → High shelf +2–4 dB at 8–12 kHz (mind sibilance).
- “Tighten low end” → HP 40–80 Hz + compression.
- “Punch up drums” → Transient shaping or fast compressor + EQ (kick 60–100 Hz, snare 3–5 kHz).
- “Dark moody vocal” → Reduce 8–12 kHz, maybe HP 80–100 Hz, heavier compression, long dark plate low mix.

===============================================================================
PARAMETER NORMALIZATION PLAYBOOK (PRECISION)
===============================================================================
- Frequencies (typical log scale): If plugin doesn’t reveal mapping, estimate:
    n ≈ (log10(f) - log10(f_min)) / (log10(f_max) - log10(f_min))
  Use f_min/f_max from plugin display if shown; otherwise assume 20–20000 Hz cautiously.
- Gains (dB): If ±R dB, normalized gain g_norm = (g_dB + R) / (2R).
  Example: ±12 dB; +3 dB → (3 + 12) / 24 = 0.625.
- Percentages: direct mapping (30% → 0.30).
- Discrete musical units (semitones, ratios): derive from STATE ranges or from two observed points; set exact musical integers where requested.
- Interpolation rule:
  If you have (n1→disp1) and (n2→disp2) and need dispT, compute:
    t = (dispT - disp1) / (disp2 - disp1)  (linear in the correct domain)
    nT = n1 + t * (n2 - n1)

===============================================================================
AUTOMATION PATTERNS (CANONICAL)
===============================================================================
- Flat baseline (0 dB / unity) across the entire track via automation:
  • CLEAR_AUTOMATION <trk> Volume
  • VOL_DIP <trk> 0.0 <track_end> 1.0
- Single dip (mute or percent) between t1 and t2:
  • CLEAR_AUTOMATION <trk> Volume
  • VOL_DIP <trk> t1 t2 v        # v=0.0 for full mute, 0.3 for 30%, etc.
- Instant FX switch at time t for a parameter p:
  • FX_PARAM_AUTO <trk> <fx> <p> 0.0 (t-0.01) v_before v_before
  • FX_PARAM_AUTO <trk> <fx> <p> t t v_after v_after
- Ramp over [t1, t2]:
  • FX_PARAM_AUTO <trk> <fx> <p> t1 t2 v1 v2

===============================================================================
RETRY & PIVOT DECISION TREE
===============================================================================
- If ADD_FX succeeded → Do NOT re-add. Next step: configure with correct paramIdx from NEW STATE.
- If a SET_FX_PARAM failed due to wrong index → read NEW STATE, find the named parameter (e.g., "Band 1 Gain" or "p3"), then retry with that index.
- If CLEAR_AUTOMATION had no effect:
  • If {actions_text} includes a specific “Delete all points on envelope” action → use that.
  • Otherwise, consider reissuing CLEAR_AUTOMATION on the correct track.
- If a method fails twice with no state change → pivot to a valid alternative, not the same command again.
- Always converge numerically with interpolation when possible; avoid random guesses.

===============================================================================
AMBIGUITY & ALREADY‑COMPLETE GUARD
===============================================================================
- Missing essentials (track/time/target) and not deducible from STATE:
  → already_complete=false; "reasoning" states exactly which single detail is missing; steps=[].
- If CURRENT STATE already matches the exact requested goal:
  → already_complete=true; steps=[]; "reasoning" explains why.

===============================================================================
EXAMPLES (REFERENCE — ADAPT PARAM INDICES FROM ACTUAL STATE)
===============================================================================
A) Volume dip 10–15s at 30% on track 1 (existing vol automation present)
  Steps:
    1) CLEAR_AUTOMATION 1 Volume
    2) VOL_DIP 1 10.0 15.0 0.3

B) Flatten volume to unity by automation across track 3 (wipe previous dips)
  Steps:
    1) CLEAR_AUTOMATION 3 Volume
    2) VOL_DIP 3 0.0 <track_end_seconds> 1.0

C) Telephone effect on track 0 (any EQ)
  Steps:
    1) If no EQ present: ADD_FX 0 <Exact EQ Name From List>
    2) Configure HP ~300 Hz and LP ~3000 Hz with steep slopes via SET_FX_PARAM on that EQ (use indices from STATE)

D) Add air to vocals on track 2 using existing Pro‑Q 3 at fxIdx=0
  Steps:
    1) Enable an unused high‑shelf band
    2) SET_FX_PARAM 2 0 <band_freq_param> <norm_for_8k>
    3) SET_FX_PARAM 2 0 <band_gain_param> <norm_for_+3dB>
    4) SET_FX_PARAM 2 0 <band_shape_param> <value_for_high_shelf>

E) Underwater switch at 3.7s on track 1 with existing EQ:
  Steps:
    1) FX_PARAM_AUTO 1 <fxIdx_EQ> <lp_freq_param> 0.0 3.69 <norm_for_high_value> <norm_for_high_value>
    2) FX_PARAM_AUTO 1 <fxIdx_EQ> <lp_freq_param> 3.7 3.7 <norm_for_1kHz> <norm_for_1kHz>

F) Warmth for synth on track 4: boost 300 Hz + tape saturation (no duplicates)
  Steps:
    1) If EQ exists: reuse it; else ADD_FX 4 <EQ>
    2) Add bell at ~300 Hz, +2.5 dB, moderate Q
    3) If saturation exists (tape/tube): set 25–35% drive; else ADD_FX 4 <Tape/Tubes Plugin> then set drive

G) Multiple dips on track 1 at [5–7s → 0%], [20–22s → 30%], flat elsewhere:
  Steps:
    1) CLEAR_AUTOMATION 1 Volume
    2) VOL_DIP 1 5.0 7.0 0.0
    3) VOL_DIP 1 20.0 22.0 0.3
    4) (Implicit flat 1.0 before/after, or add a baseline dip covering full track at 1.0 if needed)

H) Brighten but reduce sibilance on track 2 with an existing EQ:
  Steps:
    1) Bell cut around 6–8 kHz, −2 dB (de‑ess region)
    2) High shelf +2 dB at 10–12 kHz (air) — use separate band
    3) Verify by STATE values; avoid shelf if it counters the de‑ess cut too much

I) If audio analysis is provided above showing “Muddy 250–500 Hz, recommend −3 dB @ 300 Hz, Q 2–3”
  Steps:
    1) Do NOT re‑analyze
    2) Use existing EQ; enable a bell band, set ~300 Hz, −3 dB, Q≈2–3

J) Distortion request “Waves distortion” → choose only Manny M / Kramer Tape / J37 / Abbey Road Saturator (from list). NOT Aphex Exciter.

===============================================================================
VALIDATION CHECKLIST (RUN BEFORE EMITTING)
===============================================================================
- Goal already satisfied? → already_complete=true, steps=[]
- Any automation conflicts? → CLEAR before adding new
- Any FX duplicates? → configure existing instead of adding
- Correct track/fxIdx/paramIdx from CURRENT STATE used?
- Values normalized 0–1 with correct scale? (dB linear, Hz log unless proven otherwise)
- Output is ONLY JSON (schema above), no extra text.

===============================================================================
ANALYSIS SECTION RULE
===============================================================================
If the prompt includes "AUDIO ANALYSIS RESULTS" above:
- Do NOT run ANALYZE_TRACK.
- Implement those recommendations directly.
- On retries, refine values based on feedback and NEW STATE (do not re‑analyze).

===============================================================================
FINAL REMINDER
===============================================================================
- Focus on goal state, not habit. If one method is blocked, choose another valid path.
- Never rely on analyzers to "fix" audio—they are read‑only.
- For multi‑parameter/FX changes, emit one step per change.
- Keep "reasoning" short and concrete. The JSON must be the only output.

"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[{"role": "user", "content": system_prompt}]
        ).content[0].text.strip()
        
        log_debug(f"Plan: {response}")
        return response
    except Exception as e:
        log_debug(f"Plan error: {e}")
        return '{}'

def translate_natural_language(user_input):
    """Convert natural language sound description to technical commands"""
    if not sound_knowledge:
        return user_input  # No translation if knowledge base not loaded
    
    # Check if input is technical/utility command (skip translation)
    technical_markers = ["pro q", "saturn", "valhalla", "db", "hz", "khz", "ms", "wet", "drive", "pitch"]
    utility_commands = ["delete", "remove", "clear", "open", "close", "mute", "solo", "play", "stop", "record"]
    user_lower = user_input.lower()
    
    if any(marker in user_lower for marker in technical_markers):
        return user_input  # Already technical, skip translation
    if any(cmd in user_lower for cmd in utility_commands):
        return user_input  # Utility command, skip translation
    
    system_prompt = f"""You are a sound design translator. Convert natural language descriptions into technical DAW commands.

**SOUND KNOWLEDGE BASE:**
{json.dumps(sound_knowledge, indent=2)}

**USER SAID:** "{user_input}"

**YOUR TASK:**
1. Analyze the sonic qualities requested (brightness, warmth, space, clarity, punch, width)
2. Consider context (vocal, drums, synth) and intensity (subtle, heavy)
3. Use the knowledge base to understand WHAT creates each quality
4. Choose appropriate plugins and specific settings
5. Output a precise technical command

**CRITICAL:**
- Don't rigidly map "warmth = Saturn" - THINK about what creates warmth (harmonics, frequency shaping, vintage color)
- Consider multiple paths and choose the best one
- Be specific with frequencies and amounts

**OUTPUT FORMAT (JSON):**
{{
  "intent_analysis": "User wants [qualities] for [context]",
  "sonic_reasoning": "Explain WHY you chose this approach",
  "technical_command": "add pro q 3 and boost at 6khz by 4db, then add saturn with 20% drive on band 1"
}}

CRITICAL: Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": system_prompt}]
        ).content[0].text.strip()
        
        translation = json.loads(response)
        technical_cmd = translation.get("technical_command", user_input)
        sonic_reasoning = translation.get("sonic_reasoning", "")
        
        print(f"\n🎨 Translation:")
        print(f"   Intent: {translation.get('intent_analysis', 'N/A')}")
        if sonic_reasoning:
            print(f"   Reasoning: {sonic_reasoning}")
        print(f"   → Technical: {technical_cmd}\n")
        
        return technical_cmd
    except Exception as e:
        log_debug(f"Translation error: {e}")
        print(f"⚠️ Translation failed, using original input: {e}")
        return user_input  # Fallback to original input

def extract_relevant_state_sections(state, commands):
    """
    Extract only the relevant parts of state based on commands executed.
    Returns focused state string with only affected tracks/sections.
    """
    relevant_sections = []
    
    # Parse commands to find affected tracks
    affected_tracks = set()
    for cmd in commands.split('\n'):
        # VOL_DIP, SET_TRACK_VOL, SELECT_TRACK, ADD_FX, etc.
        track_match = re.search(r'(?:VOL_DIP|SET_TRACK_VOL|SELECT_TRACK|ADD_FX|REMOVE_FX|SET_FX_PARAM|FX_PARAM_AUTO)\s+(\d+)', cmd)
        if track_match:
            affected_tracks.add(int(track_match.group(1)))
    
    # Extract each affected track's section
    current_track = None
    current_section = []
    in_relevant_track = False
    
    for line in state.split('\n'):
        # Track header line
        track_match = re.match(r'--- Track (\d+):', line)
        if track_match:
            # Save previous section if it was relevant
            if in_relevant_track and current_section:
                relevant_sections.append('\n'.join(current_section))
            
            current_track = int(track_match.group(1))
            in_relevant_track = current_track in affected_tracks
            current_section = [line] if in_relevant_track else []
        elif in_relevant_track:
            current_section.append(line)
            
            # Stop collecting if we hit next track or end marker
            if line.startswith('---') and 'Track' not in line:
                break
    
    # Add last section
    if in_relevant_track and current_section:
        relevant_sections.append('\n'.join(current_section))
    
    # Also include AUTOMATED PARAMETERS section if exists
    if '=== AUTOMATED PARAMETERS ===' in state:
        auto_section = state.split('=== AUTOMATED PARAMETERS ===')[1].split('===')[0]
        relevant_sections.append('=== AUTOMATED PARAMETERS ===' + auto_section)
    
    # If no tracks found, return first 3000 chars as fallback
    if not relevant_sections:
        return state[:3000]
    
    return '\n\n'.join(relevant_sections)

def verify_result(user_input, initial_state, final_state, executed_commands, feedback, lyrics_extracted=False):
    """Phase 3: Check if goal was achieved"""
    
    lyrics_note = ""
    if lyrics_extracted:
        lyrics_note = "\n**LYRICS:** ✅ Lyrics were successfully extracted and displayed to user (check console output above)."
    
    # Extract only relevant sections from states (smart truncation)
    relevant_before = extract_relevant_state_sections(initial_state, executed_commands)
    relevant_after = extract_relevant_state_sections(final_state, executed_commands)
    
    system_prompt = f"""You executed commands in Reaper. Verify if the user's goal was ACTUALLY achieved.

**USER WANTED:** {user_input}

**STATE BEFORE (relevant sections only):**
{relevant_before}

**COMMANDS EXECUTED:**
{executed_commands}

**REAPER FEEDBACK:**
{feedback}

**STATE AFTER (relevant sections only):**
{relevant_after}

**CRITICAL:** Check the AUTOMATED PARAMETERS section in STATE AFTER (near the end) to see if automation was created.
{lyrics_note}

**YOUR TASK:**
Compare before/after states. BE STRICT - only say success if the EXACT goal was met.

**═══════════════════════════════════════════════════════════════════════════════**
**COMMAND-SPECIFIC VERIFICATION - WHERE TO LOOK FOR EACH COMMAND TYPE**
**═══════════════════════════════════════════════════════════════════════════════**

**CRITICAL: Different commands change different parts of state. Look in the RIGHT place!**

**1. VOL_DIP commands (volume automation):**
   WHERE TO LOOK: Search STATE AFTER for "Volume Automation:" under the target track
   
   Example command: VOL_DIP 3 0.0 211.0 1.0
   
   What to check:
   - Find "--- Track 3:" section in STATE AFTER
   - Look for "Volume Automation: X points" line
   - Read the automation point values (timestamps and dB levels)
   - Compare to BEFORE: Did number of points change? Did values change?
   
   SUCCESS criteria:
   - If goal was "flat 0dB": automation points should all be at ~0dB or ~57dB (Reaper's way of showing 0dB)
   - If goal was "dip at 20s": should see point at 20s with low dB value
   - Point count may increase (new automation added) or stay same (overwrite)
   
   FAILURE signs:
   - BEFORE and AFTER show identical "Volume Automation: 17 points" with same values
   - No change in automation point dB levels
   - Still shows dips when goal was flat line

**2. ADD_FX commands (adding plugins):**
   WHERE TO LOOK: Search STATE AFTER for "FX [N]" list under target track
   
   Example command: ADD_FX 2 VST3: ValhallaRoom (Valhalla DSP, LLC)
   
   What to check:
   - Find "--- Track 2:" section
   - Look for "FX [0]", "FX [1]", "FX [2]" lines
   - Check if plugin name appears (e.g., "VST3: ValhallaRoom")
   - Note the FX index number
   
   SUCCESS criteria:
   - Plugin name appears in FX list
   - Has associated parameters listed below it
   
   FAILURE signs:
   - Plugin name not found in FX list
   - Same FX count as BEFORE
   - Feedback says "plugin not found" or "failed to add"

**3. SET_FX_PARAM commands (setting plugin parameters):**
   WHERE TO LOOK: Find the specific plugin and parameter in STATE AFTER
   
   Example command: SET_FX_PARAM 2 0 67 0.7959
   (Track 2, FX index 0, param 67, value 0.7959)
   
   What to check:
   - Find "--- Track 2:" → "FX [0]" section
   - Scroll through params until you find "p67" or "[ 67]"
   - Read the value: should be close to 0.7959 (or formatted value like "8000 Hz")
   - Compare to BEFORE: Did this specific param value change?
   
   SUCCESS criteria:
   - Param 67 shows new value (0.7959 or ~80% or frequency ~8000Hz)
   - Value is DIFFERENT from BEFORE state
   
   FAILURE signs:
   - Param 67 has same value as BEFORE
   - Can't find param 67 (wrong FX index or param doesn't exist)

**4. FX_PARAM_AUTO commands (FX parameter automation):**
   WHERE TO LOOK: Search for "=== AUTOMATED PARAMETERS ===" section in STATE AFTER
   
   Example command: FX_PARAM_AUTO 0 1 11 3.7 3.7 1.0 1.0
   (Track 0, FX 1, param 11, instant change at 3.7s to 100%)
   
   What to check:
   - Find "=== AUTOMATED PARAMETERS ===" section (appears AFTER all tracks)
   - Look for line mentioning track 0, FX 1, param 11
   - Check if automation points at 3.7s appear
   
   SUCCESS criteria:
   - "=== AUTOMATED PARAMETERS ===" section exists in AFTER (not in BEFORE)
   - Shows automation for correct track/FX/param
   - Timestamps match command (3.7s in example)
   
   FAILURE signs:
   - No "=== AUTOMATED PARAMETERS ===" section in AFTER
   - Section exists but doesn't mention the target param
   - Automation exists but wrong track/FX/param

**5. Action ID commands (e.g., 40280 for solo):**
   WHERE TO LOOK: Depends on action type
   
   For solo/mute (40280, 40294):
   - Find track section → look for "Solo: YES" or "Muted: YES"
   
   For envelope visibility (6, 40406):
   - Look for "Volume Envelope: Visible" or similar
   - May NOT show in state (UI change only)
   
   For delete automation (40205):
   - Check "Volume Automation:" line → should show fewer points or "no automation"

**6. SELECT_TRACK commands:**
   WHERE TO LOOK: Check which track shows "Selected: YES"
   
   What to check:
   - Find "--- Track N:" sections
   - Look for "Selected: YES" line
   - Only ONE track should be selected (others show "Selected: NO")
   
   SUCCESS: Target track has "Selected: YES"
   FAILURE: Wrong track selected or no track selected

**CRITICAL RULES:**

1. **For lyrics requests:**
   - If LYRICS note above says "✅ Lyrics were successfully extracted", lyrics task is COMPLETE
   - NEVER say "lyrics were not extracted" if the LYRICS note confirms success
   - Lyrics don't show in STATE - they're printed to console separately

2. **For filter type requests (low-pass, high-pass, band-pass):**
   - Check EXACT filter type in STATE AFTER
   - "Low Shelf" ≠ "Low-Pass" (different filter types)
   - "High Shelf" ≠ "High-Pass" (different filter types)
   - "Bell" ≠ "Band-Pass" (different filter types)
   - If user wanted "low-pass" but got "low shelf", that's FAILURE

3. **For frequency/parameter changes:**
   - Check if values actually changed in STATE AFTER
   - Compare before/after numerically
   - If nothing changed, it's FAILURE

4. **Don't accept "close enough":**
   - If user wanted low-pass filter, ONLY low-pass filter = success
   - Similar-sounding names don't count

**NO CHANGE RULE:** If states are identical but BEFORE state already matches the user's goal exactly, it's SUCCESS with explanation: "Already in desired state."

**COMMAND-TO-STATE MAPPING (what to search for):**

VOL_DIP → "Volume Automation: X points" under target track
ADD_FX → "FX [N] PluginName" appears in FX list
REMOVE_FX → Plugin disappears from FX list
SET_FX_PARAM → Specific "pN:" value changes
FX_PARAM_AUTO → "=== AUTOMATED PARAMETERS ===" section appears/updates
SELECT_TRACK → "Selected: YES" on target track
SET_TRACK_VOL → "Volume: X.XdB" line changes
Action 40280 (solo) → "Solo: YES" appears
Action 40294 (mute) → "Muted: YES" appears

**OUTPUT REQUIREMENTS - CRITICAL:**
1. ONLY output valid JSON - NO explanatory text before or after
2. Do NOT write any prose or analysis outside the JSON
3. Start your response with {{ and end with }}
4. The ENTIRE response must be parseable as JSON

**OUTPUT FORMAT (COPY THIS STRUCTURE EXACTLY):**
{{{{
  "success": true/false,
  "explanation": "What actually happened (max 2 sentences)",
  "issues": "What's wrong or what still needs to be done"
}}}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0,
            messages=[{"role": "user", "content": system_prompt}]
        ).content[0].text.strip()
        
        log_debug(f"Verify: {response}")
        return response
    except Exception as e:
        log_debug(f"Verify error: {e}")
        return '{"success": false, "explanation": "Verification failed", "issues": "API error"}'

def break_into_subgoals(user_input, state):
    """Break user's request into sequential sub-goals using CoT"""
    
    prompt = f"""Break this DAW request into SEQUENTIAL sub-goals (chain of thought approach).

**USER REQUEST:** {user_input}

**CURRENT STATE:** {state[:1500]}

**YOUR JOB:** Identify the logical sub-goals needed to achieve the request.

**EXAMPLES:**

Request: "add reverb to track 1 and make it underwater"
Sub-goals:
1. Add reverb plugin to track 1
2. Configure reverb settings (decay, mix)
3. Add low-pass filter for underwater effect

Request: "make track 3 sound like a phone call"
Sub-goals:
1. Add EQ to track 3
2. Configure band-pass filter 300-3000Hz with steep slopes

Request: "create volume dip on track 1 from 5-10s and add compression"
Sub-goals:
1. Create volume automation dip on track 1 from 5-10 seconds
2. Add compressor to track 1
3. Configure compression settings

**RULES:**
1. Each sub-goal should be independently verifiable
2. Sub-goals should be sequential (can't do step 3 before step 1)
3. Keep it simple - 2-5 sub-goals max
4. Each sub-goal is ONE clear action

**OUTPUT JSON:**
{{{{
  "sub_goals": [
    "Add EQ to track 1",
    "Configure low-pass filter at 1000Hz",
    "Set filter slope to brickwall"
  ]
}}}}"""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text.strip()
        
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()
        
        result = json.loads(response)
        return result.get("sub_goals", [])
    except:
        # If parsing fails, treat entire request as one goal
        return [user_input]

def execute_user_command(user_input):
    """Main agentic loop with Chain of Thought: Break into sub-goals → Execute each → Verify"""
    
    print(f"\n🎤 User: {user_input}")
    
    # Check for reference matching requests
    user_lower = user_input.lower()
    if "sound like" in user_lower:
        # Simple parsing: extract track number and reference part
        # "make track 1 sound like reference.wav"
        
        # Find target track number
        track_match = re.search(r'track\s+(\d+)', user_lower)
        if not track_match:
            print("⚠️ Please specify which track to process (e.g., 'track 1')")
            return
        
        target_track = int(track_match.group(1))
        
        # Extract everything after "sound like" from ORIGINAL input (preserve case/path)
        sound_like_pos = user_input.lower().find("sound like")
        ref_part = user_input[sound_like_pos + len("sound like"):].strip()
        
        if not ref_part:
            print("⚠️ Please specify reference (e.g., 'sound like reference.wav')")
            return
        
        print(f"🎯 Reference matching: Track {target_track} → '{ref_part}'")
        
        # Call the matching function
        result = match_to_reference(target_track, ref_part)
        return
    
    # Check if user is requesting analysis-based actions
    analysis_keywords = ['muddy', 'harsh', 'bright', 'dark', 'compressed', 'loud', 'quiet', 'thin', 'fix', 'improve', 'balance']
    action_keywords = ['fix', 'improve', 'add', 'configure', 'adjust', 'change', 'boost', 'cut', 'reduce', 'mix']
    
    user_lower = user_input.lower()
    needs_analysis = any(keyword in user_lower for keyword in analysis_keywords)
    wants_action = any(keyword in user_lower for keyword in action_keywords)
    
    # Auto-analyze if:
    # 1. User wants to fix/improve something (needs_analysis=True)
    # 2. AND user wants action taken (wants_action=True)  
    # 3. This ensures "analyze and fix" triggers auto-analysis, but "does it sound muddy?" doesn't
    analysis_context = ""
    if needs_analysis and wants_action:
        # User wants to fix/improve something - analyze first
        print("🔬 Analysis-based request detected - analyzing audio first...")
        
        # Parse which track to analyze (default to track 0)
        track_idx = 0
        track_match = re.search(r'track\s+(\d+)', user_input.lower())
        if track_match:
            track_idx = int(track_match.group(1))
        
        # Get track name from state  
        state = get_reaper_state()
        track_name_match = re.search(rf'--- Track {track_idx}: (.+) ---', state)
        track_name = track_name_match.group(1) if track_name_match else f"Track_{track_idx}"
        
        # Start playback before export (prevents offline/empty exports)
        print("▶️ Starting playback for export...")
        send_reaper_commands(["1007"])  # Play command
        time.sleep(0.5)  # Brief wait for playback to start
        
        # Export and analyze
        Path(TEMP_AUDIO_DIR).mkdir(exist_ok=True)
        temp_audio_folder = Path(TEMP_AUDIO_DIR) / f"analyze_track_{track_idx}_{int(time.time())}"
        
        if send_reaper_commands([f"EXPORT_AUDIO {track_idx} {temp_audio_folder}"]):
            time.sleep(2.0)
            wav_files = list(temp_audio_folder.glob("*.wav")) if temp_audio_folder.exists() else []
            if wav_files:
                temp_audio = wav_files[0]
                analysis = analyze_audio_track(track_idx, track_name, str(temp_audio))
                
                if "error" not in analysis:
                    # Format analysis for Claude (with safety checks for missing keys)
                    loudness = analysis.get('loudness', {})
                    stereo = analysis.get('stereo_image', {})
                    tonal = analysis.get('tonal_characteristics', {})
                    
                    analysis_context = f"""
**AUDIO ANALYSIS RESULTS for {track_name}:**
Loudness: {loudness.get('average_rms_db', 'N/A')}dB RMS, Peak: {loudness.get('peak_db', 'N/A')}dB
Dynamic Range: {loudness.get('dynamic_range_db', 'N/A')}dB ({loudness.get('assessment', 'N/A')})
Stereo Width: {stereo.get('width_percentage', 'N/A')}% ({stereo.get('assessment', 'N/A')})
Brightness: {tonal.get('assessment', 'N/A')}

Frequency Balance:
- Sub Bass (20-60Hz): {analysis.get('frequency_balance', {}).get('sub_bass_20_60hz', 0):.1f}dB
- Bass (60-250Hz): {analysis.get('frequency_balance', {}).get('bass_60_250hz', 0):.1f}dB  
- Low Mids (250-500Hz): {analysis.get('frequency_balance', {}).get('low_mids_250_500hz', 0):.1f}dB
- Mids (500-2kHz): {analysis.get('frequency_balance', {}).get('mids_500_2khz', 0):.1f}dB
- High Mids (2-5kHz): {analysis.get('frequency_balance', {}).get('high_mids_2_5khz', 0):.1f}dB
- Highs (5-20kHz): {analysis.get('frequency_balance', {}).get('highs_5_20khz', 0):.1f}dB

Effects Detected (what's actually applied to the audio):
- Filtering: {analysis.get('effects_detected', {}).get('filtering', {}).get('assessment', 'N/A')} (rolloff at {analysis.get('effects_detected', {}).get('filtering', {}).get('rolloff_frequency_hz', 0):.0f}Hz)
- Distortion/Saturation: {analysis.get('effects_detected', {}).get('distortion', {}).get('assessment', 'N/A')}
- Harmonic Content: {analysis.get('effects_detected', {}).get('harmonics', {}).get('assessment', 'N/A')}
- Reverb/Space: {analysis.get('effects_detected', {}).get('reverb', {}).get('assessment', 'N/A')}

Issues Detected: {', '.join(analysis.get('issues_detected', [])) if analysis.get('issues_detected') else 'None'}
Recommendations: {', '.join(analysis.get('recommendations', [])) if analysis.get('recommendations') else 'None'}

**CRITICAL: Use the "Effects Detected" section to verify if your changes actually worked:**
- If you added low-pass filter → check if rolloff frequency dropped to ~1000Hz
- If you added distortion → check if distortion level increased
- If you added saturation → check if harmonic content increased
- If you added reverb → check if reverb assessment changed from "Dry" to "Moderate/Heavy"

**Use this analysis to decide what plugins/settings to apply to fix the detected issues.**
"""
                    print(f"✅ Analysis complete - {len(analysis['issues_detected'])} issues found")
                
                # Clean up
                try:
                    shutil.rmtree(temp_audio_folder)
                except:
                    pass
    
    # Check if user is requesting word-based automation
    word_pattern = r'(?:after|before|at|during)\s+(?:the\s+word\s+)?([A-Z]+)'
    word_match = re.search(word_pattern, user_input, re.IGNORECASE)
    
    lyric_context = ""
    if word_match:
        target_word = word_match.group(1).upper()
        print(f"🎵 Word-based automation detected: '{target_word}'")
        
        # Parse which track (default to track 0)
        track_idx = 0
        track_match = re.search(r'track\s+(\d+)', user_input.lower())
        if track_match:
            track_idx = int(track_match.group(1))
        
        # Get track name from state
        state = get_reaper_state()
        track_name_match = re.search(rf'--- Track {track_idx}: (.+) ---', state)
        track_name = track_name_match.group(1) if track_name_match else f"Track_{track_idx}"
        
        # Analyze lyrics
        lyrics_data = analyze_lyrics(track_idx, track_name)
        
        if lyrics_data:
            timestamp = find_word_timestamp(lyrics_data, target_word)
            
            # Format ALL lyrics for Claude to see
            lyrics_text = "\n".join([f"[{w['start']:.1f}s-{w['end']:.1f}s] {w['word']}" for w in lyrics_data[:50]])
            if len(lyrics_data) > 50:
                lyrics_text += f"\n... ({len(lyrics_data) - 50} more words)"
            
            if timestamp:
                lyric_context = f"\n**LYRIC TIMELINE (all words with timestamps):**\n{lyrics_text}\n\n**TARGET WORD:** '{target_word}' ends at {timestamp:.2f} seconds. Use this exact timestamp for automation."
                print(f"✅ Found '{target_word}' at {timestamp:.2f}s")
            else:
                lyric_context = f"\n**LYRIC TIMELINE (all words with timestamps):**\n{lyrics_text}\n\n**WARNING:** Word '{target_word}' not found in lyrics. Choose closest match or ask user."
                print(f"⚠️ Word '{target_word}' not found in lyrics")
                # Show available words
                all_words = [w['word'] for w in lyrics_data[:30]]
                print(f"   Available words: {', '.join(all_words)}")
    
    # Translate natural language to technical commands if needed
    # DISABLED FOR NOW - causing translation failures
    # technical_input = translate_natural_language(user_input)
    technical_input = user_input  # Skip translation for now
    
    # Get initial state
    print("📊 Reading Reaper state...")
    initial_state = get_reaper_state()
    
    # Load all actions and plugins
    known_actions = load_action_list()
    available_plugins = load_plugin_list()
    print(f"💪 Loaded {len(known_actions)} total actions")
    print(f"🎛️ Loaded {len(available_plugins)} available plugins")
    
    # Retry loop (up to 6 attempts - if it's not working by then, it won't work)
    max_retries = 6
    retry_count = 0
    previous_issues = ""
    previous_feedback = ""
    retry_history = []  # Track what we tried and what happened
    lyrics_already_displayed = False  # Track if we've already shown lyrics to user
    no_recommendations_count = 0  # Track consecutive retries with no recommendations
    failed_actions = set()  # Track action IDs that failed (don't retry these)
    failed_commands = set()  # Track custom commands that failed (don't retry these)
    reasoning = ""  # Initialize reasoning variable
    
    while retry_count < max_retries:
        if retry_count == 0:
            print(f"\n🧠 Planning actions...")
        else:
            print(f"\n🔄 RETRY {retry_count}/{max_retries} - Replanning with new information...")
            if previous_issues:
                print(f"⚠️ Previous issue: {previous_issues[:150]}...")
            
            # Clear feedback file to prevent stale feedback from previous attempt
            clear_reaper_feedback()
            
            # Save snapshot before retry so we can compare what changed
            retry_snapshot_label = f"retry_{retry_count}: {user_input[:40]}"
            save_state_snapshot(retry_snapshot_label)
            print(f"📸 Snapshot saved: {retry_snapshot_label}")
        
        # PHASE 1: PLAN
        # Filter out failed actions from available actions (don't retry what already failed)
        available_actions_filtered = {k: v for k, v in known_actions.items() if k not in failed_actions}
        if failed_actions:
            print(f"🚫 Blocking {len(failed_actions)} previously failed action IDs from retry")
        if failed_commands:
            print(f"🚫 Blocking {len(failed_commands)} previously failed command variants from retry")
        
        # DEBUG: Log what we're sending to planner
        log_debug(f"Sending to planner: user_input='{technical_input[:100]}...', state_len={len(initial_state)}, plugins={len(available_plugins)}")
        print(f"🔍 DEBUG: Sending user request to planner: '{technical_input[:100]}...'")
        
        plan_response = plan_actions(technical_input, initial_state, available_actions_filtered, available_plugins, previous_issues, previous_feedback, lyric_context, analysis_context, retry_history, conversation_history, failed_commands)
        
        # Strip markdown code blocks if present (Claude sometimes wraps JSON in ```json ... ```)
        plan_response_clean = plan_response.strip()
        if plan_response_clean.startswith("```json"):
            plan_response_clean = plan_response_clean[7:]  # Remove ```json
        if plan_response_clean.startswith("```"):
            plan_response_clean = plan_response_clean[3:]  # Remove ```
        if plan_response_clean.endswith("```"):
            plan_response_clean = plan_response_clean[:-3]  # Remove trailing ```
        plan_response_clean = plan_response_clean.strip()
        
        try:
            plan = json.loads(plan_response_clean)
            reasoning = plan.get("reasoning", "")
            already_complete = plan.get("already_complete", False)
            steps = plan.get("steps", [])
            
            print(f"\n💭 Reasoning: {reasoning}")
            
            # Check if agent needs clarification
            clarification_keywords = ["need clarification", "unclear", "ambiguous", "specify", "which", "please clarify"]
            needs_clarification = any(keyword in reasoning.lower() for keyword in clarification_keywords)
            
            if needs_clarification and len(steps) == 0:
                print(f"\n❓ Agent needs clarification to proceed.")
                print(f"💬 Please provide more details and I'll continue.\n")
                break  # Exit retry loop and return to chat
            
            # Check if task is already complete
            # BUT: If we're on a retry and nothing changed, this is a FALSE POSITIVE (agent gave up)
            if already_complete and retry_count == 0:
                print(f"\n✅ ALREADY COMPLETE: Task already fulfilled in current state")
                
                # Verify with librosa analysis if it's an effect request
                if any(keyword in user_input.lower() for keyword in ['underwater', 'sound', 'effect', 'distortion', 'reverb', 'saturation']):
                    track_match = re.search(r'track\s+(\d+)', user_input.lower())
                    if track_match:
                        track_idx = int(track_match.group(1))
                        track_name_match = re.search(rf'--- Track {track_idx}: (.+) ---', initial_state)
                        track_name = track_name_match.group(1) if track_name_match else f"Track_{track_idx}"
                        
                        print(f"🔬 Verifying with audio analysis...")
                        
                        send_reaper_commands(["1007"])  # Play
                        time.sleep(0.5)
                        
                        Path(TEMP_AUDIO_DIR).mkdir(exist_ok=True)
                        verify_folder = Path(TEMP_AUDIO_DIR) / f"verify_{track_idx}_{int(time.time())}"
                        
                        if send_reaper_commands([f"EXPORT_AUDIO {track_idx} {verify_folder}"]):
                            time.sleep(2.0)
                            wav_files = list(verify_folder.glob("*.wav")) if verify_folder.exists() else []
                            if wav_files:
                                analysis = analyze_audio_track(track_idx, track_name, str(wav_files[0]))
                                
                                if "error" not in analysis and 'effects_detected' in analysis:
                                    print(f"\n📊 Audio Analysis Verification:")
                                    print(f"   Filtering: {analysis['effects_detected']['filtering']['assessment']}")
                                    print(f"   Distortion: {analysis['effects_detected']['distortion']['assessment']}")
                                    print(f"   Reverb: {analysis['effects_detected']['reverb']['assessment']}")
                                    print(f"   Harmonics: {analysis['effects_detected']['harmonics']['assessment']}")
                                    
                                    # Librosa is the final authority - if it confirms the effect, we're done
                                    effect_confirmed = False
                                    if 'underwater' in user_input.lower():
                                        rolloff = analysis['effects_detected']['filtering']['rolloff_frequency_hz']
                                        if rolloff < 2000:  # Underwater detected
                                            print(f"\n✅ Librosa confirms: Underwater effect detected (rolloff at {rolloff:.0f}Hz)")
                                            effect_confirmed = True
                                    
                                    if 'distortion' in user_input.lower() or 'saturation' in user_input.lower():
                                        if 'saturation' in analysis['effects_detected']['distortion']['assessment'].lower() or 'distortion' in analysis['effects_detected']['distortion']['assessment'].lower():
                                            print(f"\n✅ Librosa confirms: Distortion/saturation detected")
                                            effect_confirmed = True
                                    
                                    if 'reverb' in user_input.lower():
                                        if 'reverb' in analysis['effects_detected']['reverb']['assessment'].lower():
                                            print(f"\n✅ Librosa confirms: Reverb detected")
                                            effect_confirmed = True
                                    
                                    if not effect_confirmed:
                                        print(f"\n⚠️ Librosa check: Effect may not be fully applied yet")
                                
                                # Clean up
                                try:
                                    shutil.rmtree(verify_folder)
                                except:
                                    pass
                
                break  # Exit loop immediately - no execution needed
            
            # Also check if steps is empty but reasoning suggests completion
            if len(steps) == 0:
                if "already" in reasoning.lower() or "fulfilled" in reasoning.lower():
                    # Only accept "already complete" on first attempt, not after multiple failures
                    if retry_count == 0:
                        print(f"\n✅ ALREADY COMPLETE: No steps needed (task already done)")
                        break
                    else:
                        print(f"\n⚠️ Agent claims 'already complete' but this is retry {retry_count} - that's a false positive (agent gave up)")
                        print(f"   User's request likely cannot be fulfilled with available commands.")
                        break
                else:
                    print(f"\n⚠️ No steps planned but task not marked complete. Will retry.")
                    previous_issues = "No steps were generated. Check state and plan appropriate actions."
                    retry_count += 1
                    continue
            
            print(f"📝 Steps ({len(steps)}):")
            for i, step in enumerate(steps, 1):
                print(f"  {i}. {step.get('description', '???')}: {step.get('command', '???')}")
            
            # SANITY CHECK: Filter out unrelated actions before executing
            # Only check if we're on a retry (first attempt gets benefit of doubt)
            if retry_count >= 2:  # Start checking from 3rd attempt onward
                steps, rejected_steps = sanity_check_actions(user_input, steps, known_actions)
                
                if rejected_steps and len(steps) == 0:
                    # All steps were rejected as unrelated
                    print(f"\n⚠️ All planned actions were unrelated to goal. Need better strategy.")
                    previous_issues = f"Previous actions were completely unrelated to goal '{user_input}'. STOP trying random actions. Think carefully: what specific action in Reaper directly achieves '{user_input}'? If no such action exists in the available actions list, explain this to user instead of guessing."
                    previous_feedback = feedback
                    initial_state = final_state
                    retry_count += 1
                    continue
                elif rejected_steps:
                    # Some steps rejected - continue with filtered ones
                    print(f"📝 Continuing with {len(steps)} relevant steps (rejected {len(rejected_steps)} unrelated)")
        except json.JSONDecodeError as e:
            log_debug(f"JSON error: {e}")
            print(f"❌ AI returned invalid JSON: {plan_response[:200]}")
            return
        
        # PHASE 2: EXECUTE
        print(f"\n⚡ Executing...")
        commands = [step.get("command", "") for step in steps]

        # Handle GET_LYRICS and ANALYZE_TRACK commands separately (Python functions, not Reaper commands)
        lyrics_results = []
        analysis_results = []
        reaper_commands = []

        for cmd in commands:
            if cmd.startswith("GET_LYRICS"):
                # Extract track index
                parts = cmd.split()
                if len(parts) >= 2:
                    track_idx = int(parts[1])

                    # Get track name from state
                    track_name_match = re.search(rf'--- Track {track_idx}: (.+) ---', initial_state)
                    track_name = track_name_match.group(1) if track_name_match else f"Track_{track_idx}"

                    print(f"🎵 Extracting lyrics from track {track_idx} ({track_name})...")
                    lyrics_data = analyze_lyrics(track_idx, track_name)

                    if lyrics_data:
                        lyrics_results.append({
                            "track": track_idx,
                            "track_name": track_name,
                            "lyrics": lyrics_data
                        })
                        print(f"✅ Extracted {len(lyrics_data)} words from track {track_idx}")
                    else:
                        print(f"❌ Failed to extract lyrics from track {track_idx}")
                        
            elif cmd.startswith("ANALYZE_TRACK"):
                # Extract track index
                parts = cmd.split()
                if len(parts) >= 2:
                    track_idx = int(parts[1])

                    # Get track name from state
                    track_name_match = re.search(rf'--- Track {track_idx}: (.+) ---', initial_state)
                    track_name = track_name_match.group(1) if track_name_match else f"Track_{track_idx}"

                    # Start playback before export (prevents offline/empty exports)
                    print("▶️ Starting playback for export...")
                    send_reaper_commands(["1007"])  # Play command
                    time.sleep(0.5)  # Brief wait for playback to start
                    
                    # Export audio for analysis
                    Path(TEMP_AUDIO_DIR).mkdir(exist_ok=True)
                    temp_audio_folder = Path(TEMP_AUDIO_DIR) / f"analyze_track_{track_idx}_{int(time.time())}"
                    
                    print(f"📤 Exporting track {track_idx} audio for analysis...")
                    if send_reaper_commands([f"EXPORT_AUDIO {track_idx} {temp_audio_folder}"]):
                        time.sleep(2.0)  # Wait for export
                        
                        # Find exported WAV file
                        wav_files = list(temp_audio_folder.glob("*.wav")) if temp_audio_folder.exists() else []
                        if wav_files:
                            temp_audio = wav_files[0]
                            print(f"✅ Found exported audio: {temp_audio.name}")
                            
                            # Analyze the audio
                            analysis = analyze_audio_track(track_idx, track_name, str(temp_audio))
                            
                            if "error" not in analysis:
                                analysis_results.append(analysis)
                                
                                # Analysis already printed by analyze_audio_track function
                                # Just show completion message
                                print(f"✅ Analysis saved to current_track_analysis.json\n")
                            else:
                                print(f"❌ Analysis failed: {analysis['error']}")
                            
                            # Clean up
                            try:
                                shutil.rmtree(temp_audio_folder)
                            except:
                                pass
                        else:
                            print(f"❌ No WAV file found in export folder")
                    else:
                        print(f"❌ Failed to export audio for analysis")
            
            elif cmd.startswith("APPLY_FROM_JSON"):
                # APPLY_FROM_JSON track_idx [json_path]
                # Deterministically applies settings from analysis JSON
                parts = cmd.split(maxsplit=2)
                if len(parts) >= 2:
                    track_idx = int(parts[1])
                    json_path = parts[2] if len(parts) >= 3 else "current_track_analysis.json"
                    
                    print(f"📋 Applying settings from {json_path} to track {track_idx}...")
                    
                    # Load analysis JSON
                    analysis = load_analysis_json(json_path)
                    if not analysis:
                        print(f"❌ Could not load {json_path}")
                        continue
                    
                    # Convert analysis to differences format for apply_production_adjustments
                    # This function expects a "differences" dict
                    differences = {
                        'filtering': {
                            'needs_telephone': False,
                            'ref_high_pass': analysis.get('filtering', {}).get('high_pass_hz'),
                            'ref_low_pass': analysis.get('filtering', {}).get('low_pass_hz')
                        },
                        'delay': {
                            'needs_delay': analysis.get('delay', {}).get('detected', False),
                            'delay_time_ms': analysis.get('delay', {}).get('time_ms', 0),
                            'feedback': analysis.get('delay', {}).get('feedback_percent', 0),
                            'mix': analysis.get('delay', {}).get('mix_percent', 0)
                        },
                        'reverb': {
                            'needs_reverb': analysis.get('reverb', {}).get('detected', False),
                            'decay_time': analysis.get('reverb', {}).get('decay_time_s', 0),
                            'mix': analysis.get('reverb', {}).get('mix_percent', 0)
                        },
                        'compression': analysis.get('compression', {}).get('amount_percent', 0),
                        'brightness': analysis.get('brightness_percent', 50),
                        'autotune': analysis.get('pitch_correction', {}).get('amount_percent', 0),
                        'needs': []
                    }
                    
                    # Generate summary of what will be applied
                    if differences['filtering']['ref_high_pass']:
                        differences['needs'].append(f"HP filter at {differences['filtering']['ref_high_pass']:.0f}Hz")
                    if differences['filtering']['ref_low_pass']:
                        differences['needs'].append(f"LP filter at {differences['filtering']['ref_low_pass']:.0f}Hz")
                    if differences['delay']['needs_delay']:
                        differences['needs'].append(f"Delay {differences['delay']['delay_time_ms']:.0f}ms")
                    if differences['reverb']['needs_reverb']:
                        differences['needs'].append(f"Reverb {differences['reverb']['decay_time']:.1f}s")
                    
                    if differences['needs']:
                        print(f"   Will apply: {', '.join(differences['needs'])}")
                        
                        # Apply settings deterministically
                        commands, actions = apply_production_adjustments(track_idx, differences)
                        
                        if commands:
                            print(f"   Sending {len(commands)} commands...")
                            if send_reaper_commands(commands):
                                print(f"✅ Applied: {', '.join(actions)}")
                            else:
                                print(f"❌ Failed to apply commands")
                        else:
                            print(f"   No changes needed")
                    else:
                        print(f"   No effects to apply from JSON")
                        
            else:
                reaper_commands.append(cmd)

        # Send remaining commands to Reaper
        if reaper_commands:
            # Reset no-recommendations counter since we're actually doing something
            no_recommendations_count = 0
            
            # Save snapshot before making changes
            snapshot_label = f"before: {user_input[:50]}"
            save_state_snapshot(snapshot_label)
            
            if not send_reaper_commands(reaper_commands):
                print("❌ Failed to send commands to Reaper")
                return
            print("✅ Commands sent")
        elif not lyrics_results:
            print("⚠️ No commands to execute")
        
        # Check if we're adding FX (needs more time to load)
        has_add_fx = any("ADD_FX" in cmd for cmd in commands)
        wait_time = 1.2 if has_add_fx else 0.6
        time.sleep(wait_time)  # Wait for execution
        
        # Get feedback from Reaper
        feedback = get_reaper_feedback()
        if feedback != "No feedback available":
            print(f"📢 Reaper says: {feedback}")
        
        # Display lyrics if extracted (only show ONCE, not on every retry)
        if lyrics_results and not lyrics_already_displayed:
            for result in lyrics_results:
                print(f"\n📝 LYRICS - Track {result['track']} ({len(result['lyrics'])} words):")
                for i, word_data in enumerate(result['lyrics'][:20], 1):
                    print(f"   {i:3d}. [{word_data['start']:6.2f}s - {word_data['end']:6.2f}s] \"{word_data['word']}\"")
                if len(result['lyrics']) > 20:
                    print(f"   ... ({len(result['lyrics']) - 20} more words)\n")
            lyrics_already_displayed = True
        
        # Check if this was ONLY an analysis/lyrics request (no action requested)
        # If user said "analyze AND fix" or similar, we need to continue planning action steps
        if (lyrics_results or analysis_results) and not reaper_commands:
            # Check if user requested actions beyond just analysis/lyrics
            action_keywords = ['fix', 'make', 'add', 'change', 'adjust', 'set', 'boost', 'cut', 'reduce', 'increase', 'apply', 'create', 'remove', 'sound', 'like', 'mix']
            user_wants_action = any(keyword in user_input.lower() for keyword in action_keywords)
            
            if not user_wants_action:
                # Pure analysis/lyrics request - we're done
                if lyrics_results:
                    print(f"\n✅ SUCCESS: Extracted lyrics from {len(lyrics_results)} track(s)")
                    for result in lyrics_results:
                        print(f"\n📝 Track {result['track']} - {result['track_name']}:")
                        if result['lyrics']:
                            print(f"   Total words: {len(result['lyrics'])}")
                            print(f"   Duration: {result['lyrics'][-1]['end']:.1f}s")
                            print(f"\n   Word-by-word timestamps:")
                            for i, word_data in enumerate(result['lyrics'], 1):
                                print(f"   {i:3d}. [{word_data['start']:6.2f}s - {word_data['end']:6.2f}s] \"{word_data['word']}\"")
                        else:
                            print("   No lyrics found")
                if analysis_results:
                    print(f"\n✅ SUCCESS: Analyzed {len(analysis_results)} track(s)")
                break
            else:
                # User wants action after analysis - continue to next retry iteration to plan action steps
                print(f"📊 Analysis complete - continuing to plan action steps...")
                
                # Check if analysis found any recommendations
                if analysis_results:
                    recommendations = analysis_results[0].get('recommendations', [])
                    issues = analysis_results[0].get('issues_detected', [])
                    
                    # If no recommendations and no issues, increment counter
                    if not recommendations and not issues:
                        no_recommendations_count += 1
                        if no_recommendations_count >= 5:
                            # After 5 attempts with no recommendations, accept that track is fine
                            print(f"\n✅ SUCCESS: Track analysis shows no issues detected after {no_recommendations_count} checks")
                            print(f"   Track appears to be well-balanced and doesn't need mixing adjustments")
                            break
                        else:
                            print(f"   No issues detected (attempt {no_recommendations_count}/5) - will re-check...")
                    else:
                        # Reset counter if we found something
                        no_recommendations_count = 0
                    
                    previous_issues = "Analysis completed. Now IMPLEMENT the recommendations from librosa analysis (add plugins and set exact parameter values to fix the detected issues)."
                    previous_feedback = f"Analysis showed: {issues}. Recommendations: {recommendations}. Now implement these fixes with actual commands."
                else:
                    previous_feedback = "Lyrics extracted, now implement the other requested actions"
                
                initial_state = get_reaper_state()  # Refresh state
                retry_count += 1
                continue  # Go back to planning phase to plan the actual actions

        # Quick check: If Reaper feedback confirms success, trust it and stop
        if feedback and feedback != "No feedback available":
            feedback_lines = [line.strip() for line in feedback.splitlines() if line.strip()]
            success_lines = [line for line in feedback_lines if feedback_contains_success(line)]
            failure_lines = [line for line in feedback_lines if '❌' in line or 'Could not' in line or 'Unknown command' in line]
            unknown_lines = [line for line in feedback_lines if '❓' in line]

            automation_success = any('VOL_DIP' in line and '✓' in line for line in feedback_lines) or ('Automated' in feedback and 'mix:' in feedback)
            fx_added = any('Added FX' in line for line in feedback_lines)
            cleared_automation = any('Cleared' in line and 'automation' in line for line in feedback_lines)

            if success_lines and len(failure_lines) <= len(unknown_lines):
                print(f"\n✅ SUCCESS: Reaper feedback confirms {len(success_lines)} successful operations")
                for line in success_lines[:5]:
                    print(f"   • {line}")
                if len(success_lines) > 5:
                    print(f"   • ... ({len(success_lines) - 5} more)")
                if automation_success:
                    print(f"   🎛️ Volume automation created successfully")
                if fx_added:
                    print(f"   🔌 Plugin added successfully")
                if cleared_automation:
                    print(f"   🗑️ Cleared existing automation")
                if lyrics_results and lyrics_already_displayed:
                    print(f"   📝 Lyrics extracted ({len(lyrics_results[0]['lyrics'])} words)")
                break  # Don't even run verification - feedback is truth
        
        # PHASE 3: VERIFY (only if feedback wasn't conclusive)
        print(f"\n🔍 Verifying results (attempt {retry_count + 1}/{max_retries})...")
        print(f"💭 Goal: {technical_input}")
        final_state = get_reaper_state()
        
        # Quick check: Did state change at all?
        if initial_state == final_state:
            print("⚠️ State is IDENTICAL to before - commands had no effect")
            verification = {
                "success": False,
                "explanation": "Commands executed but state did not change at all",
                "issues": "The commands had no effect on the project. State is identical to before."
            }
        else:
            # Tell verification if lyrics were extracted at any point (so it doesn't claim failure when they were shown)
            lyrics_were_extracted = len(lyrics_results) > 0 or lyrics_already_displayed
            verify_response = verify_result(technical_input, initial_state, final_state, "\n".join(commands), feedback, lyrics_were_extracted)
            
            # Strip markdown code blocks if present (Claude sometimes wraps JSON in ```json ... ```)
            verify_response_clean = verify_response.strip()
            
            if verify_response_clean.startswith("```json"):
                verify_response_clean = verify_response_clean[7:]
            if verify_response_clean.startswith("```"):
                verify_response_clean = verify_response_clean[3:]
            if verify_response_clean.endswith("```"):
                verify_response_clean = verify_response_clean[:-3]
            verify_response_clean = verify_response_clean.strip()
            
            # Check if this was an FX parameter command
            has_fx_param = any("SET_FX_PARAM" in cmd for cmd in commands)
            
            try:
                verification = json.loads(verify_response_clean)
            except json.JSONDecodeError as e:
                print(f"⚠️ Verification response malformed: {str(e)}")
                verification = {
                    "success": False,
                    "explanation": "Verification failed (JSON parse error)",
                    "issues": f"Could not parse verification response: {verify_response_clean[:200]}"
                }
        
        # Extract results
        success = verification.get("success", False)
        explanation = verification.get("explanation", "")
        issues = verification.get("issues", "")
        
        # Log what verification actually said
        log_debug(f"Verification result: success={success}, explanation={explanation}, issues={issues}")
        
        if success:
            # CONFIDENCE CHECK: Before declaring success, do a final analysis to verify
            print(f"\n🤔 Claiming success - doing confidence check...")
            
            # For audio effects (underwater, etc.), analyze the audio to verify it actually sounds right
            if any(keyword in user_input.lower() for keyword in ['underwater', 'sound', 'effect', 'filter', 'eq', 'frequency']):
                # Extract track number from user input or commands
                track_match = re.search(r'track\s+(\d+)', user_input.lower())
                if track_match:
                    track_idx = int(track_match.group(1))
                    
                    # Get track name from state
                    track_name_match = re.search(rf'--- Track {track_idx}: (.+) ---', final_state)
                    track_name = track_name_match.group(1) if track_name_match else f"Track_{track_idx}"
                    
                    print(f"🔬 Analyzing track {track_idx} to verify the effect worked...")
                    
                    # Start playback and export for analysis
                    send_reaper_commands(["1007"])  # Play
                    time.sleep(0.5)
                    
                    Path(TEMP_AUDIO_DIR).mkdir(exist_ok=True)
                    verify_audio_folder = Path(TEMP_AUDIO_DIR) / f"verify_track_{track_idx}_{int(time.time())}"
                    
                    if send_reaper_commands([f"EXPORT_AUDIO {track_idx} {verify_audio_folder}"]):
                        time.sleep(2.0)
                        wav_files = list(verify_audio_folder.glob("*.wav")) if verify_audio_folder.exists() else []
                        if wav_files:
                            verify_audio = wav_files[0]
                            verify_analysis = analyze_audio_track(track_idx, track_name, str(verify_audio))
                            
                            if "error" not in verify_analysis:
                                print(f"\n📊 Confidence Check Analysis:")
                                print(f"   Brightness: {verify_analysis['tonal_characteristics']['assessment']}")
                                print(f"   Highs (5-20kHz): {verify_analysis['frequency_balance']['highs_5_20khz']:.1f}dB")
                                
                                # Show detected effects
                                if 'effects_detected' in verify_analysis:
                                    print(f"   Filtering: {verify_analysis['effects_detected']['filtering']['assessment']}")
                                    print(f"   Distortion: {verify_analysis['effects_detected']['distortion']['assessment']}")
                                    print(f"   Reverb: {verify_analysis['effects_detected']['reverb']['assessment']}")
                                
                                print(f"   Issues: {', '.join(verify_analysis['issues_detected']) if verify_analysis['issues_detected'] else 'None'}")
                                
                                # Verify specific effects based on request
                                
                                # For underwater effect, check if low-pass filter is detected
                                if 'underwater' in user_input.lower():
                                    rolloff_freq = verify_analysis['effects_detected']['filtering']['rolloff_frequency_hz']
                                    
                                    # Underwater should have rolloff around 800-1500Hz
                                    if rolloff_freq > 2000:
                                        print(f"\n❌ CONFIDENCE CHECK FAILED: Rolloff at {rolloff_freq:.0f}Hz, should be <1500Hz for underwater")
                                        print(f"🔄 Low-pass filter didn't work - continuing retries...")
                                        
                                        previous_issues = f"Analysis shows rolloff at {rolloff_freq:.0f}Hz. Need LOW-PASS filter at ~1000Hz for underwater. Filter detection: {verify_analysis['effects_detected']['filtering']['assessment']}"
                                        previous_feedback = feedback
                                        initial_state = final_state
                                        retry_count += 1
                                        
                                        # Clean up
                                        try:
                                            shutil.rmtree(verify_audio_folder)
                                        except:
                                            pass
                                        continue  # Keep retrying
                                    
                                # For distortion/saturation requests, verify it was added
                                if any(word in user_input.lower() for word in ['distortion', 'saturation', 'warm', 'grit']):
                                    distortion_detected = verify_analysis['effects_detected']['distortion']['assessment']
                                    if 'Clean' in distortion_detected and ('distortion' in user_input.lower() or 'saturation' in user_input.lower()):
                                        print(f"\n❌ CONFIDENCE CHECK FAILED: Audio still clean, no distortion detected")
                                        print(f"🔄 Distortion wasn't added - continuing retries...")
                                        
                                        previous_issues = f"Analysis shows: {distortion_detected}. User requested distortion but audio is still clean."
                                        previous_feedback = feedback
                                        initial_state = final_state
                                        retry_count += 1
                                        
                                        # Clean up
                                        try:
                                            shutil.rmtree(verify_audio_folder)
                                        except:
                                            pass
                                        continue
                                    
                                # For reverb requests, verify reverb was added
                                if 'reverb' in user_input.lower():
                                    reverb_detected = verify_analysis['effects_detected']['reverb']['assessment']
                                    if 'Dry' in reverb_detected:
                                        print(f"\n❌ CONFIDENCE CHECK FAILED: Audio still dry, no reverb detected")
                                        print(f"🔄 Reverb wasn't added or automation didn't work - continuing retries...")
                                        
                                        previous_issues = f"Analysis shows: {reverb_detected}. User requested reverb but audio is still dry."
                                        previous_feedback = feedback
                                        initial_state = final_state
                                        retry_count += 1
                                        
                                        # Clean up
                                        try:
                                            shutil.rmtree(verify_audio_folder)
                                        except:
                                            pass
                                        continue
                            
                            # Clean up
                            try:
                                shutil.rmtree(verify_audio_folder)
                            except:
                                pass
            
            # If we get here, confidence check passed or wasn't needed
            print(f"\n✅ SUCCESS CONFIRMED: {explanation}")
            if issues:
                print(f"📌 Notes: {issues}")
            break  # Done!
        else:
            print(f"\n❌ FAILED (attempt {retry_count + 1}/{max_retries}): {explanation}")
            if issues:
                print(f"📌 What's wrong: {issues}")
                print(f"🔄 Will retry with this information...")
            
            # Track failed action IDs and custom commands so we don't retry them
            for cmd in commands:
                if cmd.strip().isdigit():
                    failed_actions.add(cmd.strip())
                    log_debug(f"Added action {cmd.strip()} to blocklist")
                else:
                    cmd_text = cmd.strip()
                    if cmd_text:
                        failed_commands.add(cmd_text)
                        log_debug(f"Added command '{cmd_text}' to blocklist")
            
            # Prepare for retry - preserve ALL context
            # Track what we tried and what happened (include commands and outcome)
            commands_summary = ", ".join([cmd[:50] for cmd in commands[:3]])  # First 3 commands, truncated
            if len(commands) > 3:
                commands_summary += f" ... (+{len(commands)-3} more)"
            
            # Build comprehensive retry entry with reasoning, commands, and result
            retry_entry = f"""
Attempt {retry_count + 1}:
  Reasoning: {reasoning[:200]}...
  Commands: {commands_summary}
  Result: {explanation}
  Issues: {issues}"""
            retry_history.append(retry_entry)
            previous_issues = f"{issues}\n\nPrevious reasoning: {reasoning[:300]}\nWhy it failed: {explanation}"
            previous_feedback = feedback
            initial_state = final_state
            retry_count += 1
            print(f"🔄 Retrying with feedback and updated state...")
    
    if retry_count == max_retries:
        print(f"\n⚠️ Reached {max_retries} attempts - stopping here")
    
    history_entry = f"User: '{user_input}' → {reasoning}"
    conversation_history.append(history_entry)
    save_memory()
    
    save_structured_memory_entry(
        goal=user_input,
        success=(retry_count < max_retries),
        actions_tried=retry_history,
        final_outcome=reasoning if retry_count < max_retries else "Max retries reached",
        failed_action_ids=list(failed_actions)
    )
    
    print("\n✨ Done!\n")

if __name__ == "__main__":
    print("=" * 70)
    print("🎵 AI AGENT FOR REAPER DAW - Claude Sonnet 4.5 🎵")
    print("=" * 70)
    print("\n✨ Features:")
    print("  • 6,309 action database with smart filtering")
    print("  • Plan → Execute → Verify loop")
    print("  • Auto-retry on failures (learns from mistakes)")
    print("  • Full state tracking and feedback")
    print("  • State snapshots & revert (type 'undo' or 'history')")
    print("  • Reference-based mixing (put files in references/ folder)")
    print("=" * 70)
    print("\n⚠️  Make sure:")
    print("  1. Reaper is running")
    print("  2. reaper_agent.lua is loaded")
    print("=" * 70)
    
    # Create necessary directories
    Path(REFERENCE_AUDIO_DIR).mkdir(exist_ok=True)
    Path(LYRICS_CACHE_DIR).mkdir(exist_ok=True)
    Path(TEMP_AUDIO_DIR).mkdir(exist_ok=True)
    
    load_memory()
    load_sound_knowledge()
    load_user_preferences()
    load_state_history()
    load_structured_memory()
    
    print("\n✅ Ready!\n")
    
    while True:
        user_input = input("💬 You (end with /e to enhance): ")
        
        # Check if user wants to enhance their prompt
        if user_input.endswith('/e') or user_input.endswith(' /e'):
            # Remove the /e flag
            vague_input = user_input.replace('/e', '').strip()
            print("✨ Enhancing your prompt...")
            
            # Import enhancer
            from prompt_enhancer import enhance_prompt
            
            # Get current state for context
            send_reaper_commands(["GET_STATE"])
            time.sleep(0.3)
            current_state = ""
            try:
                with open(STATE_FILE, 'r') as f:
                    current_state = f.read()
            except:
                pass
            
            enhanced = enhance_prompt(vague_input, current_state)
            print(f"\n📝 Your vague prompt: {vague_input}")
            print(f"✨ Enhanced version: {enhanced}")
            
            confirm = input("\n[Enter]=send  [e]=edit  [c]=cancel: ")
            if confirm.lower() == 'c':
                print("❌ Cancelled\n")
                continue
            elif confirm.lower() == 'e':
                # Copy enhanced text to clipboard
                if CLIPBOARD_AVAILABLE:
                    pyperclip.copy(enhanced)
                    print(f"\n✏️ Enhanced text copied to clipboard!")
                    print(f"📋 Press Ctrl+V to paste and edit:")
                else:
                    print(f"\n✏️ Enhanced text:")
                    print(f"   {enhanced}")
                    print(f"\n📋 Copy-paste and edit:")
                edited = input("→ ")
                user_input = edited if edited.strip() else enhanced
            else:
                user_input = enhanced
                print(f"✅ Sending: {user_input}\n")
        
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n👋 Goodbye!")
            break
        if user_input.strip():
            # Handle snapshot commands
            if user_input.lower() in ["revert", "revert last", "undo", "undo last"]:
                success, message = revert_to_snapshot(-1)
                print(f"\n{'✅' if success else '❌'} {message}")
                if success:
                    time.sleep(0.8)
                    updated_state = get_reaper_state()
                    print(f"\n📊 Current state after revert:\n{updated_state[:500]}...")
                continue
            elif user_input.lower().startswith("revert to "):
                try:
                    index = int(user_input.split()[-1])
                    success, message = revert_to_snapshot(index)
                    print(f"\n{'✅' if success else '❌'} {message}")
                    if success:
                        time.sleep(0.8)
                        updated_state = get_reaper_state()
                        print(f"\n📊 Current state after revert:\n{updated_state[:500]}...")
                except ValueError:
                    print("❌ Invalid snapshot number. Use: revert to <number>")
                continue
            elif user_input.lower() in ["list snapshots", "show snapshots", "snapshots", "history"]:
                print(f"\n{list_snapshots()}")
                continue
            
            execute_user_command(user_input)

