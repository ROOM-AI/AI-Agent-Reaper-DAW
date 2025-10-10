import json
import time
from openai import OpenAI

# Initialize OpenAI
client = OpenAI(api_key="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")

COMMAND_FILE = r"C:\Users\moosb\AIAGENT DAW\fl_commands.json"

def send_fl_command(command):
    """Send command to FL Studio by writing to file"""
    try:
        with open(COMMAND_FILE, 'w') as f:
            json.dump(command, f)
        time.sleep(0.1)  # Give FL Studio time to process
        return True
    except Exception as e:
        print(f"Error sending command: {e}")
        return False

def ask_ai(user_input):
    """Ask OpenAI to interpret user's intent for FL Studio"""
    
    system_prompt = """You are an AI that controls FL Studio DAW.

Available commands:

TRANSPORT:
{"type": "transport", "action": "play"} - start playback
{"type": "transport", "action": "stop"} - stop playback
{"type": "transport", "action": "record"} - start recording

MIXER:
{"type": "mixer", "track": 0, "param": "volume", "value": 0.8} - set track volume (0.0 to 1.0)
{"type": "mixer", "track": 0, "param": "pan", "value": 0.0} - set pan (-1.0 left to 1.0 right)
{"type": "mixer", "track": 0, "param": "mute"} - toggle mute

AUTOMATION:
{"type": "automation", "track": 0, "param": "volume", "points": [
  {"time": 16, "value": 0.5},
  {"time": 32, "value": 1.0}
]} - create automation points

PLAYLIST:
{"type": "playlist", "action": "goto", "position": 16} - jump to position (in seconds)

User will describe what they want. Respond with a JSON object with a "commands" array.

Examples:
User: "start playing"
Response: {"commands": [{"type": "transport", "action": "play"}]}

User: "set mixer track 1 volume to 50%"
Response: {"commands": [{"type": "mixer", "track": 1, "param": "volume", "value": 0.5}]}

User: "drop volume to 50% from second 16 to 32 on track 1"
Response: {"commands": [
  {"type": "automation", "track": 1, "param": "volume", "points": [
    {"time": 16, "value": 0.5},
    {"time": 32, "value": 1.0}
  ]}
]}

Only respond with valid JSON. No explanation."""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )
    
    return response.choices[0].message.content.strip()

def execute_user_command(user_input):
    """Main function: take user input, get AI decision, execute commands"""
    print(f"\n🎤 User: {user_input}")
    
    # Ask AI what to do
    print("🤖 Asking AI...")
    ai_response = ask_ai(user_input)
    print(f"💭 AI response: {ai_response}")
    
    # Parse AI response
    try:
        response_data = json.loads(ai_response)
        commands = response_data.get("commands", [])
    except json.JSONDecodeError:
        print("❌ AI didn't return valid JSON")
        return
    
    # Execute each command
    print(f"\n⚡ Executing {len(commands)} command(s)...")
    for i, command in enumerate(commands, 1):
        cmd_type = command.get("type", "unknown")
        print(f"  {i}. {cmd_type.upper()}: {command}")
        success = send_fl_command(command)
        if success:
            print(f"     ✅ Sent to FL Studio")
        else:
            print(f"     ❌ Failed")
        time.sleep(0.2)  # Small delay between commands
    
    print("\n✨ Done!\n")

# Run it
if __name__ == "__main__":
    print("=" * 60)
    print("AI Agent for FL Studio")
    print("=" * 60)
    print("\nMake sure:")
    print("1. FL Studio is running")
    print("2. fl_studio_controller.py is installed in FL Studio")
    print("3. FL Studio has been restarted after installing the script")
    print("=" * 60)
    
    # Test command
    execute_user_command("start playing the track")
    
    # Uncomment to make it interactive:
    # while True:
    #     user_input = input("\n💬 You: ")
    #     if user_input.lower() in ["quit", "exit"]:
    #         break
    #     execute_user_command(user_input)

