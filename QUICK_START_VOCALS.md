# Quick Start: Generate Full Songs with Vocals

## What Changed

✅ **Vocal melody now sees the beat style** - Claude generates melody that matches your instrumental  
✅ **Proper .ds file generation** - Correct format for DiffSinger  
✅ **Full pipeline** - Lyrics → Melody → .ds → Audio  
✅ **Better error handling** - Clear messages if something fails  

## How to Use

### 1. Test the Pipeline

```bash
# Install phoneme converter first
pip install g2p-en

# Test with your trained model
python test_vocals.py YOUR_EXPERIMENT_NAME
```

This will:
- Generate test lyrics + melody
- Create a .ds file
- Run DiffSinger inference
- Output vocal audio in `temp_audio/output/`

### 2. Generate Full Song

```python
from prompt_enhancer import generate_full_song

result = generate_full_song(
    "dark R&B about heartbreak at 140 BPM",
    experiment_name="YOUR_EXPERIMENT_NAME",
    use_local=True
)

# Check result
vocals = result['vocals']
if vocals['synthesis_result']['status'] == 'success':
    audio_path = vocals['synthesis_result']['audio_path']
    print(f"Vocals ready: {audio_path}")
```

### 3. Via API

```bash
curl -X POST http://localhost:5000/api/vocals/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "heartbreak",
    "mood": "dark and emotional",
    "beat_prompt": "140 BPM R&B with 808 bass",
    "experiment_name": "YOUR_EXPERIMENT_NAME",
    "use_local": true
  }'
```

## File Outputs

Generated files are saved in:
- `.ds files`: `temp_audio/test_vocals.ds`
- `Vocal WAV`: `temp_audio/output/test_vocals.wav`
- `Instrumental`: (your existing Reaper output)

## Next Step: Mix Vocals + Instrumental

Once you have:
- Instrumental audio (from Reaper)
- Vocal audio (from DiffSinger)

Mix them together:

```python
from pydub import AudioSegment

# Load both tracks
instrumental = AudioSegment.from_wav("instrumental.wav")
vocals = AudioSegment.from_wav("temp_audio/output/vocals.wav")

# Simple mix (adjust volumes as needed)
vocals = vocals - 3  # Reduce vocal volume by 3dB
final = instrumental.overlay(vocals)

# Export
final.export("final_song.wav", format="wav")
```

Or import the vocal WAV back into Reaper as a new track.

## Troubleshooting

### "Experiment not found"
- Check folder name in `DiffSinger/checkpoints/`
- Use exact folder name as experiment_name

### "Phoneme converter not found"
```bash
pip install g2p-en
# OR
pip install espeak-ng
```

### "Vocals sound robotic/bad"
- Check if model finished training (120k+ steps recommended)
- Verify training used English data (not Chinese)
- Try adjusting F0 curve generation in `diffsinger_integration.py`

### "Audio file not generated"
- Check DiffSinger logs for errors
- Verify checkpoint files exist in experiment folder
- Check that .ds file was created properly

## What's Next

Once this works:
1. Generate multiple songs to test consistency
2. Adjust vocal FX (reverb, EQ, compression)
3. Fine-tune melody generation prompts
4. Add mixing automation
5. Build a full song generation API endpoint

## Architecture

```
User Prompt
    ↓
Generate Beat (Claude → Reaper commands)
    ↓
Extract Style Info (tempo, key, mood)
    ↓
Generate Lyrics (Claude, aware of style)
    ↓
Generate Melody (Claude, sees style context)  ← NEW: Style-aware
    ↓
Convert to .ds Format (phonemes + F0 curves)
    ↓
DiffSinger Inference (your trained model)
    ↓
Vocal Audio WAV
    ↓
Mix with Instrumental
    ↓
Final Song
```

The key improvement: **Melody generation now receives style context** so it matches the instrumental.




