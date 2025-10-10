# FL Studio AI Agent Controller
# Place this file in: Documents\Image-Line\FL Studio\Settings\Hardware\
# name=AI Agent

import mixer
import playlist
import transport
import ui
import device
import channels
import patterns
import json
import os

# Command file path - external script writes commands here
COMMAND_FILE = r"C:\Users\moosb\AIAGENT DAW\fl_commands.json"

# Global state
last_check = 0

def OnInit():
    """Called when FL Studio starts"""
    print("AI Agent FL Studio Controller Loaded!")
    ui.setHintMsg("AI Agent Controller Active")

def OnIdle():
    """Called regularly by FL Studio"""
    global last_check
    
    # Check command file every ~100ms
    last_check += 1
    if last_check < 10:
        return
    last_check = 0
    
    # Check if command file exists
    if not os.path.exists(COMMAND_FILE):
        return
        
    try:
        # Read command
        with open(COMMAND_FILE, 'r') as f:
            command = json.load(f)
        
        # Delete file immediately
        os.remove(COMMAND_FILE)
        
        # Execute command
        execute_command(command)
        
    except Exception as e:
        print(f"Error processing command: {e}")

def execute_command(command):
        """Execute FL Studio command"""
        cmd_type = command.get("type")
        
        if cmd_type == "transport":
            action = command.get("action")
            if action == "play":
                transport.start()
                print("▶️ Playing")
            elif action == "stop":
                transport.stop()
                print("⏹️ Stopped")
            elif action == "record":
                transport.record()
                print("⏺️ Recording")
                
        elif cmd_type == "mixer":
            track = command.get("track", 0)
            param = command.get("param")
            value = command.get("value")
            
            if param == "volume":
                mixer.setTrackVolume(track, value)
                print(f"🔊 Track {track} volume → {value}")
            elif param == "pan":
                mixer.setTrackPan(track, value)
                print(f"↔️ Track {track} pan → {value}")
            elif param == "mute":
                current = mixer.isTrackMuted(track)
                mixer.muteTrack(track)
                print(f"🔇 Track {track} mute toggled")
                
        elif cmd_type == "automation":
            track = command.get("track", 0)
            param = command.get("param", "volume")
            points = command.get("points", [])
            
            print(f"📈 Creating automation on track {track}")
            for point in points:
                time_pos = point.get("time", 0)
                value = point.get("value", 0.8)
                # Note: FL Studio automation clips are complex
                # This is simplified - would need more work for real automation
                print(f"  Point: {time_pos}s → {value}")
                
        elif cmd_type == "playlist":
            action = command.get("action")
            if action == "goto":
                pos = command.get("position", 0)
                transport.setPlaybackPos(pos)
                print(f"⏩ Jump to {pos}s")
                
        else:
            print(f"Unknown command type: {cmd_type}")

def OnDeInit():
    """Called when FL Studio closes"""
    print("AI Agent Controller Unloaded")

def OnMidiMsg(event):
    """Handle MIDI messages - not used but required"""
    event.handled = False

