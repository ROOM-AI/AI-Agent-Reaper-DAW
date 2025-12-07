"""
Combine all cached lyrics JSON files into one TXT file
"""
import json
from pathlib import Path

LYRICS_CACHE_DIR = Path(__file__).parent / "lyrics_cache"
OUTPUT_FILE = Path(__file__).parent / "all_lyrics.txt"

def combine_lyrics():
    all_lyrics = []
    
    # Get all JSON files sorted by name
    json_files = sorted(LYRICS_CACHE_DIR.glob("*.json"))
    
    print(f"Found {len(json_files)} lyrics files")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            track_name = data.get("track_name", json_file.stem)
            lyrics = data.get("lyrics", [])
            
            # Build lyrics text
            track_text = f"\n{'='*60}\n"
            track_text += f"TRACK: {track_name}\n"
            track_text += f"{'='*60}\n\n"
            
            if lyrics:
                # Full lyrics with timestamps
                track_text += "Word-by-word timestamps:\n"
                track_text += "-" * 40 + "\n"
                for word_data in lyrics:
                    word = word_data.get("word", "")
                    start = word_data.get("start", 0)
                    end = word_data.get("end", 0)
                    track_text += f"[{start:6.2f}s - {end:6.2f}s] {word}\n"
                
                # Also add plain text version
                track_text += "\n" + "-" * 40 + "\n"
                track_text += "Plain text:\n"
                track_text += "-" * 40 + "\n"
                plain_words = [w.get("word", "") for w in lyrics]
                track_text += " ".join(plain_words) + "\n"
                
                track_text += f"\nTotal words: {len(lyrics)}\n"
            else:
                track_text += "(No lyrics found)\n"
            
            all_lyrics.append(track_text)
            print(f"[OK] {track_name}: {len(lyrics)} words")
            
        except Exception as e:
            print(f"[ERR] Error reading {json_file.name}: {e}")
    
    # Write combined file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("ALL LYRICS - Combined Export\n")
        f.write(f"Generated from {len(json_files)} tracks\n")
        f.write("=" * 60 + "\n")
        f.write("\n".join(all_lyrics))
    
    print(f"\n[DONE] Combined lyrics saved to: {OUTPUT_FILE}")
    print(f"   Total tracks: {len(json_files)}")

if __name__ == "__main__":
    combine_lyrics()

