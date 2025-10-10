"""
Filter the exported actions to create a bite-sized, useful action list
Removes noise and keeps only relevant commands
"""

import re

INPUT_FILE = r"C:\Users\moosb\AIAGENT DAW\lol reaper_actions_good.txt"
OUTPUT_FILE = r"C:\Users\moosb\AIAGENT DAW\reaper_actions_filtered.txt"

def is_useful_action(action_id, description):
    """Determine if an action is useful enough to keep"""
    
    # Skip header lines
    if not action_id or action_id.startswith("REAPER") or action_id.startswith("Format"):
        return False
    
    # Keep all numeric action IDs (core Reaper actions)
    if action_id.isdigit():
        return True
    
    # Keep _SWS actions (SWS extension - very useful)
    if action_id.startswith("_SWS"):
        return True
    
    # Keep _XENAKIOS actions (also SWS)
    if action_id.startswith("_XENAKIOS"):
        return True
    
    # Keep _BR_ actions (SWS extension)
    if action_id.startswith("_BR_"):
        return True
    
    # Keep _OSARA actions (accessibility/screen reader)
    if action_id.startswith("_OSARA"):
        return True
    
    # Keep _FNG actions (Fingers MIDI)
    if action_id.startswith("_FNG"):
        return True
    
    # Keep _S&M actions (SWS)
    if action_id.startswith("_S&M"):
        return True
    
    # Keep _RS actions that have good descriptions (useful custom scripts)
    if action_id.startswith("_RS"):
        # Keep if description doesn't look like a hash
        if len(description) > 5 and not re.match(r'^RS[a-f0-9]{40}', action_id):
            return True
    
    # Skip random ReaScript hashes (RSxxxxxxxxxxxx...)
    if re.match(r'^RS[a-f0-9]{40}', action_id):
        return False
    
    # Keep named custom actions
    if action_id.startswith("_") and "Script:" not in description:
        return True
    
    # Default: skip
    return False

def filter_actions():
    """Read full action list and create filtered version"""
    
    print(f"Reading from: {INPUT_FILE}")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ File not found: {INPUT_FILE}")
        print("Make sure the export script finished running first!")
        return
    
    print(f"📚 Read {len(lines)} lines")
    
    filtered = []
    kept = 0
    skipped = 0
    
    for line in lines:
        line = line.strip()
        if not line or '|' not in line:
            continue
        
        parts = line.split('|', 1)
        if len(parts) != 2:
            continue
        
        action_id = parts[0].strip()
        description = parts[1].strip()
        
        if is_useful_action(action_id, description):
            filtered.append(f"{action_id}|{description}")
            kept += 1
        else:
            skipped += 1
    
    print(f"\n✅ Kept: {kept} actions")
    print(f"❌ Skipped: {skipped} actions")
    print(f"📊 Reduction: {100 - (kept/len(lines)*100):.1f}%")
    
    # Write filtered list
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("REAPER FILTERED ACTIONS - Bite-Sized List\n")
        f.write("Format: ActionID|Description\n\n")
        for line in filtered:
            f.write(line + '\n')
    
    print(f"\n💾 Saved to: {OUTPUT_FILE}")
    print(f"\nSample actions:")
    for line in filtered[:20]:
        print(f"  {line}")

if __name__ == "__main__":
    filter_actions()

