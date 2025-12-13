"""
Drum Index - ID-based sample lookup.
Cloud picks by ID, bridge resolves to full path.
"""

import os
import json
from pathlib import Path

INDEX_FILE = os.path.join(os.path.dirname(__file__), "drum_index.json")

CATEGORIES = {
    "kick": ["kick", "kik", "bd"],
    "snare": ["snare", "snr", "sd", "rim"],
    "hihat": ["hihat", "hi-hat", "hat", "hh", "chh", "ohh"],
    "808": ["808"],
    "clap": ["clap", "clp"],
    "perc": ["perc", "tom", "shaker", "tamb"],
}


def build_index(root_path="F:\\", max_per_category=30):
    """Build ID-based index. Limited samples per category to keep cloud prompt small."""
    print(f"[SCAN] Building drum index from {root_path}...")
    
    extensions = {'.wav', '.mp3'}
    index = {"samples": {}, "by_category": {cat: [] for cat in CATEGORIES}}
    sample_id = 1
    
    for path in Path(root_path).rglob('*'):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        
        name_lower = path.stem.lower()
        
        for cat, keywords in CATEGORIES.items():
            if len(index["by_category"][cat]) >= max_per_category:
                continue
            
            if any(kw in name_lower for kw in keywords):
                # Store sample
                index["samples"][str(sample_id)] = {
                    "name": path.stem,
                    "path": str(path),
                    "category": cat
                }
                index["by_category"][cat].append(sample_id)
                sample_id += 1
                break
    
    # Save
    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)
    
    # Summary
    total = len(index["samples"])
    print(f"\n[DONE] Index built: {total} samples")
    for cat, ids in index["by_category"].items():
        if ids:
            print(f"   {cat}: {len(ids)} samples")
    
    print(f"[SAVED] {INDEX_FILE}")
    return index


def load_index():
    """Load index from file."""
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r') as f:
            return json.load(f)
    return None


def get_path_by_id(sample_id):
    """Get full file path by sample ID."""
    index = load_index()
    if not index:
        return None
    
    sample = index["samples"].get(str(sample_id))
    if sample:
        return sample["path"]
    return None


def get_cloud_summary():
    """
    Compact summary for Claude to pick samples.
    Format: CATEGORY: [id]name, [id]name, ...
    """
    index = load_index()
    if not index:
        return "No drum index. Run: python drum_index.py F:\\"
    
    lines = []
    for cat, ids in index["by_category"].items():
        if not ids:
            continue
        
        samples = []
        for sid in ids[:15]:  # Max 15 per category for cloud
            s = index["samples"].get(str(sid))
            if s:
                # Short name (max 20 chars)
                short_name = s["name"][:20]
                samples.append(f"[{sid}]{short_name}")
        
        if samples:
            lines.append(f"{cat.upper()}: {', '.join(samples)}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "F:\\"
    build_index(path)
    
    print("\n" + "="*50)
    print("CLOUD SUMMARY (send this to Claude):")
    print("="*50)
    print(get_cloud_summary())
