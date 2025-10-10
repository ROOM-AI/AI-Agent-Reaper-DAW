import json
import time
import os
import re
import shutil
import numpy as np
from pathlib import Path
from contextlib import contextmanager
from anthropic import Anthropic
from openai import OpenAI

# Audio analysis imports (install with: pip install librosa soundfile)
try:
    import librosa
    import soundfile as sf
    AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    AUDIO_ANALYSIS_AVAILABLE = False
    print("⚠️ Audio analysis disabled - install: pip install librosa soundfile")

# Initialize Anthropic Claude
client = Anthropic(api_key="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")

# Initialize OpenAI for Whisper
openai_client = OpenAI(api_key="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")

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
LYRICS_CACHE_DIR = r"C:\Users\moosb\AIAGENT DAW\lyrics_cache"
TEMP_AUDIO_DIR = r"C:\Users\moosb\AIAGENT DAW\temp_audio"

conversation_history = []
sound_knowledge = None
lyrics_cache = {}

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

def send_reaper_commands(commands):
    """Send commands to Reaper"""
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
    """Get current Reaper state"""
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

def load_action_list():
    """Load complete action database (6,309 actions!)"""
    known_actions = {}
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
        log_debug(f"Loaded {len(known_actions)} actions")
    except Exception as e:
        log_debug(f"Action load error: {e}")
    
    return known_actions

def load_plugin_list():
    """Load available plugins from Reaper"""
    plugins = []
    try:
        with open(r"C:\Users\moosb\AIAGENT DAW\reaper_plugins_list.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("===") or line in ["Video processor", "Container"]:
                    continue
                if line.startswith("ReWire:"):
                    continue  # Skip ReWire entries
                plugins.append(line)
        log_debug(f"Loaded {len(plugins)} plugins")
    except Exception as e:
        log_debug(f"Plugin load error: {e}")
    
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

    try:
        with open_file_when_ready(temp_audio, 'rb', timeout=wait_timeout, poll_interval=poll_interval) as (audio_file, waited):
            wait_msg = f" ({waited:.1f}s wait)" if waited >= poll_interval else ""
            print(f"✅ Audio file ready{wait_msg}")
            print(f"🔍 Analyzing vocals with Whisper API...")
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )
        
        # Extract word-level timestamps
        lyrics_data = []
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
    """Analyze audio file and return detailed characteristics"""
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
        
        # Identify problematic frequencies
        issues = []
        if band_energies["low_mids_250_500hz"] > band_energies["mids_500_2khz"] + 6:
            issues.append("Muddy (excess 250-500Hz)")
        if band_energies["high_mids_2_5khz"] > band_energies["mids_500_2khz"] + 8:
            issues.append("Harsh (peaks 2-5kHz)")
        if band_energies["bass_60_250hz"] < band_energies["mids_500_2khz"] - 15:
            issues.append("Thin (lacking bass)")
        if band_energies["highs_5_20khz"] < band_energies["mids_500_2khz"] - 20:
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
        
        analysis_result = {
            "track_name": track_name,
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
            
            "issues_detected": issues,
            
            "recommendations": []
        }
        
        # Generate recommendations
        if "Muddy" in ' '.join(issues):
            analysis_result["recommendations"].append("Cut 250-400Hz by 2-4dB")
        if "Harsh" in ' '.join(issues):
            analysis_result["recommendations"].append("Reduce 2-5kHz harshness by 2-3dB")
        if "Thin" in ' '.join(issues):
            analysis_result["recommendations"].append("Boost bass around 100-200Hz")
        if dynamic_range < 6:
            analysis_result["recommendations"].append("Reduce compression - dynamics too squashed")
        if stereo_width < 30 and is_stereo:
            analysis_result["recommendations"].append("Consider stereo widening")
        
        return analysis_result
        
    except Exception as e:
        log_debug(f"Audio analysis error: {e}")
        return {"error": str(e)}

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

def plan_actions(user_input, state, known_actions, available_plugins, previous_issues="", feedback="", lyric_context=""):
    """Phase 1: AI Plans what to do"""
    
    # Use smart index search instead of old filter (MUCH faster!)
    relevant_actions = smart_index_search(user_input, max_results=100)
    
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
    
    issues_section = f"\n**PREVIOUS ATTEMPT - WHAT FAILED:**\n{previous_issues}\n" if previous_issues else ""
    feedback_section = f"\n**FEEDBACK FROM LAST COMMANDS:**\n{feedback}\n\n**IMPORTANT**: Look at the feedback above to see what ACTUALLY executed. Only retry the commands that failed or are missing. Don't repeat successful commands!\n" if feedback else ""
    lyric_section = lyric_context if lyric_context else ""
    
    system_prompt = f"""You are an AI controlling Reaper DAW. THINK STEP-BY-STEP and pick EXACT matches.

**CURRENT PROJECT STATE:**
{state}

**AVAILABLE ACTIONS (pre-filtered for you):**
{actions_text}

**AVAILABLE PLUGINS (use EXACT names from this list):**
{plugins_text}

**CUSTOM COMMANDS (use these for plugins and automation):**
- SELECT_TRACK <trackIdx> - Select track (REQUIRED before track actions!)
- VOL_DIP <trackIdx> <tStart> <tEnd> <value0-1> - Volume automation
- SET_TRACK_VOL <trackIdx> <volumeDB> - Set track volume
- GET_LYRICS <trackIdx> - Use OpenAI Whisper API to transcribe audio track and extract word-level timestamps
  * Exports track audio, sends to Whisper API for voice-to-text transcription
  * Returns timestamped lyrics (not copyrighted search results - actual audio transcription)
  * Results are cached for reuse
  * Example: GET_LYRICS 0 → transcribes track 0's audio into timestamped words
- ANALYZE_TRACK <trackIdx> - Analyze audio characteristics of a track
  * Exports and analyzes: frequency balance, loudness, dynamic range, stereo width
  * Detects issues: muddy frequencies, harshness, compression, brightness
  * Returns detailed analysis with recommendations
  * Example: ANALYZE_TRACK 0 → analyzes track 0's audio quality
- ADD_FX <trackIdx> <pluginName> - Add FX plugin by searching the AVAILABLE PLUGINS list above
  * CRITICAL: Search the AVAILABLE PLUGINS list and use the EXACT name from that list
  * Example: User says "open ssl channel" → Search list → Find "VST: SSLChannel Stereo (x86) (Waves)" → Use that exact name
  * Example: User says "add reverb" → Search list → Find "VST3: ValhallaRoom (Valhalla DSP, LLC)" or similar → Use exact name
  * If plugin already exists on track, it will just open it (no duplicate)
- REMOVE_FX <trackIdx> <fxIdx> - Remove FX plugin from track
  * Example: REMOVE_FX 0 1 (removes second plugin from track 0)
  * fxIdx: 0=first plugin, 1=second, 2=third, etc.
- SET_FX_PARAM <trackIdx> <fxIdx> <paramIdx> <value0-1> - Set FX parameter (STATIC VALUE, NO AUTOMATION)
  * Example: SET_FX_PARAM 2 0 5 0.8 (track 2, first FX, param 5, 80%)
  * This sets a static value - use FX_PARAM_AUTO for automation over time
- FX_PARAM_AUTO <trackIdx> <fxIdx> <paramIdx> <tStart> <tEnd> <startValue> <endValue> - Automate FX parameter over time
  * CRITICAL: Use this for FX parameter automation, NOT SET_FX_PARAM
  * **MUST READ CURRENT STATE FIRST** to find correct fxIdx and paramIdx:
    1. Find the FX by name in the state (e.g., "MannyM Reverb" at index [1])
    2. Find the parameter by name (e.g., "p11 Dry/Wet" = index 11)
    3. DO NOT GUESS parameter indices - they vary by plugin!
  * Example: State shows "[1] MannyM Reverb" with "p11 Dry/Wet" → use fxIdx=1, paramIdx=11
  
  **INSTANT CHANGES (most common):**
  When user says "turn on X at/after [word/time]" or "X from 0% before [word] to 100% at [time]", they want INSTANT jump:
  - **CRITICAL:** Need TWO commands to define the full automation curve:
    1. First command: Set the "before" state from START of track (0.0s) to switch point
    2. Second command: Create the instant jump at the switch point
  - Example: "reverb from 0% before to 100% at 3.7s"
    Step 1: FX_PARAM_AUTO 0 1 11 0.0 3.69 0.0 0.0 (keep at 0% from start until just before switch)
    Step 2: FX_PARAM_AUTO 0 1 11 3.7 3.7 1.0 1.0 (instant jump to 100% at 3.7s, stays 100% after)
  - This creates: 0% from 0.00s → 3.69s, instant jump to 100% AT 3.7s, stays 100% until end of track
  
  **GRADUAL RAMPS (less common):**
  When user explicitly says "fade/ramp/gradually increase from X to Y", use different times:
  - Example: "fade reverb from 3.0s to 5.0s" → FX_PARAM_AUTO 0 1 11 3.0 5.0 0.0 1.0
  
  **After executing, STATE will show "=== AUTOMATED PARAMETERS ===" section with automation points - check this to verify success**
- GOTO <seconds> - Jump to position

**CRITICAL: PARAMETER VALUE CONVERSION (DYNAMIC REASONING):**
Reaper uses normalized 0-1 values, but each plugin displays different ranges. DO NOT use hardcoded formulas!

**HOW TO CONVERT PARAMETERS (think for yourself per plugin):**
1. Look at the CURRENT STATE to find the parameter
2. Read the current normalized value and display value
3. Infer the range from the display pattern
4. Calculate the target normalized value with PROPER PRECISION

**Example reasoning:**
- State shows: `p5 Pitch: 50.0% [+0 semitones]`
- User wants: "pitch to -4 semitones"
- Your reasoning: "50% = 0 semitones, so range is -12 to +12 semitones (typical for pitch). Using formula: (target - min) / (max - min) = (-4 - (-12)) / (12 - (-12)) = 8 / 24 = 0.333"
- Result: SET_FX_PARAM trackIdx fxIdx 5 0.333

**Example 2:**
- State shows: `p8 Dry/Wet: 100% [100.0]`
- User wants: "set dry/wet to 30%"
- Your reasoning: "This is already in percentage format. 100% normalized = 1.0, so 30% = 0.3"
- Result: SET_FX_PARAM trackIdx fxIdx 8 0.3

**Example 3:**
- State shows: `p3 Gain: 50.0% [-0.0 dB]`
- User wants: "boost by 3dB"
- Your reasoning: "50% = 0dB. Typical EQ gain range is -30dB to +30dB. 3dB = (3 - (-30)) / (30 - (-30)) = 33 / 60 = 0.55"
- Result: SET_FX_PARAM trackIdx fxIdx 3 0.55

**PRECISION & COMMON SENSE:**
- **Pitch/Semitones**: When user says "pitch to -4", they mean EXACTLY -4.0 semitones, not -4.3. Calculate precisely so the plugin shows the exact value requested. Pitch is discrete and musical, so whole numbers matter.
- **EQ Gain (dB)**: Small variations are acceptable. 3.1dB vs 3.0dB is fine. Don't overthink it.
- **Mix/Dry-Wet (%)**: Match what the user asked for. "30%" means 30%, not 29.7% or 30.5%.
- **Time/Delay**: For time-based parameters (delay time, attack, release), use STATE DATA to calculate range accurately.

**Audio Frequency Ranges (for reference):**
- Sub Bass: 20-60Hz | Bass: 60-250Hz | Low Mids: 250-500Hz
- Mids: 500Hz-2kHz | High Mids: 2-5kHz | Highs: 5-20kHz

**IMPORTANT: For adding/removing plugins, ALWAYS use ADD_FX/REMOVE_FX commands, NOT action IDs!**

**CRITICAL: MULTIPLE FX AUTOMATIONS:**
When user wants automation on multiple FX parameters, use FX_PARAM_AUTO for each one:
- CORRECT: FX_PARAM_AUTO 0 0 11 3.7 3.7 0.3 0.3, then FX_PARAM_AUTO 0 1 5 5.0 5.0 0.5 0.5
- Each command directly targets specific track/FX/param - no "last touched" confusion
- You can automate multiple parameters on different FX in any order
{issues_section}{feedback_section}{lyric_section}
**USER REQUEST:** "{user_input}"

**AUDIO ANALYSIS REQUESTS:**
When user asks questions about audio quality/characteristics, use ANALYZE_TRACK:
- "Does this sound muddy?" → ANALYZE_TRACK to check frequency balance
- "Is the vocal too loud/quiet?" → ANALYZE_TRACK to check loudness levels
- "Is this compressed?" → ANALYZE_TRACK to check dynamic range
- "Does this sound bright/dark?" → ANALYZE_TRACK to check tonal characteristics
Analysis returns: frequency balance (6 bands), loudness (RMS, peak, dynamic range), stereo width, detected issues, recommendations
After analysis, interpret results and answer user's question in natural language

**CRITICAL INSTRUCTIONS:**
1. **MULTIPLE PLUGINS/COMMANDS**: When user says "open X and Y" or "add A, B, and C", create SEPARATE steps for each plugin/action.
   - User: "open pro q and timeless 3" → Step 1: ADD_FX Pro-Q 3, Step 2: ADD_FX Timeless 3
   - User: "add reverb and delay" → Step 1: ADD_FX reverb, Step 2: ADD_FX delay
   - ALWAYS handle each plugin/action as its own command in the steps array

2. **ADD PLUGIN + ADJUST PARAMETERS IN SAME REQUEST**: When user wants to add a plugin AND adjust it (e.g., "add saturn with 30% drive"), you have TWO options:
   
   **OPTION A - If plugin is NOT in current state (need to add it):**
   - Step 1: ADD_FX (adds the plugin)
   - Step 2: Wait for retry - on retry, NEW STATE will show all plugin parameters with names and indices
   - Step 3 (in retry): Search the parameter names to find "Drive" or whatever, then SET_FX_PARAM with correct index
   
   **OPTION B - If you're confident about parameter layout:**
   - Step 1: ADD_FX
   - Step 2-N: SET_FX_PARAM (but accept it might fail - retry will fix it)
   
   **CRITICAL:** For multi-band plugins like Saturn (Band 1 Drive, Band 2 Drive), don't guess - wait for state on retry to find exact param names/indices

3. **RETRY LOGIC** (if on a retry after previous failure):
   **STEP 1: ANALYZE FEEDBACK** - Parse line by line:
   - Lines with "✅" or "🎛️ Added FX" = SUCCEEDED (skip these)
   - Lines with "❌" = FAILED (need to retry)
   - Missing commands = NEED TO ADD
   
   **STEP 2: CROSS-REFERENCE WITH NEW STATE**:
   - The CURRENT STATE now shows the added plugin with ALL parameters listed
   - Example: You tried param index 2 for gain but failed
   - Look in state for "Band 1 Gain" → See it's at param index 3 → Use 3, not 2
   
   **STEP 3: OUTPUT ONLY RETRY COMMANDS**:
   - Don't repeat successful commands
   - Only add commands for what FAILED or is MISSING
   
   **EXAMPLE RETRY:**
   Feedback showed:
   ```
   ✅ Added Pro-Q 3 to track 0
   ✅ Set param 0: Band 1 Used
   ❌ Could not find parameter at index 2
   ```
   
   Analysis: Plugin added ✅, Band enabled ✅, Gain failed (wrong index)
   New State shows: `p3 Band 1 Gain: 0% [0.0 dB]`
   Retry command: Only SET_FX_PARAM 0 3 3 0.6 (gain to +6dB using correct index 3)

4. If user mentions a SPECIFIC TRACK NUMBER (e.g., "track 7"):
   - Look for EXACT MATCH in action descriptions
   - "Toggle solo for track 07" or "Toggle solo for track 7" = EXACT MATCH
   - "Toggle solo for selected tracks" = GENERIC (only use if no exact match!)
   
5. CHAIN OF THOUGHT in your reasoning:
   - User asked for: [extract exact track number]
   - Available actions: [list the top 3 matches]
   - EXACT match is: [action ID] because [why]
   
6. Read state BEFORE acting:
   - Is the track already in desired state? If yes, do nothing!
   
7. For track-specific actions (NOT generic "selected tracks"):
   - Do NOT use SELECT_TRACK first
   - Use the direct track action ID

**CRITICAL: CHECK IF ALREADY COMPLETE FIRST**
BEFORE planning ANY actions, check if CURRENT STATE already has what user wants.

Example 1: User wants "Pro-Q 3 open with +3dB mid boost"
- State shows: Pro-Q 3 at index [3], Band 1 at 1039Hz with +3.00 dB gain
- Result: ALREADY COMPLETE! Set "already_complete": true, "steps": []
- DO NOT add "just to be sure" commands or "open plugin" steps

Example 2: User wants "boost mids +3db" (plugin not specified)
- State shows: Pro-Q 3 with mid band at +3dB
- Result: ALREADY COMPLETE! They didn't say which plugin, but mids are boosted
- Set "already_complete": true

Rule: If your reasoning says "already at +3dB" or "already configured" → USE THE FLAG, NO STEPS

**OUTPUT ONLY THIS JSON:**
{{
  "reasoning": "CHAIN OF THOUGHT: [your analysis]",
  "already_complete": true/false,
  "steps": [
    {{"command": "23", "description": "Toggle solo for track 07"}},
    {{"command": "ADD_FX 2 ReaVerb", "description": "Add ReaVerb plugin"}}
  ]
}}

If already_complete=true, reasoning must explain WHY (what state shows) and steps must be empty [].

CRITICAL: Return ONLY valid JSON. No text before or after."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
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
            max_tokens=1500,
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

def verify_result(user_input, initial_state, final_state, executed_commands, feedback):
    """Phase 3: Check if goal was achieved"""
    
    system_prompt = f"""You executed commands in Reaper. Verify if the user's goal was achieved.

**USER WANTED:** {user_input}

**STATE BEFORE:**
{initial_state[:1500]}

**COMMANDS EXECUTED:**
{executed_commands}

**REAPER FEEDBACK:**
{feedback}

**STATE AFTER:**
{final_state[:1500]}

**YOUR TASK:**
Compare before/after states and feedback. Check if goal was achieved. Be BRIEF.

**NO CHANGE RULE:** If states are identical but BEFORE state already matches the user's goal (e.g., "Pro-Q 3 open with +3dB" and state shows this), it's SUCCESS. Explanation: "No action needed - already in desired state."

**AUTOMATION VERIFICATION:** For FX_PARAM_AUTO commands, check if AFTER state shows "=== AUTOMATED PARAMETERS ===" section under the FX. If automation points appear there, it's SUCCESS even if the parameter's current value didn't change.

**OUTPUT ONLY THIS JSON (keep explanation SHORT - max 2 sentences):**
{{{{
  "success": true/false,
  "explanation": "Brief summary (max 2 sentences)",
  "issues": "What failed (brief)"
}}}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": system_prompt}]
        ).content[0].text.strip()
        
        log_debug(f"Verify: {response}")
        return response
    except Exception as e:
        log_debug(f"Verify error: {e}")
        return '{"success": false, "explanation": "Verification failed", "issues": "API error"}'

def execute_user_command(user_input):
    """Main agentic loop: Plan → Execute → Verify → Retry if needed"""
    
    print(f"\n🎤 User: {user_input}")
    
    # Check if user is requesting word-based automation
    word_pattern = r'(?:after|before|at|during)\s+(?:the\s+word\s+)?([A-Z]+)'
    word_match = re.search(word_pattern, user_input, re.IGNORECASE)
    
    lyric_context = ""
    if word_match:
        target_word = word_match.group(1).upper()
        print(f"🎵 Word-based automation detected: '{target_word}'")
        
        # Determine which track (default to track 0 for now)
        track_idx = 0
        
        # Get track name from state
        state = get_reaper_state()
        track_name_match = re.search(r'--- Track 0: (.+) ---', state)
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
    
    # Retry loop (up to 6 attempts for complex multi-step commands)
    max_retries = 6
    retry_count = 0
    previous_issues = ""
    previous_feedback = ""
    
    while retry_count < max_retries:
        attempt_label = "" if retry_count == 0 else f" (retry {retry_count}/{max_retries})"
        print(f"\n🧠 Planning actions{attempt_label}...")
        
        # PHASE 1: PLAN
        plan_response = plan_actions(technical_input, initial_state, known_actions, available_plugins, previous_issues, previous_feedback, lyric_context)
        
        try:
            plan = json.loads(plan_response)
            reasoning = plan.get("reasoning", "")
            already_complete = plan.get("already_complete", False)
            steps = plan.get("steps", [])
            
            print(f"\n💭 Reasoning: {reasoning}")
            
            # Check if task is already complete
            if already_complete:
                print(f"\n✅ ALREADY COMPLETE: Task already fulfilled in current state")
                break  # Exit loop immediately - no execution needed
            
            # Also check if steps is empty but reasoning suggests completion
            if len(steps) == 0:
                if "already" in reasoning.lower() or "fulfilled" in reasoning.lower():
                    print(f"\n✅ ALREADY COMPLETE: No steps needed (task already done)")
                    break
                else:
                    print(f"\n⚠️ No steps planned but task not marked complete. Will retry.")
                    previous_issues = "No steps were generated. Check state and plan appropriate actions."
                    retry_count += 1
                    continue
            
            print(f"📝 Steps ({len(steps)}):")
            for i, step in enumerate(steps, 1):
                print(f"  {i}. {step.get('description', '???')}: {step.get('command', '???')}")
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
                                
                                # Display summary
                                print(f"\n🔬 Analysis Results for {track_name}:")
                                print(f"   Loudness: {analysis['loudness']['average_rms_db']}dB RMS, Peak: {analysis['loudness']['peak_db']}dB")
                                print(f"   Dynamic Range: {analysis['loudness']['dynamic_range_db']}dB ({analysis['loudness']['assessment']})")
                                print(f"   Stereo Width: {analysis['stereo_image']['width_percentage']}% ({analysis['stereo_image']['assessment']})")
                                print(f"   Brightness: {analysis['tonal_characteristics']['assessment']}")
                                if analysis['issues_detected']:
                                    print(f"   Issues: {', '.join(analysis['issues_detected'])}")
                                if analysis['recommendations']:
                                    print(f"   Recommendations: {', '.join(analysis['recommendations'])}")
                                print()
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
                        
            else:
                reaper_commands.append(cmd)

        # Send remaining commands to Reaper
        if reaper_commands:
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
        
        # If we only extracted lyrics or analysis (no Reaper commands), we're done
        if (lyrics_results or analysis_results) and not reaper_commands:
            if lyrics_results:
                print(f"\n✅ SUCCESS: Extracted lyrics from {len(lyrics_results)} track(s)")
                for result in lyrics_results:
                    print(f"\n📝 Track {result['track']} - {result['track_name']}:")
                    print(f"   Total words: {len(result['lyrics'])}")
                    print(f"   Duration: {result['lyrics'][-1]['end']:.1f}s" if result['lyrics'] else "   No lyrics found")
            if analysis_results:
                print(f"\n✅ SUCCESS: Analyzed {len(analysis_results)} track(s)")
            break

        # Quick check: If all commands have feedback confirmation, assume success
        num_commands = len(reaper_commands)
        if feedback and feedback != "No feedback available" and num_commands > 0:
            success_indicators = feedback.count('✅') + feedback.count('🎛️') + feedback.count('🎚️') + feedback.count('🗑️')
            failure_indicators = feedback.count('❌')

            if success_indicators >= num_commands and failure_indicators == 0:
                print(f"\n✅ SUCCESS: All {num_commands} commands confirmed by Reaper feedback")
                if lyrics_results:
                    print(f"\n📝 Also extracted lyrics from {len(lyrics_results)} track(s)")
                break  # Don't even run verification - feedback is truth
        
        # PHASE 3: VERIFY (only if feedback wasn't conclusive)
        print("\n🔍 Verifying results...")
        final_state = get_reaper_state()
        verify_response = verify_result(technical_input, initial_state, final_state, "\n".join(commands), feedback)
        
        # Check if this was an FX parameter command
        has_fx_param = any("SET_FX_PARAM" in cmd for cmd in commands)
        
        try:
            verification = json.loads(verify_response)
            success = verification.get("success", False)
            explanation = verification.get("explanation", "")
            issues = verification.get("issues", "")
            
            if success:
                print(f"\n✅ SUCCESS: {explanation}")
                if issues:
                    print(f"📌 Notes: {issues}")
                break  # Done!
            else:
                print(f"\n⚠️ PARTIAL: {explanation}")
                if issues:
                    print(f"📌 Issues: {issues}")
                
                # Prepare for retry
                previous_issues = issues
                previous_feedback = feedback
                initial_state = final_state  # Continue from current state
                retry_count += 1
                
                print(f"🔄 Retrying with feedback and updated state...")
                
        except json.JSONDecodeError as e:
            print(f"⚠️ Verification response malformed: {str(e)}")
            print(f"📋 Raw: {verify_response[:300]}")
            
            # Check if truncated JSON contains "success": true
            if '"success": true' in verify_response:
                print(f"✅ SUCCESS detected in truncated response (good enough!)")
                break  # Stop retrying if verification said success
            
            # Check feedback to see if commands actually succeeded
            if feedback and ("Added FX" in feedback or "Removed FX" in feedback or "Set" in feedback):
                # Commands executed - check if they seem complete
                num_commands = len(commands)
                num_feedback_lines = feedback.count('✅') + feedback.count('🎛️') + feedback.count('🎚️') + feedback.count('🗑️')
                
                if num_feedback_lines >= num_commands:
                    print(f"✅ All {num_commands} commands appear to have executed successfully based on feedback")
                    break  # Don't retry if feedback shows success
                else:
                    print(f"⚠️ Only {num_feedback_lines}/{num_commands} commands confirmed in feedback")
            
            # Retry if unclear or incomplete
            if retry_count < max_retries:
                print("📌 Will retry to verify or complete remaining steps")
                previous_issues = f"Verification unclear. Feedback: {feedback}. Check NEW STATE for what actually happened."
                previous_feedback = feedback if feedback else "No feedback"
                initial_state = final_state
                retry_count += 1
                print(f"🔄 Retrying (attempt {retry_count + 1}/{max_retries})...")
                continue
            else:
                print("❌ Max retries reached")
                break
    
    if retry_count == max_retries:
        print("\n❌ Max retries reached - giving up")
    
    # Save to memory
    history_entry = f"User: '{user_input}' → {reasoning}"
    conversation_history.append(history_entry)
    save_memory()
    
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
    print("=" * 70)
    print("\n⚠️  Make sure:")
    print("  1. Reaper is running")
    print("  2. reaper_agent.lua is loaded")
    print("=" * 70)
    
    load_memory()
    load_sound_knowledge()
    
    print("\n✅ Ready!\n")
    
    while True:
        user_input = input("💬 You: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n👋 Goodbye!")
            break
        if user_input.strip():
            execute_user_command(user_input)

