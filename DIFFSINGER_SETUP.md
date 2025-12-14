# DiffSinger Integration Guide

This guide explains how to use your trained DiffSinger model to generate vocals for full songs.

## Overview

The system now supports **local DiffSinger inference**, meaning you can generate vocals directly on your machine once your model finishes training.

## Setup Steps

### 1. Install Phoneme Converter (Required)

You need a text-to-phoneme converter for English. Choose one:

**Option A: espeak-ng (Recommended)**
```bash
pip install espeak-ng
```

**Option B: g2p-en**
```bash
pip install g2p-en
```

### 2. Train Your DiffSinger Model

Train your acoustic model following DiffSinger's training guide. Your model will be saved in:
```
DiffSinger/checkpoints/YOUR_EXPERIMENT_NAME/
```

### 3. Find Your Experiment Name

After training, your checkpoint folder will be named something like:
- `DiffSinger/checkpoints/my_vocal_model/`
- `DiffSinger/checkpoints/acoustic_20250101/`

The folder name is your **experiment_name**.

### 4. Generate Vocals

#### Using Python API:

```python
from prompt_enhancer import generate_vocals_for_beat

vocals = generate_vocals_for_beat(
    beat_commands=your_beat_commands,
    topic="heartbreak",
    mood="emotional",
    experiment_name="my_vocal_model",  # Your trained model name
    use_local=True
)

# Check result
if vocals['synthesis_result']['status'] == 'success':
    audio_path = vocals['synthesis_result']['audio_path']
    print(f"✅ Generated vocals: {audio_path}")
```

#### Using HTTP API:

```bash
curl -X POST http://localhost:5000/api/vocals/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "heartbreak",
    "mood": "emotional",
    "beat_prompt": "dark R&B beat",
    "experiment_name": "my_vocal_model",
    "use_local": true
  }'
```

#### Generate Full Song:

```python
from prompt_enhancer import generate_full_song

result = generate_full_song(
    "dark R&B about heartbreak",
    experiment_name="my_vocal_model",
    use_local=True
)
```

## How It Works

1. **Lyrics Generation**: Claude generates lyrics based on topic/mood
2. **Melody Generation**: Claude creates MIDI melody notes
3. **Phoneme Conversion**: Text → phonemes (using espeak/g2p)
4. **F0 Generation**: MIDI pitches → F0 curves
5. **.ds File Creation**: Format data into DiffSinger's `.ds` format
6. **Inference**: Run DiffSinger locally to generate audio

## File Structure

```
your_project/
├── diffsinger_integration.py  # Core integration module
├── prompt_enhancer.py          # Updated with local inference
├── temp_audio/
│   └── vocals_*.ds            # Generated .ds files
│   └── output/
│       └── *.wav              # Generated audio
└── DiffSinger/
    └── checkpoints/
        └── YOUR_EXPERIMENT_NAME/  # Your trained model
```

## Troubleshooting

### "No phoneme converter found"
Install espeak-ng or g2p-en (see Step 1)

### "Experiment not found"
- Check that your model folder exists in `DiffSinger/checkpoints/`
- Use the exact folder name as `experiment_name`
- The script will auto-match prefixes (e.g., "my" matches "my_vocal_model")

### "Model checkpoint not found"
- Ensure training completed successfully
- Check for `model_ckpt_steps_*.ckpt` files in your experiment folder
- Specify `checkpoint_steps` if you want a specific checkpoint

### Phoneme quality issues
The basic phoneme converter is approximate. For production:
- Use espeak-ng for better accuracy
- Consider training with a phoneme dictionary
- Manually review/edit `.ds` files if needed

## Next Steps

1. **Test with a simple song**: Generate a short test song to verify everything works
2. **Tune phoneme conversion**: Adjust phoneme mapping if needed
3. **Optimize F0 curves**: Fine-tune vibrato and pitch curves
4. **Batch processing**: Process multiple songs in sequence

## API Reference

### `generate_vocals_for_beat()`
```python
generate_vocals_for_beat(
    beat_commands: str,
    topic: str,
    mood: str,
    runpod_endpoint: Optional[str] = None,
    experiment_name: Optional[str] = None,
    use_local: bool = True
) -> Dict
```

### `synthesize_vocals_local()` (from diffsinger_integration)
```python
synthesize_vocals_local(
    lyrics: str,
    melody_data: List[Dict],
    tempo: float,
    experiment_name: str,
    output_path: Optional[str] = None,
    checkpoint_steps: Optional[int] = None
) -> str  # Returns audio file path
```

## Notes

- Local inference requires GPU for reasonable speed (CPU works but is slow)
- `.ds` files are saved in `temp_audio/` for debugging
- Generated audio is saved in `temp_audio/output/`
- The system falls back to RunPod API if local inference fails




