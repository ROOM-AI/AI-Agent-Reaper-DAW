"""
Drum Scanner - Scans folders for drum samples and categorizes them.
Claude can then pick samples by category/description.
"""

import os
import json
import random
from pathlib import Path

# Where to cache the sample catalog
CATALOG_PATH = os.path.join(os.path.dirname(__file__), "drum_catalog.json")

# Keywords for categorization
CATEGORIES = {
    "kick": ["kick", "kik", "kck", "bd", "bass drum", "bassdrum"],
    "snare": ["snare", "snr", "sd", "rimshot", "rim"],
    "clap": ["clap", "clp", "handclap"],
    "hihat": ["hihat", "hi-hat", "hi hat", "hh", "hat", "closed hat", "open hat", "chh", "ohh"],
    "808": ["808", "sub", "bass", "low"],
    "perc": ["perc", "percussion", "conga", "bongo", "shaker", "tambourine", "tom", "cymbal", "crash", "ride"],
    "fx": ["fx", "effect", "riser", "impact", "downlifter", "uplifter", "transition"],
    "loop": ["loop", "break", "drum loop", "beat"],
}


def categorize_sample(filename):
    """Determine category from filename."""
    name_lower = filename.lower()
    
    # Check each category
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category
    
    return "other"


def scan_drums(root_path, max_depth=5):
    """
    Recursively scan for drum samples.
    Returns dict of category -> list of sample paths.
    """
    print(f"🔍 Scanning {root_path} for drum samples...")
    
    catalog = {cat: [] for cat in CATEGORIES.keys()}
    catalog["other"] = []
    
    extensions = {'.wav', '.mp3', '.aiff', '.flac', '.ogg'}
    count = 0
    
    root = Path(root_path)
    
    for path in root.rglob('*'):
        # Skip if too deep
        try:
            depth = len(path.relative_to(root).parts)
            if depth > max_depth:
                continue
        except:
            continue
        
        # Check if it's an audio file
        if path.is_file() and path.suffix.lower() in extensions:
            category = categorize_sample(path.stem)
            catalog[category].append(str(path))
            count += 1
            
            if count % 500 == 0:
                print(f"   Found {count} samples...")
    
    # Print summary
    print(f"\n📊 Scan complete! Found {count} samples:")
    for cat, samples in catalog.items():
        if samples:
            print(f"   {cat}: {len(samples)} samples")
    
    return catalog


def save_catalog(catalog):
    """Save catalog to JSON file."""
    with open(CATALOG_PATH, 'w') as f:
        json.dump(catalog, f, indent=2)
    print(f"💾 Saved catalog to {CATALOG_PATH}")


def load_catalog():
    """Load catalog from JSON file."""
    if os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH, 'r') as f:
            return json.load(f)
    return None


def get_sample(category, description=None):
    """
    Get a sample from a category.
    If description provided, try to match it.
    """
    catalog = load_catalog()
    if not catalog:
        print("⚠️ No drum catalog found! Run scan_and_save() first.")
        return None
    
    samples = catalog.get(category, [])
    if not samples:
        print(f"⚠️ No samples found for category: {category}")
        return None
    
    if description:
        # Try to find samples matching description
        desc_lower = description.lower()
        matches = [s for s in samples if desc_lower in s.lower()]
        if matches:
            return random.choice(matches)
    
    # Random sample from category
    return random.choice(samples)


def get_samples_for_kit(kit_request=None):
    """
    Get a complete drum kit (kick, snare, hihat, 808, clap, perc).
    Optionally tries to match a style description.
    """
    catalog = load_catalog()
    if not catalog:
        return None
    
    kit = {}
    
    # Get one sample per main category
    main_categories = ["kick", "snare", "hihat", "808", "clap", "perc"]
    
    for cat in main_categories:
        samples = catalog.get(cat, [])
        if samples:
            if kit_request:
                # Try to match request
                req_lower = kit_request.lower()
                matches = [s for s in samples if any(word in s.lower() for word in req_lower.split())]
                if matches:
                    kit[cat] = random.choice(matches)
                else:
                    kit[cat] = random.choice(samples)
            else:
                kit[cat] = random.choice(samples)
    
    return kit


def scan_and_save(root_path="D:\\"):
    """Scan drums and save catalog."""
    catalog = scan_drums(root_path)
    save_catalog(catalog)
    return catalog


def get_catalog_summary():
    """Get a summary of the catalog for Claude."""
    catalog = load_catalog()
    if not catalog:
        return "No drum catalog available. Scan needed."
    
    summary = []
    for cat, samples in catalog.items():
        if samples:
            # Get some example names
            examples = [Path(s).stem for s in random.sample(samples, min(3, len(samples)))]
            summary.append(f"{cat} ({len(samples)} samples): {', '.join(examples)}")
    
    return "\n".join(summary)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "D:\\"
    
    print(f"Scanning: {path}")
    catalog = scan_and_save(path)
    
    print("\n\n--- Testing sample retrieval ---")
    print(f"Random kick: {get_sample('kick')}")
    print(f"Random snare: {get_sample('snare')}")
    print(f"Random 808: {get_sample('808')}")
    
    print("\n--- Full kit ---")
    kit = get_samples_for_kit()
    for cat, path in kit.items():
        print(f"{cat}: {Path(path).name}")

