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
    """Classify: new song, compose around existing MIDI, or mixing/effects?"""
    prompt = f""""{user_input}"

Classify this DAW request:
1. SONG = Create brand new music from scratch
2. COMPOSE_AROUND = User has existing MIDI and wants to add parts around it (finish song, add bass to my melody, etc.)
3. AGENTIC = Manipulate/mix existing audio (effects, EQ, reverb, volume, etc.)

Answer with ONE word: SONG, COMPOSE_AROUND, or AGENTIC"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
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
    """Claude reads the request and generates the entire song."""
    
    # Build drum sample info if available
    drum_info = ""
    if DRUM_SAMPLES_AVAILABLE and DRUM_SUMMARY:
        drum_info = f"""
FOR DRUMS (tracks 2+) - Load sample into sampler, then trigger with MIDI:

STEP 1: Load samples (pick ANY available tracks):
LOAD_SAMPLER [track] [sample_id] 60 60 60
- You can use multiple tracks for different drum sounds (kick, snare, hats, percs)
- For 808s/Bass samples: use LOAD_SAMPLER [track] [id] 36 24 96 (for pitching)

STEP 2: Create MIDI items for those tracks:
MIDI_CREATE_ITEM [track] [start] [end]

STEP 3: Insert MIDI notes to trigger samples:
MIDI_INSERT_NOTE [track] 60 [velocity] [start] [end]
- For drums: always use pitch 60
- For 808: use different pitches for bass melody

SAMPLE IDS:
{DRUM_SUMMARY}

"""
    else:
        drum_info = """
FOR DRUMS & 808 - Use MIDI instruments:

TRACK 2 - DRUMS:
- INSERT_INSTRUMENT 2 VSTi: ReaSynDr (Cockos)
- kick=36, snare=38, hihat=42

TRACK 3 - 808 BASS:
- INSERT_INSTRUMENT 3 VSTi: Analog Lab V (Arturia)
- Use bass notes (C2=36, D2=38, etc.) MATCHING YOUR KEY!

"""

    prompt = f"""You are composing music in a DAW. Read what the user wants and create it.

USER REQUEST: "{user_input}"

=== TRACK LAYOUT ===
- Tracks 0-1: Melody/Chords (recommended)
- Tracks 2+: Drums/Bass/Percussion (flexible - use as many as needed)

=== COMMANDS ===

SET_TEMPO [bpm] - Set project tempo

FOR MELODY/CHORDS - Use INSERT_INSTRUMENT (VSTi ONLY):
- INSERT_INSTRUMENT [track] [Instrument Name]
  * MUST be an INSTRUMENT plugin (VSTi/VST3i), NOT an effect!
  
AVAILABLE INSTRUMENTS (Top selection):
{INSTRUMENT_LIST_STR}
(And others installed on the system)

- MIDI_CREATE_ITEM [track] [start] [end]
- MIDI_INSERT_NOTE [track] [pitch] [velocity] [start] [end]

{drum_info}
AUTOMATION:
- VOL_DIP [track] [start] [end] [volume_0_to_1]

MIDI PITCH: C3=48, C4=60, C5=72 (add 2=D, 4=E, 5=F, 7=G, 9=A, 11=B)
TIMING: beat = 60/BPM seconds

STRUCTURE (follow this EXACT order):
1. SET_TEMPO [bpm]
2. INSERT_INSTRUMENT / LOAD_SAMPLER for all tracks
3. MIDI_CREATE_ITEM for ALL tracks
4. MIDI_INSERT_NOTE for ALL tracks
5. VOL_DIP automation (optional)

Generate 1+ minute of music. Output ONLY commands, one per line.
ALL tracks need MIDI items and notes - samplers are triggered by MIDI!"""

    print(f"🎵 Claude composing: \"{user_input}\"")
    if DRUM_SAMPLES_AVAILABLE:
        print(f"   🥁 Real drum samples enabled!")
    
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
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
        model="claude-sonnet-4-5-20250929",
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
        model="claude-sonnet-4-5-20250929",
        max_tokens=200,
        temperature=0,
        messages=[{"role": "user", "content": f"Fix typos: \"{user_input}\"\nOutput only the fixed text:"}]
    ).content[0].text.strip().strip('"\'')
    return response


def enhance_prompt(user_input, reaper_state="", midi_notes=None):
    """Route to song generation, compose-around, or agentic mode."""
    mode = classify_request(user_input)
    
    if mode == "song_generation":
        print(f"🎵 SONG MODE - Creating from scratch")
        return generate_song_commands(user_input)
    elif mode == "compose_around":
        print(f"🎼 COMPOSE AROUND MODE - Building on existing MIDI")
        return generate_compose_around_commands(user_input, midi_notes)
    else:
        print(f"🎛️ AGENTIC MODE - Mixing/effects")
        return enhance_simple_prompt(user_input)


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
