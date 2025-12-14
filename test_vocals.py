"""
Test script for DiffSinger vocal generation pipeline
Run this to test the full flow: lyrics + melody → .ds file → audio
"""

import sys

def test_vocal_generation(experiment_name="my_model"):
    """
    Test the vocal generation pipeline
    
    Args:
        experiment_name: Your trained DiffSinger model name
    """
    print("=" * 60)
    print("🎤 TESTING DIFFSINGER VOCAL PIPELINE")
    print("=" * 60)
    
    # Test 1: Generate test melody
    print("\n[1/4] Generating test melody...")
    from prompt_enhancer import generate_vocal_melody
    
    test_lyrics = "I can't feel my face when I'm with you"
    test_melody = generate_vocal_melody(
        lyrics=test_lyrics,
        tempo=140,
        key="F#",
        style_context="Dark R&B with deep 808 bass at 140 BPM"
    )
    
    print(f"✅ Generated {len(test_melody)} notes")
    for i, note in enumerate(test_melody[:5]):
        print(f"   Note {i+1}: MIDI {note['pitch']}, {note['duration_beats']:.2f} beats, '{note['syllable']}'")
    
    # Test 2: Create .ds file
    print("\n[2/4] Creating .ds file...")
    from diffsinger_integration import create_ds_file
    
    ds_path = create_ds_file(
        lyrics=test_lyrics,
        melody_data=test_melody,
        tempo=140,
        output_path="temp_audio/test_vocals.ds"
    )
    
    print(f"✅ .ds file created: {ds_path}")
    
    # Test 3: Run DiffSinger inference
    print("\n[3/4] Running DiffSinger inference...")
    print(f"Using experiment: {experiment_name}")
    
    try:
        from diffsinger_integration import run_diffsinger_inference
        
        audio_path = run_diffsinger_inference(
            ds_file_path=ds_path,
            experiment_name=experiment_name,
            output_dir="temp_audio/output"
        )
        
        print(f"✅ Audio generated: {audio_path}")
        
        # Test 4: Verify output
        print("\n[4/4] Verifying output...")
        import pathlib
        audio_file = pathlib.Path(audio_path)
        
        if audio_file.exists():
            size_kb = audio_file.stat().st_size / 1024
            print(f"✅ Audio file exists: {size_kb:.1f} KB")
            
            print("\n" + "=" * 60)
            print("🎉 SUCCESS! Vocal generation pipeline is working!")
            print("=" * 60)
            print(f"\nGenerated files:")
            print(f"  .ds file:  {ds_path}")
            print(f"  Audio WAV: {audio_path}")
            print(f"\nNext steps:")
            print(f"  1. Listen to {audio_path}")
            print(f"  2. If it sounds good, integrate into your DAW")
            print(f"  3. If not, check phoneme conversion or model training")
            
        else:
            print(f"❌ Audio file not found: {audio_path}")
            
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check that your model finished training")
        print("  2. Verify experiment name matches folder in DiffSinger/checkpoints/")
        print("  3. Look for checkpoint files (model_ckpt_steps_*.ckpt)")
        
    except Exception as e:
        print(f"\n❌ Inference failed: {e}")
        print("\nCheck the error above for details.")


if __name__ == "__main__":
    # Get experiment name from command line or use default
    if len(sys.argv) > 1:
        experiment_name = sys.argv[1]
    else:
        print("Usage: python test_vocals.py YOUR_EXPERIMENT_NAME")
        print("\nNo experiment name provided. Checking available experiments...")
        
        import pathlib
        ckpt_dir = pathlib.Path("DiffSinger/checkpoints")
        if ckpt_dir.exists():
            experiments = [p.name for p in ckpt_dir.iterdir() if p.is_dir()]
            if experiments:
                print(f"\nFound experiments: {experiments}")
                experiment_name = experiments[0]
                print(f"Using first experiment: {experiment_name}")
            else:
                print("\n❌ No trained models found in DiffSinger/checkpoints/")
                print("   Train a model first before testing vocals.")
                sys.exit(1)
        else:
            print("\n❌ DiffSinger checkpoints directory not found")
            sys.exit(1)
    
    # Run test
    test_vocal_generation(experiment_name)




