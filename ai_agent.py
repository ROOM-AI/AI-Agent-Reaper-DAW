import requests
import json
from openai import OpenAI
import os

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def load_reaper_actions():
    """Load all available Reaper actions from file"""
    actions = {}
    with open("reaper_actions.txt", "r") as f:
        for line in f:
            if "|" in line:
                action_id, description = line.strip().split("|", 1)
                actions[action_id] = description
    return actions


def send_reaper_command(action_id):
    """Send command to Reaper via web API"""
    try:
        response = requests.get(f"http://localhost:8080/_/{action_id}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending command {action_id}: {e}")
        return False


def send_reaper_api_command(command):
    """Send raw API command to Reaper (like SET/TRACK/1/VOL/0.5)"""
    try:
        url = f"http://localhost:8080/_/{command}"
        response = requests.get(url)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending API command {command}: {e}")
        return False


def ask_ai(user_input, actions_list):
    """Ask OpenAI to figure out which Reaper actions to execute"""

    # Format actions for AI
    actions_text = "\n".join([f"{aid}: {desc}" for aid, desc in actions_list.items()])

    system_prompt = f"""You are an AI that controls Reaper DAW. 

Available Reaper actions:
{actions_text}

You can also use these Web API commands:
- SET/TRACK/{{track}}/VOL/{{value}} - set track volume (0.0 to 2.0, where 1.0 is 0dB)
- SET/TRACK/{{track}}/PAN/{{value}} - set track pan (-1.0 to 1.0)
- SET/TRACK/{{track}}/MUTE/-1 - toggle mute
- SET/TRACK/{{track}}/SOLO/-1 - toggle solo
- SET/POS_STR/{{time}} - move playhead to time (format: "16.0" for 16 seconds)
- SET/TRACK/{{track}}/P_NAME/{{name}} - rename track

The user will describe what they want. Respond with a JSON object with a "steps" array.
Each step can be:
- {{"type": "action", "id": "40044"}} for action IDs
- {{"type": "api", "command": "SET/TRACK/1/VOL/0.5"}} for API commands

Examples:
User: "start playing"
Response: {{"steps": [{{"type": "action", "id": "40044"}}]}}

User: "set track 1 volume to 50%"
Response: {{"steps": [{{"type": "api", "command": "SET/TRACK/1/VOL/0.5"}}]}}

User: "drop volume to 50% from second 16 to 32"
Response: {{"steps": [
  {{"type": "api", "command": "SET/POS_STR/16.0"}},
  {{"type": "api", "command": "SET/TRACK/1/VOL/0.5"}},
  {{"type": "api", "command": "SET/POS_STR/32.0"}},
  {{"type": "api", "command": "SET/TRACK/1/VOL/1.0"}}
]}}

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
    """Main function: take user input, get AI decision, execute actions"""
    print(f"\n🎤 User: {user_input}")

    # Load available actions
    actions = load_reaper_actions()
    print(f"📚 Loaded {len(actions)} Reaper actions")

    # Ask AI what to do
    print("🤖 Asking AI...")
    ai_response = ask_ai(user_input, actions)
    print(f"💭 AI response: {ai_response}")

    # Parse AI response
    try:
        response_data = json.loads(ai_response)
        if isinstance(response_data, list):
            # Old format - just action IDs
            steps = [{"type": "action", "id": str(aid)} for aid in response_data]
        elif isinstance(response_data, dict) and "steps" in response_data:
            # New format - steps array
            steps = response_data["steps"]
        else:
            print("❌ AI returned unexpected format")
            return
    except json.JSONDecodeError:
        print("❌ AI didn't return valid JSON")
        return

    # Execute each step
    print(f"\n⚡ Executing {len(steps)} step(s)...")
    for i, step in enumerate(steps, 1):
        step_type = step.get("type", "action")

        if step_type == "action":
            action_id = str(step.get("id", ""))
            if action_id in actions:
                desc = actions[action_id]
                print(f"  {i}. Action {action_id}: {desc}")
                success = send_reaper_command(action_id)
                if success:
                    print(f"     ✅ Success")
                else:
                    print(f"     ❌ Failed")
            else:
                print(f"  {i}. ⚠️  Unknown action ID: {action_id}")

        elif step_type == "api":
            command = step.get("command", "")
            print(f"  {i}. API command: {command}")
            success = send_reaper_api_command(command)
            if success:
                print(f"     ✅ Success")
            else:
                print(f"     ❌ Failed")

        else:
            print(f"  {i}. ⚠️  Unknown step type: {step_type}")

    print("\n✨ Done!\n")


# Run it
if __name__ == "__main__":
    # Test command - automation
    execute_user_command("drop the volume to 50% from second 16 to 32")

    # Uncomment to make it interactive:
    # while True:
    #     user_input = input("\n💬 You: ")
    #     if user_input.lower() in ["quit", "exit"]:
    #         break
    #     execute_user_command(user_input)