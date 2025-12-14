"""
Prompt Enhancer - Claude generates everything freely.
Supports: song generation, compose around existing MIDI, and agentic mixing.
Now with real drum sample support!
"""

import os
import re
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY_ENHANCER") or os.getenv("ANTHROPIC_API_KEY"))


def extract_bpm_from_text(text: str) -> int | None:
    """Best-effort BPM extraction from user prompt (e.g. '160 bpm', 'bpm 140', 'tempo=128')."""
    if not text:
        return None
    t = str(text).lower()
    m = re.search(r"\b(\d{2,3})\s*bpm\b", t)
    if not m:
        m = re.search(r"\bbpm\s*(\d{2,3})\b", t)
    if not m:
        m = re.search(r"\btempo\s*[:=]?\s*(\d{2,3})\b", t)
    if not m:
        return None
    try:
        bpm = int(m.group(1))
        if 40 <= bpm <= 220:
            return bpm
    except Exception:
        return None
    return None


# Default VSTs for each track type (non-drum tracks only)
DEFAULT_VSTS = {
    0: 'VSTi: Piano V3 (Arturia)',      # Track 0 = Piano/Keys
    1: 'VSTi: Analog Lab V (Arturia)',   # Track 1 = Bass synth
    # Track 2 = Drums (no VST - uses samples)
    3: 'VSTi: Analog Lab V (Arturia)',   # Track 3 = Lead/Melody synth
    4: 'VSTi: Analog Lab V (Arturia)',   # Track 4+ = Synth
}

# Load drum samples for MIDI-triggered sampler approach
try:
    from drum_index import get_cloud_summary, load_index
    _drum_index = load_index()
    DRUM_SAMPLES_AVAILABLE = _drum_index is not None and len(_drum_index.get("samples", {})) > 0
    sample_count = len(_drum_index.get("samples", {})) if _drum_index else 0
    DRUM_SUMMARY = get_cloud_summary() if DRUM_SAMPLES_AVAILABLE else ""
    print(f"[DRUMS] Samples available: {DRUM_SAMPLES_AVAILABLE}, count: {sample_count}")
    if DRUM_SAMPLES_AVAILABLE:
        print(f"[DRUMS] Summary preview: {DRUM_SUMMARY[:200]}...")
except Exception as e:
    print(f"[DRUMS] No drum index: {e}")
    DRUM_SAMPLES_AVAILABLE = False
    DRUM_SUMMARY = ""


def get_available_instruments():
    """Load available VSTi/VST3i instruments from reaper_plugins_list.txt"""
    instruments = []
    try:
        with open("reaper_plugins_list.txt", "r", encoding="utf-8") as f:
            for line in f:
                if "VSTi:" in line or "VST3i:" in line or "CLAPi:" in line:
                    instruments.append(line.strip())
    except:
        # Fallback if file not found
        return [
            "VSTi: Analog Lab V (Arturia)",
            "VSTi: Piano V3 (Arturia)",
            "VSTi: Acid V (Arturia)",
            "VSTi: Ample Guitar M II Lite (Ample Sound)"
        ]
    
    # Return top 20 instruments to avoid cluttering context
    return instruments[:30] if instruments else ["VSTi: Analog Lab V (Arturia)"]

AVAILABLE_INSTRUMENTS = get_available_instruments()
INSTRUMENT_LIST_STR = "\n".join([f"- {inst}" for inst in AVAILABLE_INSTRUMENTS])

def classify_request(user_input):
    """Classify: EL1 full song, new song, compose around existing MIDI, or mixing/effects?"""
    
    # Check for EL1 prefix first (case insensitive)
    user_lower = user_input.strip().lower()
    if user_lower.startswith("el1 ") or user_lower.startswith("el1:"):
        return "el1_fullsong"
    
    prompt = f""""{user_input}"

Classify this DAW request:
1. SONG = Create brand new music from scratch
2. COMPOSE_AROUND = User has existing MIDI and wants to add parts around it (finish song, add bass to my melody, etc.)
3. AGENTIC = Manipulate/mix existing audio (effects, EQ, reverb, volume, etc.)

Answer with ONE word: SONG, COMPOSE_AROUND, or AGENTIC"""

    try:
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=15,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text.strip().upper()
        
        if "COMPOSE" in response or "AROUND" in response:
            return "compose_around"
        elif "SONG" in response:
            return "song_generation"
        else:
            return "agentic"
    except:
        return "agentic"


def resolve_drum_samples(commands):
    """
    DRUM_SAMPLE commands are passed through as-is.
    The local bridge will resolve them to actual file paths.
    """
    # Just pass through - bridge handles resolution
    return commands


def ensure_instruments_and_items(commands):
    """
    Post-process commands to ensure:
    1. Every track with MIDI notes has an INSERT_INSTRUMENT
    2. Every track with MIDI notes has a MIDI_CREATE_ITEM
    3. Drum sample commands are resolved to actual files
    4. Tracks 2-5 use LOAD_SAMPLER instead of INSERT_INSTRUMENT
    Returns properly ordered commands.
    """
    # Default sample IDs for drum tracks (from drum_index.json)
    DEFAULT_DRUM_SAMPLES = {
        2: ('86', 60, 60, 60),    # kick - ID 86, trigger on C4
        3: ('98', 60, 60, 60),    # snare - ID 98, trigger on C4
        4: ('31', 60, 60, 60),    # hihat - ID 31, trigger on C4
        5: ('1', 36, 24, 96),     # 808 - ID 1, pitched (C2 base, full range)
    }
    
    # Parse existing commands
    tempo_cmds = []
    instrument_cmds = {}  # track -> command
    sampler_cmds = {}  # track -> LOAD_SAMPLER command
    midi_create_cmds = {}  # track -> command
    midi_note_cmds = []
    drum_cmds = []  # DRUM_SAMPLE or INSERT_AUDIO commands
    other_cmds = []
    
    # Track which tracks have MIDI notes vs drum samples
    tracks_with_notes = set()
    tracks_with_drums = set()
    max_end_time = 0
    
    for cmd in commands:
        if cmd.startswith('SET_TEMPO'):
            tempo_cmds.append(cmd)
        elif cmd.startswith('LOAD_SAMPLER'):
            # Keep existing LOAD_SAMPLER commands
            parts = cmd.split()
            if len(parts) >= 3:
                track = int(parts[1])
                sampler_cmds[track] = cmd
                tracks_with_drums.add(track)
        elif cmd.startswith('INSERT_INSTRUMENT'):
            parts = cmd.split()
            if len(parts) >= 3:
                track = int(parts[1])
                instrument_cmds[track] = cmd
        elif cmd.startswith('MIDI_CREATE_ITEM'):
            parts = cmd.split()
            if len(parts) >= 4:
                track = int(parts[1])
                midi_create_cmds[track] = cmd
                try:
                    end_time = float(parts[3])
                    max_end_time = max(max_end_time, end_time)
                except:
                    pass
        elif cmd.startswith('MIDI_INSERT_NOTE'):
            midi_note_cmds.append(cmd)
            parts = cmd.split()
            if len(parts) >= 6:
                track = int(parts[1])
                tracks_with_notes.add(track)
                try:
                    end_time = float(parts[5])
                    max_end_time = max(max_end_time, end_time)
                except:
                    pass
        elif cmd.startswith('DRUM_SAMPLE') or cmd.startswith('INSERT_AUDIO') or cmd.startswith('USE_SAMPLE'):
            drum_cmds.append(cmd)
            parts = cmd.split()
            if len(parts) >= 2:
                try:
                    track = int(parts[1])
                    tracks_with_drums.add(track)
                except:
                    pass
        elif cmd.startswith('VOL_DIP'):
            other_cmds.append(cmd)
    
    # Default song length if not found
    if max_end_time == 0:
        max_end_time = 60.0  # 1 minute default
    
    # Resolve drum samples to actual files
    drum_cmds = resolve_drum_samples(drum_cmds)
    
    # SAFETY: Ensure EVERY track with MIDI notes or sampler/instrument has everything it needs
    all_active_tracks = tracks_with_notes.union(instrument_cmds.keys()).union(sampler_cmds.keys())
    
    for track in all_active_tracks:
        has_instrument = track in instrument_cmds
        has_sampler = track in sampler_cmds
        
        # 1. Ensure Sound Source (Instrument or Sampler)
        if not has_instrument and not has_sampler:
            # If it looks like a drum track (checked via default map or heuristic), give it a sampler
            if DRUM_SAMPLES_AVAILABLE and track in DEFAULT_DRUM_SAMPLES:
                sample_id, base, start, end = DEFAULT_DRUM_SAMPLES[track]
                sampler_cmds[track] = f'LOAD_SAMPLER {track} {sample_id} {base} {start} {end}'
                print(f"   🎹 Added missing sampler for track {track}")
            else:
                # Otherwise default to Analog Lab
                vst = 'VSTi: Analog Lab V (Arturia)'
                instrument_cmds[track] = f'INSERT_INSTRUMENT {track} {vst}'
                print(f"   🎸 Added missing instrument for track {track}")
        
        # 2. Ensure MIDI Item (so notes can exist)
        if track not in midi_create_cmds:
             midi_create_cmds[track] = f'MIDI_CREATE_ITEM {track} 0.0 {round(max_end_time + 1, 1)}'
             print(f"   📝 Added missing MIDI item for track {track}")

    # Rebuild commands in correct order
    final_commands = []
    
    # 1. Tempo first
    final_commands.extend(tempo_cmds)
    if tempo_cmds:
        final_commands.append('')
    
    # 2. Instruments & Samplers (sorted by track)
    # Combine them to ensure track order is respected (Track 1, then 2, then 3...)
    all_sound_sources = {}
    all_sound_sources.update(instrument_cmds)
    all_sound_sources.update(sampler_cmds)
    
    for track in sorted(all_sound_sources.keys()):
        final_commands.append(all_sound_sources[track])
    if all_sound_sources:
        final_commands.append('')
    
    # 3. MIDI items (sorted by track)
    for track in sorted(midi_create_cmds.keys()):
        final_commands.append(midi_create_cmds[track])
    if midi_create_cmds:
        final_commands.append('')
    
    # 4. MIDI notes
    final_commands.extend(midi_note_cmds)
    if midi_note_cmds:
        final_commands.append('')
    
    # 5. Other commands (automation, etc.)
    final_commands.extend(other_cmds)
    
    return final_commands


def generate_song_commands(user_input):
    """Claude reads the request and generates the entire song with CREATIVE FREEDOM."""

    requested_bpm = extract_bpm_from_text(user_input)
    
    # Detect if user explicitly wants drums/beats vs. no drums
    user_lower = user_input.lower()
    wants_drums = any(w in user_lower for w in ['beat', 'drum', 'trap', 'hip hop', 'hiphop', 'edm', 'house', 'techno', '808', 'kick', 'snare', 'percussion', 'bounce'])
    wants_no_drums = any(w in user_lower for w in ['piano', 'acoustic', 'classical', 'ambient', 'ballad', 'strings', 'orchestral', 'no drums', 'no beat', 'solo', 'gentle', 'soft'])
    
    # Build drum sample info ONLY if user wants drums and doesn't want no-drums
    drum_info = ""
    if wants_drums and not wants_no_drums:
        if DRUM_SAMPLES_AVAILABLE and DRUM_SUMMARY:
            drum_info = f"""
DRUM SAMPLES (use ONLY if drums fit the music):
LOAD_SAMPLER [track] [sample_id] 60 60 60
MIDI_CREATE_ITEM [track] [start] [end]
MIDI_INSERT_NOTE [track] 60 [velocity] [start] [end]

SAMPLES: {DRUM_SUMMARY}
"""
        else:
            drum_info = """
DRUMS (use ONLY if drums fit the music):
INSERT_INSTRUMENT [track] VSTi: ReaSynDr (Cockos)
kick=36, snare=38, hihat=42
"""

    prompt = f"""You are a CREATIVE MUSICIAN composing original music. NO TEMPLATES. NO FORMULAS.

USER WANTS: "{user_input}"

THINK LIKE A REAL MUSICIAN:
1. What FEELING does this request evoke?
2. What instruments ACTUALLY fit? (A piano ballad doesn't need kicks/hi-hats!)
3. What key and chord progression creates the right mood?
4. What tempo feels natural for this style?
5. Should it be sparse and emotional, or dense and energetic?

COMMIT TO A KEY AND STAY IN IT:
- Major keys: C (C-E-G), G (G-B-D), D (D-F#-A), A (A-C#-E), F (F-A-C)
- Minor keys: Am (A-C-E), Em (E-G-B), Dm (D-F-A), Bm (B-D-F#)
- USE CHORD TONES on strong beats (beats 1 and 3)
- USE PASSING TONES on weak beats

{f'REQUESTED TEMPO: {requested_bpm} BPM - respect this!' if requested_bpm else 'PICK A TEMPO that fits the mood.'}

COMMANDS:
SET_TEMPO [bpm]
INSERT_INSTRUMENT [track] [instrument name]
MIDI_CREATE_ITEM [track] [start_seconds] [end_seconds]
MIDI_INSERT_NOTE [track] [pitch] [velocity] [start_seconds] [end_seconds]
VOL_DIP [track] [start] [end] [volume_0_to_1]

INSTRUMENTS (pick what FITS, not everything):
{INSTRUMENT_LIST_STR}
{drum_info}
MIDI PITCH: C3=48, C4=60, C5=72 (chromatic: +2=D, +4=E, +5=F, +7=G, +9=A, +11=B)
TIMING: In 4/4 at 120 BPM, each beat = 0.5 seconds. Adjust for your tempo.

COMPOSE FREELY:
- DON'T add drums/hi-hats unless the style actually needs them
- DON'T follow a rigid verse/chorus template unless it fits
- DO focus on melody and harmony first
- DO create musical phrases that breathe and flow
- DO use dynamics (velocity changes, volume automation)
- DO make it sound like REAL MUSIC, not a robotic loop

Output ONLY commands, one per line. 
Start with SET_TEMPO, then instruments, then MIDI items/notes.
Generate at least 1 minute of MUSICAL, EMOTIONAL, CREATIVE composition."""

    print(f"🎵 Claude composing: \"{user_input}\"")
    if DRUM_SAMPLES_AVAILABLE:
        print(f"   🥁 Real drum samples enabled!")
    
    response = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=16000,
        temperature=0.95,
        messages=[{"role": "user", "content": prompt}]
    ).content[0].text.strip()
    
    # Keep only valid commands
    valid_prefixes = ('SET_TEMPO', 'INSERT_INSTRUMENT', 'MIDI_CREATE_ITEM', 
                      'MIDI_INSERT_NOTE', 'VOL_DIP', 'USE_SAMPLE', 'INSERT_AUDIO', 'LOAD_SAMPLER')
    raw_commands = []
    for line in response.split('\n'):
        line = line.strip()
        if any(line.startswith(p) for p in valid_prefixes):
            raw_commands.append(line)
    
    # Post-process to ensure all tracks have instruments and items
    final_commands = ensure_instruments_and_items(raw_commands)
    
    # Count stats
    inst_count = len([c for c in final_commands if c.startswith('INSERT_INSTRUMENT')])
    note_count = len([c for c in final_commands if c.startswith('MIDI_INSERT_NOTE')])
    sampler_count = len([c for c in final_commands if c.startswith('LOAD_SAMPLER')])
    midi_item_count = len([c for c in final_commands if c.startswith('MIDI_CREATE_ITEM')])
    print(f"   ✅ Final: {inst_count} instruments, {sampler_count} samplers, {midi_item_count} MIDI items, {note_count} notes")
    
    # Verify all tracks with notes have sound sources
    final_tracks_with_notes = set()
    final_tracks_with_sound = set()
    for c in final_commands:
        if c.startswith('MIDI_INSERT_NOTE'):
            parts = c.split()
            if len(parts) >= 2:
                final_tracks_with_notes.add(int(parts[1]))
        elif c.startswith('INSERT_INSTRUMENT') or c.startswith('LOAD_SAMPLER'):
            parts = c.split()
            if len(parts) >= 2:
                final_tracks_with_sound.add(int(parts[1]))
    
    missing = final_tracks_with_notes - final_tracks_with_sound
    if missing:
        print(f"   ⚠️ WARNING: Tracks {missing} have notes but NO instrument/sampler!")
    
    return '\n'.join(final_commands)


def generate_compose_around_commands(user_input, midi_notes=None):
    """
    Generate music that fits around existing MIDI.
    First step: return command to READ the existing MIDI.
    Second step (when called with midi_notes): generate complementary parts.
    """
    
    if midi_notes is None:
        return "ANALYZE_MIDI_FIRST"
    
    # Build drum sample info if available
    drum_info = ""
    if DRUM_SAMPLES_AVAILABLE and DRUM_SUMMARY:
        drum_info = f"""
FOR DRUMS - Use USE_SAMPLE to place audio samples:
- USE_SAMPLE [track] [sample_id] [start_time_in_seconds]
- Put ALL drums on track 2
- DO NOT use INSERT_INSTRUMENT for the drum track!

CRITICAL: Pick ONLY ONE sample ID per category, then REUSE it for the pattern!

AVAILABLE SAMPLES:
{DRUM_SUMMARY}

Example: Pick kick ID 86, reuse it: USE_SAMPLE 2 86 0.0, USE_SAMPLE 2 86 1.0, USE_SAMPLE 2 86 2.0

"""
    else:
        drum_info = """
FOR DRUMS & 808s - Use MIDI:
- TRACK 2 for drums: INSERT_INSTRUMENT 2 VSTi: ReaSynDr (Cockos)
  Pitches: kick=36, snare=38, hihat=42
- TRACK 3 for 808 bass: INSERT_INSTRUMENT 3 VSTi: Analog Lab V (Arturia)
  Use LOW notes (C1=24, C2=36) - MATCH THE KEY of existing melody!

"""

    prompt = f"""You are composing music to COMPLEMENT existing MIDI in a DAW.

USER REQUEST: "{user_input}"

EXISTING MIDI NOTES (pitch, velocity, start_time, end_time):
{midi_notes}

YOUR TASK:
1. Analyze the existing notes - figure out the key, tempo feel, and style
2. Generate COMPLEMENTARY parts that FIT with what's already there
3. Don't duplicate what exists - ADD to it (bass, drums, counter-melody, harmony, etc.)

COMMANDS YOU CAN USE:

FOR MELODY/BASS/SYNTHS - Use MIDI:
- SET_TEMPO [bpm] (if not already set)
- INSERT_INSTRUMENT [track_number] [instrument]
  * "VSTi: Piano V3 (Arturia)" - for piano, keys, chords
  * "VSTi: Analog Lab V (Arturia)" - for synths, bass, pads, leads
- MIDI_CREATE_ITEM [track] [start_seconds] [end_seconds]
- MIDI_INSERT_NOTE [track] [midi_pitch] [velocity] [start_seconds] [end_seconds]

{drum_info}
AUTOMATION:
- VOL_DIP [track] [start_seconds] [end_seconds] [target_volume_0_to_1]

MIDI PITCH REFERENCE:
- Notes: C3=48, C4=60, C5=72 (add 2 for D, 4 for E, 5 for F, 7 for G, 9 for A, 11 for B)

IMPORTANT:
- The existing MIDI is on track 0 (don't add instrument there)
- Put your new parts on tracks 1, 2, 3, etc.
- EVERY new melodic track MUST have INSERT_INSTRUMENT before MIDI notes
- Match the timing and feel of the existing notes
- Stay in the same key!

Output ONLY commands, one per line."""

    print(f"🎵 Claude composing around existing MIDI...")
    if DRUM_SAMPLES_AVAILABLE:
        print(f"   🥁 Real drum samples enabled!")

    response = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=16000,
        temperature=0.9,
        messages=[{"role": "user", "content": prompt}]
    ).content[0].text.strip()

    # Keep only valid commands
    valid_prefixes = ('SET_TEMPO', 'INSERT_INSTRUMENT', 'MIDI_CREATE_ITEM', 
                      'MIDI_INSERT_NOTE', 'VOL_DIP', 'USE_SAMPLE', 'INSERT_AUDIO', 'LOAD_SAMPLER')
    raw_commands = []
    for line in response.split('\n'):
        line = line.strip()
        if any(line.startswith(p) for p in valid_prefixes):
            raw_commands.append(line)
    
    # Post-process to ensure all tracks have instruments and items
    final_commands = ensure_instruments_and_items(raw_commands)
    
    inst_count = len([c for c in final_commands if c.startswith('INSERT_INSTRUMENT')])
    note_count = len([c for c in final_commands if c.startswith('MIDI_INSERT_NOTE')])
    drum_count = len([c for c in final_commands if c.startswith(('USE_SAMPLE', 'INSERT_AUDIO'))])
    print(f"   Generated {inst_count} instruments, {note_count} notes, {drum_count} drum hits")
    
    return '\n'.join(final_commands)


def enhance_simple_prompt(user_input):
    """Fix typos for mixing requests."""
    response = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=200,
        temperature=0,
        messages=[{"role": "user", "content": f"Fix typos: \"{user_input}\"\nOutput only the fixed text:"}]
    ).content[0].text.strip().strip('"\'')
    return response


def enhance_prompt(user_input, reaper_state="", midi_notes=None):
    """Route to EL1 full song, song generation, compose-around, or agentic mode."""
    mode = classify_request(user_input)
    
    if mode == "el1_fullsong":
        print(f"🎵 EL1 MODE - Full song via ElevenLabs + stems")
        # Strip the "EL1" prefix to get the actual song description
        description = user_input.strip()
        if description.lower().startswith("el1 "):
            description = description[4:].strip()
        elif description.lower().startswith("el1:"):
            description = description[4:].strip()
        return generate_el1_fullsong(description)
    elif mode == "song_generation":
        print(f"🎵 SONG MODE - Full song (instrumental + vocals trigger)")
        # IMPORTANT: In song mode we want the prompt enhancer to do everything:
        # - generate instrumental commands
        # - generate lyrics + melody (for brief)
        # - append ELEVEN_VOCALS so the local bridge triggers ElevenLabs and imports into Reaper
        result = generate_full_song(user_input, use_local=False)
        if isinstance(result, dict) and isinstance(result.get("beat_commands"), str):
            return result["beat_commands"]
        # Fallback: instrumental only
        return generate_song_commands(user_input)
    elif mode == "compose_around":
        print(f"🎼 COMPOSE AROUND MODE - Building on existing MIDI")
        return generate_compose_around_commands(user_input, midi_notes)
    else:
        print(f"🎛️ AGENTIC MODE - Mixing/effects")
        return enhance_simple_prompt(user_input)


# =============================================
# VOCAL GENERATION PIPELINE
# =============================================

def analyze_beat_for_vocals(commands):
    """
    Analyze beat commands to extract musical info for vocal generation.
    Returns: tempo, key, chord progression, song structure, instruments, etc.
    """
    from collections import Counter, defaultdict
    
    tempo = 120  # default
    all_pitches = []
    timing_info = []
    instruments = []  # Track instruments used
    
    # Track notes by track and time for chord detection
    notes_by_track = defaultdict(list)  # track -> [(pitch, start, end), ...]
    
    # Handle both string and list input
    if isinstance(commands, str):
        lines = commands.split('\n')
    elif isinstance(commands, list):
        lines = commands
    else:
        lines = []
    
    for cmd in lines:
        if not cmd or not isinstance(cmd, str):
            continue
        try:
            if cmd.startswith('SET_TEMPO'):
                parts = cmd.split()
                if len(parts) >= 2:
                    tempo = int(float(parts[1]))  # handle "120.0" format too
            elif cmd.startswith('INSERT_INSTRUMENT'):
                # Extract instrument name (everything after track number)
                parts = cmd.split(maxsplit=2)
                if len(parts) >= 3:
                    inst_name = parts[2]
                    # Clean up the name for readability
                    inst_name = inst_name.replace("VSTi: ", "").replace("VST3i: ", "")
                    inst_name = inst_name.replace(" (Arturia)", "").replace(" (Cockos)", "")
                    if inst_name and inst_name not in instruments:
                        instruments.append(inst_name)
            elif cmd.startswith('LOAD_SAMPLER'):
                # Track that we have drum samples
                parts = cmd.split()
                if len(parts) >= 3:
                    sample_id = parts[2]
                    # Map common sample types
                    track = int(parts[1])
                    if track == 2:
                        if "Kick" not in instruments:
                            instruments.append("Kick Drum")
                    elif track == 3:
                        if "Snare" not in instruments:
                            instruments.append("Snare")
                    elif track == 4:
                        if "Hi-hat" not in instruments:
                            instruments.append("Hi-hats")
                    elif track == 5:
                        if "808" not in instruments:
                            instruments.append("808 Bass")
            elif cmd.startswith('MIDI_INSERT_NOTE'):
                parts = cmd.split()
                if len(parts) >= 6:
                    track = int(parts[1])
                    pitch = int(float(parts[2]))
                    start = float(parts[4])
                    end = float(parts[5])
                    all_pitches.append(pitch)
                    timing_info.append((start, end))
                    notes_by_track[track].append((pitch, start, end))
        except (ValueError, IndexError):
            continue  # skip malformed lines
    
    # Better key detection using scale profile matching
    key = 'C major'
    key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Scale templates (intervals from root)
    MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11}  # W W H W W W H
    MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10}  # W H W W H W W
    
    if all_pitches:
        pitch_classes = [p % 12 for p in all_pitches]
        pitch_set = set(pitch_classes)
        pitch_counts = Counter(pitch_classes)
        
        best_score = -1
        best_key = 'C major'
        
        # Try each possible root for both major and minor
        for root in range(12):
            # Major scale fit
            major_notes = {(root + interval) % 12 for interval in MAJOR_SCALE}
            major_match = len(pitch_set & major_notes)
            # Weight by frequency of notes in the scale
            major_score = sum(pitch_counts.get(n, 0) for n in major_notes)
            
            # Minor scale fit
            minor_notes = {(root + interval) % 12 for interval in MINOR_SCALE}
            minor_match = len(pitch_set & minor_notes)
            minor_score = sum(pitch_counts.get(n, 0) for n in minor_notes)
            
            # Pick the best match
            if major_score > best_score:
                best_score = major_score
                best_key = f"{key_names[root]} major"
            if minor_score > best_score:
                best_score = minor_score
                best_key = f"{key_names[root]} minor"
        
        key = best_key
    
    # Calculate song length
    song_length = 60  # default
    if timing_info:
        song_length = max(t[1] for t in timing_info)
    
    # Calculate beat duration in seconds
    beat_duration = 60.0 / tempo
    total_bars = int(song_length / (beat_duration * 4)) + 1  # Assuming 4/4 time
    
    # Extract chord progression from track 0 (usually chords/piano)
    # Group simultaneous notes into chords
    chord_progression = []
    if 0 in notes_by_track:
        chord_notes = notes_by_track[0]
        # Group notes by start time (within small tolerance)
        time_groups = defaultdict(list)
        for pitch, start, end in chord_notes:
            # Round to nearest 0.1 second for grouping
            time_key = round(start * 10) / 10
            time_groups[time_key].append(pitch)
        
        for start_time in sorted(time_groups.keys()):
            pitches = sorted(time_groups[start_time])
            chord_name = _pitches_to_chord_name(pitches, key)
            bar = int(start_time / (beat_duration * 4)) + 1
            beat = int((start_time % (beat_duration * 4)) / beat_duration) + 1
            chord_progression.append({
                "bar": bar,
                "beat": beat,
                "chord": chord_name,
                "time": start_time
            })
    
    # Build song structure (estimate sections based on energy/density changes)
    song_structure = _estimate_song_structure(notes_by_track, tempo, song_length)
    
    return {
        'tempo': tempo,
        'key': key,
        'song_length_seconds': song_length,
        'beat_count': int(song_length * tempo / 60),
        'note_count': len(all_pitches),
        'total_bars': total_bars,
        'chord_progression': chord_progression,
        'song_structure': song_structure,
        'instruments': instruments,
    }


def _pitches_to_chord_name(pitches: list, key: str = "C") -> str:
    """Convert a list of MIDI pitches to a chord name."""
    if not pitches:
        return "N/C"
    
    key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Get pitch classes (0-11)
    pitch_classes = sorted(set(p % 12 for p in pitches))
    
    if len(pitch_classes) < 2:
        # Single note - just return the note name
        return key_names[pitch_classes[0]]
    
    # Find root (lowest pitch class)
    root = pitch_classes[0]
    root_name = key_names[root]
    
    # Calculate intervals from root
    intervals = [(p - root) % 12 for p in pitch_classes]
    
    # Detect chord quality based on intervals
    has_minor_3rd = 3 in intervals
    has_major_3rd = 4 in intervals
    has_perfect_5th = 7 in intervals
    has_dim_5th = 6 in intervals
    has_minor_7th = 10 in intervals
    has_major_7th = 11 in intervals
    has_9th = 2 in intervals or 14 in intervals
    
    # Build chord suffix
    suffix = ""
    if has_minor_3rd:
        suffix = "m"
        if has_dim_5th:
            suffix = "dim"
    elif has_major_3rd:
        suffix = ""  # major
        if has_dim_5th:
            suffix = "(b5)"
    
    if has_minor_7th:
        suffix += "7"
    elif has_major_7th:
        suffix += "maj7"
    
    if has_9th and len(pitch_classes) >= 4:
        suffix += "9" if "7" not in suffix else ""
    
    return root_name + suffix


def _estimate_song_structure(notes_by_track: dict, tempo: int, song_length: float) -> list:
    """Estimate song structure based on note density and patterns."""
    beat_duration = 60.0 / tempo
    bar_duration = beat_duration * 4  # 4/4 time
    total_bars = int(song_length / bar_duration) + 1
    
    # Calculate note density per 8-bar section
    sections = []
    section_size = 8  # bars
    
    for section_start_bar in range(1, total_bars + 1, section_size):
        section_end_bar = min(section_start_bar + section_size - 1, total_bars)
        section_start_time = (section_start_bar - 1) * bar_duration
        section_end_time = section_end_bar * bar_duration
        
        # Count notes in this section
        note_count = 0
        section_pitches = []
        for track, notes in notes_by_track.items():
            for pitch, start, end in notes:
                if section_start_time <= start < section_end_time:
                    note_count += 1
                    section_pitches.append(pitch)
        
        # Estimate section type based on position and density
        position_ratio = section_start_bar / max(1, total_bars)
        
        if section_start_bar <= 4:
            section_name = "Intro"
        elif position_ratio < 0.25:
            section_name = "Verse 1"
        elif position_ratio < 0.4:
            section_name = "Pre-Chorus" if note_count > 20 else "Verse 1"
        elif position_ratio < 0.55:
            section_name = "Chorus"
        elif position_ratio < 0.7:
            section_name = "Verse 2"
        elif position_ratio < 0.85:
            section_name = "Chorus"
        else:
            section_name = "Outro" if note_count < 15 else "Chorus"
        
        # Get chords for this section from track 0
        section_chords = []
        if 0 in notes_by_track:
            from collections import defaultdict
            time_groups = defaultdict(list)
            for pitch, start, end in notes_by_track[0]:
                if section_start_time <= start < section_end_time:
                    time_key = round(start * 10) / 10
                    time_groups[time_key].append(pitch)
            
            for start_time in sorted(time_groups.keys())[:4]:  # First 4 chords
                chord_name = _pitches_to_chord_name(time_groups[start_time])
                if chord_name not in section_chords:
                    section_chords.append(chord_name)
        
        sections.append({
            "section": section_name,
            "start_bar": section_start_bar,
            "end_bar": section_end_bar,
            "chords": " - ".join(section_chords) if section_chords else "",
            "timing": f"{section_start_time:.1f}s - {section_end_time:.1f}s"
        })
    
    return sections


def generate_lyrics(topic, mood, song_structure="verse-chorus-verse-chorus-bridge-chorus", tempo=120, key="C"):
    """
    Generate lyrics that fit the beat.
    Returns structured lyrics with sections.
    """
    
    prompt = f"""Write song lyrics for a {mood} song about "{topic}".

MUSICAL CONTEXT:
- Tempo: {tempo} BPM
- Key: {key}
- Structure: {song_structure}

RULES:
1. Keep syllable count consistent within sections
2. Make choruses catchy and repeatable
3. Verses tell the story, choruses are the hook
4. Keep lines short enough to sing (4-8 syllables per line typically)
5. Include natural pauses for breath

OUTPUT FORMAT:
[VERSE 1]
Line 1
Line 2
...

[CHORUS]
Line 1
Line 2
...

[VERSE 2]
Line 1
Line 2
...

[BRIDGE]
Line 1
...

Write the complete lyrics now:"""

    print(f"📝 Generating lyrics: {mood} song about '{topic}'")
    
    try:
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=2000,
            temperature=0.9,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text.strip()
    except Exception as e:
        print(f"   ❌ Lyrics API error: {e}")
        return f"[VERSE 1]\nCouldn't generate lyrics\nPlease try again\n\n[CHORUS]\nTry again\nTry again"
    
    # Count sections
    sections = response.count('[')
    lines = len([l for l in response.split('\n') if l.strip() and not l.startswith('[')])
    print(f"   ✅ Generated {sections} sections, {lines} lines")
    
    return response


def generate_vocal_melody(lyrics, tempo=120, key="C", chord_progression=None, style_context=""):
    """
    Generate MIDI notes for a vocal melody that fits the lyrics.
    Returns list of (pitch, duration, lyric_syllable) tuples.
    
    Args:
        lyrics: Lyrics text
        tempo: BPM
        key: Musical key
        chord_progression: Optional chord info (not used yet)
        style_context: Description of instrumental style to match
    """
    
    # Key to starting pitch mapping
    key_to_pitch = {
        'C': 60, 'C#': 61, 'D': 62, 'D#': 63, 'E': 64, 'F': 65,
        'F#': 66, 'G': 67, 'G#': 68, 'A': 69, 'A#': 70, 'B': 71
    }
    root = key_to_pitch.get(key, 60)
    
    # Build style-aware prompt
    musical_context = f"""
MUSICAL CONTEXT:
- Tempo: {tempo} BPM
- Key: {key} (root pitch = MIDI {root})
- Beat duration: {60/tempo:.3f} seconds
- Singable range: MIDI 55-75 (G3 to D5)
"""
    
    if style_context:
        musical_context += f"\nINSTRUMENTAL STYLE:\n{style_context}\n"
        musical_context += f"""
IMPORTANT: Your melody must FIT this instrumental.
- Think in terms of MIDI note numbers that work over {key}
- Match the energy and vibe described above
- Avoid notes that would clash with the bass/harmony
- Use melodic rhythms that complement the beat style
"""
    
    prompt = f"""Create a vocal melody for these lyrics. Output note data for a SINGER to perform.

LYRICS:
{lyrics}

{musical_context}

MELODY RULES:
1. Stay in {key} scale and within MIDI 55-75 range
2. Mostly stepwise motion (1-2 semitones between notes)
3. Longer notes on emphasized syllables
4. Match the natural rhythm of the words
5. Create memorable, singable phrases
6. Leave space for breaths between phrases
7. CRITICAL: Think like a topline writer - make notes that sound GOOD over this instrumental

OUTPUT FORMAT (one line per note):
VOCAL_NOTE [midi_pitch] [duration_beats] [syllable/word]

Example:
VOCAL_NOTE 60 1.0 I
VOCAL_NOTE 62 0.5 can't
VOCAL_NOTE 64 1.5 feel
VOCAL_NOTE 62 1.0 my
VOCAL_NOTE 60 2.0 face

Generate the complete vocal melody:"""

    print(f"🎤 Generating vocal melody in {key} at {tempo} BPM")
    
    try:
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=8000,
            temperature=0.8,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text.strip()
    except Exception as e:
        print(f"   ❌ Melody API error: {e}")
        # Return minimal fallback melody
        return [{'pitch': 60, 'start': 0, 'end': 1, 'duration_beats': 1, 'syllable': 'la'}]

    # Parse the response
    melody_data = []
    beat_duration = 60 / tempo
    current_time = 0.0
    parse_errors = 0
    
    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('VOCAL_NOTE'):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    pitch = int(float(parts[1]))
                    duration_beats = float(parts[2])
                    syllable = ' '.join(parts[3:])
                    
                    # Sanity checks
                    if pitch < 30 or pitch > 90:  # outside singable range
                        pitch = max(55, min(75, pitch))  # clamp to safe range
                    if duration_beats <= 0 or duration_beats > 16:  # unreasonable duration
                        duration_beats = 1.0
                    
                    duration_sec = duration_beats * beat_duration
                    melody_data.append({
                        'pitch': pitch,
                        'start': current_time,
                        'end': current_time + duration_sec,
                        'duration_beats': duration_beats,
                        'syllable': syllable
                    })
                    current_time += duration_sec
                except (ValueError, IndexError):
                    parse_errors += 1
                    continue
    
    if parse_errors > 0:
        print(f"   ⚠️ Skipped {parse_errors} malformed notes")
    print(f"   ✅ Generated {len(melody_data)} notes, {current_time:.1f}s total")
    
    return melody_data


def format_for_diffsinger(lyrics, melody_data, tempo):
    """
    Format lyrics and melody for DiffSinger API input.
    Returns dict ready to send to RunPod.
    """
    
    # Build note sequence string
    pitch_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    notes = []
    durations = []
    syllables = []
    
    for note in melody_data:
        pitch = note['pitch']
        octave = pitch // 12 - 1
        note_name = pitch_names[pitch % 12]
        notes.append(f"{note_name}{octave}")
        durations.append(f"{note['duration_beats']:.2f}")
        syllables.append(note['syllable'])
    
    return {
        'lyrics': ' '.join(syllables),
        'notes': ' '.join(notes),
        'durations': ' '.join(durations),
        'tempo': tempo,
        'note_count': len(notes),
        'total_duration': melody_data[-1]['end'] if melody_data else 0
    }


def call_diffsinger_api(diffsinger_input, runpod_endpoint=None, api_key=None, 
                       experiment_name=None, melody_data=None, lyrics=None, 
                       use_local=True):
    """
    Call DiffSinger to synthesize vocals.
    
    Supports:
    - Local inference (if use_local=True and experiment_name provided)
    - RunPod API (if runpod_endpoint provided)
    
    Args:
        diffsinger_input: Formatted input dict (for API compatibility)
        runpod_endpoint: Optional RunPod endpoint URL
        api_key: Optional API key for RunPod
        experiment_name: Name of trained model (for local inference)
        melody_data: Original melody data (for local inference)
        lyrics: Original lyrics (for local inference)
        use_local: Try local inference first if experiment_name provided
    
    Returns:
        Dict with 'status', 'audio_path' (if local), or 'audio_url' (if API)
    """
    
    # Try local inference first if enabled
    if use_local and experiment_name and melody_data and lyrics:
        try:
            from diffsinger_integration import synthesize_vocals_local
            
            tempo = diffsinger_input.get('tempo', 120)
            print(f"🎤 Running LOCAL DiffSinger inference...")
            print(f"   Experiment: {experiment_name}")
            print(f"   Tempo: {tempo} BPM")
            
            audio_path = synthesize_vocals_local(
                lyrics=lyrics,
                melody_data=melody_data,
                tempo=tempo,
                experiment_name=experiment_name
            )
            
            return {
                'status': 'success',
                'audio_path': audio_path,
                'method': 'local'
            }
        except Exception as e:
            print(f"⚠️ Local inference failed: {e}")
            print("   Falling back to API or placeholder...")
            if runpod_endpoint:
                # Continue to API call
                pass
            else:
                # Return placeholder
                return {
                    'status': 'pending',
                    'message': f'Local inference failed: {e}. Model may not be ready yet.',
                    'error': str(e)
                }
    
    # Try RunPod API if endpoint provided
    if runpod_endpoint:
        try:
            import requests
            response = requests.post(
                f"{runpod_endpoint}/synthesize",
                json=diffsinger_input,
                headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return {
                'status': 'success',
                'audio_url': result.get('audio_url'),
                'method': 'runpod'
            }
        except Exception as e:
            print(f"⚠️ RunPod API error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'method': 'runpod'
            }
    
    # No inference method available - return placeholder
    print("⚠️ DiffSinger not configured - returning placeholder")
    lyrics_preview = diffsinger_input.get('lyrics', '')[:100]
    notes_preview = diffsinger_input.get('notes', '')[:50]
    return {
        'status': 'pending',
        'message': 'DiffSinger not configured. Provide experiment_name for local inference or runpod_endpoint for API.',
        'input_preview': {
            'lyrics': lyrics_preview + ('...' if len(lyrics_preview) >= 100 else ''),
            'notes': notes_preview + ('...' if len(notes_preview) >= 50 else ''),
            'tempo': diffsinger_input.get('tempo', 120)
        }
    }


def call_elevenlabs_music_api(
    *,
    lyrics: str,
    tempo: int,
    key: str,
    mood: str,
    melody_data=None,
    music_length_ms: int | None = None,
    chord_progression=None,  # Actual chords from the beat
    song_structure=None,     # Sections (verse, chorus, etc.)
    instruments=None,        # Instruments in the track
):
    """
    Generate VOCALS-ONLY (a cappella) via ElevenLabs Eleven Music (official SDK).

    Returns: (audio_bytes, filename, meta_json)

    Docs: https://elevenlabs.io/docs/developers/guides/cookbooks/music/quickstart
    """
    from elevenlabs_vocals import VocalBrief, build_vocals_prompt, compose_vocals_mp3

    midi_hint = None
    if melody_data:
        try:
            midi_hint = [int(n.get("pitch")) for n in melody_data if isinstance(n, dict) and "pitch" in n]
        except Exception:
            midi_hint = None

    brief = VocalBrief(
        lyrics=lyrics,
        bpm=int(tempo) if tempo else None,
        key=str(key) if key else None,
        style=str(mood) if mood else None,
        melody_midi=midi_hint,
        voice_tags=["lead vocal", "a cappella", "vocals only"],
        chord_progression=chord_progression,
        song_structure=song_structure,
        instruments=instruments,
    )
    prompt = build_vocals_prompt(brief)

    if music_length_ms is None:
        # Default: 30s if we can't infer a better length.
        music_length_ms = 30000
    music_length_ms = int(max(3000, min(int(music_length_ms), 180000)))

    return compose_vocals_mp3(prompt=prompt, length_ms=music_length_ms, retries=3, retry_backoff_s=1.5)


def generate_vocals_for_beat(beat_commands, topic, mood, runpod_endpoint=None, 
                            experiment_name=None, use_local=True, original_prompt="",
                            engine: str = "diffsinger",
                            return_audio_bytes: bool = False):
    """
    FULL VOCAL PIPELINE:
    1. Analyze beat → extract tempo, key
    2. Generate lyrics → Claude writes words
    3. Generate melody → Claude creates MIDI for voice (AWARE of beat style)
    4. Synthesize → DiffSinger (local or RunPod)
    
    Args:
        beat_commands: Reaper commands for the beat
        topic: Song topic/theme
        mood: Song mood
        runpod_endpoint: Optional RunPod API endpoint
        experiment_name: Name of trained DiffSinger model (for local inference)
        use_local: Try local inference if experiment_name provided
        original_prompt: Original user prompt (for style context)
    
    Returns all components for debugging/review.
    """
    
    print("=" * 50)
    print("🎤 VOCAL GENERATION PIPELINE")
    print("=" * 50)
    
    # Step 1: Analyze the beat
    beat_info = analyze_beat_for_vocals(beat_commands)
    print(f"📊 Beat: {beat_info['tempo']} BPM, Key: {beat_info['key']}, Length: {beat_info['song_length_seconds']:.1f}s")
    
    # Step 2: Generate lyrics
    lyrics = generate_lyrics(
        topic=topic,
        mood=mood,
        tempo=beat_info['tempo'],
        key=beat_info['key']
    )
    
    # Step 3: Build style context for melody generation
    style_context = f"""
The instrumental beat is {beat_info['tempo']} BPM in {beat_info['key']}.
Style/vibe: {mood}
"""
    if original_prompt:
        style_context += f"Original request: {original_prompt}\n"
    
    style_context += f"""
Think like a topline writer: what MIDI notes (55-75 range) would sound good
singing over this {mood} instrumental in {beat_info['key']}?
Match the energy and vibe of the beat.
"""
    
    # Step 4: Generate vocal melody (now style-aware)
    melody = generate_vocal_melody(
        lyrics=lyrics,
        tempo=beat_info['tempo'],
        key=beat_info['key'],
        style_context=style_context
    )
    
    print(f"🎵 Generated {len(melody)} vocal notes")
    
    # Step 5: Format (legacy DiffSinger input) - kept for debugging / compatibility
    diffsinger_input = format_for_diffsinger(lyrics, melody, beat_info['tempo'])

    # Step 6: Synthesize vocals (optional)
    # In the current cloud→local bridge architecture, we often only want a "vocal brief"
    # here and let the local bridge trigger ElevenLabs via ELEVEN_VOCALS.
    if engine == "brief":
        synth_result = {
            "status": "skipped",
            "method": "brief_only",
            "message": "Synthesis skipped (brief-only). Bridge will trigger ElevenLabs via ELEVEN_VOCALS.",
        }
    elif engine == "elevenlabs":
        try:
            # Try to infer length from melody timing
            length_ms = None
            if melody:
                try:
                    length_ms = int(max(0.0, melody[-1].get("end", 0.0)) * 1000)
                except Exception:
                    length_ms = None

            audio_bytes, filename, meta = call_elevenlabs_music_api(
                lyrics=lyrics,
                tempo=int(beat_info['tempo']),
                key=str(beat_info['key']),
                mood=str(mood),
                melody_data=melody,
                music_length_ms=length_ms,
                chord_progression=beat_info.get('chord_progression'),
                song_structure=beat_info.get('song_structure'),
                instruments=beat_info.get('instruments'),
            )
            synth_result = {
                "status": "success",
                "method": "elevenlabs_music",
                "filename": filename,
                "bytes": len(audio_bytes),
                "meta": meta,
            }
            if return_audio_bytes:
                synth_result["audio_bytes"] = audio_bytes
        except Exception as e:
            synth_result = {
                "status": "error",
                "method": "elevenlabs_music",
                "error": str(e),
            }
    else:
        synth_result = call_diffsinger_api(
            diffsinger_input,
            runpod_endpoint=runpod_endpoint,
            experiment_name=experiment_name,
            melody_data=melody,
            lyrics=lyrics,
            use_local=use_local,
        )
    
    print("=" * 50)
    print("✅ VOCAL PIPELINE COMPLETE")
    print("=" * 50)
    
    return {
        'beat_info': beat_info,
        'lyrics': lyrics,
        'melody': melody,
        'diffsinger_input': diffsinger_input,
        'synthesis_result': synth_result
    }


# =============================================
# EL1 MODE - Full ElevenLabs Song + Stems
# =============================================

def generate_el1_fullsong(song_description: str) -> str:
    """
    EL1 Mode: Generate full song with ElevenLabs + split into stems.
    
    Flow:
    1. Claude generates lyrics based on description
    2. Returns EL1_SONG command which the bridge will:
       - Send to ElevenLabs for full song generation
       - Separate into stems
       - Import all stems to Reaper tracks
    
    Args:
        song_description: What the song should be about (already stripped of "EL1" prefix)
    
    Returns:
        Commands including EL1_SONG with full payload
    """
    import json
    
    print(f"🎵 [EL1] Generating full song for: {song_description[:100]}...")
    
    # Step 1: Have Claude generate lyrics and suggest musical style
    lyrics_prompt = f"""You are a professional songwriter. Write lyrics for a song with this theme:

"{song_description}"

Also suggest the best musical style for these lyrics.

Respond in this EXACT JSON format:
{{
    "lyrics": "verse 1 lyrics here\\n\\nchorus lyrics here\\n\\nverse 2 lyrics here\\n\\nchorus lyrics here",
    "genre": "pop rock",
    "mood": "uplifting, energetic",
    "tempo": 120,
    "key": "G major",
    "vocal_style": "male",
    "title": "Song Title Here"
}}

Guidelines:
- Lyrics should be 2-3 minutes when sung (2 verses, chorus, maybe bridge)
- Genre should match the vibe of the description
- Tempo 80-160 BPM depending on energy
- vocal_style: "male", "female", or "mixed"
- Make the lyrics emotional, authentic, and memorable"""

    try:
        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=2000,
            temperature=0.8,
            messages=[{"role": "user", "content": lyrics_prompt}]
        )
        response_text = response.content[0].text.strip()
        
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            song_data = json.loads(response_text[json_start:json_end])
        else:
            raise ValueError("No JSON found in response")
            
    except Exception as e:
        print(f"⚠️ [EL1] Failed to generate lyrics: {e}")
        # Fallback with defaults
        song_data = {
            "lyrics": f"Verse about {song_description}\n\nChorus about {song_description}",
            "genre": "pop",
            "mood": "emotional",
            "tempo": 120,
            "key": "C major",
            "vocal_style": "mixed",
            "title": "Untitled"
        }
    
    print(f"✅ [EL1] Generated lyrics for '{song_data.get('title', 'Untitled')}'")
    print(f"   Genre: {song_data.get('genre')}, Tempo: {song_data.get('tempo')} BPM")
    
    # Step 2: Build EL1_SONG command payload
    # This will be processed by the local bridge
    payload = {
        "lyrics": song_data.get("lyrics", ""),
        "genre": song_data.get("genre", "pop"),
        "mood": song_data.get("mood", "emotional"),
        "tempo": song_data.get("tempo", 120),
        "key": song_data.get("key", "C major"),
        "vocal_style": song_data.get("vocal_style", "mixed"),
        "title": song_data.get("title", "Untitled"),
        "song_length_seconds": 120,  # 2 minutes
        "description": song_description
    }
    
    # Build commands:
    # 1. SET_TEMPO for Reaper project
    # 2. EL1_SONG command which the bridge will expand into multiple INSERT_AUDIO commands
    commands = []
    commands.append(f"SET_TEMPO {payload['tempo']}")
    
    # EL1_SONG format: EL1_SONG <start_time> <json_payload>
    # The bridge will:
    # - Generate full song via ElevenLabs
    # - Separate into stems
    # - Convert to INSERT_AUDIO commands for tracks 0-3
    payload_json = json.dumps(payload)
    commands.append(f'EL1_SONG 0.0 {payload_json}')
    
    result = "\n".join(commands)
    print(f"✅ [EL1] Commands ready:\n{result[:500]}...")
    
    return result


# =============================================
# FULL SONG WITH VOCALS (One Command)
# =============================================

def generate_full_song(user_prompt, runpod_endpoint=None, experiment_name=None, use_local=True):
    """
    Generate a complete song with instrumental AND vocals.
    
    Usage: generate_full_song("dark R&B about heartbreak")
    
    Returns: {
        'beat_commands': str (Reaper commands),
        'vocals': dict (lyrics, melody, audio)
    }
    """
    
    # Parse mood/topic from prompt
    prompt_lower = user_prompt.lower()
    
    # Detect mood
    if any(w in prompt_lower for w in ['dark', 'sad', 'emotional', 'melancholy']):
        mood = 'dark and emotional'
    elif any(w in prompt_lower for w in ['happy', 'upbeat', 'fun', 'party']):
        mood = 'upbeat and energetic'
    elif any(w in prompt_lower for w in ['chill', 'lofi', 'relaxed', 'mellow']):
        mood = 'chill and mellow'
    else:
        mood = 'soulful'
    
    # Extract topic (everything after "about" if present)
    topic = "life and feelings"  # default
    if 'about' in prompt_lower:
        parts = user_prompt.lower().split('about', 1)
        if len(parts) > 1 and parts[1].strip():
            topic = parts[1].strip()
    
    print(f"🎵 FULL SONG: {mood} | Topic: {topic}")
    
    # Step 1: Generate beat
    beat_commands = generate_song_commands(user_prompt)
    
    # Step 2: Generate vocal brief (lyrics + melody + beat_info). Do NOT synthesize here.
    # The bridge will synthesize via ELEVEN_VOCALS and import into Reaper.
    vocals = generate_vocals_for_beat(
        beat_commands=beat_commands,
        topic=topic,
        mood=mood,
        runpod_endpoint=runpod_endpoint,
        experiment_name=experiment_name,
        use_local=use_local,
        engine="brief",
        original_prompt=user_prompt,
    )

    # Step 3: Append ELEVEN_VOCALS command so the local bridge can fetch bytes
    # and rewrite into INSERT_AUDIO 1 "<local_mp3_path>" 0.0 before Lua sees it.
    #
    # This makes "prompt enhancer does everything" true: beat + vocals import trigger.
    try:
        beat_info = vocals.get("beat_info", {}) if isinstance(vocals, dict) else {}
        tempo = int(beat_info.get("tempo") or 120)
        key = str(beat_info.get("key") or "C")
        lyrics_text = str((vocals.get("lyrics") or "") if isinstance(vocals, dict) else "")

        # Prefer melody-derived duration, else default 30s
        music_length_ms = 30000
        melody = vocals.get("melody") if isinstance(vocals, dict) else None
        if isinstance(melody, list) and melody:
            try:
                music_length_ms = int(max(0.0, melody[-1].get("end", 0.0)) * 1000)
            except Exception:
                music_length_ms = 30000

        # Extract chord progression, song structure, and instruments for better vocal sync
        chord_progression = beat_info.get("chord_progression", [])
        song_structure = beat_info.get("song_structure", [])
        song_length_seconds = beat_info.get("song_length_seconds", 60)
        instruments = beat_info.get("instruments", [])

        # Build comprehensive payload with full musical context
        payload = {
            "session_id": "demo",
            "lyrics": lyrics_text,
            "tempo": tempo,
            "key": key,
            "mood": mood,
            "music_length_ms": music_length_ms,
            # NEW: Full musical context for better vocal sync
            "chord_progression": chord_progression,
            "song_structure": song_structure,
            "song_length_seconds": song_length_seconds,
            "instruments": instruments,
        }
        import json as _json
        eleven_cmd = f"ELEVEN_VOCALS 1 0.0 {_json.dumps(payload, ensure_ascii=False)}"

        # Append to the command script
        beat_commands_with_vocals = beat_commands.rstrip() + "\n\n" + eleven_cmd + "\n"
    except Exception:
        beat_commands_with_vocals = beat_commands

    return {
        # Backward compatible fields
        'beat_commands': beat_commands_with_vocals,
        'vocals': vocals,
        # Extra debug
        'beat_commands_instrumental_only': beat_commands,
    }


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Prompt Enhancer")
    print("=" * 50)
    
    print("✅ Drum samples enabled (resolved locally by bridge)")
    
    print("\n--- Test Song Generation ---")
    result = enhance_prompt("make a chill lofi beat with drums")
    print(f"Generated {len(result.split(chr(10)))} lines")
    print("\nFirst 30 lines:")
    for line in result.split('\n')[:30]:
        print(f"  {line}")
    
    print("\n--- Test Lyrics Generation ---")
    lyrics = generate_lyrics("lost love", "dark and emotional", tempo=85, key="Am")
    print(lyrics[:500] + "..." if len(lyrics) > 500 else lyrics)
