#!/usr/bin/env python3
"""
Test script for cloud agent wrapper
"""

import json
from cloud_agent_wrapper import execute_user_command_cloud, update_reaper_state

def test_cloud_agent():
    """Test the cloud agent with REAL REAPER state"""
    
    # Load REAL REAPER state from your actual files
    import json
    
    # Load from reaper_state.json
    with open("reaper_state.json", "r") as f:
        real_state = json.load(f)
    
    # Parse the detailed state from reaper_state.txt
    with open("reaper_state.txt", "r") as f:
        state_text = f.read()
    
    # Extract track info from the text format
    track_list = []
    lines = state_text.split('\n')
    current_track = None
    
    for line in lines:
        if line.startswith('--- Track '):
            # Extract track number and name
            parts = line.split(': ')
            if len(parts) >= 2:
                track_num = int(parts[0].split(' ')[2])
                track_name = parts[1].replace(' ---', '')
                current_track = {"num": track_num, "name": track_name, "volume_db": 0.0, "fx": []}
                track_list.append(current_track)
        elif current_track and 'Volume:' in line:
            # Extract volume
            vol_match = line.split('Volume: ')[1].split(' dB')[0]
            try:
                current_track["volume_db"] = float(vol_match)
            except:
                pass
        elif current_track and 'FX Chain:' in line:
            # Extract FX info
            if 'empty' not in line:
                current_track["fx"] = [{"name": "Unknown FX"}]
    
    # Build complete real state
    real_state.update({
        "track_list": track_list,
        "state_text": state_text
    })
    
    print(f"🎵 Using REAL REAPER state: {real_state['tracks']} tracks")
    for track in track_list[:3]:  # Show first 3 tracks
        print(f"   Track {track['num']}: {track['name']} ({track['volume_db']}dB)")
    
    # Update state for session
    update_reaper_state("test_session", real_state)
    
    # Test with REAL commands that match your actual tracks
    test_commands = [
        "add reverb to The Weeknd track",
        "make the vocals louder", 
        "add compression to track 1"
    ]
    
    for i, command in enumerate(test_commands):
        print(f"\n🧪 Test {i+1}: '{command}'")
        
        result = execute_user_command_cloud(
            user_input=command,
            session_id="test_session"
        )
        
        print(f"   Result: {result['status']} - {result['message']}")
        
        # Get commands that were generated
        from cloud_agent_wrapper import get_queued_commands
        commands = get_queued_commands("test_session")
        print(f"   Commands: {commands}")
        
        if commands:
            print(f"   ✅ SUCCESS: Generated {len(commands)} command(s)")
        else:
            print(f"   ❌ FAILED: No commands generated")
        
        # Clear commands for next test
        from cloud_agent_wrapper import clear_commands
        clear_commands("test_session")
    
    print("\n🎉 Cloud agent test completed!")
    return True

if __name__ == "__main__":
    test_cloud_agent()
