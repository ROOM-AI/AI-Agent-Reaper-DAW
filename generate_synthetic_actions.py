"""
Generate synthetic action descriptions for Reaper
Based on action ID patterns and common Reaper conventions
"""

def generate_synthetic_actions():
    """Generate clean synthetic action descriptions"""
    
    actions = []
    
    # Transport actions (1000-1050 range)
    transport = {
        1007: "Transport: Play",
        1008: "Transport: Pause",
        1013: "Transport: Record",
        1016: "Transport: Stop",
        1068: "Transport: Rewind",
        1011: "Transport: Fast forward",
        40044: "Transport: Play/stop",
        40073: "Transport: Toggle repeat",
        40043: "Transport: Toggle metronome",
        40317: "Transport: Go to start of project",
        40318: "Transport: Go to end of project",
    }
    actions.extend(transport.items())
    
    # Track actions (40000-41000 range)
    track = {
        40142: "Track: Insert new track",
        40001: "Track: Insert virtual instrument on new track",
        40005: "Track: Remove tracks",
        40280: "Track: Toggle solo for selected tracks",
        40294: "Track: Toggle mute for selected tracks",
        40298: "Track: Set volume for selected tracks",
        40281: "Track: Solo/unsolo tracks",
        40340: "Track: Show FX chain for selected tracks",
        40291: "Track: Toggle FX window for last touched track",
        40293: "Track: Toggle FX bypass for selected tracks",
        40271: "Track: Add FX to selected tracks (opens FX browser)",
        40296: "Track: Select all tracks",
        40297: "Track: Unselect all tracks",
        40285: "Track: Duplicate tracks",
        40421: "Track: Select next track",
        40417: "Track: Select previous track",
        40339: "Track: Unmute all tracks",
        40341: "Track: Unsolo all tracks",
        40290: "Track: Set track panwidth to 100%",
        40406: "Track: Toggle volume envelope visible",
        40407: "Track: Toggle pan envelope visible",
        40420: "Track: Rename last touched track",
    }
    actions.extend(track.items())
    
    # Item/media actions
    item = {
        40029: "Edit: Undo",
        40030: "Edit: Redo",
        40058: "Edit: Copy items/tracks",
        40057: "Edit: Cut items/tracks",
        40058: "Edit: Paste items/tracks",
        40006: "Item: Remove items",
        40108: "Item: Split items at cursor",
        40061: "Item: Split items at time selection",
        40012: "Item: Select all items",
        40289: "Item: Unselect all items",
        40034: "Item: Group items",
        40033: "Item: Remove items from group",
        40718: "Item: Select all items on selected tracks in current time selection",
        40421: "Item: Select all items in track",
        40176: "Item: Glue items",
    }
    actions.extend(item.items())
    
    # Envelope/automation actions
    envelope = {
        40063: "Envelope: Show all track envelopes",
        40406: "Envelope: Toggle track volume envelope visible",
        40407: "Envelope: Toggle track pan envelope visible",
        40867: "Envelope: Clear all automation",
        40333: "Envelope: Toggle automation latch mode",
        40070: "Envelope: Delete all selected automation items",
    }
    actions.extend(envelope.items())
    
    # View/zoom actions
    view = {
        40110: "View: Zoom in horizontally",
        40111: "View: Zoom out horizontally",
        40112: "View: Zoom in vertically",
        40113: "View: Zoom out vertically",
        40295: "View: Zoom out project",
        1012: "View: Zoom to selected items",
        40031: "View: Toggle mixer visible",
    }
    actions.extend(view.items())
    
    # Markers/regions
    markers = {
        40157: "Markers: Insert marker at current position",
        40174: "Markers: Insert region from time selection",
        40613: "Markers: Go to previous marker",
        40614: "Markers: Go to next marker",
    }
    actions.extend(markers.items())
    
    # Time selection
    time = {
        40290: "Time selection: Set start point",
        40291: "Time selection: Set end point",
        40020: "Time selection: Remove time selection",
        40625: "Time selection: Select all items in time selection",
    }
    actions.extend(time.items())
    
    # Master track
    master = {
        40075: "Master: Show master track",
        40076: "Master: Hide master track",
    }
    actions.extend(master.items())
    
    return sorted(set(actions), key=lambda x: x[0])

def save_synthetic_actions():
    """Save synthetic actions to file"""
    actions = generate_synthetic_actions()
    
    output_file = r"C:\Users\moosb\AIAGENT DAW\reaper_actions_synthetic.txt"
    
    with open(output_file, 'w') as f:
        f.write("# Synthetic Reaper Action Descriptions\n")
        f.write("# Generated based on common action patterns\n")
        f.write("# Format: ActionID|Description\n\n")
        
        for action_id, description in actions:
            f.write(f"{action_id}|{description}\n")
    
    print(f"✅ Generated {len(actions)} synthetic action descriptions")
    print(f"💾 Saved to: {output_file}")
    print(f"\nSample actions:")
    for action_id, description in actions[:10]:
        print(f"  {action_id}: {description}")

if __name__ == "__main__":
    save_synthetic_actions()

