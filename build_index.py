import json
from collections import defaultdict

# Load all actions
actions = {}
line_count = 0
file_path = "lol reaper_actions_good.txt"

print(f"Opening: {file_path}")

try:
    with open(file_path, 'rb') as f:
        raw = f.read()
        print(f"File size: {len(raw)} bytes")
except Exception as e:
    print(f"Error reading file: {e}")

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        line_count += 1
        line = line.strip()
        
        # Skip header and empty lines
        if not line or line.startswith('REAPER') or line.startswith('Format:') or line.startswith('Generated:'):
            continue
            
        if '|' in line:
            parts = line.split('|', 1)
            if len(parts) == 2:
                action_id = parts[0].strip()
                description = parts[1].strip()
                actions[action_id] = description

print(f'Read {line_count} total lines')
print(f'Loaded {len(actions)} actions')

# Build flat searchable index
index = {}
stop_words = {'a', 'an', 'and', 'or', 'the', 'to', 'for', 'in', 'on', 'of', 'with', 'at', 'by', 'from', 'is'}

for action_id, desc in actions.items():
    # Create searchable key from description
    # Convert "Track: Toggle solo for track 01" -> "track_toggle_solo_track_01"
    key_parts = desc.lower()
    # Remove parentheses content
    if '(' in key_parts:
        key_parts = key_parts.split('(')[0]
    
    # Replace special chars with underscores
    key_parts = key_parts.replace(':', ' ').replace('/', ' ').replace(',', ' ')
    key_parts = key_parts.replace('-', '_').replace('.', '_')
    
    # Split into words and filter
    words = [w.strip() for w in key_parts.split() if w.strip() and w.strip() not in stop_words]
    
    # Join with underscore
    search_key = '_'.join(words[:8])  # Limit to 8 words for readability
    
    # Store action
    index[search_key] = {
        'id': action_id,
        'desc': desc
    }

print(f'Built index with {len(index)} actions')

# Save index
with open('action_index.json', 'w', encoding='utf-8') as f:
    json.dump(index, f, indent=2)

print('Saved to action_index.json')

# Show sample
print('\nSample entries:')
for i, (key, action_data) in enumerate(list(index.items())[:10]):
    print(f'  {key}: {action_data["id"]} - {action_data["desc"][:60]}...')
