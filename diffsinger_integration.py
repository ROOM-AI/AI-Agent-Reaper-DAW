"""
DiffSinger Integration - Convert lyrics + melody to .ds format and run inference locally
"""

import json
import pathlib
import numpy as np
from typing import List, Dict, Optional
import subprocess
import sys

# Try to import espeak for phoneme conversion
try:
    import espeak_phonemizer
    ESPEAK_AVAILABLE = True
except ImportError:
    ESPEAK_AVAILABLE = False
    try:
        # Try alternative: g2p library
        from g2p_en import G2p
        g2p = G2p()
        G2P_AVAILABLE = True
    except ImportError:
        G2P_AVAILABLE = False
        print("⚠️ Warning: No phoneme converter found. Install 'espeak-ng' or 'g2p-en'")
        print("   For espeak: pip install espeak-ng")
        print("   For g2p: pip install g2p-en")


def midi_to_hz(midi_note: int) -> float:
    """Convert MIDI note number to frequency in Hz"""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def text_to_phonemes(text: str) -> List[str]:
    """
    Convert English text to phonemes.
    Returns list of phonemes in ARPABET-like format.
    
    Note: DiffSinger expects phonemes that match your training dictionary.
    If you trained with a specific phoneme set, ensure this matches.
    """
    if ESPEAK_AVAILABLE:
        try:
            phonemes = espeak_phonemizer.phonemize(text, language='en-us', backend='espeak')
            # Convert espeak format to ARPABET-like
            # espeak uses SAMPA format, may need conversion
            return phonemes.strip().split()
        except Exception as e:
            print(f"⚠️ espeak error: {e}")
    
    if G2P_AVAILABLE:
        try:
            phonemes = g2p(text)
            # g2p returns ARPABET format directly
            return phonemes
        except Exception as e:
            print(f"⚠️ g2p error: {e}")
    
    # Fallback: Very basic approximation
    # WARNING: This is NOT accurate - install espeak-ng or g2p-en for production
    print("⚠️ Using fallback phoneme converter - results will be poor!")
    print("   Install 'espeak-ng' or 'g2p-en' for proper phoneme conversion")
    
    words = text.lower().strip().split()
    if not words:
        return ['SP']
    
    phonemes = []
    for word in words:
        # Very rough approximation - one phoneme per syllable estimate
        # This is a placeholder - NOT production-ready
        syllable_count = max(1, len([c for c in word if c in 'aeiou']) or 1)
        for _ in range(syllable_count):
            phonemes.append('AH')  # Generic vowel placeholder
    
    return phonemes if phonemes else ['SP']


def generate_f0_curve(midi_pitch: int, duration_seconds: float, timestep: float = 0.005) -> List[float]:
    """
    Generate F0 curve for a note.
    
    Args:
        midi_pitch: MIDI note number
        duration_seconds: Duration in seconds
        timestep: F0 timestep (default 0.005s = 200Hz)
    
    Returns:
        List of F0 values in Hz
    """
    base_f0 = midi_to_hz(midi_pitch)
    num_frames = int(duration_seconds / timestep)
    
    # Generate smooth F0 curve with slight vibrato
    f0_curve = []
    for i in range(num_frames):
        t = i * timestep
        # Add slight vibrato (2-3 Hz variation at ~5Hz rate)
        vibrato = 1.0 + 0.01 * np.sin(2 * np.pi * 5.0 * t)
        f0 = base_f0 * vibrato
        f0_curve.append(f0)
    
    return f0_curve


def create_ds_segment(
    lyrics: str,
    melody_data: List[Dict],
    tempo: float,
    offset: float = 0.0
) -> Dict:
    """
    Create a .ds file segment from lyrics and melody.
    
    Args:
        lyrics: Full lyrics text
        melody_data: List of dicts with 'pitch', 'duration_beats', 'syllable'
        tempo: Tempo in BPM
        offset: Time offset in seconds
    
    Returns:
        Dictionary representing one .ds segment
    """
    if not melody_data:
        print("⚠️ Warning: Empty melody data")
        return None
    
    pitch_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    beat_duration = 60.0 / tempo
    
    # Build note sequences
    note_seq = []
    note_dur = []
    note_slur = []
    phonemes = []
    phoneme_durations = []
    phoneme_nums = []
    f0_seq = []
    
    f0_timestep = 0.005
    
    # Add initial pause
    phonemes.append('AP')
    phoneme_durations.append('0.5')
    
    # Generate F0 for initial pause
    pause_f0 = [f"{117.0:.1f}"] * int(0.5 / f0_timestep)
    f0_seq.extend(pause_f0)
    
    # Process each note
    for i, note in enumerate(melody_data):
        pitch = note.get('pitch', 60)
        duration_beats = note.get('duration_beats', 1.0)
        syllable = note.get('syllable', '').strip()
        
        if not syllable:
            syllable = 'la'  # Fallback syllable
        
        duration_sec = duration_beats * beat_duration
        
        # Convert MIDI to note name
        octave = pitch // 12 - 1
        note_name = pitch_names[pitch % 12]
        note_seq.append(f"{note_name}{octave}")
        note_dur.append(f"{duration_beats:.3f}")
        note_slur.append("0")
        
        # Generate phonemes for this syllable
        word_phonemes = text_to_phonemes(syllable)
        if not word_phonemes:
            word_phonemes = ['AH']  # Fallback phoneme
        
        num_phonemes = len(word_phonemes)
        
        # Distribute duration across phonemes
        ph_dur_per_phoneme = duration_sec / num_phonemes
        
        for ph in word_phonemes:
            phonemes.append(ph)
            phoneme_durations.append(f"{ph_dur_per_phoneme:.4f}")
        
        # Track phoneme count per note (for ph_num)
        phoneme_nums.append(str(num_phonemes))
        
        # Generate F0 curve for this note
        f0_curve = generate_f0_curve(pitch, duration_sec, f0_timestep)
        f0_seq.extend([f"{f0:.1f}" for f0 in f0_curve])
    
    # Add final pause
    phonemes.append('SP')
    phoneme_durations.append('0.4')
    
    # F0 for final pause
    final_pause_f0 = [f"{117.0:.1f}"] * int(0.4 / f0_timestep)
    f0_seq.extend(final_pause_f0)
    
    # Add rests for pauses
    note_seq = ['rest'] + note_seq + ['rest']
    note_dur = ['0.5'] + note_dur + ['0.4']
    note_slur = ['0'] + note_slur + ['0']
    phoneme_nums = ['1'] + phoneme_nums + ['1']
    
    # Build text representation
    text_parts = ['AP'] + [note.get('syllable', 'la') for note in melody_data] + ['SP']
    text = ' '.join(text_parts)
    
    print(f"✅ Created .ds segment:")
    print(f"   - {len(note_seq)} notes")
    print(f"   - {len(phonemes)} phonemes")
    print(f"   - {len(f0_seq)} F0 frames ({len(f0_seq) * f0_timestep:.2f}s)")
    
    return {
        "offset": offset,
        "text": text,
        "ph_seq": ' '.join(phonemes),
        "ph_dur": ' '.join(phoneme_durations),
        "ph_num": ' '.join(phoneme_nums),
        "note_seq": ' '.join(note_seq),
        "note_dur": ' '.join(note_dur),
        "note_slur": ' '.join(note_slur),
        "f0_seq": ' '.join(f0_seq),
        "f0_timestep": str(f0_timestep)
    }


def create_ds_file(
    lyrics: str,
    melody_data: List[Dict],
    tempo: float,
    output_path: str
) -> str:
    """
    Create a .ds file from lyrics and melody.
    
    Args:
        lyrics: Full lyrics text
        melody_data: List of dicts with 'pitch', 'duration_beats', 'syllable'
        tempo: Tempo in BPM
        output_path: Path to save .ds file
    
    Returns:
        Path to created .ds file
    """
    print(f"\n📝 Creating .ds file from {len(melody_data)} notes at {tempo} BPM")
    
    segment = create_ds_segment(lyrics, melody_data, tempo)
    
    if segment is None:
        raise ValueError("Failed to create .ds segment - check melody data")
    
    ds_data = [segment]
    
    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ds_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved .ds file: {output_path}")
    print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB")
    
    return str(output_path)


def run_diffsinger_inference(
    ds_file_path: str,
    experiment_name: str,
    output_dir: Optional[str] = None,
    checkpoint_steps: Optional[int] = None,
    device: str = "cuda"
) -> str:
    """
    Run DiffSinger inference locally.
    
    Args:
        ds_file_path: Path to .ds file
        experiment_name: Name of the trained model experiment
        output_dir: Output directory (default: temp_audio/output)
        checkpoint_steps: Specific checkpoint steps (optional)
        device: Device to use ('cuda' or 'cpu')
    
    Returns:
        Path to generated audio file
    """
    ds_path = pathlib.Path(ds_file_path)
    if not ds_path.exists():
        raise FileNotFoundError(f".ds file not found: {ds_file_path}")
    
    if output_dir is None:
        output_dir = pathlib.Path("temp_audio/output")
    else:
        output_dir = pathlib.Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if experiment exists
    exp_path = pathlib.Path("DiffSinger/checkpoints") / experiment_name
    if not exp_path.exists():
        raise FileNotFoundError(
            f"Experiment not found: {exp_path}\n"
            f"Available experiments: {[p.name for p in pathlib.Path('DiffSinger/checkpoints').iterdir() if p.is_dir()]}"
        )
    
    # Build inference command
    cmd = [
        sys.executable,
        "DiffSinger/scripts/infer.py",
        "acoustic",
        str(ds_path.absolute()),
        "--exp", experiment_name,
        "--out", str(output_dir.absolute()),
        "--title", ds_path.stem
    ]
    
    if checkpoint_steps:
        cmd.extend(["--ckpt", str(checkpoint_steps)])
    
    print(f"\n🎤 Running DiffSinger inference...")
    print(f"   Experiment: {experiment_name}")
    print(f"   Input: {ds_path}")
    print(f"   Output dir: {output_dir}")
    print(f"   Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=pathlib.Path(__file__).parent,
            capture_output=True,
            text=True,
            check=True,
            timeout=300  # 5 minute timeout
        )
        
        # Print stdout for debugging
        if result.stdout:
            print("DiffSinger output:")
            print(result.stdout)
        
        # Find output file
        output_file = output_dir / f"{ds_path.stem}.wav"
        if output_file.exists():
            file_size = output_file.stat().st_size / 1024  # KB
            print(f"\n✅ Generated vocal audio: {output_file}")
            print(f"   Size: {file_size:.1f} KB")
            return str(output_file)
        else:
            # List what files were created
            created_files = list(output_dir.glob("*.wav"))
            print(f"Output file not found: {output_file}")
            print(f"Files in output dir: {created_files}")
            if created_files:
                return str(created_files[0])  # Return first wav found
            raise FileNotFoundError(f"No WAV output generated")
            
    except subprocess.TimeoutExpired:
        print(f"❌ DiffSinger inference timed out (>5 minutes)")
        raise
    except subprocess.CalledProcessError as e:
        print(f"❌ DiffSinger inference failed:")
        print(f"   Return code: {e.returncode}")
        if e.stdout:
            print(f"   stdout: {e.stdout}")
        if e.stderr:
            print(f"   stderr: {e.stderr}")
        raise


def synthesize_vocals_local(
    lyrics: str,
    melody_data: List[Dict],
    tempo: float,
    experiment_name: str,
    output_path: Optional[str] = None,
    checkpoint_steps: Optional[int] = None
) -> str:
    """
    Complete pipeline: lyrics + melody → .ds file → audio.
    
    Args:
        lyrics: Full lyrics text
        melody_data: List of dicts with 'pitch', 'duration_beats', 'syllable'
        tempo: Tempo in BPM
        experiment_name: Name of trained DiffSinger model
        output_path: Optional path for .ds file (auto-generated if None)
        checkpoint_steps: Optional checkpoint steps
    
    Returns:
        Path to generated audio file
    """
    # Create .ds file
    if output_path is None:
        output_path = f"temp_audio/vocals_{experiment_name}.ds"
    
    ds_file = create_ds_file(lyrics, melody_data, tempo, output_path)
    
    # Run inference
    audio_file = run_diffsinger_inference(
        ds_file,
        experiment_name,
        checkpoint_steps=checkpoint_steps
    )
    
    return audio_file

