"""
MIDI Foundation Model API Client

Connects to the custom 170M param MIDI model trained on 176K MIDI files (LAKH dataset).
Generates pure MIDI from scratch - no prompts, no control tokens in v1.

The model outputs raw MIDI that gets imported directly into Reaper.
"""

import requests
import base64
import os
import time
import uuid
import io
from typing import Optional, Tuple, List

# Try to import mido for MIDI parsing
try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False
    print("[MIDI_MODEL] mido not installed - track detection disabled")

# Model API endpoint - Lambda Labs GPU server via Serveo tunnel
MIDI_MODEL_URL = os.getenv("MIDI_MODEL_URL", "https://29c6b2f9c285e8a0-192-222-51-140.serveousercontent.com")

# Local directory to save generated MIDI files
MIDI_OUTPUT_DIR = os.getenv("MIDI_OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "generated_midi"))


def check_health() -> bool:
    """Check if the MIDI model server is running and model is loaded."""
    try:
        resp = requests.get(f"{MIDI_MODEL_URL}/health", timeout=30)  # 30s for cold start
        data = resp.json()
        is_healthy = data.get("status") == "healthy" and data.get("model_loaded", False)
        if is_healthy:
            params = data.get("model_params", 0)
            device = data.get("device", "unknown")
            print(f"[MIDI_MODEL] Connected: {params/1e6:.0f}M params on {device}")
        return is_healthy
    except Exception as e:
        print(f"[MIDI_MODEL] Health check failed: {e}")
        return False


def generate_midi(
    max_tokens: int = 2048,
    temperature: float = 0.9,
    top_k: int = 50,
    top_p: float = 0.95,
    seed: Optional[int] = None,
    retries: int = 3
) -> Tuple[bytes, dict]:
    """
    Generate MIDI from the foundation model.
    
    Args:
        max_tokens: Length of generation (1024 ≈ 30sec, 2048 ≈ 1min, 4096 ≈ 2min)
        temperature: Creativity (0.7=safe, 0.9=balanced, 1.1=wild)
        top_k: Sample from top K tokens
        top_p: Nucleus sampling threshold
        seed: Random seed for reproducibility
        retries: Number of retry attempts
    
    Returns:
        Tuple of (midi_bytes, metadata_dict)
    """
    payload = {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_k": top_k,
        "top_p": top_p,
        "output_format": "midi"
    }
    if seed is not None:
        payload["seed"] = seed
    
    last_error = None
    for attempt in range(retries):
        try:
            print(f"[MIDI_MODEL] Generating... (attempt {attempt+1}/{retries}, timeout=300s)")
            resp = requests.post(
                f"{MIDI_MODEL_URL}/generate",
                json=payload,
                timeout=300  # 5 min for long generations
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("success") and data.get("midi_b64"):
                midi_bytes = base64.b64decode(data["midi_b64"])
                metadata = {
                    "num_tokens": data.get("num_tokens", 0),
                    "num_notes": data.get("num_notes", 0),
                    "generation_time_ms": data.get("generation_time_ms", 0),
                }
                return midi_bytes, metadata
            else:
                last_error = data.get("message", "Unknown error")
                
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            print(f"[MIDI_MODEL] Attempt {attempt+1} failed: {e}")
            
        # Wait before retry
        if attempt < retries - 1:
            wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s...
            print(f"[MIDI_MODEL] Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    raise RuntimeError(f"MIDI generation failed after {retries} attempts: {last_error}")


def generate_midi_file(
    output_path: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.9,
    top_k: int = 50,
    top_p: float = 0.95,
    seed: Optional[int] = None
) -> Tuple[str, dict]:
    """
    Generate MIDI and save to a file.
    
    Args:
        output_path: Path to save MIDI file (auto-generated if None)
        max_tokens: Length of generation
        temperature: Creativity level
        top_k: Sample from top K tokens
        top_p: Nucleus sampling threshold
        seed: Random seed
    
    Returns:
        Tuple of (file_path, metadata_dict)
    """
    # Ensure output directory exists
    os.makedirs(MIDI_OUTPUT_DIR, exist_ok=True)
    
    # Generate unique filename if not provided
    if output_path is None:
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(MIDI_OUTPUT_DIR, f"midi_{timestamp}_{unique_id}.mid")
    
    # Generate MIDI
    midi_bytes, metadata = generate_midi(
        max_tokens=max_tokens,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
        seed=seed
    )
    
    # Save to file
    with open(output_path, "wb") as f:
        f.write(midi_bytes)
    
    metadata["file_path"] = output_path
    return output_path, metadata


def count_midi_tracks(midi_bytes: bytes) -> int:
    """Count the number of tracks with notes in a MIDI file."""
    if not MIDO_AVAILABLE:
        return 4  # Default assumption
    
    try:
        midi_file = mido.MidiFile(file=io.BytesIO(midi_bytes))
        tracks_with_notes = 0
        for track in midi_file.tracks:
            has_notes = any(msg.type == 'note_on' and msg.velocity > 0 for msg in track)
            if has_notes:
                tracks_with_notes += 1
        return max(tracks_with_notes, 1)
    except Exception as e:
        print(f"[MIDI_MODEL] Error counting tracks: {e}")
        return 4  # Default


def generate_reaper_commands(
    max_tokens: int = 2048,
    temperature: float = 0.9,
    track: int = 1,
    start_time: float = 0.0
) -> list:
    """
    Generate MIDI and return Reaper commands to import it WITH instruments.
    
    The model generates pure MIDI, so we:
    1. Generate and save the MIDI file
    2. Count tracks in the MIDI
    3. Add INSERT_INSTRUMENT for each track (ReaSynth)
    4. Return INSERT_AUDIO command to import it into Reaper
    
    Args:
        max_tokens: Length of generation
        temperature: Creativity level  
        track: Which Reaper track to start importing to
        start_time: Where to place the MIDI (in seconds)
    
    Returns:
        List of Reaper commands
    """
    # Generate MIDI bytes first (before saving to file)
    midi_bytes, metadata = generate_midi(
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    # Count tracks in the MIDI
    num_tracks = count_midi_tracks(midi_bytes)
    print(f"[MIDI_MODEL] Generated {metadata['num_notes']} notes across {num_tracks} tracks in {metadata['generation_time_ms']}ms")
    
    # Save to file
    os.makedirs(MIDI_OUTPUT_DIR, exist_ok=True)
    timestamp = int(time.time())
    unique_id = uuid.uuid4().hex[:8]
    midi_path = os.path.join(MIDI_OUTPUT_DIR, f"midi_{timestamp}_{unique_id}.mid")
    
    with open(midi_path, "wb") as f:
        f.write(midi_bytes)
    
    # Normalize path for Windows
    midi_path = midi_path.replace('/', '\\')
    
    # Build commands
    commands = []
    
    # 1. Import the MIDI file FIRST (preserves all velocities from foundation model)
    commands.append(f'INSERT_AUDIO {track} "{midi_path}" {start_time}')
    
    # 2. Add instruments AFTER (so they play the MIDI that's now on the tracks)
    for i in range(num_tracks):
        track_num = track + i
        commands.append(f'INSERT_INSTRUMENT {track_num} ReaSynth')
    
    # 3. Add basic FX to each track
    for i in range(num_tracks):
        track_num = track + i
        commands.append(f'ADD_FX {track_num} ReaEQ')
    
    return commands


def generate_multi_track_song(
    max_tokens: int = 4096,
    temperature: float = 0.85,
    num_variations: int = 1
) -> list:
    """
    Generate a complete multi-track song WITH instruments and FX.
    
    The v1 model already generates multi-track MIDI (typically 2-6 tracks).
    This function generates the MIDI, adds instruments, and returns import commands.
    
    Args:
        max_tokens: Length of generation (4096 for longer pieces)
        temperature: Creativity level
        num_variations: Number of different generations to layer
    
    Returns:
        List of Reaper commands
    """
    all_commands = []
    current_track = 1
    
    for i in range(num_variations):
        try:
            # Generate and count tracks
            midi_bytes, metadata = generate_midi(
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            num_tracks = count_midi_tracks(midi_bytes)
            print(f"[MIDI_MODEL] Variation {i+1}: {metadata['num_notes']} notes across {num_tracks} tracks")
            
            # Save to file
            os.makedirs(MIDI_OUTPUT_DIR, exist_ok=True)
            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex[:8]
            midi_path = os.path.join(MIDI_OUTPUT_DIR, f"midi_{timestamp}_{unique_id}.mid")
            
            with open(midi_path, "wb") as f:
                f.write(midi_bytes)
            
            # Normalize path for Windows
            midi_path = midi_path.replace('/', '\\')
            
            # 1. Import MIDI FIRST (preserves velocities)
            all_commands.append(f'INSERT_AUDIO {current_track} "{midi_path}" 0.0')
            
            # 2. Add instruments AFTER
            for t in range(num_tracks):
                track_num = current_track + t
                all_commands.append(f'INSERT_INSTRUMENT {track_num} ReaSynth')
            
            # 3. Add FX
            for t in range(num_tracks):
                track_num = current_track + t
                all_commands.append(f'ADD_FX {track_num} ReaEQ')
            
            # Move to next set of tracks for next variation
            current_track += num_tracks
            
        except Exception as e:
            print(f"[MIDI_MODEL] Variation {i+1} failed: {e}")
    
    return all_commands


# Temperature presets for different styles
TEMPERATURE_PRESETS = {
    "safe": 0.7,
    "balanced": 0.9,
    "creative": 1.0,
    "experimental": 1.2,
}

# Token length presets
LENGTH_PRESETS = {
    "short": 512,      # ~15-20 seconds
    "medium": 1024,    # ~30-45 seconds
    "long": 2048,      # ~1-2 minutes
    "extended": 4096,  # ~2-4 minutes
}


def quick_generate(
    length: str = "medium",
    style: str = "balanced",
    track: int = 1
) -> list:
    """
    Quick generation with presets.
    
    Args:
        length: "short", "medium", "long", or "extended"
        style: "safe", "balanced", "creative", or "experimental"
        track: Reaper track number
    
    Returns:
        List of Reaper commands
    """
    max_tokens = LENGTH_PRESETS.get(length, 1024)
    temperature = TEMPERATURE_PRESETS.get(style, 0.9)
    
    print(f"[MIDI_MODEL] Quick generate: {length} ({max_tokens} tokens), {style} (temp={temperature})")
    
    return generate_reaper_commands(
        max_tokens=max_tokens,
        temperature=temperature,
        track=track
    )


# ============================================================
# Quick test
# ============================================================
if __name__ == "__main__":
    print("Testing MIDI Foundation Model API...")
    print(f"Server: {MIDI_MODEL_URL}")
    
    if check_health():
        print("✅ Model server is healthy and ready")
        
        # Test generation
        print("\nGenerating test MIDI...")
        try:
            commands = generate_reaper_commands(max_tokens=512, temperature=0.9)
            print(f"\nGenerated commands:")
            for cmd in commands:
                print(f"  {cmd}")
        except Exception as e:
            print(f"❌ Generation failed: {e}")
    else:
        print("❌ Model server not reachable or not loaded")
